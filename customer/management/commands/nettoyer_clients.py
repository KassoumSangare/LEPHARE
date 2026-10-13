"""
Applique le nettoyage du fichier clients à partir de la feuille « Correspondance des références »
du classeur d'analyse (une ligne par fiche : ancien idclient, fiche de référence, décision).

    python manage.py nettoyer_clients "NETTOYAGE_FICHIER_CLIENTS.xlsx"              (essai à blanc)
    python manage.py nettoyer_clients "NETTOYAGE_FICHIER_CLIENTS.xlsx" --appliquer

- regroupé : contrats, devis, quittances, chèques, ayants droit… de la fiche en double passent sur
  la fiche de référence ; la référence est complétée par les coordonnées qui lui manquent (jamais
  écrasées) et reprend le solde/avoir ; la fiche en double est archivée (statut « A ») ;
- exclu : la fiche est archivée (statut « A ») avec ses devis, sauf si elle a un contrat entre-temps ;
- conservé / à vérifier : aucune modification.

Chaque fiche traitée est inscrite dans lephare_client_nettoyage (décision, ancien statut, champs
remplacés, lignes rattachées à la référence) : la commande peut être relancée sans rien refaire, et
réappliquée telle quelle après une nouvelle reprise URANUS (mêmes identifiants).
"""

import os
import re
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from autorisations.journal import journaliser
from customer.models import STATUT_ARCHIVE, ClientNettoyage

FEUILLE = "Correspondance des références"
DECISIONS = {
    "conservé": ClientNettoyage.CONSERVE,
    "regroupé": ClientNettoyage.REGROUPE,
    "exclu": ClientNettoyage.EXCLU,
    "à vérifier": ClientNettoyage.A_VERIFIER,
}
# Toutes les colonnes qui désignent une fiche client (clés étrangères ou non)
LIENS = [
    ("stdcontrat", "idclient"), ("stdcontrat", "idassure"), ("stdcontratdetail", "idassure"),
    ("stddevis", "idclient"), ("stddevis", "idassure"), ("stdquittance", "idclient"), ("stdcheque", "idclient"),
    ("stdayantdroitia", "idassure"), ("lephare_sauvegarde_part_ayant_droit_ia", "idassure"),
    ("stdcertificattransport", "idclienturanus"), ("institutionnel_crminteraction", "client_id"),
]
# Coordonnées reprises d'une fiche en double quand la référence ne les a pas
CHAMPS = ["telephone", "mobile", "fixe", "fax", "email", "adresse1", "adresse2", "idville", "codepostal",
          "datenaissance", "lieunaissance", "idqualite", "idprofession", "idsecteuractivite", "responsable",
          "Fonction", "idstatutjuridique"]
VIDES = {"", "-", ".", "..", "...", "--", "BP", "NONE", "NULL", "0", "00", "TELP", "N/A", "NA", "NEANT", "X"}


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


class Command(BaseCommand):
    help = "Applique le nettoyage du fichier clients (regroupement des doublons, archivage des fiches sans contrat)."

    def add_arguments(self, parser):
        parser.add_argument("classeur", help="Classeur d'analyse (.xlsx) contenant la feuille « Correspondance des références »")
        parser.add_argument("--appliquer", action="store_true", help="Enregistre les modifications (sinon essai à blanc)")
        parser.add_argument("--lot", default="", help="Nom du lot inscrit dans lephare_client_nettoyage")

    def lire(self, chemin):
        from openpyxl import load_workbook

        if not os.path.isfile(chemin):
            raise CommandError(f"Classeur introuvable : {chemin}")
        classeur = load_workbook(chemin, read_only=True, data_only=True)
        if FEUILLE not in classeur.sheetnames:
            raise CommandError(f"Feuille « {FEUILLE} » absente du classeur.")
        lignes = {}
        for ligne in classeur[FEUILLE].iter_rows(min_row=2, values_only=True):
            if ligne[0] is None:
                continue
            decision = DECISIONS.get(str(ligne[4] or "").strip().lower())
            if decision is None:
                raise CommandError(f"Décision inconnue pour la fiche {ligne[0]} : « {ligne[4]} ».")
            lignes[int(ligne[0])] = {
                "nom": str(ligne[1] or ""), "reference": int(ligne[3]) if ligne[3] not in (None, "") else None,
                "decision": decision, "motif": str(ligne[5] or ""),
            }
        return lignes

    def handle(self, *args, classeur, appliquer, lot, **options):
        lignes = self.lire(classeur)
        lot = lot or f"Nettoyage fichier clients {timezone.localdate():%d/%m/%Y} ({os.path.basename(classeur)})"
        with connection.cursor() as cur:
            cur.execute("SELECT idclient FROM stdclient")
            existants = {r[0] for r in cur.fetchall()}
        inconnus = sorted(set(lignes) - existants)
        if inconnus:
            raise CommandError(f"{len(inconnus)} fiche(s) du classeur absente(s) de la base : {inconnus[:20]}")
        for idc, l in lignes.items():
            if l["decision"] == ClientNettoyage.REGROUPE:
                ref = lignes.get(l["reference"])
                if not ref or l["reference"] == idc or ref["decision"] != ClientNettoyage.CONSERVE:
                    raise CommandError(f"Fiche {idc} : la référence {l['reference']} doit être une fiche « conservé » du classeur.")

        deja = set(ClientNettoyage.objects.values_list("idclient", flat=True))
        bilan = {"regroupées": 0, "archivées": 0, "lignes rattachées": 0, "références complétées": 0,
                 "exclues gardées (contrat apparu)": 0, "déjà traitées": len(deja & set(lignes))}
        with transaction.atomic():
            with connection.cursor() as cur:
                # La clé anti-doublon ne doit pas être recalculée par les mises à jour du nettoyage
                cur.execute("ALTER TABLE stdclient DISABLE TRIGGER trg_clients_cle_unique")
                cles = {}
                for table, _ in LIENS:
                    cur.execute("""SELECT a.attname FROM pg_index i JOIN pg_attribute a
                                   ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                                   WHERE i.indrelid = to_regclass(%s) AND i.indisprimary""", [table])
                    cle = cur.fetchone()
                    if cle:
                        cles[table] = cle[0]
                liens = [(t, c) for t, c in LIENS if t in cles]
                cur.execute("SELECT idclient FROM stdcontrat UNION SELECT idassure FROM stdcontrat")
                avec_contrat = {r[0] for r in cur.fetchall()}

                def fiche(idc):
                    cur.execute("SELECT statut, solde, avoir, " + ", ".join(f'"{c}"' for c in CHAMPS)
                                + " FROM stdclient WHERE idclient = %s", [idc])
                    v = cur.fetchone()
                    return {"statut": v[0], "solde": v[1], "avoir": v[2], **dict(zip(CHAMPS, v[3:]))}

                a_creer = []
                # 1. Doublons confirmés : tout passe sur la fiche de référence
                par_reference = {}
                for idc, l in lignes.items():
                    if l["decision"] == ClientNettoyage.REGROUPE and idc not in deja:
                        par_reference.setdefault(l["reference"], []).append(idc)
                for ref, doublons in sorted(par_reference.items()):
                    r = fiche(ref)
                    remplaces = {}
                    for idc in sorted(doublons):
                        d = fiche(idc)
                        deplaces = {}
                        for table, colonne in liens:
                            cur.execute(f'UPDATE {table} SET "{colonne}" = %s WHERE "{colonne}" = %s RETURNING "{cles[table]}"',
                                        [ref, idc])
                            ids = [x[0] for x in cur.fetchall()]
                            if ids:
                                deplaces[f"{table}.{colonne}"] = ids
                                bilan["lignes rattachées"] += len(ids)
                        for champ in CHAMPS:
                            source = d[champ]
                            if vide(champ, r[champ]) and not vide(champ, source) and not (champ == "email" and "oreole" in str(source).lower()):
                                remplaces.setdefault(champ, json_ok(r[champ]))
                                r[champ] = source
                                cur.execute(f'UPDATE stdclient SET "{champ}" = %s WHERE idclient = %s', [source, ref])
                        montants = {}
                        for champ in ("solde", "avoir"):
                            if d[champ]:
                                montants[champ] = json_ok(d[champ])
                                remplaces.setdefault(champ, json_ok(r[champ]))
                                r[champ] = (r[champ] or 0) + d[champ]
                                cur.execute(f"UPDATE stdclient SET {champ} = %s WHERE idclient = %s", [r[champ], ref])
                                cur.execute(f"UPDATE stdclient SET {champ} = 0 WHERE idclient = %s", [idc])
                        cur.execute("UPDATE stdclient SET statut = %s, datemaj = now() WHERE idclient = %s", [STATUT_ARCHIVE, idc])
                        a_creer.append(ClientNettoyage(
                            idclient=idc, idclient_reference=ref, decision=ClientNettoyage.REGROUPE,
                            motif=lignes[idc]["motif"], nom_origine=lignes[idc]["nom"][:310], statut_avant=d["statut"] or "",
                            donnees_avant={"lignes_rattachees": deplaces, "montants_transferes": montants}, lot=lot))
                        bilan["regroupées"] += 1
                    if remplaces:
                        cur.execute("UPDATE stdclient SET datemaj = now() WHERE idclient = %s", [ref])
                        bilan["références complétées"] += 1
                    if ref not in deja:
                        a_creer.append(ClientNettoyage(
                            idclient=ref, idclient_reference=ref, decision=ClientNettoyage.CONSERVE,
                            motif=f"référence de {len(doublons) + 1} fiches : {', '.join('#%d' % x for x in sorted(doublons))}",
                            nom_origine=lignes[ref]["nom"][:310], statut_avant=r["statut"] or "",
                            donnees_avant={"champs_remplaces": remplaces}, lot=lot))
                        deja.add(ref)

                # 2. Fiches sans contrat : archivées (sauf contrat apparu depuis l'analyse)
                exclues = [i for i, l in lignes.items() if l["decision"] == ClientNettoyage.EXCLU and i not in deja]
                gardees = [i for i in exclues if i in avec_contrat]
                archiver = [i for i in exclues if i not in avec_contrat]
                bilan["exclues gardées (contrat apparu)"] = len(gardees)
                statuts = {}
                if archiver:
                    cur.execute("SELECT idclient, statut FROM stdclient WHERE idclient = ANY(%s)", [archiver])
                    statuts = dict(cur.fetchall())
                    cur.execute("UPDATE stdclient SET statut = %s, datemaj = now() WHERE idclient = ANY(%s)",
                                [STATUT_ARCHIVE, archiver])
                    bilan["archivées"] = cur.rowcount
                for i in archiver:
                    a_creer.append(ClientNettoyage(idclient=i, decision=ClientNettoyage.EXCLU, motif=lignes[i]["motif"],
                                                   nom_origine=lignes[i]["nom"][:310], statut_avant=statuts.get(i) or "", lot=lot))
                for i in gardees:
                    a_creer.append(ClientNettoyage(idclient=i, decision=ClientNettoyage.CONSERVE, nom_origine=lignes[i]["nom"][:310],
                                                   motif="classée « exclu » par l'analyse mais liée à un contrat à l'application : conservée",
                                                   lot=lot))

                # 3. Conservées et à vérifier : inscrites pour la traçabilité, sans modification
                for i, l in lignes.items():
                    if i not in deja and l["decision"] in (ClientNettoyage.CONSERVE, ClientNettoyage.A_VERIFIER):
                        a_creer.append(ClientNettoyage(idclient=i, idclient_reference=l["reference"], decision=l["decision"],
                                                       motif=l["motif"], nom_origine=l["nom"][:310], lot=lot))
                ClientNettoyage.objects.bulk_create(a_creer)
                # Les clés étrangères vers stdclient sont différées : les contrôler maintenant
                # (rattachements valides) libère la table pour réactiver le déclencheur
                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
                cur.execute("ALTER TABLE stdclient ENABLE TRIGGER trg_clients_cle_unique")

            journaliser(
                auteur=f"console serveur ({os.environ.get('USERNAME') or os.environ.get('USER') or 'inconnu'})",
                module="clients", action="clients.nettoyage",
                description=f"{lot} : {bilan['regroupées']} doublons regroupés, {bilan['archivées']} fiches sans contrat archivées",
                objet_type="client", details=bilan,
            )
            if not appliquer:
                transaction.set_rollback(True)

        for cle, valeur in bilan.items():
            self.stdout.write(f"  {cle} : {valeur}")
        if appliquer:
            self.stdout.write(self.style.SUCCESS(f"Nettoyage appliqué ({lot})."))
        else:
            self.stdout.write(self.style.WARNING("Essai à blanc : rien n'a été enregistré (relancer avec --appliquer)."))
