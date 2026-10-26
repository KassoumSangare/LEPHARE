"""
Reprise des affaires antérieures (demande du 2026-10-26 : « une session de saisie des affaires antérieures »).

Les contrats des années passées qui ne sont pas dans LE PHARE (papier, Excel, extranets des compagnies, autres
courtiers) sont repris tels qu'ils ont été émis, sans tarif ni confirmation de devis :
- toute année antérieure, toute compagnie, toute branche ; dates d'effet et d'émission avant le 1er janvier de
  l'année en cours (la production de l'année n'est pas touchée), comptées dans les états de leur année ;
- primes du document (prime nette, accessoires, taxes, TTC exacte : pas d'arrondi à 5 F) ;
- quittance dans son état réel : payée, partiellement payée ou impayée (le reste dû est à encaisser en caisse
  comme toute quittance), commission perçue ou non ;
- numéro de police OREOLE de l'année d'origine (série des polices de la compagnie), quittance dans une série
  « R » de son exercice (« 1186/2023/R00001 ») : aucun risque de doublon avec les numéros existants ;
- saisie par tout utilisateur habilité (droit contrats.reprise), sans validation ; une reprise erronée se
  supprime tant que rien n'a été fait dessus (encaissement, avenant, sinistre).

Chaque affaire reprise crée un devis confirmé, son détail, le contrat, son détail et la quittance, comme une
confirmation de devis, et une ligne lephare_reprise (données saisies, mode, lot d'import, commission perçue).
"""

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction

ID_INTERMEDIAIRE = 1
ID_AVENANT_AFFAIRE_NOUVELLE = 1
ID_PRODUIT_AUTO = 1
ID_OFFRE_NON_SPECIFIEE = 0
SOURCE_REPRISE = 2
STATUT_QUITTANCE_EN_COURS = 1
ECART_TTC_TOLERE = Decimal("2")
PAIEMENTS = {"PAYEE": "Payée", "PARTIELLE": "Partiellement payée", "IMPAYEE": "Impayée"}


class ErreurReprise(Exception):
    """Reprise refusée : message affiché tel quel."""


def normaliser(texte):
    texte = unicodedata.normalize("NFD", str(texte or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texte).strip().upper()


def montant(valeur, libelle, obligatoire=False):
    texte = str(valeur if valeur is not None else "").replace(" ", "").replace("\xa0", "").replace(" ", "").replace(",", ".")
    if texte in ("", "None"):
        if obligatoire:
            raise ErreurReprise(f"{libelle} : montant obligatoire.")
        return Decimal(0)
    try:
        nombre = Decimal(texte)
    except InvalidOperation as erreur:
        raise ErreurReprise(f"{libelle} : nombre attendu (« {valeur} »).") from erreur
    if nombre < 0:
        raise ErreurReprise(f"{libelle} : montant négatif.")
    return nombre


def jour(valeur, libelle, obligatoire=True):
    if isinstance(valeur, datetime):
        return valeur.date()
    if isinstance(valeur, date):
        return valeur
    texte = str(valeur or "").strip()[:10]
    if not texte or texte in ("None", "NA"):
        if obligatoire:
            raise ErreurReprise(f"{libelle} : date obligatoire.")
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(texte, fmt).date()
        except ValueError:
            continue
    raise ErreurReprise(f"{libelle} : date illisible (« {valeur} »), jj/mm/aaaa attendu.")


def entier(valeur, libelle, obligatoire=False):
    texte = str(valeur if valeur is not None else "").strip()
    if texte in ("", "None"):
        if obligatoire:
            raise ErreurReprise(f"{libelle} : valeur obligatoire.")
        return None
    try:
        return int(Decimal(texte.replace(" ", "").replace(",", ".")))
    except InvalidOperation as erreur:
        raise ErreurReprise(f"{libelle} : nombre entier attendu (« {valeur} »).") from erreur


def _un(cursor, sql, params=None):
    cursor.execute(sql, params or [])
    ligne = cursor.fetchone()
    return ligne[0] if ligne else None


def controler(cursor, d):
    """Données d'une affaire (écran ou ligne d'import, clés de l'API) contrôlées et complétées. Lève ErreurReprise."""
    debut_annee = date(date.today().year, 1, 1)
    r = {}
    r["IdClient"] = entier(d.get("IdClient"), "Client", obligatoire=True)
    if not _un(cursor, "SELECT 1 FROM stdclient WHERE idclient = %s", [r["IdClient"]]):
        raise ErreurReprise(f"Client n° {r['IdClient']} introuvable.")
    r["IdCompagnie"] = entier(d.get("IdCompagnie"), "Compagnie", obligatoire=True)
    if not _un(cursor, "SELECT 1 FROM stdcompagnie WHERE idcompagnie = %s", [r["IdCompagnie"]]):
        raise ErreurReprise(f"Compagnie n° {r['IdCompagnie']} introuvable.")
    r["IdProduit"] = entier(d.get("IdProduit"), "Branche", obligatoire=True)
    tarifs = {t: c for t, _, c in _tarifs_produit(cursor, r["IdProduit"])}
    if not tarifs:
        raise ErreurReprise("Branche inconnue ou sans catégorie.")
    r["IdTarif"] = entier(d.get("IdTarif"), "Catégorie") or next(iter(tarifs))
    if r["IdTarif"] not in tarifs:
        raise ErreurReprise("La catégorie choisie n'appartient pas à la branche.")
    r["CodeCategorie"] = tarifs[r["IdTarif"]]

    r["NumeroPoliceCompagnie"] = str(d.get("NumeroPoliceCompagnie") or "").strip()[:50]
    if not r["NumeroPoliceCompagnie"]:
        raise ErreurReprise("Numéro de police de la compagnie obligatoire.")
    r["DateEmission"] = jour(d.get("DateEmission"), "Date d'émission")
    r["DateEffet"] = jour(d.get("DateEffet"), "Date d'effet")
    r["DateExpiration"] = jour(d.get("DateExpiration"), "Date d'échéance")
    if r["DateEffet"] >= debut_annee or r["DateEmission"] >= debut_annee:
        raise ErreurReprise(f"Affaire de l'année en cours : seules les affaires antérieures au 01/01/{debut_annee.year} "
                            "se reprennent ici (les autres se saisissent en devis).")
    if r["DateExpiration"] < r["DateEffet"]:
        raise ErreurReprise("La date d'échéance précède la date d'effet.")
    if r["DateEmission"] > r["DateExpiration"]:
        raise ErreurReprise("La date d'émission suit la date d'échéance.")

    r["PrimeNette"] = montant(d.get("PrimeNette"), "Prime nette", obligatoire=True)
    r["Accessoire"] = montant(d.get("Accessoire"), "Accessoires")
    r["Taxe"] = montant(d.get("Taxe"), "Taxes")
    r["Fga"] = montant(d.get("Fga"), "FGA")
    r["Cedeao"] = montant(d.get("Cedeao"), "CEDEAO")
    somme = r["PrimeNette"] + r["Accessoire"] + r["Taxe"]
    ttc = montant(d.get("PrimeTtc"), "Prime TTC")
    r["PrimeTtc"] = ttc if ttc > 0 else somme
    if abs(r["PrimeTtc"] - somme) > ECART_TTC_TOLERE:
        raise ErreurReprise(f"Prime TTC {r['PrimeTtc']:,.0f} différente de prime nette + accessoires + taxes "
                            f"({somme:,.0f}) : la prime nette comprend le FGA et la CEDEAO.".replace(",", " "))
    if r["PrimeTtc"] <= 0:
        raise ErreurReprise("Prime TTC nulle.")

    taux = d.get("TauxCommission")
    r["TauxCommission"] = (montant(taux, "Taux de commission") if str(taux if taux is not None else "").strip() not in ("", "None")
                           else Decimal(str(_un(cursor, "SELECT public.fn_get_taux_commission(%s, %s, %s)",
                                                    [r["IdProduit"], r["IdCompagnie"], r["DateEmission"]]) or 0)))
    commission = d.get("Commission")
    r["Commission"] = (montant(commission, "Commission") if str(commission if commission is not None else "").strip() not in ("", "None")
                       else (r["PrimeNette"] * r["TauxCommission"] / 100).quantize(Decimal(1)))
    r["CommissionPercue"] = str(d.get("CommissionPercue")).strip().lower() in ("true", "1", "oui", "o", "vrai")

    statut = normaliser(d.get("StatutPaiement") or "PAYEE").replace(" ", "")
    statut = {"PAYEE": "PAYEE", "PAYE": "PAYEE", "OUI": "PAYEE", "PARTIELLE": "PARTIELLE", "PARTIELLEMENTPAYEE": "PARTIELLE",
              "IMPAYEE": "IMPAYEE", "IMPAYE": "IMPAYEE", "NON": "IMPAYEE"}.get(statut)
    if not statut:
        raise ErreurReprise("Paiement : Payée, Partiellement payée ou Impayée.")
    if statut == "PAYEE":
        r["MontantEncaisse"] = r["PrimeTtc"]
    elif statut == "IMPAYEE":
        r["MontantEncaisse"] = Decimal(0)
    else:
        r["MontantEncaisse"] = montant(d.get("MontantEncaisse"), "Montant encaissé", obligatoire=True)
        if not 0 < r["MontantEncaisse"] < r["PrimeTtc"]:
            raise ErreurReprise("Paiement partiel : le montant encaissé doit être entre 0 et la prime TTC.")
    r["StatutPaiement"] = statut

    # Risque : véhicule (Automobile) ou description (autres branches)
    r["Immatriculation"] = normaliser(d.get("Immatriculation"))[:50]
    r["IdMarque"] = entier(d.get("IdMarque"), "Marque") or 0
    r["Modele"] = str(d.get("Modele") or "").strip()[:30]
    r["Puissance"] = entier(d.get("Puissance"), "Puissance") or 0
    r["Places"] = entier(d.get("Places"), "Places") or (5 if r["IdProduit"] == ID_PRODUIT_AUTO else 0)
    r["IdEnergie"] = entier(d.get("IdEnergie"), "Énergie") or 0
    r["ChargeUtile"] = montant(d.get("ChargeUtile"), "Charge utile")
    r["ValeurNeuve"] = montant(d.get("ValeurNeuve"), "Valeur neuve")
    r["ValeurVenale"] = montant(d.get("ValeurVenale"), "Valeur vénale")
    r["DateMec"] = jour(d.get("DateMec"), "Date de mise en circulation", obligatoire=False)
    r["Risque"] = str(d.get("Risque") or "").strip()[:500]
    r["Observation"] = str(d.get("Observation") or "").strip()[:500]
    if r["IdProduit"] == ID_PRODUIT_AUTO and not r["Immatriculation"]:
        raise ErreurReprise("Automobile : immatriculation du véhicule obligatoire.")

    doublon = _un(cursor, """SELECT numeropolice FROM stdcontrat
                            WHERE idcompagnie = %s AND UPPER(TRIM(COALESCE(numeropolicecompagnie, ''))) = %s
                              AND dateeffet::date = %s AND COALESCE(idcontratannulation, 0) = 0 LIMIT 1""",
                  [r["IdCompagnie"], r["NumeroPoliceCompagnie"].upper(), r["DateEffet"]])
    if doublon:
        raise ErreurReprise(f"Déjà dans LE PHARE : police compagnie {r['NumeroPoliceCompagnie']} du {r['DateEffet']:%d/%m/%Y} "
                            f"(police OREOLE {doublon}).")
    return r


def _tarifs_produit(cursor, id_produit):
    cursor.execute("SELECT id_tarif, libelle_tarif, TRIM(code_categorie) FROM public.fn_liste_tarif_produit(%s) ORDER BY 3, 1", [id_produit])
    return cursor.fetchall()


def _numero_police(cursor, r):
    """Numéro de police de la série de la compagnie (sp_generer_numero_police), avec l'année d'émission d'origine."""
    cursor.execute("CALL public.sp_generer_numero_police(%s, %s, %s, %s, %s)",
                   [ID_INTERMEDIAIRE, r["IdCompagnie"], r["CodeCategorie"], "", ""])
    numero = (cursor.fetchone() or [""])[0] or ""
    if len(numero) < 10:
        raise ErreurReprise("Numéro de police non généré (série de la compagnie absente).")
    return numero[:7] + f"{r['DateEmission'].year % 100:02d}" + numero[9:]


def _numero_quittance(cursor, r):
    code = (_un(cursor, "SELECT TRIM(COALESCE(codeintermediaire, '0')) FROM stdintermediairecompagnie "
                        "WHERE idintermediaire = %s AND idcompagnie = %s", [ID_INTERMEDIAIRE, r["IdCompagnie"]]) or "0")[-4:].rjust(4, "0")
    exercice = r["DateEffet"].year
    cursor.execute("SELECT pg_advisory_xact_lock(hashtext('lephare_reprise_quittance'))")
    dernier = _un(cursor, "SELECT MAX(SUBSTRING(numeroquittance FROM '/R([0-9]+)$')::int) FROM stdquittance WHERE numeroquittance LIKE %s",
                  [f"{code}/{exercice}/R%"]) or 0
    return f"{code}/{exercice}/R{dernier + 1:05d}"


def enregistrer(cursor, r, utilisateur, mode="saisie", lot=None):
    """Affaire contrôlée (controler) écrite en base, dans la transaction de l'appelant. Renvoie la reprise créée."""
    cursor.execute("SELECT set_config('lephare.reprise', 'on', true)")  # TTC exacte du document (pas d'arrondi à 5 F)
    duree = (r["DateExpiration"] - r["DateEffet"]).days
    periode = _un(cursor, "SELECT public.fn_calcul_periode_contrat(%s)", [duree])
    id_duree = _un(cursor, "SELECT public.fn_calcul_id_duree_contrat(%s)", [duree])
    part = _un(cursor, "SELECT public.fn_lephare_part_accessoires_cabinet(%s)", [r["IdCompagnie"]])
    acc_cabinet = (r["Accessoire"] * Decimal(str(part)) / 100).quantize(Decimal(1)) if part is not None else Decimal(0)
    acc_compagnie = r["Accessoire"] - acc_cabinet
    police = _numero_police(cursor, r)
    quittance = _numero_quittance(cursor, r)
    pn = r["PrimeNette"]
    entete = dict(
        idintermediaire=ID_INTERMEDIAIRE, idcompagnie=r["IdCompagnie"], idaperiteur=r["IdCompagnie"], idproduit=r["IdProduit"],
        idclient=r["IdClient"], idassure=r["IdClient"], idavenant=ID_AVENANT_AFFAIRE_NOUVELLE, flotte=False, coassurance=False,
        periode=periode, numeroavenant="0000001", dateemission=r["DateEmission"], dateeffet=r["DateEffet"],
        dateexpiration=r["DateExpiration"], primeannuelle=pn, primenette=pn, accessoire=r["Accessoire"],
        accessoirecompagnie=acc_compagnie, accessoireintermediaire=acc_cabinet, taxe=r["Taxe"], fga=r["Fga"], cedeao=r["Cedeao"],
        primettc=r["PrimeTtc"], commissionintermediaire=r["Commission"], idduree=id_duree, idoperateur=utilisateur.id,
        numeropolicecompagnie=r["NumeroPoliceCompagnie"], primeimposee=True, observation="Reprise affaire antérieure",
    )
    colonnes = list(entete)
    cursor.execute(
        f"INSERT INTO stddevis ({', '.join(colonnes)}, numerodevis, idoffre, confirme, renouvelable, statut, datecreation) "
        f"VALUES ({', '.join(['%s'] * len(colonnes))}, %s, %s, true, true, 'ACTIVE', now()) RETURNING iddevis",
        [entete[c] for c in colonnes] + [police, ID_OFFRE_NON_SPECIFIEE],
    )
    id_devis = cursor.fetchone()[0]
    vehicule = dict(
        idtarif=r["IdTarif"], nombreplace=r["Places"], chargeutile=r["ChargeUtile"], valeurneuve=r["ValeurNeuve"],
        valeurvenale=r["ValeurVenale"], valeuraccessoire=0, matricule=r["Immatriculation"], idmarque=r["IdMarque"],
        puissancefiscale=r["Puissance"], modelevehicule=r["Modele"], datemec=r["DateMec"], primeannuelle=pn, primenette=pn,
        taxeenregistrement=r["Taxe"], fga=r["Fga"],
    )
    cols_v = list(vehicule)
    cursor.execute(
        f"INSERT INTO stddevisdetail (iddevis, {', '.join(cols_v)}, vehicule, idoffre, essence, primeimposee) "
        f"VALUES (%s, {', '.join(['%s'] * len(cols_v))}, 1, %s, %s, true) RETURNING iddevisdetail",
        [id_devis] + [vehicule[c] for c in cols_v] + [ID_OFFRE_NON_SPECIFIEE, r["IdEnergie"]],
    )
    cursor.execute(
        f"INSERT INTO stdcontrat ({', '.join(colonnes)}, iddevis, numeropolice, renouvelable, taux_commission) "
        f"VALUES ({', '.join(['%s'] * len(colonnes))}, %s, %s, true, %s) RETURNING idcontrat",
        [entete[c] for c in colonnes] + [id_devis, police, r["TauxCommission"]],
    )
    id_contrat = cursor.fetchone()[0]
    cursor.execute(
        f"INSERT INTO stdcontratdetail (idcontrat, idproduit, idassure, {', '.join(cols_v)}, idoffre, codecarburant, extincteur, "
        f"sexe, attestation, mt_delegation) VALUES (%s, %s, %s, {', '.join(['%s'] * len(cols_v))}, %s, %s, false, 'M', '', 0)",
        [id_contrat, r["IdProduit"], r["IdClient"]] + [vehicule[c] for c in cols_v]
        + [ID_OFFRE_NON_SPECIFIEE, str(r["IdEnergie"] or "")],
    )
    cursor.execute(
        """INSERT INTO stdquittance (numeroquittance, idintermediaire, idclient, nature, dateeffet, dateexpiration, exercice, source,
                                     statut, primenette, taxe, accessoire, commission, primettc, encaissee, mt_encaisse, reglee, mt_regle,
                                     numeropolice, idaperiteur, coassurance, idproduit, taux_commission, dateemission, idquittannul)
           VALUES (%s, %s, %s, 'C', %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, false, 0, %s, %s, false, %s, %s, %s, NULL)
           RETURNING idquittance""",
        [quittance, ID_INTERMEDIAIRE, r["IdClient"], r["DateEffet"], r["DateExpiration"], r["DateEffet"].year, SOURCE_REPRISE,
         STATUT_QUITTANCE_EN_COURS, pn, r["Taxe"], r["Accessoire"], r["PrimeTtc"], r["MontantEncaisse"] >= r["PrimeTtc"],
         r["MontantEncaisse"], police, r["IdCompagnie"], r["IdProduit"], r["TauxCommission"], r["DateEmission"]],
    )
    id_quittance = cursor.fetchone()[0]
    cursor.execute("UPDATE stdcontrat SET idquittance = %s WHERE idcontrat = %s", [id_quittance, id_contrat])
    reste = r["PrimeTtc"] - r["MontantEncaisse"]
    if reste:
        cursor.execute("UPDATE stdclient SET solde = COALESCE(solde, 0) + %s WHERE idclient = %s", [reste, r["IdClient"]])
    donnees = {k: (v.isoformat() if isinstance(v, date) else str(v) if isinstance(v, Decimal) else v) for k, v in r.items()}
    cursor.execute(
        """INSERT INTO lephare_reprise (idcontrat, iddevis, idquittance, mode, lot, donnees, commission_percue, creepar,
                                        idutilisateur, datecreation)
           VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, now()) RETURNING id""",
        [id_contrat, id_devis, id_quittance, mode, lot, _json(donnees), r["CommissionPercue"],
         (getattr(utilisateur, "email", "") or "")[:150], utilisateur.id],
    )
    id_reprise = cursor.fetchone()[0]
    cursor.execute("SELECT set_config('lephare.reprise', 'off', true)")
    return {"Id": id_reprise, "IdContrat": id_contrat, "NumeroPolice": police, "NumeroQuittance": quittance}


def _json(valeur):
    import json
    return json.dumps(valeur, ensure_ascii=False)


def reprendre(donnees, utilisateur, mode="saisie", lot=None):
    """Contrôle et enregistrement d'une affaire, en une transaction."""
    with transaction.atomic(), connection.cursor() as cursor:
        return enregistrer(cursor, controler(cursor, donnees), utilisateur, mode, lot)


def supprimer(id_reprise, utilisateur, peut_tout_supprimer):
    """Reprise erronée retirée (devis, contrat, quittance, solde du client) tant que rien n'a été fait dessus."""
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("""SELECT r.idcontrat, r.iddevis, r.idquittance, r.idutilisateur, c.numeropolice,
                                 c.numeropolicecompagnie, c.idclient, q.numeroquittance, q.primettc, q.mt_encaisse
                          FROM lephare_reprise r JOIN stdcontrat c ON c.idcontrat = r.idcontrat
                          JOIN stdquittance q ON q.idquittance = r.idquittance WHERE r.id = %s FOR UPDATE OF r""", [id_reprise])
        ligne = cursor.fetchone()
        if not ligne:
            raise ErreurReprise("Reprise introuvable.")
        (id_contrat, id_devis, id_quittance, auteur, police, police_cie, id_client, numero_quittance, ttc, encaisse) = ligne
        if auteur != utilisateur.id and not peut_tout_supprimer:
            raise ErreurReprise("Seul l'auteur de la reprise (ou un utilisateur habilité à annuler les contrats) peut la supprimer.")
        if _un(cursor, "SELECT 1 FROM stddetailencaissement WHERE numeroquittance = %s LIMIT 1", [numero_quittance]):
            raise ErreurReprise("Un encaissement a été fait sur cette quittance : annulez-le d'abord.")
        if _un(cursor, "SELECT 1 FROM stdcontrat WHERE idoldhist = %s LIMIT 1", [id_contrat]):
            raise ErreurReprise("Un avenant ou un renouvellement a été établi sur ce contrat.")
        if _un(cursor, "SELECT 1 FROM institutionnel_sinistredelegue WHERE police_num IN (%s, %s) LIMIT 1", [police, police_cie or police]):
            raise ErreurReprise("Un sinistre est déclaré sur ce contrat.")
        reste = Decimal(str(ttc or 0)) - Decimal(str(encaisse or 0))
        cursor.execute("DELETE FROM lephare_reprise WHERE id = %s", [id_reprise])
        cursor.execute("UPDATE stdcontrat SET idquittance = NULL WHERE idcontrat = %s", [id_contrat])
        cursor.execute("DELETE FROM stdquittance WHERE idquittance = %s", [id_quittance])
        cursor.execute("DELETE FROM stdcontratdetail WHERE idcontrat = %s", [id_contrat])
        cursor.execute("DELETE FROM stdcontrat WHERE idcontrat = %s", [id_contrat])
        cursor.execute("DELETE FROM stddevisdetail WHERE iddevis = %s", [id_devis])
        cursor.execute("DELETE FROM stddevis WHERE iddevis = %s", [id_devis])
        if reste:
            cursor.execute("UPDATE stdclient SET solde = COALESCE(solde, 0) - %s WHERE idclient = %s", [reste, id_client])
        return {"NumeroPolice": police, "NumeroQuittance": numero_quittance}
