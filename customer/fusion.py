"""
Fusion de deux fiches clients en double (Administration > Corrections > Fiches clients en double, 2026-11-25), même règle
que le dédoublonnage du fichier clients (commande nettoyer_clients) :

- tout ce qui désigne la fiche en double (contrats, devis, quittances, chèques, ayants droit, adhérents Oreole Santé et AFA,
  conventions RAFAS, interactions commerciales…) passe sur la fiche gardée ;
- la fiche gardée reçoit les coordonnées qui lui manquent (jamais écrasées), le solde et l'avoir de l'autre ;
- la fiche en double est archivée (statut « A ») et inscrite dans lephare_client_nettoyage (décision « regroupé », lignes
  rattachées par table, montants transférés, champs complétés) : la fusion reste lisible et réversible fiche par fiche.

Refus : même fiche, fiche inconnue, fiche à garder archivée, fiche déjà regroupée, une personne et une entreprise.
"""

import re
from decimal import Decimal

from django.db import connection
from django.utils import timezone

from .models import STATUT_ARCHIVE, ClientNettoyage

# Toutes les colonnes qui désignent une fiche client (clés étrangères ou non) ; une table absente est ignorée
LIENS = [
    ("stdcontrat", "idclient"), ("stdcontrat", "idassure"), ("stdcontratdetail", "idassure"),
    ("stddevis", "idclient"), ("stddevis", "idassure"), ("stdquittance", "idclient"), ("stdcheque", "idclient"),
    ("stdayantdroitia", "idassure"), ("lephare_sauvegarde_part_ayant_droit_ia", "idassure"),
    ("stdcertificattransport", "idclienturanus"), ("institutionnel_crminteraction", "client_id"),
    ("lephare_afa_assure", "idclient"), ("lephare_oreole_adherent", "idclient"), ("lephare_rafas_convention", "idclient"),
]
# Libellés des rattachements montrés avant la fusion
LIBELLES_LIENS = {
    "stdcontrat.idclient": "Contrats (souscripteur)", "stdcontrat.idassure": "Contrats (assuré)", "stdcontratdetail.idassure": "Risques assurés",
    "stddevis.idclient": "Devis (souscripteur)", "stddevis.idassure": "Devis (assuré)", "stdquittance.idclient": "Quittances",
    "stdcheque.idclient": "Chèques", "stdayantdroitia.idassure": "Ayants droit IA", "lephare_sauvegarde_part_ayant_droit_ia.idassure": "Parts IA sauvegardées",
    "stdcertificattransport.idclienturanus": "Certificats transport", "institutionnel_crminteraction.client_id": "Suivi commercial",
    "lephare_afa_assure.idclient": "Assurés AFA", "lephare_oreole_adherent.idclient": "Adhérents Oreole Santé",
    "lephare_rafas_convention.idclient": "Conventions RAFAS",
}
# Coordonnées reprises de la fiche en double quand la fiche gardée ne les a pas
CHAMPS = ["telephone", "mobile", "fixe", "fax", "email", "adresse1", "adresse2", "idville", "codepostal",
          "datenaissance", "lieunaissance", "idqualite", "idprofession", "idsecteuractivite", "responsable",
          "Fonction", "idstatutjuridique"]
VIDES = {"", "-", ".", "..", "...", "--", "BP", "NONE", "NULL", "0", "00", "TELP", "N/A", "NA", "NEANT", "X"}
LIBELLES_CHAMPS = {
    "telephone": "Téléphone", "mobile": "Mobile", "fixe": "Fixe", "fax": "Fax", "email": "E-mail", "adresse1": "Adresse",
    "adresse2": "Adresse (suite)", "idville": "Ville", "codepostal": "Boîte postale", "datenaissance": "Date de naissance",
    "lieunaissance": "Lieu de naissance", "idqualite": "Civilité", "idprofession": "Profession", "idsecteuractivite": "Secteur d'activité",
    "responsable": "Contact", "Fonction": "Fonction", "idstatutjuridique": "Statut juridique",
}


class ErreurFusion(Exception):
    """Fusion refusée : message affiché tel quel."""


def vide(champ, valeur):
    if valeur is None:
        return True
    if champ in ("telephone", "mobile", "fixe", "fax"):
        return len(re.sub(r"\D", "", str(valeur))) < 8
    if champ == "email":
        return "@" not in str(valeur)
    if isinstance(valeur, int):
        return valeur == 0
    return isinstance(valeur, str) and valeur.strip().upper() in VIDES


def json_ok(valeur):
    return str(valeur) if isinstance(valeur, Decimal) or hasattr(valeur, "isoformat") else valeur


def liens_presents(cur):
    """(table, colonne, clé primaire) des liens dont la table existe."""
    presents = []
    for table, colonne in LIENS:
        cur.execute("""SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                       WHERE i.indrelid = to_regclass(%s) AND i.indisprimary""", [table])
        cle = cur.fetchone()
        if cle:
            presents.append((table, colonne, cle[0]))
    return presents


def lire_fiche(cur, idclient):
    cur.execute("SELECT idclient, TRIM(COALESCE(nom, '')), TRIM(COALESCE(prenoms, '')), statut, solde, avoir, particulier, cle_unique, cnipat, "
                + ", ".join(f'"{c}"' for c in CHAMPS) + " FROM stdclient WHERE idclient = %s", [idclient])
    v = cur.fetchone()
    if not v:
        return None
    return {"idclient": v[0], "nom": v[1], "prenoms": v[2], "statut": (v[3] or "").strip(), "solde": v[4], "avoir": v[5],
            "particulier": v[6], "cle_unique": v[7], "cnipat": v[8], **dict(zip(CHAMPS, v[9:]))}


def _refus(garder, fusionner, a, b):
    refus = []
    if garder == fusionner:
        refus.append("Choisissez deux fiches différentes.")
    if not a:
        refus.append(f"La fiche n° {garder} n'existe pas.")
    if not b:
        refus.append(f"La fiche n° {fusionner} n'existe pas.")
    if refus:
        return refus
    if a["statut"] == STATUT_ARCHIVE:
        refus.append(f"La fiche à garder (n° {garder}) est archivée : restaurez-la d'abord depuis les Archives.")
    deja = ClientNettoyage.objects.filter(idclient=fusionner, decision=ClientNettoyage.REGROUPE).first()
    if deja and b["statut"] == STATUT_ARCHIVE:
        refus.append(f"La fiche n° {fusionner} est déjà regroupée sur la fiche n° {deja.idclient_reference}.")
    if a["particulier"] is not None and b["particulier"] is not None and bool(a["particulier"]) != bool(b["particulier"]):
        refus.append("L'une des fiches est une personne, l'autre une entreprise : corrigez d'abord la fiche erronée.")
    return refus


def _nom(f):
    return " ".join(x for x in (f["nom"], f["prenoms"]) if x)


def _resume(cur, f, liens):
    compteurs = {}
    for table, colonne, _ in liens:
        cur.execute(f'SELECT COUNT(*) FROM {table} WHERE "{colonne}" = %s', [f["idclient"]])
        n = cur.fetchone()[0]
        if n:
            compteurs[f"{table}.{colonne}"] = n
    return {
        "IdClient": f["idclient"], "Nom": _nom(f), "Statut": f["statut"], "Particulier": bool(f["particulier"]),
        "Solde": float(f["solde"] or 0), "Avoir": float(f["avoir"] or 0), "Piece": (f["cnipat"] or "").strip(),
        "Coordonnees": {LIBELLES_CHAMPS[c]: json_ok(f[c]) for c in CHAMPS if not vide(c, f[c])},
        "Rattachements": [{"Cle": cle, "Libelle": LIBELLES_LIENS.get(cle, cle), "Nombre": n} for cle, n in compteurs.items()],
    }


def apercu(garder, fusionner):
    """Ce que la fusion ferait, sans rien écrire : les deux fiches, les lignes qui changeront de fiche, les coordonnées
    complétées, les refus."""
    with connection.cursor() as cur:
        a, b = lire_fiche(cur, garder), lire_fiche(cur, fusionner)
        refus = _refus(garder, fusionner, a, b)
        if not a or not b:
            return {"Refus": refus}
        liens = liens_presents(cur)
        completes = [LIBELLES_CHAMPS[c] for c in CHAMPS if vide(c, a[c]) and not vide(c, b[c])
                     and not (c == "email" and "oreole" in str(b[c]).lower())]
        return {"Garder": _resume(cur, a, liens), "Fusionner": _resume(cur, b, liens), "Completes": completes, "Refus": refus}


def fusionner_fiches(garder, fusionner, motif, utilisateur=None):
    """Fusion dans la transaction de l'appelant. Renvoie le bilan (lignes rattachées par table, champs complétés,
    montants transférés)."""
    motif = " ".join(str(motif or "").split())
    if len(motif) < 5:
        raise ErreurFusion("Indiquez le motif de la fusion (5 caractères au moins).")
    with connection.cursor() as cur:
        cur.execute("SELECT idclient FROM stdclient WHERE idclient = ANY(%s) ORDER BY idclient FOR UPDATE", [[garder, fusionner]])
        a, b = lire_fiche(cur, garder), lire_fiche(cur, fusionner)
        refus = _refus(garder, fusionner, a, b)
        if refus:
            raise ErreurFusion(" ".join(refus))
        # Fiche gardée sans clé anti-doublon : sa clé serait recalculée (trg_clients_cle_unique) au premier changement et
        # pourrait reprendre celle de la fiche en double ; elle prend la clé de son numéro, comme à la restauration
        if not (a["cle_unique"] or "").strip():
            cur.execute("UPDATE stdclient SET cle_unique = %s WHERE idclient = %s", [f"CLIENT-{garder}", garder])
        deplaces = {}
        for table, colonne, cle in liens_presents(cur):
            cur.execute(f'UPDATE {table} SET "{colonne}" = %s WHERE "{colonne}" = %s RETURNING "{cle}"', [garder, fusionner])
            ids = [x[0] for x in cur.fetchall()]
            if ids:
                deplaces[f"{table}.{colonne}"] = ids
        completes = {}
        for champ in CHAMPS:
            source = b[champ]
            if vide(champ, a[champ]) and not vide(champ, source) and not (champ == "email" and "oreole" in str(source).lower()):
                completes[champ] = json_ok(a[champ])
                cur.execute(f'UPDATE stdclient SET "{champ}" = %s WHERE idclient = %s', [source, garder])
        montants = {}
        for champ in ("solde", "avoir"):
            if b[champ]:
                montants[champ] = json_ok(b[champ])
                cur.execute(f"UPDATE stdclient SET {champ} = COALESCE({champ}, 0) + %s WHERE idclient = %s", [b[champ], garder])
                cur.execute(f"UPDATE stdclient SET {champ} = 0 WHERE idclient = %s", [fusionner])
        cur.execute("UPDATE stdclient SET datemaj = now() WHERE idclient = %s", [garder])
        cur.execute("UPDATE stdclient SET statut = %s, datemaj = now() WHERE idclient = %s", [STATUT_ARCHIVE, fusionner])
        # Les clés étrangères vers stdclient sont différées : contrôlées maintenant, une erreur annule tout
        cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

    lot = f"Fusion manuelle du {timezone.localdate():%d/%m/%Y}"
    donnees = {"lignes_rattachees": deplaces, "montants_transferes": montants, "champs_completes_sur_reference": completes,
               "auteur": getattr(utilisateur, "email", "") or ""}
    precedent = ClientNettoyage.objects.filter(idclient=fusionner).first()
    if precedent:
        donnees["decision_precedente"] = {"decision": precedent.decision, "reference": precedent.idclient_reference, "lot": precedent.lot}
    ClientNettoyage.objects.update_or_create(idclient=fusionner, defaults={
        "idclient_reference": garder, "decision": ClientNettoyage.REGROUPE, "motif": motif[:2000], "nom_origine": _nom(b)[:310],
        "statut_avant": b["statut"][:1], "donnees_avant": donnees, "lot": lot,
    })
    ClientNettoyage.objects.get_or_create(idclient=garder, defaults={
        "idclient_reference": garder, "decision": ClientNettoyage.CONSERVE, "motif": f"référence de la fusion de la fiche #{fusionner}",
        "nom_origine": _nom(a)[:310], "statut_avant": a["statut"][:1], "donnees_avant": {"champs_remplaces": completes}, "lot": lot,
    })
    return {
        "Garder": garder, "Fusionner": fusionner, "Nom": _nom(a),
        "Rattachements": [{"Libelle": LIBELLES_LIENS.get(cle, cle), "Nombre": len(ids)} for cle, ids in deplaces.items()],
        "Completes": [LIBELLES_CHAMPS[c] for c in completes], "Montants": montants,
    }


NOM_NORMALISE = "UPPER(REGEXP_REPLACE(TRIM(COALESCE(cl.nom, '') || ' ' || COALESCE(cl.prenoms, '')), '\\s+', ' ', 'g'))"
TELEPHONE = "NULLIF(RIGHT(REGEXP_REPLACE(COALESCE(NULLIF(TRIM(cl.mobile), ''), cl.telephone, ''), '\\D', '', 'g'), 8), '')"


def doublons_probables(limite=200):
    """Fiches actives de même nom : « certain » si elles partagent aussi le téléphone, la date de naissance ou la pièce,
    sinon « à vérifier ». Chaque groupe donne ses fiches avec leurs contrats, pour choisir celle à garder."""
    with connection.cursor() as cur:
        cur.execute(f"""
            WITH actifs AS (
                SELECT cl.idclient, {NOM_NORMALISE} AS nom, {TELEPHONE} AS tel, cl.datenaissance::date AS naissance,
                       NULLIF(UPPER(REGEXP_REPLACE(COALESCE(cl.cnipat, ''), '\\s+', '', 'g')), '') AS piece
                FROM stdclient cl WHERE COALESCE(cl.statut, '') <> 'A' AND LENGTH(TRIM(COALESCE(cl.nom, ''))) > 1
            ), groupes AS (SELECT nom FROM actifs GROUP BY nom HAVING COUNT(*) > 1)
            SELECT a.nom, a.idclient, a.tel, a.naissance, a.piece,
                   (SELECT COUNT(*) FROM stdcontrat ct WHERE ct.idclient = a.idclient) AS contrats,
                   (SELECT COUNT(*) FROM stddevis d WHERE d.idclient = a.idclient) AS devis,
                   COALESCE(NULLIF(TRIM(c2.mobile), ''), NULLIF(TRIM(c2.telephone), ''), '') AS telephone_affiche,
                   c2.datecreation
            FROM actifs a JOIN groupes g ON g.nom = a.nom JOIN stdclient c2 ON c2.idclient = a.idclient
            ORDER BY a.nom, a.idclient""")
        lignes = cur.fetchall()
    groupes = {}
    for nom, idc, tel, naissance, piece, contrats, devis, telephone, creation in lignes:
        groupes.setdefault(nom, []).append({"IdClient": idc, "Telephone": telephone, "Naissance": json_ok(naissance) or "",
                                            "Piece": piece or "", "Contrats": contrats, "Devis": devis,
                                            "Creation": json_ok(creation) or "", "_tel": tel, "_naissance": naissance, "_piece": piece})
    resultat = []
    for nom, fiches in groupes.items():
        certain = any(
            (x["_tel"] and x["_tel"] == y["_tel"]) or (x["_naissance"] and x["_naissance"] == y["_naissance"]) or (x["_piece"] and x["_piece"] == y["_piece"])
            for i, x in enumerate(fiches) for y in fiches[i + 1:]
        )
        for f in fiches:
            for cle in ("_tel", "_naissance", "_piece"):
                f.pop(cle)
        # Fiche proposée à garder : celle qui porte le plus de contrats, puis de devis, puis la plus ancienne
        fiches.sort(key=lambda f: (-f["Contrats"], -f["Devis"], f["IdClient"]))
        resultat.append({"Nom": nom, "Certain": certain, "Fiches": fiches})
    resultat.sort(key=lambda g: (not g["Certain"], g["Nom"]))
    return {"Groupes": resultat[:limite], "Total": len(resultat), "Certains": sum(1 for g in resultat if g["Certain"])}
