"""
Reprise des affaires antérieures : routes de l'écran Production > Affaires antérieures (production/reprise.py).

GET    /api/reprise/                      liste des reprises (filtres, totaux, pages de 50)
GET    /api/reprise/referentiels/         compagnies, branches et leurs catégories, énergies, marques
POST   /api/reprise/                      une affaire saisie à l'écran
PATCH  /api/reprise/<id>/commission/      commission perçue ou non
DELETE /api/reprise/<id>/                 reprise erronée retirée (rien n'a été fait dessus)
GET    /api/reprise/modele/               modèle Excel de l'import
POST   /api/reprise/import/analyse/       fichier contrôlé ligne par ligne, rien n'est enregistré
POST   /api/reprise/import/               lignes correctes reprises, les autres signalées
"""

import io
import uuid
from datetime import date, datetime
from decimal import Decimal

from django.db import connection, transaction
from django.http import HttpResponse
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from rest_framework import permissions, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from autorisations.rbac import a_le_droit
from customer.models import Client
from institutionnel.authentication import KnoxOrDemoTokenAuthentication

from .reprise import PAIEMENTS, ErreurReprise, controler, enregistrer, normaliser, reprendre, supprimer

AUTHENTIFICATION = [KnoxOrDemoTokenAuthentication, BasicAuthentication]
PAGE = 50
LIGNES_MAX = 2000

# Colonnes du modèle Excel : (titre, clé de l'API ou de la résolution, aide)
COLONNES = [
    ("N° client", "IdClient", "Facultatif : numéro du client dans LE PHARE. Sinon le client est cherché par son nom (et son téléphone), créé s'il n'existe pas."),
    ("Nom ou raison sociale", "Nom", "Obligatoire sans n° client."),
    ("Prénoms", "Prenoms", ""),
    ("Téléphone", "Telephone", "Départage les homonymes ; repris sur la fiche d'un nouveau client."),
    ("Type de client", "TypeClient", "Particulier (par défaut) ou Entreprise."),
    ("Compagnie", "Compagnie", "Raison sociale, ex. NSIA ASSURANCES (ou son début)."),
    ("Branche", "Branche", "Automobile, Individuelle Accidents, Voyage, MRH, Santé, Transport, MRP, RC, Dommages."),
    ("Catégorie", "Categorie", "Facultatif : code de la catégorie (ex. 201) ; la première de la branche à défaut."),
    ("N° police compagnie", "NumeroPoliceCompagnie", "Obligatoire."),
    ("Date d'émission", "DateEmission", "jj/mm/aaaa, avant le 1er janvier de l'année en cours."),
    ("Date d'effet", "DateEffet", "jj/mm/aaaa, avant le 1er janvier de l'année en cours."),
    ("Date d'échéance", "DateExpiration", "jj/mm/aaaa."),
    ("Prime nette", "PrimeNette", "Automobile : FGA et CEDEAO compris, comme sur la quittance."),
    ("Accessoires", "Accessoire", ""),
    ("Taxes", "Taxe", ""),
    ("FGA", "Fga", "Automobile, facultatif (compris dans la prime nette)."),
    ("CEDEAO", "Cedeao", "Automobile, facultatif (comprise dans la prime nette)."),
    ("Prime TTC", "PrimeTtc", "Prime nette + accessoires + taxes ; calculée si vide."),
    ("Taux de commission (%)", "TauxCommission", "Facultatif : taux de la compagnie et de la branche à défaut."),
    ("Commission perçue", "CommissionPercue", "Oui ou Non (par défaut)."),
    ("Paiement", "StatutPaiement", "Payée (par défaut), Partiellement payée ou Impayée."),
    ("Montant encaissé", "MontantEncaisse", "Paiement partiel seulement."),
    ("Immatriculation", "Immatriculation", "Automobile : obligatoire."),
    ("Marque", "Marque", "Automobile."),
    ("Modèle", "Modele", "Automobile."),
    ("Puissance (CV)", "Puissance", "Automobile."),
    ("Places", "Places", "Automobile."),
    ("Énergie", "Energie", "Essence, Diésel, Électrique, Hybride."),
    ("Valeur neuve", "ValeurNeuve", ""),
    ("Valeur vénale", "ValeurVenale", ""),
    ("Date de mise en circulation", "DateMec", "jj/mm/aaaa."),
    ("Description du risque", "Risque", "Autres branches : objet assuré, lieu, capitaux…"),
    ("Observation", "Observation", ""),
]
SYNONYMES_BRANCHES = {
    "AUTO": 1, "AUTOMOBILE": 1, "IA": 2, "INDIVIDUELLE": 2, "INDIVIDUELLE ACCIDENT": 2, "INDIVIDUELLE ACCIDENTS": 2,
    "VOYAGE": 3, "ASSURANCE VOYAGE": 3, "MRH": 4, "MULTIRISQUE HABITATION": 4, "MULTIRISQUES HABITATION": 4, "SANTE": 5,
    "TRANSPORT": 6, "MRP": 7, "MULTIRISQUE PROFESSIONNELLE": 7, "MULTIRISQUES PROFESSIONNELLE": 7, "RC": 8,
    "RESPONSABILITE CIVILE": 8, "DOMMAGES": 9, "TOUS DOMMAGES": 9,
}


def _lignes_sql(cursor, sql, params=None):
    cursor.execute(sql, params or [])
    colonnes = [c[0] for c in cursor.description]
    return [dict(zip(colonnes, ligne)) for ligne in cursor.fetchall()]


def _iso(v):
    return v.date().isoformat() if isinstance(v, datetime) else v.isoformat() if isinstance(v, date) else v


def _erreur(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


# ------------------------------------------------------------------ liste
@api_view(["GET", "POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def reprises(request):
    """GET : liste filtrée (annee, compagnie, produit, paiement, commission=A_PERCEVOIR, q, page) ; POST : une affaire."""
    if request.method == "POST":
        try:
            resultat = reprendre(request.data, request.user)
        except ErreurReprise as erreur:
            return _erreur(str(erreur))
        return Response({**resultat, "message": f"Affaire reprise : police {resultat['NumeroPolice']}, quittance "
                                                 f"{resultat['NumeroQuittance']}."}, status=status.HTTP_201_CREATED)
    p = request.query_params
    conditions, params = ["TRUE"], []
    if p.get("annee"):
        conditions.append("EXTRACT(YEAR FROM c.dateeffet) = %s")
        params.append(int(p["annee"]))
    if p.get("compagnie"):
        conditions.append("c.idcompagnie = %s")
        params.append(int(p["compagnie"]))
    if p.get("produit"):
        conditions.append("c.idproduit = %s")
        params.append(int(p["produit"]))
    paiement = p.get("paiement")
    if paiement == "PAYEE":
        conditions.append("q.primettc - COALESCE(q.mt_encaisse, 0) <= 0")
    elif paiement == "PARTIELLE":
        conditions.append("COALESCE(q.mt_encaisse, 0) > 0 AND q.primettc - COALESCE(q.mt_encaisse, 0) > 0")
    elif paiement == "IMPAYEE":
        conditions.append("COALESCE(q.mt_encaisse, 0) = 0")
    if p.get("commission") == "A_PERCEVOIR":
        conditions.append("NOT r.commission_percue AND COALESCE(c.commissionintermediaire, 0) > 0")
    if p.get("q"):
        conditions.append("(UPPER(c.numeropolice) LIKE %s OR UPPER(COALESCE(c.numeropolicecompagnie, '')) LIKE %s "
                          "OR UPPER(TRIM(cl.nom || ' ' || COALESCE(cl.prenoms, ''))) LIKE %s OR UPPER(q.numeroquittance) LIKE %s)")
        terme = f"%{str(p['q']).strip().upper()}%"
        params += [terme] * 4
    where = " AND ".join(conditions)
    base = f"""FROM lephare_reprise r
               JOIN stdcontrat c ON c.idcontrat = r.idcontrat
               JOIN stdquittance q ON q.idquittance = r.idquittance
               LEFT JOIN stdclient cl ON cl.idclient = c.idclient
               LEFT JOIN stdcompagnie co ON co.idcompagnie = c.idcompagnie
               LEFT JOIN stdproduit pr ON pr.idproduit = c.idproduit
               WHERE {where}"""
    page = max(1, int(p.get("page") or 1))
    with connection.cursor() as cursor:
        totaux = _lignes_sql(cursor, f"""SELECT COUNT(*) AS nombre, COALESCE(SUM(q.primettc), 0) AS ttc,
                                               COALESCE(SUM(q.mt_encaisse), 0) AS encaisse,
                                               COALESCE(SUM(q.primettc - COALESCE(q.mt_encaisse, 0)), 0) AS reste,
                                               COALESCE(SUM(c.commissionintermediaire), 0) AS commission,
                                               COALESCE(SUM(c.commissionintermediaire) FILTER (WHERE NOT r.commission_percue), 0) AS commission_a_percevoir
                                        {base}""", params)[0]
        lignes = _lignes_sql(cursor, f"""SELECT r.id, r.idcontrat, r.mode, r.lot, r.commission_percue, r.creepar, r.idutilisateur,
                                                r.datecreation, c.numeropolice, c.numeropolicecompagnie, c.dateemission, c.dateeffet,
                                                c.dateexpiration, c.idcompagnie, co.raisonsociale AS compagnie, c.idproduit,
                                                pr.libelleproduit AS branche, c.idclient,
                                                TRIM(cl.nom || ' ' || COALESCE(cl.prenoms, '')) AS client,
                                                c.commissionintermediaire AS commission, c.taux_commission,
                                                q.numeroquittance, q.primettc, COALESCE(q.mt_encaisse, 0) AS encaisse
                                         {base}
                                         ORDER BY r.id DESC LIMIT {PAGE} OFFSET %s""", params + [(page - 1) * PAGE])
        annees = [a[0] for a in _lignes_sql_brut(cursor, "SELECT DISTINCT EXTRACT(YEAR FROM c.dateeffet)::int FROM lephare_reprise r "
                                                         "JOIN stdcontrat c ON c.idcontrat = r.idcontrat ORDER BY 1 DESC")]
    resultat = []
    for l in lignes:
        ttc, encaisse = Decimal(l["primettc"] or 0), Decimal(l["encaisse"] or 0)
        statut = "PAYEE" if encaisse >= ttc else "PARTIELLE" if encaisse > 0 else "IMPAYEE"
        resultat.append({
            "Id": l["id"], "IdContrat": l["idcontrat"], "NumeroPolice": l["numeropolice"], "NumeroPoliceCompagnie": l["numeropolicecompagnie"] or "",
            "NumeroQuittance": l["numeroquittance"], "Client": l["client"] or "", "IdClient": l["idclient"],
            "Compagnie": l["compagnie"] or "", "Branche": l["branche"] or "", "DateEmission": _iso(l["dateemission"]),
            "DateEffet": _iso(l["dateeffet"]), "DateExpiration": _iso(l["dateexpiration"]), "PrimeTtc": float(ttc),
            "Encaisse": float(encaisse), "Reste": float(ttc - encaisse), "Paiement": statut, "PaiementLibelle": PAIEMENTS[statut],
            "Commission": float(l["commission"] or 0), "TauxCommission": float(l["taux_commission"] or 0),
            "CommissionPercue": l["commission_percue"], "Mode": l["mode"], "Lot": l["lot"] or "", "CreePar": l["creepar"],
            "Auteur": l["idutilisateur"] == request.user.id, "DateCreation": _iso(l["datecreation"]),
        })
    return Response({
        "Lignes": resultat, "Page": page, "Pages": max(1, -(-int(totaux["nombre"]) // PAGE)), "Annees": annees,
        "Totaux": {"Nombre": int(totaux["nombre"]), "PrimeTtc": float(totaux["ttc"]), "Encaisse": float(totaux["encaisse"]),
                   "Reste": float(totaux["reste"]), "Commission": float(totaux["commission"]),
                   "CommissionAPercevoir": float(totaux["commission_a_percevoir"])},
        "PeutToutSupprimer": a_le_droit(request.user, "contrats.cancel"),
    })


def _lignes_sql_brut(cursor, sql, params=None):
    cursor.execute(sql, params or [])
    return cursor.fetchall()


@api_view(["DELETE"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def reprise(request, pk):
    try:
        resultat = supprimer(pk, request.user, a_le_droit(request.user, "contrats.cancel"))
    except ErreurReprise as erreur:
        return _erreur(str(erreur))
    return Response({**resultat, "message": f"Reprise retirée : police {resultat['NumeroPolice']} et quittance {resultat['NumeroQuittance']} supprimées."})


@api_view(["PATCH"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def commission(request, pk):
    """PATCH {Percue: bool} : commission de la reprise perçue (date du jour) ou à percevoir."""
    percue = str(request.data.get("Percue")).lower() in ("true", "1", "oui")
    with connection.cursor() as cursor:
        cursor.execute("UPDATE lephare_reprise SET commission_percue = %s, date_commission_percue = %s WHERE id = %s",
                       [percue, date.today() if percue else None, pk])
        if not cursor.rowcount:
            return _erreur("Reprise introuvable.", status.HTTP_404_NOT_FOUND)
    return Response({"Id": pk, "CommissionPercue": percue})


@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def referentiels(request):
    """Listes de l'écran : compagnies actives, branches actives et leurs catégories, énergies, marques."""
    with connection.cursor() as cursor:
        compagnies = _lignes_sql(cursor, "SELECT idcompagnie AS id, raisonsociale AS nom FROM stdcompagnie "
                                         "WHERE idcompagnie > 0 AND COALESCE(active, true) ORDER BY raisonsociale")
        produits = _lignes_sql(cursor, "SELECT idproduit AS id, libelleproduit AS libelle FROM stdproduit "
                                       "WHERE active AND idproduit BETWEEN 1 AND 9 ORDER BY idproduit")
        for p in produits:
            p["categories"] = [{"id": t, "libelle": f"{c} — {l}", "code": c}
                               for t, l, c in _lignes_sql_brut(cursor, "SELECT id_tarif, libelle_tarif, TRIM(code_categorie) "
                                                                       "FROM fn_liste_tarif_produit(%s) ORDER BY 3, 1", [p["id"]])]
        energies = _lignes_sql(cursor, "SELECT idenergie AS id, libelle FROM stdenergie WHERE idenergie > 0 ORDER BY 1")
        marques = _lignes_sql(cursor, "SELECT idmarque AS id, libellemarque AS libelle FROM stdmarque ORDER BY libellemarque")
    return Response({"Compagnies": compagnies, "Produits": produits, "Energies": energies, "Marques": marques,
                     "AnneeLimite": date.today().year})


# ------------------------------------------------------------------ import Excel
@api_view(["GET"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
def modele(request):
    """Modèle Excel : une ligne par quittance reprise, aide de chaque colonne en deuxième feuille."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Affaires antérieures"
    ws.append([t for t, _, _ in COLONNES])
    ws.append(["", "KOUASSI", "AMANI JEAN", "0700000000", "Particulier", "NSIA ASSURANCES", "Automobile", "201", "PC-2023-001245",
               "15/03/2023", "15/03/2023", "14/03/2024", 98205, 5000, 14965, "", 1000, 118170, 20, "Non", "Payée", "",
               "AB 1234 CI", "TOYOTA", "COROLLA", 8, 5, "Essence", 15000000, 9000000, "10/01/2019", "", "Ligne d'exemple : à remplacer"])
    for cellule in ws[1]:
        cellule.font = Font(bold=True, color="FFFFFF")
        cellule.fill = PatternFill("solid", fgColor="1F4E78")
        cellule.alignment = Alignment(wrap_text=True, vertical="center")
    for i, (titre, _, _) in enumerate(COLONNES, start=1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = max(14, min(30, len(titre) + 4))
    ws.freeze_panes = "A2"
    aide = wb.create_sheet("Aide")
    aide.append(["Colonne", "Contenu attendu"])
    for titre, _, texte in COLONNES:
        aide.append([titre, texte])
    aide.column_dimensions["A"].width = 30
    aide.column_dimensions["B"].width = 110
    for cellule in aide[1]:
        cellule.font = Font(bold=True)
    tampon = io.BytesIO()
    wb.save(tampon)
    reponse = HttpResponse(tampon.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    reponse["Content-Disposition"] = 'attachment; filename="modele_reprise_affaires_anterieures.xlsx"'
    return reponse


def _lire_fichier(fichier):
    """Lignes du fichier (dict par clé de COLONNES, numéro de ligne Excel). Lève ErreurReprise."""
    try:
        wb = load_workbook(fichier, data_only=True, read_only=True)
    except Exception as erreur:  # fichier illisible
        raise ErreurReprise(f"Fichier Excel illisible : {str(erreur).splitlines()[0]}") from erreur
    ws = wb.worksheets[0]
    lignes = list(ws.iter_rows(values_only=True))
    if not lignes:
        raise ErreurReprise("Le fichier est vide.")
    entetes = [normaliser(str(v or "")).replace("'", " ") for v in lignes[0]]
    index = {}
    for titre, cle, _ in COLONNES:
        t = normaliser(titre).replace("'", " ")
        if t in entetes:
            index[cle] = entetes.index(t)
    manquantes = [titre for titre, cle, _ in COLONNES if cle in ("Compagnie", "Branche", "NumeroPoliceCompagnie", "DateEffet",
                                                                  "DateExpiration", "PrimeNette") and cle not in index]
    if manquantes:
        raise ErreurReprise("Colonnes absentes de la 1re ligne : " + ", ".join(manquantes) + " (téléchargez le modèle).")
    resultat = []
    for numero, ligne in enumerate(lignes[1:], start=2):
        valeurs = {cle: ligne[i] if i < len(ligne) else None for cle, i in index.items()}
        if all(v in (None, "") for v in valeurs.values()):
            continue
        if "ligne d'exemple" in str(valeurs.get("Observation") or "").lower():
            continue
        valeurs["_ligne"] = numero
        resultat.append(valeurs)
    if len(resultat) > LIGNES_MAX:
        raise ErreurReprise(f"{LIGNES_MAX} lignes au plus par fichier : découpez-le.")
    return resultat


class _Resolution:
    """Compagnies, branches, catégories, énergies et marques désignées en clair dans le fichier ; clients retrouvés."""

    def __init__(self, cursor):
        self.cursor = cursor
        self.compagnies = [(i, normaliser(n)) for i, n in _lignes_sql_brut(cursor, "SELECT idcompagnie, raisonsociale FROM stdcompagnie WHERE idcompagnie > 0")]
        self.produits = {i: normaliser(l) for i, l in _lignes_sql_brut(cursor, "SELECT idproduit, libelleproduit FROM stdproduit WHERE idproduit BETWEEN 1 AND 9")}
        self.energies = {normaliser(l): i for i, l in _lignes_sql_brut(cursor, "SELECT idenergie, libelle FROM stdenergie")}
        self.energies.update({"DIESEL": 2, "GASOIL": 2, "GAZOIL": 2})
        self.marques = {normaliser(l): i for i, l in _lignes_sql_brut(cursor, "SELECT idmarque, libellemarque FROM stdmarque")}
        self.nouveaux = {}

    def compagnie(self, valeur, id_produit=None):
        """Raison sociale exacte, sinon son début (« NSIA ») ; une affaire non-vie écarte les compagnies vie
        (NSIA VIE, ALLIANZ CI VIE) quand le nom désigne aussi la compagnie IARD."""
        texte = normaliser(valeur)
        if not texte:
            raise ErreurReprise("Compagnie obligatoire.")
        if texte.isdigit() and any(i == int(texte) for i, _ in self.compagnies):
            return int(texte)
        exactes = [i for i, n in self.compagnies if n == texte]
        trouvees = exactes or [i for i, n in self.compagnies if n.startswith(texte) or texte in n]
        if len(trouvees) > 1 and id_produit and id_produit <= 9:
            non_vie = [i for i in trouvees if " VIE" not in f" {dict(self.compagnies)[i]} "]
            trouvees = non_vie or trouvees
        if len(trouvees) != 1:
            noms = ", ".join(dict(self.compagnies)[i] for i in trouvees[:4])
            raise ErreurReprise(f"Compagnie « {valeur} » inconnue." if not trouvees else f"Compagnie « {valeur} » ambiguë ({noms}) : précisez.")
        return trouvees[0]

    def produit(self, valeur):
        texte = normaliser(valeur)
        if texte in SYNONYMES_BRANCHES:
            return SYNONYMES_BRANCHES[texte]
        trouves = [i for i, l in self.produits.items() if l == texte or l.startswith(texte)]
        if len(trouves) != 1:
            raise ErreurReprise(f"Branche « {valeur} » inconnue.")
        return trouves[0]

    def categorie(self, id_produit, valeur):
        texte = normaliser(valeur)
        if not texte:
            return None
        for t, l, c in _lignes_sql_brut(self.cursor, "SELECT id_tarif, libelle_tarif, TRIM(code_categorie) FROM fn_liste_tarif_produit(%s) "
                                                      "ORDER BY 3, 1", [id_produit]):
            if texte in (c, normaliser(l)):
                return t
        raise ErreurReprise(f"Catégorie « {valeur} » inconnue pour cette branche.")

    def client(self, v):
        if str(v.get("IdClient") or "").strip():
            return int(float(str(v["IdClient"]).strip()))
        nom = normaliser(v.get("Nom"))
        if not nom:
            raise ErreurReprise("Client : n° client ou nom obligatoire.")
        prenoms = normaliser(v.get("Prenoms"))
        telephone = "".join(ch for ch in str(v.get("Telephone") or "") if ch.isdigit())
        cle = (nom, prenoms, telephone)
        if cle in self.nouveaux:
            return self.nouveaux[cle]
        candidats = [(i, t, m) for i, n, p, t, m in _lignes_sql_brut(
            self.cursor, "SELECT idclient, nom, prenoms, telephone, mobile FROM stdclient WHERE statut <> 'A' "
                         "AND UPPER(TRIM(nom)) = %s", [str(v.get("Nom")).strip().upper()]) if normaliser(n) == nom and normaliser(p) == prenoms]
        if telephone and len(candidats) > 1:
            candidats = [c for c in candidats if telephone in "".join(ch for ch in f"{c[1] or ''} {c[2] or ''}" if ch.isdigit())] or candidats
        if len(candidats) > 1:
            raise ErreurReprise(f"{len(candidats)} clients « {nom} {prenoms} » : indiquez le n° client "
                                f"({', '.join(str(c[0]) for c in candidats[:5])}).")
        if candidats:
            return candidats[0][0]
        entreprise = normaliser(v.get("TypeClient")).startswith("ENTREPRISE")
        client = Client.objects.create(
            Nom=str(v.get("Nom")).strip()[:150], Prenoms=str(v.get("Prenoms") or "").strip()[:150] or None,
            Telephone=str(v.get("Telephone") or "").strip()[:20], Mobile=str(v.get("Telephone") or "").strip()[:20],
            Particulier="F" if entreprise else "V", Statut="V", Vip="V", CreeCie="V", NumeroCompte="NUMERO-COMPTE",
            Adresse1="", Adresse2="", Email="", Fonction="",
        )
        self.nouveaux[cle] = client.IdClient
        return client.IdClient

    def donnees(self, v):
        d = {k: v.get(k) for _, k, _ in COLONNES}
        d["IdProduit"] = self.produit(v.get("Branche"))
        d["IdCompagnie"] = self.compagnie(v.get("Compagnie"), d["IdProduit"])
        d["IdClient"] = self.client(v)
        d["IdTarif"] = self.categorie(d["IdProduit"], v.get("Categorie"))
        if str(v.get("Energie") or "").strip():
            d["IdEnergie"] = self.energies.get(normaliser(v.get("Energie")))
            if not d["IdEnergie"]:
                raise ErreurReprise(f"Énergie « {v.get('Energie')} » inconnue.")
        if str(v.get("Marque") or "").strip():
            d["IdMarque"] = self.marques.get(normaliser(v.get("Marque"))) or 0
            if not d["IdMarque"]:
                d["Modele"] = f"{v.get('Marque')} {v.get('Modele') or ''}".strip()
        return d


def _importer(fichier, utilisateur, executer):
    """Toutes les lignes reprises dans une transaction (point de sauvegarde par ligne) : les lignes refusées sont
    signalées ; l'analyse annule tout à la fin, l'import garde les lignes correctes."""
    lignes = _lire_fichier(fichier)
    lot = uuid.uuid4().hex[:12]
    compte_rendu = []
    with transaction.atomic(), connection.cursor() as cursor:
        resolution = _Resolution(cursor)
        for v in lignes:
            point = transaction.savepoint()
            nouveaux_avant = len(resolution.nouveaux)
            try:
                donnees = resolution.donnees(v)
                r = controler(cursor, donnees)
                cree = enregistrer(cursor, r, utilisateur, mode="import", lot=lot)
                transaction.savepoint_commit(point)
                compte_rendu.append({
                    "Ligne": v["_ligne"], "Statut": "OK", "Message": "",
                    "Client": f"{v.get('Nom') or ''} {v.get('Prenoms') or ''}".strip() or f"n° {donnees['IdClient']}",
                    "NouveauClient": len(resolution.nouveaux) > nouveaux_avant, "NumeroPoliceCompagnie": r["NumeroPoliceCompagnie"],
                    "DateEffet": r["DateEffet"].isoformat(), "PrimeTtc": float(r["PrimeTtc"]), "Paiement": PAIEMENTS[r["StatutPaiement"]],
                    "NumeroPolice": cree["NumeroPolice"], "NumeroQuittance": cree["NumeroQuittance"],
                })
            except (ErreurReprise, ValueError) as erreur:
                transaction.savepoint_rollback(point)
                resolution.nouveaux = dict(list(resolution.nouveaux.items())[:nouveaux_avant])
                compte_rendu.append({"Ligne": v["_ligne"], "Statut": "ERREUR", "Message": str(erreur),
                                     "Client": f"{v.get('Nom') or ''} {v.get('Prenoms') or ''}".strip(),
                                     "NumeroPoliceCompagnie": str(v.get("NumeroPoliceCompagnie") or ""), "PrimeTtc": None})
        if not executer:
            transaction.set_rollback(True)
    ok = [l for l in compte_rendu if l["Statut"] == "OK"]
    return {
        "Lot": lot if executer else "", "Lignes": compte_rendu, "Correctes": len(ok), "Erreurs": len(compte_rendu) - len(ok),
        "NouveauxClients": sum(1 for l in ok if l.get("NouveauClient")), "PrimeTtc": sum(l["PrimeTtc"] for l in ok),
        "Importe": executer,
    }


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def import_analyse(request):
    """POST (multipart : fichier) : chaque ligne contrôlée comme à l'import, rien n'est enregistré."""
    fichier = request.FILES.get("fichier")
    if not fichier:
        return _erreur("Choisissez le fichier Excel.")
    try:
        return Response(_importer(fichier, request.user, executer=False))
    except ErreurReprise as erreur:
        return _erreur(str(erreur))


@api_view(["POST"])
@authentication_classes(AUTHENTIFICATION)
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def import_fichier(request):
    """POST (multipart : fichier) : lignes correctes reprises (un lot), lignes refusées signalées."""
    fichier = request.FILES.get("fichier")
    if not fichier:
        return _erreur("Choisissez le fichier Excel.")
    try:
        return Response(_importer(fichier, request.user, executer=True))
    except ErreurReprise as erreur:
        return _erreur(str(erreur))
