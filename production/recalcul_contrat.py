"""
Recalcul des primes d'un contrat corrigé dans l'Administration des contrats (demande du 2026-11-19 : « quand je fais une
modification sur la prime d'un contrat, ou une quelconque modification qui nécessite le recalcul de la prime, le recalcul
doit se faire dans tous les cas »).

Jusqu'ici l'écran écrivait chaque montant tel que saisi : une prime de garantie changée laissait le total du risque, la
prime nette, la taxe et la TTC du contrat, et sa quittance, à leurs anciennes valeurs.

Toute saisie d'un élément de prime est désormais propagée, de la garantie jusqu'à la quittance :
- garantie : taxe à son taux (stdtauxtaxegarantieproduit ; sans taux, au rapport de sa taxe enregistrée), prime annuelle
  au même rapport à la prime nette qu'avant quand elle n'est pas saisie ; FGA (2) et CEDEAO (3) jamais taxés ;
- risque (véhicule, assuré, maison...) : ses primes et sa taxe suivent l'écart de ses garanties acquises (une garantie
  cochée ou décochée compte) ; une prime nette du risque saisie est répartie sur ses garanties au prorata (plus forts
  restes : la somme tombe juste) ; risque sans garanties (Transport) : taxe au rapport de sa taxe enregistrée ;
- contrat : prime nette, prime annuelle, FGA et CEDEAO suivent l'écart des risques ; une prime nette du contrat saisie
  est répartie sur toutes les garanties ; taxe : Automobile = (prime nette hors FGA et CEDEAO + accessoire) x 14,5 % en
  une fois (taxe_auto.py) ; autres branches = la règle que suit déjà le contrat (taxes des garanties + taxe de
  l'accessoire au taux du produit, ou taxe globale au taux du produit), à défaut la taxe enregistrée corrigée des
  écarts ; client ou offre exonéré de taxes : 0 ; TTC = somme exacte ; commission au taux quand elle valait le taux ;
  accessoires du cabinet et de la compagnie au même partage (le déclencheur trg_lephare_commission_courtier applique
  ensuite le partage réglé pour la compagnie) ;
- quittance du contrat : mêmes montants (comme sp_maj_manuelle_primes), « encaissée » selon le reste (reliquat < 5 F),
  solde du client corrigé de l'écart de TTC ; refus si la TTC devient inférieure au montant déjà encaissé.

La taxe ne se saisit pas : une valeur envoyée est recalculée. Rien n'est recalculé quand aucune prime n'est touchée
(montants repris d'URANUS gardés tels quels).

Prime TTC saisie (demande du 2026-11-24 : « je veux pouvoir saisir la prime à la main ») : c'est la cible. La prime nette
qui y conduit est déduite et répartie sur les garanties acquises dont la prime n'est pas saisie (risques sans garanties :
sur les risques), la taxe restant à sa règle ; les autres saisies (accessoire, FGA, primes de garanties...) comptent
d'abord. Quand l'arrondi de la taxe empêche de tomber juste (Automobile : 1 F de saut de temps en temps), la TTC la plus
proche est retenue, au-dessous à égalité, et signalée. Prime nette et prime TTC du contrat ne se saisissent pas ensemble.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from django.db import connection, transaction

from .reste_encaissement import RELIQUAT_NEGLIGEABLE
from .taxe_auto import ID_PRODUIT_AUTO, TAUX_TAXE_AUTO, taux_taxe_auto

ID_FGA = 2
ID_CEDEAO = 3
# Composantes de prime de l'Automobile : ni taxées, ni concernées par la répartition d'une prime nette saisie
HORS_REPARTITION = (ID_FGA, ID_CEDEAO)

# Champs dont la saisie demande le recalcul
CHAMPS_GARANTIE = ("acquise", "primenette", "primeannuelle", "taxe", "idgarantie")
CHAMPS_DETAIL = ("primenette", "primeannuelle", "taxeenregistrement", "fga")
CHAMPS_CONTRAT = ("primenette", "primeannuelle", "accessoire", "accessoiregestionnaire", "taxe", "fga", "cedeao", "primettc")
# Taux de commission seul : la commission est recalculée, pas la prime
# Montants de l'en-tête relus après l'enregistrement (déclencheurs compris)
MONTANTS_CONTRAT = (
    "primeannuelle", "primenette", "accessoire", "accessoirecompagnie", "accessoireintermediaire",
    "accessoiregestionnaire", "taxe", "fga", "cedeao", "primettc", "commissionintermediaire",
)
MONTANTS_DETAIL = ("primenette", "primeannuelle", "taxeenregistrement", "fga")
MONTANTS_GARANTIE = ("primenette", "primeannuelle", "taxe")
MONTANTS_QUITTANCE = ("primenette", "accessoire", "taxe", "primettc")

ZERO = Decimal("0")


class ErreurRecalcul(ValueError):
    """Recalcul impossible : rien n'est enregistré."""


class PrimeNegative(ErreurRecalcul):
    """Prime nette répartie qui deviendrait négative."""


def _d(valeur):
    if valeur is None or valeur == "":
        return ZERO
    return valeur if isinstance(valeur, Decimal) else Decimal(str(valeur))


def _franc(valeur):
    return _d(valeur).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _identifiant(valeur):
    """Clé étrangère validée par le sérialiseur (objet) ou identifiant brut."""
    return getattr(valeur, "pk", valeur)


def _montant_texte(valeur):
    return f"{int(_franc(valeur)):,}".replace(",", " ")


def demande_recalcul(saisies):
    """Vrai si la saisie touche un élément de prime (garantie, risque ou contrat)."""
    return bool(
        set(saisies.get("contrat", {})) & set(CHAMPS_CONTRAT)
        or any(set(s) & set(CHAMPS_DETAIL) for s in saisies.get("details", {}).values())
        or any(set(s) & set(CHAMPS_GARANTIE) for s in saisies.get("garanties", {}).values())
    )


@dataclass
class Contexte:
    idproduit: int
    exonere: bool = False
    taux_garanties: dict = field(default_factory=dict)
    taux_produit: Decimal | None = None
    taux_auto: Decimal = TAUX_TAXE_AUTO
    # Automobile : CEDEAO comprise dans la prime nette enregistrée (prime calculée) ou à part (prime imposée)
    cedeao_incluse: bool = True

    @property
    def auto(self):
        return self.idproduit == ID_PRODUIT_AUTO


# ------------------------------------------------------------------ règles de calcul (sans base de données)
def repartir(cible, poids):
    """Répartit le montant cible (arrondi au franc) entre les éléments [(clé, poids)] au prorata des poids, en francs
    entiers, le reliquat aux plus forts restes : la somme tombe juste. Poids tous nuls : parts égales."""
    cible = _franc(cible)
    if not poids:
        return {}
    total = sum((p for _, p in poids), ZERO)
    if total == 0:
        poids = [(cle, Decimal(1)) for cle, _ in poids]
        total = Decimal(len(poids))
    brutes = [(cle, cible * p / total) for cle, p in poids]
    parts = {cle: b.to_integral_value(rounding=ROUND_FLOOR) for cle, b in brutes}
    reste = int(cible - sum(parts.values(), ZERO))
    for cle, _ in sorted(brutes, key=lambda cb: (parts[cb[0]] - cb[1], -cb[1]))[:reste]:
        parts[cle] += 1
    return parts


def _au_rapport(prime, ancienne_prime, ancienne_taxe):
    """Taxe au taux que suivait la taxe enregistrée : taux arrondi au centième de point s'il y retombe (25 % pour
    75 748 F sur 302 990 F), sinon rapport exact."""
    taux = (ancienne_taxe * 100 / ancienne_prime).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if abs(ancienne_taxe - _franc(ancienne_prime * taux / 100)) <= 1:
        return _franc(_d(prime) * taux / 100)
    return _franc(_d(prime) * ancienne_taxe / ancienne_prime)


def taxe_garantie(ctx, idgarantie, prime, ancienne_prime=None, ancienne_taxe=None):
    """
    Taxe d'une garantie, selon la règle qu'elle suivait : son taux (stdtauxtaxegarantieproduit) si sa taxe enregistrée
    y retombe, sinon le rapport de sa taxe enregistrée (ex. MRH : dommages électriques taxés à 25 % comme l'incendie,
    14,5 % au barème) ; garantie jamais taxée : 0. Sans historique (garantie qui vient d'être cochée ou changée) : son
    taux, sinon celui du produit.
    """
    if ctx.exonere or (ctx.auto and idgarantie in HORS_REPARTITION):
        return ZERO
    taux = ctx.taux_garanties.get(idgarantie)
    ancienne_prime, ancienne_taxe = _d(ancienne_prime), _d(ancienne_taxe)
    if ancienne_prime and ancienne_taxe:
        if taux is not None and abs(ancienne_taxe - _franc(ancienne_prime * _d(taux) / 100)) <= 1:
            return _franc(_d(prime) * _d(taux) / 100)
        return _au_rapport(prime, ancienne_prime, ancienne_taxe)
    if taux is not None:
        return _franc(_d(prime) * _d(taux) / 100)
    if ancienne_prime:
        return ZERO
    if ctx.taux_produit is not None:
        return _franc(_d(prime) * ctx.taux_produit / 100)
    return ZERO


def taxe_risque_sans_garantie(ctx, prime, ancienne_prime, ancienne_taxe):
    """Risque sans garanties (Transport) : taxe au rapport de sa taxe enregistrée (taux du mode), sinon au taux du produit."""
    if ctx.exonere:
        return ZERO
    if _d(ancienne_prime):
        return _au_rapport(prime, _d(ancienne_prime), _d(ancienne_taxe)) if _d(ancienne_taxe) else ZERO
    if ctx.taux_produit is not None:
        return _franc(_d(prime) * ctx.taux_produit / 100)
    return ZERO


def prime_annuelle(nouvelle_prime, ancienne_prime, ancienne_annuelle):
    """Prime annuelle non saisie : même rapport à la prime nette qu'avant (prorata de la durée)."""
    if _d(ancienne_prime):
        return _franc(_d(nouvelle_prime) * _d(ancienne_annuelle) / _d(ancienne_prime))
    return _d(nouvelle_prime)


def taxe_contrat_hors_auto(ctx, avant, taxes_risques_avant, taxes_risques, prime_nette, accessoire):
    """Taxe du contrat hors Automobile, selon la règle que suivait déjà le contrat."""
    if ctx.exonere:
        return ZERO
    taxe_avant = _d(avant["taxe"])
    ecart_risques = taxes_risques - taxes_risques_avant
    taux = ctx.taux_produit
    if taux is None:
        return _franc(taxe_avant + ecart_risques)
    taxe_accessoire_avant = _franc(_d(avant["accessoire"]) * taux / 100)
    taxe_accessoire = _franc(accessoire * taux / 100)
    # Taxes des garanties + taxe de l'accessoire (sp_finalisation_devis)
    if abs(taxe_avant - (taxes_risques_avant + taxe_accessoire_avant)) <= 1:
        return _franc(taxes_risques + taxe_accessoire)
    # Taxe globale sur la prime nette et l'accessoire (prime imposée IA, RC)
    if abs(taxe_avant - _franc((_d(avant["primenette"]) + _d(avant["accessoire"])) * taux / 100)) <= 1:
        return _franc((prime_nette + accessoire) * taux / 100)
    return _franc(taxe_avant + ecart_risques + taxe_accessoire - taxe_accessoire_avant)


def commission_au_taux(avant, sc, ht_avant, ht):
    """Commission recalculée sur la prime HT quand elle valait le taux (une commission convenue autrement est gardée) ;
    None si elle est saisie ou si elle ne suivait pas le taux."""
    taux_avant = _d(avant.get("taux_commission"))
    taux = _d(sc["taux_commission"]) if "taux_commission" in sc else taux_avant
    commission = _d(avant.get("commissionintermediaire"))
    if "commissionintermediaire" in sc or taux <= 0:
        return None
    au_taux = (taux_avant == 0 and commission == 0) or any(
        abs(commission - _franc(base * taux_avant / 100)) <= 1 for base in (ht_avant, _d(avant["primenette"]))
    )
    return _franc(ht * taux / 100) if au_taux else None


def calculer(ctx, avant, saisies):
    """
    Montants finaux d'un contrat après saisie.

    avant : {"contrat": {champ: valeur}, "details": {iddetail: {champ: valeur, "garanties": {idgarantie_ligne: {...}}}}},
            valeurs enregistrées avant la saisie (garanties : idgarantie, acquise, primenette, primeannuelle, taxe).
    saisies : {"contrat": {...}, "details": {iddetail: {...}}, "garanties": {idligne: {...}}}, valeurs saisies.
    Retour : {"contrat": {...}, "details": {iddetail: {...}}, "garanties": {idligne: {...}}} des lignes dont un montant
    change ou a été saisi, plus "avertissements" quand la prime TTC saisie ne tombe pas juste ; None si aucune prime
    n'est touchée. Taux de commission seul saisi : la commission seule.
    """
    sc = saisies.get("contrat", {})
    if "primettc" not in sc:
        return _calculer(ctx, avant, saisies)
    if "primenette" in sc:
        raise ErreurRecalcul(
            "Saisissez la prime nette du contrat ou sa prime TTC, pas les deux : l'une se déduit de l'autre."
        )
    cible = _franc(sc["primettc"])
    if cible <= 0:
        raise ErreurRecalcul("La prime TTC saisie doit être supérieure à zéro.")
    saisies = {**saisies, "contrat": {cle: v for cle, v in sc.items() if cle not in ("primettc", "taxe")}}
    # Autres saisies seules : une saisie impossible garde son propre message
    resultat = _calculer(ctx, avant, saisies, ZERO)
    base = (resultat, _d(resultat["contrat"]["primettc"]))
    essais = {ZERO: base}

    def essai(ajustement):
        """TTC obtenue avec cet écart de prime nette réparti (None : une prime deviendrait négative)."""
        if ajustement not in essais:
            try:
                resultat = _calculer(ctx, avant, saisies, ajustement)
                essais[ajustement] = (resultat, _d(resultat["contrat"]["primettc"]))
            except PrimeNegative:
                essais[ajustement] = None
        return essais[ajustement]

    ecart = cible - base[1]
    # TTC gagnée par franc de prime nette (taxe comprise), mesurée sur l'écart (réduit de moitié tant qu'il rendrait une
    # prime négative)
    pente = Decimal(1)
    sonde = ecart
    while sonde:
        mesure = essai(sonde)
        if mesure is not None:
            if mesure[1] != base[1]:
                pente = (mesure[1] - base[1]) / sonde
            break
        sonde = Decimal(int(sonde / 2))
    ajustement, possible = _franc(ecart / pente), ZERO
    for _ in range(8):
        trouve = essai(ajustement)
        if trouve is None:
            # Au-delà de ce qu'admettent les primes : retour à mi-chemin du dernier essai possible
            recul = Decimal(int((ajustement - possible) / 2))
            if not recul:
                break
            ajustement = possible + recul
            continue
        possible = ajustement
        if trouve[1] == cible:
            break
        ajustement += _franc((cible - trouve[1]) / pente) or (1 if trouve[1] < cible else -1)
    # Arrondis des taxes : voisins essayés ; la TTC exacte d'abord, sinon la plus proche, au-dessous à égalité
    if (essai(ajustement) or (None, None))[1] != cible:
        for voisin in range(-3, 4):
            essai(ajustement + voisin)
    valides = [(a, e) for a, e in essais.items() if e is not None]
    _, (resultat, ttc) = min(valides, key=lambda ae: (abs(ae[1][1] - cible), ae[1][1] > cible, abs(ae[0] - ajustement)))
    if abs(ttc - cible) > 2:
        if ttc > cible:
            raise ErreurRecalcul(
                f"La prime TTC saisie ({_montant_texte(cible)} F) est trop basse : elle ne couvre pas les accessoires, "
                "les frais et les primes déjà fixés."
            )
        raise ErreurRecalcul(
            f"La prime TTC saisie ({_montant_texte(cible)} F) ne peut pas être atteinte : {_montant_texte(ttc)} F au plus près."
        )
    if ttc != cible:
        resultat["avertissements"] = [
            f"La prime TTC saisie ({_montant_texte(cible)} F) ne peut pas tomber juste avec l'arrondi de la taxe : "
            f"{_montant_texte(ttc)} F retenus."
        ]
    return resultat


def _calculer(ctx, avant, saisies, ajustement=None):
    """Calcul de calculer() ; ajustement : écart de prime nette à répartir pour atteindre une prime TTC saisie (None :
    pas de TTC saisie)."""
    sc = saisies.get("contrat", {})
    c = avant["contrat"]
    if ajustement is None and not demande_recalcul(saisies):
        if "taux_commission" not in sc:
            return None
        ht = _d(c["primenette"])
        if ctx.auto:
            ht -= _d(c["fga"]) + (_d(c["cedeao"]) if ctx.cedeao_incluse else ZERO)
        commission = commission_au_taux(c, sc, ht, ht)
        return {"contrat": {} if commission is None else {"commissionintermediaire": commission}, "details": {}, "garanties": {}}
    sd = saisies.get("details", {})
    sg = saisies.get("garanties", {})
    details = avant["details"]

    # 1. Garanties telles que saisies, taxe recalculée
    garanties = {}
    for det in details.values():
        for idg, g in det["garanties"].items():
            s = sg.get(idg, {})
            n = dict(g)
            if "acquise" in s:
                n["acquise"] = bool(s["acquise"])
            if "idgarantie" in s:
                n["idgarantie"] = _identifiant(s["idgarantie"])
            if "primeannuelle" in s:
                n["primeannuelle"] = _d(s["primeannuelle"])
            if "primenette" in s:
                n["primenette"] = _d(s["primenette"])
                if "primeannuelle" not in s:
                    n["primeannuelle"] = prime_annuelle(n["primenette"], g["primenette"], g["primeannuelle"])
            if set(s) & {"acquise", "idgarantie", "primenette", "taxe"}:
                # Taxe enregistrée d'une garantie non acquise ou d'une autre garantie : sans valeur de référence
                if g["acquise"] and n["idgarantie"] == g["idgarantie"]:
                    n["taxe"] = taxe_garantie(ctx, n["idgarantie"], n["primenette"], g["primenette"], g["taxe"])
                else:
                    n["taxe"] = taxe_garantie(ctx, n["idgarantie"], n["primenette"])
            garanties[idg] = n

    # Risques sans garanties : prime nette saisie telle quelle
    primes_libres = {
        iddet: _d(sd.get(iddet, {}).get("primenette", det["primenette"]))
        for iddet, det in details.items() if not det["garanties"]
    }
    risques_garanties_saisies = {
        iddet for iddet, det in details.items()
        if any(set(sg.get(idg, {})) & set(CHAMPS_GARANTIE) for idg in det["garanties"])
    }
    risques_saisis = {iddet for iddet, s in sd.items() if set(s) & set(CHAMPS_DETAIL)}

    def unites_de(risques, exclues=frozenset()):
        """Garanties acquises (hors FGA et CEDEAO, hors garanties exclues) des risques, ou risques sans garanties,
        avec leurs primes nettes."""
        unites = []
        for iddet in risques:
            det = details[iddet]
            if det["garanties"]:
                unites += [
                    (("g", idg), _d(garanties[idg]["primenette"])) for idg in det["garanties"]
                    if idg not in exclues and garanties[idg]["acquise"]
                    and garanties[idg]["idgarantie"] not in HORS_REPARTITION
                ]
            else:
                unites.append((("r", iddet), primes_libres[iddet]))
        return unites

    def repartir_prime(ecart, risques, libelle, exclues=frozenset(), vide=None):
        """Prime nette saisie au-dessus des garanties : l'écart est réparti sur les garanties acquises (hors FGA et
        CEDEAO, hors garanties exclues) des risques, ou sur les risques sans garanties, au prorata de leurs primes."""
        unites = unites_de(risques, exclues)
        if not unites:
            raise ErreurRecalcul(
                vide or f"Aucune garantie acquise sur laquelle répartir la prime nette {libelle} : cochez au moins une garantie."
            )
        total = sum((p for _, p in unites), ZERO)
        if total + ecart < 0:
            raise PrimeNegative(f"La prime nette {libelle} deviendrait négative sur ses garanties.")
        for (nature, ident), nouvelle in repartir(total + ecart, unites).items():
            if nature == "r":
                primes_libres[ident] = nouvelle
                continue
            g = garanties[ident]
            if nouvelle == _d(g["primenette"]):
                continue
            g["primeannuelle"] = prime_annuelle(nouvelle, g["primenette"], g["primeannuelle"])
            g["taxe"] = taxe_garantie(ctx, g["idgarantie"], nouvelle, g["primenette"], g["taxe"])
            g["primenette"] = nouvelle

    # 2. Prime nette d'un risque saisie sans toucher à ses garanties : répartie sur elles
    for iddet, s in sd.items():
        det = details.get(iddet)
        if det and "primenette" in s and det["garanties"] and iddet not in risques_garanties_saisies:
            ecart = _d(s["primenette"]) - _d(det["primenette"])
            if ecart:
                repartir_prime(ecart, [iddet], "du risque")

    # 3. Prime nette du contrat saisie sans toucher aux risques : répartie sur toutes les garanties
    if "primenette" in sc and details and not risques_garanties_saisies and not risques_saisis:
        ecart = _d(sc["primenette"]) - _d(c["primenette"])
        if "fga" in sc:
            ecart -= _d(sc["fga"]) - _d(c["fga"])
        if ctx.auto and ctx.cedeao_incluse and "cedeao" in sc:
            ecart -= _d(sc["cedeao"]) - _d(c["cedeao"])
        if ecart:
            repartir_prime(ecart, list(details), "du contrat")

    # 3 bis. Prime TTC saisie : écart de prime nette réparti sur les garanties et les risques dont la prime n'est pas
    # saisie. Garanties et risques tous à 0 F (contrats repris d'URANUS, prime portée par l'en-tête seul) : l'écart porte
    # sur la prime nette de l'en-tête, comme pour un contrat sans risque
    entete_seule = not details
    if ajustement and details:
        risques_libres = [iddet for iddet in details if "primenette" not in sd.get(iddet, {})]
        exclues = {idg for idg, s in sg.items() if "primenette" in s}
        unites = unites_de(risques_libres, exclues)
        entete_seule = bool(unites) and not any(p for _, p in unites)
        if not entete_seule:
            repartir_prime(
                ajustement, risques_libres, "du contrat", exclues=exclues,
                vide="Toutes les primes sont saisies : aucune garantie acquise ne peut recevoir l'écart de prime TTC. "
                     "Rétablissez une prime de garantie ou de risque.",
            )

    # 4. Risques : écarts de leurs garanties acquises
    resultat = {"contrat": {}, "details": {}, "garanties": {}}
    ecarts = {"primenette": ZERO, "primeannuelle": ZERO, "taxe": ZERO, "fga": ZERO, "cedeao_garanties": ZERO,
              "fga_garanties": ZERO}
    taxes_risques_avant = taxes_risques = ZERO

    def somme(lignes, cle, idgarantie=None):
        return sum((_d(g[cle]) for g in lignes if idgarantie is None or g["idgarantie"] == idgarantie), ZERO)

    for iddet, det in details.items():
        s = sd.get(iddet, {})
        if det["garanties"]:
            anciennes = [g for g in det["garanties"].values() if g["acquise"]]
            nouvelles = [garanties[idg] for idg in det["garanties"] if garanties[idg]["acquise"]]
            pn = _d(det["primenette"]) + somme(nouvelles, "primenette") - somme(anciennes, "primenette")
            pa = _d(det["primeannuelle"]) + somme(nouvelles, "primeannuelle") - somme(anciennes, "primeannuelle")
            tx = _d(det["taxeenregistrement"]) + somme(nouvelles, "taxe") - somme(anciennes, "taxe")
            if ctx.auto:
                ecarts["cedeao_garanties"] += somme(nouvelles, "primenette", ID_CEDEAO) - somme(anciennes, "primenette", ID_CEDEAO)
                ecarts["fga_garanties"] += somme(nouvelles, "primenette", ID_FGA) - somme(anciennes, "primenette", ID_FGA)
            for idg, g in det["garanties"].items():
                n = garanties[idg]
                if idg in sg or any(_d(n[cle]) != _d(g[cle]) for cle in MONTANTS_GARANTIE):
                    resultat["garanties"][idg] = {cle: _d(n[cle]) for cle in MONTANTS_GARANTIE}
        else:
            pn = primes_libres[iddet]
            if "primeannuelle" in s:
                pa = _d(s["primeannuelle"])
            elif pn != _d(det["primenette"]):
                pa = prime_annuelle(pn, det["primenette"], det["primeannuelle"])
            else:
                pa = _d(det["primeannuelle"])
            if pn != _d(det["primenette"]) or "taxeenregistrement" in s:
                tx = taxe_risque_sans_garantie(ctx, pn, det["primenette"], det["taxeenregistrement"])
            else:
                tx = _d(det["taxeenregistrement"])
        fga = _d(s["fga"]) if "fga" in s else _d(det["fga"])
        final = {"primenette": pn, "primeannuelle": pa, "taxeenregistrement": tx, "fga": fga}
        if iddet in sd or any(final[cle] != _d(det[cle]) for cle in MONTANTS_DETAIL):
            resultat["details"][iddet] = final
        ecarts["primenette"] += pn - _d(det["primenette"])
        ecarts["primeannuelle"] += pa - _d(det["primeannuelle"])
        ecarts["fga"] += fga - _d(det["fga"])
        taxes_risques_avant += _d(det["taxeenregistrement"])
        taxes_risques += tx

    # 5. Contrat
    accessoire = _d(sc["accessoire"]) if "accessoire" in sc else _d(c["accessoire"])
    gestion = _d(sc["accessoiregestionnaire"]) if "accessoiregestionnaire" in sc else _d(c["accessoiregestionnaire"])
    # Contrat sans risques ou à prime portée par l'en-tête seul : l'écart de prime TTC porte sur sa prime nette
    sans_risque = ajustement if ajustement and entete_seule else ZERO
    if ctx.auto:
        fga = _d(sc["fga"]) if "fga" in sc else _d(c["fga"]) + ecarts["fga"] + ecarts["fga_garanties"]
        cedeao = _d(sc["cedeao"]) if "cedeao" in sc else _d(c["cedeao"]) + ecarts["cedeao_garanties"]
        ht_avant = _d(c["primenette"]) - _d(c["fga"]) - (_d(c["cedeao"]) if ctx.cedeao_incluse else ZERO)
        ht = ht_avant + ecarts["primenette"] - ecarts["cedeao_garanties"] - ecarts["fga_garanties"] + sans_risque
        if sans_risque and ht < 0:
            raise PrimeNegative("La prime nette du contrat deviendrait négative.")
        prime_nette = ht + fga + (cedeao if ctx.cedeao_incluse else ZERO)
        taxe = ZERO if ctx.exonere else _franc((ht + accessoire) * ctx.taux_auto / 100)
        ttc = prime_nette + accessoire + taxe + gestion + (ZERO if ctx.cedeao_incluse else cedeao)
    else:
        fga, cedeao = _d(c["fga"]), _d(c["cedeao"])
        if details:
            prime_nette = _d(c["primenette"]) + ecarts["primenette"] + sans_risque
        else:
            prime_nette = (_d(sc["primenette"]) if "primenette" in sc else _d(c["primenette"])) + sans_risque
        if sans_risque and prime_nette < 0:
            raise PrimeNegative("La prime nette du contrat deviendrait négative.")
        ht_avant, ht = _d(c["primenette"]), prime_nette
        taxe = taxe_contrat_hors_auto(ctx, c, taxes_risques_avant, taxes_risques, prime_nette, accessoire)
        ttc = prime_nette + accessoire + taxe + gestion
    annuelle = _d(sc["primeannuelle"]) if "primeannuelle" in sc else _d(c["primeannuelle"]) + ecarts["primeannuelle"]
    final = {
        "primeannuelle": annuelle, "primenette": prime_nette, "accessoire": accessoire, "accessoiregestionnaire": gestion,
        "taxe": taxe, "fga": fga, "cedeao": cedeao, "primettc": ttc,
    }

    # Accessoires du cabinet et de la compagnie : même partage qu'avant, sauf saisie
    if accessoire != _d(c["accessoire"]) and not {"accessoirecompagnie", "accessoireintermediaire"} & set(sc):
        cabinet_avant = _d(c["accessoireintermediaire"])
        cabinet = _franc(cabinet_avant * accessoire / _d(c["accessoire"])) if _d(c["accessoire"]) else ZERO
        final["accessoireintermediaire"] = cabinet
        final["accessoirecompagnie"] = _d(c["accessoirecompagnie"]) + accessoire - _d(c["accessoire"]) - (cabinet - cabinet_avant)

    commission = commission_au_taux(c, sc, ht_avant, ht)
    if commission is not None:
        final["commissionintermediaire"] = commission

    resultat["contrat"] = final
    return resultat


# ------------------------------------------------------------------ lecture et écriture en base
def etat_contrat(contrat, saisies):
    """Montants enregistrés du contrat (avant la saisie) ; ses risques et leurs garanties si une prime est touchée."""
    from .models import ContratDetail, ContratDetGarantie

    entete = {cle: getattr(contrat, cle) for cle in MONTANTS_CONTRAT}
    entete["taux_commission"] = contrat.taux_commission
    entete["prime_imposee"] = bool(contrat.prime_imposee)
    if not demande_recalcul(saisies):
        return {"contrat": entete, "details": None}
    details = {
        d["idcontratdetail"]: {**{cle: d[cle] for cle in MONTANTS_DETAIL}, "garanties": {}}
        for d in ContratDetail.objects.filter(idcontrat=contrat).order_by("pk").values("idcontratdetail", *MONTANTS_DETAIL)
    }
    lignes = ContratDetGarantie.objects.filter(idcontratdetail__idcontrat=contrat).order_by("pk").values(
        "idcontratdetgarantie", "idcontratdetail_id", "idgarantie_id", "acquise", *MONTANTS_GARANTIE
    )
    for g in lignes:
        details[g["idcontratdetail_id"]]["garanties"][g["idcontratdetgarantie"]] = {
            "idgarantie": g["idgarantie_id"], "acquise": bool(g["acquise"]),
            **{cle: g[cle] for cle in MONTANTS_GARANTIE},
        }
    return {"contrat": entete, "details": details}


def _date(valeur):
    return valeur.date() if isinstance(valeur, datetime) else valeur


def contexte_contrat(cursor, contrat, avant, saisies):
    """Taux et conventions du contrat (après saisie : compagnie, client, date d'effet éventuellement corrigés)."""
    date_effet = _date(contrat.dateeffet)
    cursor.execute(
        "SELECT idoffre FROM stdcontratdetail WHERE idcontrat = %s ORDER BY idcontratdetail LIMIT 1", [contrat.pk]
    )
    ligne = cursor.fetchone()
    idoffre = ligne[0] if ligne else None
    # Exonération du client ou de l'offre, comme à la génération de la quittance (sp_generation_quittance)
    cursor.execute(
        """
        SELECT COALESCE((SELECT exoneredetaxes FROM stdclient WHERE idclient = %s), FALSE)
            OR COALESCE((SELECT exoneredetaxes FROM stdoffre WHERE idoffre = %s), FALSE)
        """,
        [contrat.idclient_id, idoffre],
    )
    exonere = bool(cursor.fetchone()[0])
    ids_garanties = {g["idgarantie"] for det in (avant["details"] or {}).values() for g in det["garanties"].values()}
    ids_garanties |= {
        _identifiant(s["idgarantie"]) for s in saisies.get("garanties", {}).values() if "idgarantie" in s
    }
    taux_garanties = {}
    if ids_garanties:
        cursor.execute(
            """
            SELECT DISTINCT ON (idgarantie) idgarantie, tauxtaxe FROM stdtauxtaxegarantieproduit
            WHERE idproduit = %s AND idgarantie = ANY(%s) AND COALESCE(%s::date, CURRENT_DATE) BETWEEN debutvalidite AND finvalidite
            ORDER BY idgarantie, debutvalidite DESC
            """,
            [contrat.idproduit_id, [i for i in ids_garanties if i is not None], date_effet],
        )
        taux_garanties = {i: _d(t) for i, t in cursor.fetchall() if t is not None}
    taux_produit = None
    try:
        with transaction.atomic():
            cursor.execute(
                "SELECT fn_get_taux_taxe(%s, %s, %s, COALESCE(%s::date, CURRENT_DATE))",
                [contrat.idcompagnie_id, contrat.idproduit_id, idoffre or 0, date_effet],
            )
            ligne = cursor.fetchone()
            taux_produit = _d(ligne[0]) if ligne and ligne[0] is not None else None
    except Exception:  # noqa: BLE001 - taux indisponible : la taxe de l'accessoire suit la taxe enregistrée
        taux_produit = None
    ctx = Contexte(
        idproduit=contrat.idproduit_id, exonere=exonere, taux_garanties=taux_garanties, taux_produit=taux_produit
    )
    if ctx.auto:
        ctx.taux_auto = taux_taxe_auto(cursor, date_effet)
        c = avant["contrat"]
        if _d(c["cedeao"]):
            # Même détection que fn_lephare_prime_ht : la composition qui retombe sur la TTC enregistrée
            cursor.execute(
                "SELECT public.fn_lephare_prime_ht(%s, %s, %s, %s, %s, %s, %s)",
                [c["primenette"], c["accessoire"], c["taxe"], c["fga"], c["cedeao"], c["primettc"], c["prime_imposee"]],
            )
            ht = _d(cursor.fetchone()[0])
            ctx.cedeao_incluse = abs(_d(c["primenette"]) - _d(c["fga"]) - ht - _d(c["cedeao"])) < Decimal("0.5")
        else:
            ctx.cedeao_incluse = not c["prime_imposee"]
    return ctx


def _ecrire(cursor, idcontrat, montants):
    if montants["garanties"]:
        cursor.executemany(
            "UPDATE stdcontratdetgarantie SET primenette = %s, primeannuelle = %s, taxe = %s WHERE idcontratdetgarantie = %s",
            [[m["primenette"], m["primeannuelle"], m["taxe"], idg] for idg, m in montants["garanties"].items()],
        )
    if montants["details"]:
        cursor.executemany(
            "UPDATE stdcontratdetail SET primenette = %s, primeannuelle = %s, taxeenregistrement = %s, fga = %s"
            " WHERE idcontratdetail = %s",
            [[m["primenette"], m["primeannuelle"], m["taxeenregistrement"], m["fga"], iddet]
             for iddet, m in montants["details"].items()],
        )
    entete = montants["contrat"]
    if entete:
        cursor.execute(
            f"UPDATE stdcontrat SET {', '.join(f'{cle} = %s' for cle in entete)} WHERE idcontrat = %s",
            [*entete.values(), idcontrat],
        )


def _aligner_quittance(cursor, idcontrat):
    """Quittance du contrat aux montants du contrat. Retour : (lignes recalculées, avertissements)."""
    cursor.execute(
        """
        SELECT q.idquittance, TRIM(q.numeroquittance), q.statut, q.idclient, COALESCE(q.mt_encaisse, 0), COALESCE(q.mt_regle, 0),
               q.primenette, q.accessoire, q.taxe, q.primettc, c.primenette, c.accessoire, c.taxe, c.primettc, c.taux_commission
        FROM stdcontrat c JOIN stdquittance q ON q.idquittance = c.idquittance
        WHERE c.idcontrat = %s
        """,
        [idcontrat],
    )
    ligne = cursor.fetchone()
    if not ligne:
        return [], []
    idq, numero, statut, idclient, encaisse, reverse = ligne[:6]
    avant = dict(zip(MONTANTS_QUITTANCE, ligne[6:10]))
    apres = dict(zip(MONTANTS_QUITTANCE, ligne[10:14]))
    if all(_d(avant[cle]) == _d(apres[cle]) for cle in MONTANTS_QUITTANCE):
        return [], []
    if statut == 4:
        return [], [f"La quittance {numero} est annulée : elle n'a pas été modifiée."]
    ttc = _d(apres["primettc"])
    encaisse = _d(encaisse)
    if encaisse > 0 and encaisse > ttc:
        raise ErreurRecalcul(
            f"La prime TTC recalculée ({_montant_texte(ttc)} F) est inférieure aux {_montant_texte(encaisse)} F déjà "
            f"encaissés sur la quittance {numero} : corrigez d'abord l'encaissement."
        )
    cursor.execute(
        """
        UPDATE stdquittance SET primenette = %s, accessoire = %s, taxe = %s, primettc = %s, taux_commission = %s,
               encaissee = CASE WHEN %s > 0 THEN (%s > 0 AND %s - %s < %s) ELSE encaissee END
        WHERE idquittance = %s
        """,
        [apres["primenette"], apres["accessoire"], apres["taxe"], ttc, ligne[14],
         ttc, encaisse, ttc, encaisse, RELIQUAT_NEGLIGEABLE, idq],
    )
    ecart_ttc = ttc - _d(avant["primettc"])
    if ecart_ttc and idclient:
        # Solde du client tenu par la génération des quittances (+ TTC) et les encaissements (- montant)
        cursor.execute("UPDATE stdclient SET solde = COALESCE(solde, 0) + %s WHERE idclient = %s", [ecart_ttc, idclient])
    recalcules = [
        {"Nature": "quittance", "Id": idq, "Element": f"Quittance {numero}", "Champ": cle,
         "Avant": float(_d(avant[cle])), "Apres": float(_d(apres[cle])), "Demande": None}
        for cle in MONTANTS_QUITTANCE if _d(avant[cle]) != _d(apres[cle])
    ]
    avertissements = []
    if _d(reverse) > 0:
        avertissements.append(
            f"La quittance {numero} a déjà été reversée à la compagnie pour {_montant_texte(reverse)} F : "
            "le bordereau n'est pas modifié."
        )
    return recalcules, avertissements


def _ligne(nature, ident, cle, avant, apres, saisies):
    demande = saisies.get(cle) if cle in saisies else None
    return {
        "Nature": nature, "Id": ident, "Champ": cle, "Avant": None if avant is None else float(_d(avant)),
        "Apres": None if apres is None else float(_d(apres)), "Demande": None if demande is None else float(_d(demande)),
    }


def recalculer(contrat, avant, saisies):
    """
    Après l'enregistrement des saisies (même transaction) : recalcule et écrit les montants dérivés, aligne la quittance.
    Retour : {"recalcules": [...], "avertissements": [...]}, les montants enregistrés autrement que saisis ou
    qu'avant la saisie (déclencheurs de la base compris). Lève ErreurRecalcul (la transaction est alors annulée).
    """
    recalcules, avertissements = [], []
    sc = saisies.get("contrat", {})
    prime = demande_recalcul(saisies)
    with connection.cursor() as cursor:
        contrat.refresh_from_db()
        montants = None
        if prime or "taux_commission" in sc:
            ctx = contexte_contrat(cursor, contrat, avant, saisies)
            montants = calculer(ctx, avant, saisies)
        if montants:
            avertissements += montants.get("avertissements", [])
            _ecrire(cursor, contrat.pk, montants)
            for idg, m in montants["garanties"].items():
                g = next(det["garanties"][idg] for det in avant["details"].values() if idg in det["garanties"])
                s = saisies.get("garanties", {}).get(idg, {})
                recalcules += [
                    _ligne("garantie", idg, cle, g[cle], m[cle], s) for cle in MONTANTS_GARANTIE
                    if _d(m[cle]) != _d(s[cle] if cle in s else g[cle])
                ]
            for iddet, m in montants["details"].items():
                det = avant["details"][iddet]
                s = saisies.get("details", {}).get(iddet, {})
                recalcules += [
                    _ligne("detail", iddet, cle, det[cle], m[cle], s) for cle in MONTANTS_DETAIL
                    if _d(m[cle]) != _d(s[cle] if cle in s else det[cle])
                ]
        # En-tête relu : montants posés ici et par les déclencheurs de la base (partage des accessoires, commission)
        contrat.refresh_from_db()
        entete_avant = avant["contrat"]
        for cle in MONTANTS_CONTRAT:
            enregistre = getattr(contrat, cle)
            attendu = sc[cle] if cle in sc else entete_avant.get(cle)
            if (attendu is None and enregistre is None) or _d(enregistre) == _d(attendu):
                continue
            recalcules.append(_ligne("contrat", contrat.pk, cle, entete_avant.get(cle), enregistre, sc))
        if prime:
            lignes, alertes = _aligner_quittance(cursor, contrat.pk)
            recalcules += lignes
            avertissements += alertes
        elif "taux_commission" in sc:
            cursor.execute(
                "UPDATE stdquittance q SET taux_commission = c.taux_commission FROM stdcontrat c"
                " WHERE c.idcontrat = %s AND q.idquittance = c.idquittance",
                [contrat.pk],
            )
    return {"recalcules": recalcules, "avertissements": avertissements}
