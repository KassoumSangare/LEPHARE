"""
Questionnaires prospects (dossier « QUESTIONNAIRE POUR PROSPECT » reçu le 2026-10-20).

Le commercial télécharge le questionnaire de la branche et l'envoie au client ; le client le remplit et le renvoie ;
le questionnaire rempli est déposé dans l'application (QuestionnaireProspect), rattaché au prospect du suivi
commercial, puis étudié jusqu'au devis.

Modèles (dossier modeles_questionnaires/) : les fichiers Word et Excel reçus sont gardés tels quels (le .doc enregistré
en .docx, seul format Word relu au retour) ; les PDF sont devenus des documents Word (conversion par Word avec cases à
cocher cliquables, ou reconstruction quand le PDF était un scan ou se convertissait mal ; « SEXE » ajouté au bulletin
d'adhésion Santé pour l'import des adhérents). Chaque fichier est téléchargé sous le titre du questionnaire
(nom_fichier). Le questionnaire rempli est relu par lecture_questionnaires.py.
"""

import os
import re

DOSSIER_MODELES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modeles_questionnaires")

# Formats acceptés pour le questionnaire rempli : celui du modèle, un PDF ou la photo d'un questionnaire papier
EXTENSIONS_DEPOT = ("docx", "doc", "xlsx", "xls", "pdf", "jpg", "jpeg", "png")
TAILLE_MAX_DEPOT = 20 * 1024 * 1024

# Étapes d'un questionnaire déposé
STATUT_RECU, STATUT_ETUDE, STATUT_A_COMPLETER, STATUT_DEVIS = "Reçu", "En étude", "À compléter", "Devis établi"
STATUTS = (STATUT_RECU, STATUT_ETUDE, STATUT_A_COMPLETER, STATUT_DEVIS)

FORMAT_WORD, FORMAT_EXCEL = "Word", "Excel"

MODELES = [
    {
        "code": "auto_fiche_tarification",
        "titre": "Fiche pour tarification - Assurance Automobile",
        "fichier": "auto_fiche_tarification.xlsx",
        "format": FORMAT_EXCEL,
        "origine": "Excel",
        "branche": "Automobile",
        "compagnie": "OREOLE",
        "description": "Un véhicule par ligne, de 1 à 40 : la fiche sert au mono comme à la flotte.",
        "rubriques": ["Marque, type et immatriculation", "Date de 1re mise en circulation", "Genre (case à cocher) et énergie",
                      "Puissance fiscale, charge utile ou cylindrée", "Nombre de places", "Valeurs neuve et vénale"],
        "route_devis": "/user/quotes/auto",
    },
    {
        "code": "sante_questionnaire_cotation",
        "titre": "Questionnaire Cotation - Assurance Santé",
        "fichier": "sante_questionnaire_cotation.docx",
        "format": FORMAT_WORD,
        "origine": "PDF converti en Word",
        "branche": "Santé",
        "compagnie": "NSIA",
        "description": "Premier contact d'une entreprise pour un contrat Santé groupe : de quoi établir la cotation.",
        "rubriques": ["Coordonnées et activité de l'entreprise", "Population à assurer (adultes, enfants)",
                      "Taux de couverture, étendue territoriale", "Centres de soins et système de gestion",
                      "Extensions (évacuation sanitaire, accidents du travail)", "Antécédents d'assurance"],
        "route_devis": "/user/quotes/sante",
    },
    {
        "code": "sante_bulletin_adhesion",
        "titre": "Bulletin d'adhésion - Assurance Santé",
        "fichier": "sante_bulletin_adhesion.docx",
        "format": FORMAT_WORD,
        "origine": "PDF converti en Word",
        "branche": "Santé",
        "compagnie": "NSIA",
        "description": "À faire remplir par chaque salarié adhérent, pour lui, son conjoint et ses enfants à charge.",
        "rubriques": ["Société adhérente et salarié", "Assuré et conjoint", "Enfants à charge (5 au plus)",
                      "Questionnaire médical par personne (OUI / NON)", "Déclaration signée « Lu et approuvé »"],
        "route_devis": "/user/quotes/sante",
    },
    {
        "code": "individuelle_accidents",
        "titre": "Formulaire - Assurance Individuelle Accidents",
        "fichier": "individuelle_accidents.xlsx",
        "format": FORMAT_EXCEL,
        "origine": "Excel",
        "branche": "Individuelle Accidents",
        "compagnie": "OREOLE",
        "description": "Liste des personnes à assurer, une par ligne (50 au plus).",
        "rubriques": ["Nom et prénoms", "Date de naissance", "Profession", "Capital Décès", "Capital IPT (invalidité permanente totale)"],
        "route_devis": "/user/quotes/ia",
    },
    {
        "code": "retraite_complementaire",
        "titre": "Formulaire Assurance Retraite Complémentaire",
        "fichier": "retraite_complementaire.xlsx",
        "format": FORMAT_EXCEL,
        "origine": "Excel",
        "branche": "Retraite complémentaire",
        "compagnie": "OREOLE",
        "description": "Personnel à couvrir, un salarié par ligne : la cotation se fait avec la compagnie Vie.",
        "rubriques": ["Matricule", "Date d'embauche", "Date de naissance", "Fonction et catégorie", "Salaire brut"],
        "route_devis": None,
    },
    {
        "code": "multirisque_professionnelle",
        "titre": "Formulaire de déclaration de risque - Multirisque Industrielle",
        "fichier": "multirisque_professionnelle.docx",
        "format": FORMAT_WORD,
        "origine": "Word",
        "branche": "Multirisque professionnelle",
        "compagnie": "OREOLE",
        "description": "Déclaration de risque des locaux professionnels ou industriels, site par site.",
        "rubriques": ["Informations générales et activité", "Installations électriques, chauffage, éléments aggravants",
                      "Aménagements, matériel et magasins", "Prévention incendie et vol", "Antécédents du risque",
                      "Capitaux à assurer, bris de machine, protection financière"],
        "route_devis": "/user/quotes/mrp",
    },
    {
        "code": "tous_risques_chantier",
        "titre": "Formulaire de déclaration de risque - Tous Risques Chantier",
        "fichier": "tous_risques_chantier.docx",
        "format": FORMAT_WORD,
        "origine": "PDF converti en Word",
        "branche": "Tous risques chantier",
        "compagnie": "SMABTP",
        "description": "Opération de construction ou de montage : intervenants, chantier, durée et garanties souhaitées.",
        "rubriques": ["Souscripteur et intervenants du marché", "Présentation de l'opération et durée des travaux",
                      "Spécificités du montage ou du chantier", "Garanties de base et optionnelles (OUI / NON)",
                      "Documents techniques à joindre"],
        "route_devis": "/user/quotes/tous-dommages",
    },
    {
        "code": "transport_questionnaire",
        "titre": "Questionnaire Assurance Transport",
        "fichier": "transport_questionnaire.docx",
        "format": FORMAT_WORD,
        "origine": "PDF converti en Word",
        "branche": "Transport",
        "compagnie": "OREOLE",
        "description": "Marchandises transportées par voie maritime, aérienne, terrestre ou ferroviaire.",
        "rubriques": ["Proposant et activité", "Nature des marchandises, emballages, conditionnement",
                      "Quantité prévisionnelle et plein par expédition", "Mode de transport, embarquement, destination",
                      "Type de police et garanties souhaitées (OUI)"],
        "route_devis": "/user/quotes/transport/hors-guce",
    },
    {
        "code": "transport_facultes",
        "titre": "Questionnaire Assurance Facultés",
        # Reçu en .doc, enregistré en .docx (même mise en page) pour être lu au retour du client
        "fichier": "transport_facultes.docx",
        "format": FORMAT_WORD,
        "origine": "Word",
        "branche": "Transport",
        "compagnie": "OREOLE",
        "description": "Facultés (marchandises) à l'import ou à l'export : expéditions, conteneurs et chiffre d'affaires.",
        "rubriques": ["Proposant et genre de commerce", "Marchandises et emballages", "Modes d'expédition et provenances",
                      "Conteneurs, ports et aérodromes", "Valeur maximale par navire, camion, avion",
                      "Garanties demandées et chiffre d'affaires"],
        "route_devis": "/user/quotes/transport/hors-guce",
    },
    {
        "code": "transport_facultes_terrestres",
        "titre": "Questionnaire Assurance Transport de marchandises par voies terrestres",
        "fichier": "transport_facultes_terrestres.docx",
        "format": FORMAT_WORD,
        "origine": "Word",
        "branche": "Transport",
        "compagnie": "OREOLE",
        "description": "Affaire nouvelle facultés terrestres : marchandises transportées par camion.",
        "rubriques": ["Assuré, profession et adresse", "Marchandise, risques spéciaux et emballage",
                      "Véhicules et transport", "Type de police", "Garanties souhaitées"],
        "route_devis": "/user/quotes/transport/hors-guce",
    },
]
PAR_CODE = {m["code"]: m for m in MODELES}


def extension(nom):
    return nom.rsplit(".", 1)[-1].lower() if "." in (nom or "") else ""


def nom_fichier_sur(texte):
    """Nom de fichier valable sous Windows comme ailleurs : sans \\ / : * ? " < > | ni caractères de contrôle."""
    texte = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", texte or "")
    return re.sub(r"\s+", " ", texte).strip(" .") or "questionnaire"


def nom_telechargement(modele):
    """Le fichier porte le titre du questionnaire : « Questionnaire Assurance Transport.docx »."""
    return f"{nom_fichier_sur(modele['titre'])}.{extension(modele['fichier'])}"


def chemin_modele(modele):
    return os.path.join(DOSSIER_MODELES, modele["fichier"])
