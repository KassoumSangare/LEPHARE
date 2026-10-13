# MINENE SANTÉ réglable dans l'administration (Réglages Santé MINENE) : ce qui était écrit dans les
# fonctions de la base (primes de base, surprimes, âges, capitaux et primes IA / RC) et dans les imprimés
# (barème de soins, délais de carence, clause d'ajustement).
#
#   - lephare_sante_formule : une ligne par formule MINENE (offres 17-22, 175, 176, 181) : prime de base,
#     taille de la famille, taux de couverture et plafonds du barème de soins.
#   - lephare_parametre, groupes minene_* : IA et RC chef de famille, surprimes et âges, délais de
#     carence, suivi du portefeuille, clause d'ajustement.
#
# Valeurs d'origine = celles appliquées jusqu'ici, tirées des documents OREOLE (Desktop\_OREOLE
# ASSURANCE\SANTE) : TARIFICATION MINENE SANTE.xlsx (primes), BAREME_70-80.pdf (barème 70 %-80 %, aussi
# appliqué aux formules VTC dont aucun barème n'a été fourni), cp_MINENE.pdf (CP) et, pour le 80 %-80 %,
# BAREMES DE SOINS- MINENE SANTE- 80% Tous actes (2).docx reçu le 2026-10-12 : plafonds par option
# (SOLO 1 000 000 F ; FAMILLE et FAMILLE PLUS 2 000 000 F, optique, dentaire et accouchement hors
# structure relevés). Une valeur déjà modifiée dans l'administration n'est pas écrasée.

from decimal import Decimal

from django.db import migrations, models

COMPOSITION_SOLO = "Assuré principal sans enfant, Monsieur ou Madame"
COMPOSITION_FAMILLE = "M + Mme + 1 enfant ou Mme + M + 1 enfant ou Mme + 2 enfants ou M + 2 enfants"
COMPOSITION_FAMILLE_PLUS = "M + Mme + 4 enfants ou Mme + M + 4 enfants ou Mme + 5 enfants ou M + 5 enfants"

# Barème 70 %-80 % (BAREME_70-80.pdf), identique pour les trois options
BAREME_70_80 = dict(
    TauxSoinsExternes=70, TauxHospitalisation=80, ChambreParJour=20000, AmbulanceParCas=20000,
    AccouchementSimple=150000, AccouchementGemellaire=200000, AccouchementChirurgical=300000,
    AccouchementHorsStructure=50000, OptiqueAdulte=50000, OptiqueEnfant=40000, DentaireParPersonne=50000,
    PlafondAnnuel=1000000,
)
# Barème 80 %-80 % (document Word du 2026-10-12)
BAREME_80_SOLO = dict(BAREME_70_80, TauxSoinsExternes=80, DentaireParPersonne=80000)
BAREME_80_FAMILLE = dict(
    BAREME_70_80, TauxSoinsExternes=80, AccouchementHorsStructure=80000, OptiqueAdulte=70000,
    OptiqueEnfant=50000, DentaireParPersonne=100000, PlafondAnnuel=2000000,
)

SOLO = dict(Option="SOLO", Composition=COMPOSITION_SOLO, PersonnesMin=1, PersonnesMax=1)
FAMILLE = dict(Option="FAMILLE", Composition=COMPOSITION_FAMILLE, PersonnesMin=2, PersonnesMax=3)
FAMILLE_PLUS = dict(Option="FAMILLE PLUS", Composition=COMPOSITION_FAMILLE_PLUS, PersonnesMin=4, PersonnesMax=6)

FORMULES = [
    # (offre, ordre, option, prime de base, barème) — primes : fn_get_prime_base_minene_sante d'origine
    (17, 1, SOLO, 349148, BAREME_70_80),
    (18, 2, FAMILLE, 543556, BAREME_70_80),
    (19, 3, FAMILLE_PLUS, 728741, BAREME_70_80),
    (175, 4, SOLO, 523722, BAREME_80_SOLO),
    (176, 5, FAMILLE, 760978, BAREME_80_FAMILLE),
    (181, 6, FAMILLE_PLUS, 1039122, BAREME_80_FAMILLE),
    (20, 7, SOLO, 349148, BAREME_70_80),
    (21, 8, FAMILLE, 543556, BAREME_70_80),
    (22, 9, FAMILLE_PLUS, 728741, BAREME_70_80),
]

CLAUSE_AJUSTEMENT = "\n".join([
    "à 50 % | Perte du bénéfice du tiers payant",
    "de 51% à 65% | Réduction de 10%",
    "de 66% à 70% | Aucune modification",
    "de 71 à 80% | 15% de majoration",
    "de 81% à 90% | 20% de majoration",
    "de 91% à 100% | 30% de majoration",
    "de 101% à 110% | 35% de majoration",
    "de 111% à 115% | 45% de majoration",
    "Au-delà de 115% | Résiliation pour ordre de la police en vue d’une nouvelle étude statistique pour une éventuelle nouvelle offre",
])

PARAMETRES = [
    # (clé, groupe, libellé, aide, type, valeur, unité, min, max, ordre)
    # Individuelle Accidents MINENE (offre 66)
    ("sante.minene.ia_capital_deces", "minene_ia", "Capital décès",
     "Versé aux ayants droit en cas de décès accidentel de l'assuré principal (barème et CP).", "montant", "2000000", "F", 1, None, 1),
    ("sante.minene.ia_capital_ipt", "minene_ia", "Capital incapacité permanente totale (IPT)",
     "Versé à l'assuré principal en cas d'incapacité permanente totale.", "montant", "2000000", "F", 1, None, 2),
    ("sante.minene.ia_frais_medicaux", "minene_ia", "Frais médicaux",
     "Remboursement des frais de traitement à la suite d'un accident.", "montant", "100000", "F", 0, None, 3),
    ("sante.minene.ia_prime_nette", "minene_ia", "Prime nette IA par adhérent",
     "Répartie entre les garanties au prorata des capitaux ; accessoire (barème Accessoires) et taxe en sus.", "montant", "14524", "F", 1, None, 4),
    # RC chef de famille MINENE (offre 67)
    ("sante.minene.rc_dommages_corporels", "minene_rc", "Dommages corporels",
     "Capital garanti, franchise néant.", "montant", "50000000", "F", 1, None, 1),
    ("sante.minene.rc_intoxications", "minene_rc", "Intoxications alimentaires",
     "Capital garanti, franchise néant.", "montant", "5000000", "F", 1, None, 2),
    ("sante.minene.rc_dommages_materiels", "minene_rc", "Dommages matériels",
     "Capital garanti.", "montant", "10000000", "F", 1, None, 3),
    ("sante.minene.rc_franchise_taux", "minene_rc", "Franchise dommages matériels",
     "Pourcentage du sinistre laissé à la charge de l'assuré.", "pourcentage", "10", "%", 0, 100, 4),
    ("sante.minene.rc_franchise_minimum", "minene_rc", "Franchise dommages matériels : minimum",
     "", "montant", "20000", "F", 0, None, 5),
    ("sante.minene.rc_franchise_maximum", "minene_rc", "Franchise dommages matériels : maximum",
     "", "montant", "200000", "F", 0, None, 6),
    ("sante.minene.rc_prime_nette", "minene_rc", "Prime nette RC par adhérent",
     "Répartie entre les garanties au prorata des capitaux ; accessoire (barème Accessoires) et taxe en sus.", "montant", "14524", "F", 1, None, 7),
    # Surprimes et âges
    ("sante.minene.surprime_affection", "minene_surprimes", "Surprime par affection chronique",
     "Pourcentage de la prime de base de la formule, par affection déclarée.", "pourcentage", "30", "%", 0, 200, 1),
    ("sante.minene.affections_max", "minene_surprimes", "Affections chroniques acceptées (au plus)",
     "Nombre d'affections au-delà duquel la saisie d'un assuré Santé est refusée.", "entier", "3", "", 0, 10, 2),
    ("sante.minene.surprime_age_1_debut", "minene_surprimes", "Première surprime d'âge : à partir de",
     "Âge atteint à la date d'effet (adhérent et conjoint).", "entier", "61", "ans", 18, 100, 3),
    ("sante.minene.surprime_age_1_taux", "minene_surprimes", "Première surprime d'âge",
     "Pourcentage de la prime de base, jusqu'à l'âge de la seconde surprime.", "pourcentage", "30", "%", 0, 200, 4),
    ("sante.minene.surprime_age_2_debut", "minene_surprimes", "Seconde surprime d'âge : à partir de",
     "", "entier", "65", "ans", 18, 100, 5),
    ("sante.minene.surprime_age_2_taux", "minene_surprimes", "Seconde surprime d'âge",
     "Pourcentage de la prime de base, jusqu'à l'âge maximum.", "pourcentage", "50", "%", 0, 200, 6),
    ("sante.minene.age_max_adulte", "minene_surprimes", "Âge maximum de l'adhérent et du conjoint",
     "Au-delà, l'assuré est refusé à la saisie.", "entier", "69", "ans", 18, 100, 7),
    ("sante.minene.age_max_enfant", "minene_surprimes", "Âge maximum d'un enfant",
     "Au-delà, un certificat de scolarité de l'année ou un rapport médical est exigé (saisie Santé).", "entier", "21", "ans", 0, 40, 8),
    ("sante.minene.age_max_enfant_certificat", "minene_surprimes", "Âge maximum d'un enfant avec certificat",
     "Au-delà, l'enfant est refusé à la saisie.", "entier", "25", "ans", 0, 40, 9),
    # Délais de carence (CP et barème)
    ("sante.minene.carence_soins_courants", "minene_carence", "Soins courants",
     "Consultations, pharmacie, analyses biologiques et radiologiques.", "entier", "3", "mois", 0, 36, 1),
    ("sante.minene.carence_soins_dentaires", "minene_carence", "Soins dentaires", "", "entier", "3", "mois", 0, 36, 2),
    ("sante.minene.carence_optique", "minene_carence", "Lunetterie et optique médicale", "", "entier", "10", "mois", 0, 36, 3),
    ("sante.minene.carence_maternite", "minene_carence", "Maternité", "Assuré(e) ou conjoint(e).", "entier", "10", "mois", 0, 36, 4),
    ("sante.minene.carence_protheses", "minene_carence", "Prothèses dentaires", "", "entier", "12", "mois", 0, 36, 5),
    ("sante.minene.carence_maladies_chroniques", "minene_carence", "Maladies chroniques", "", "entier", "12", "mois", 0, 36, 6),
    # Gestion des remboursements et clause d'ajustement
    ("sante.minene.etendue_territoriale", "minene_gestion", "Étendue territoriale", "", "texte", "Côte d'Ivoire exclusivement", "", None, None, 1),
    ("sante.minene.optique_periodicite", "minene_gestion", "Renouvellement de l'optique",
     "Les frais d'optique sont pris en charge une fois par période.", "entier", "2", "ans", 1, 10, 2),
    ("sante.minene.quota_bons", "minene_gestion", "Quota d'alerte : à partir du bon de prise en charge n°",
     "Alerte automatique à partir de ce bon de prise en charge.", "entier", "15", "", 1, 100, 3),
    ("sante.minene.quota_pharmacie", "minene_gestion", "Quota d'alerte : frais pharmaceutiques",
     "Alerte automatique à partir de ce montant.", "montant", "200000", "F", 0, None, 4),
    ("sante.minene.seuil_sinistralite", "minene_gestion", "Seuil de sinistralité",
     "Au-delà, l'assuré passe en mode remboursement (fin du tiers payant).", "pourcentage", "50", "%", 0, 200, 5),
    ("sante.minene.clause_ajustement", "minene_gestion", "Clause d'ajustement (rapport S/P)",
     "Une ligne par tranche : « rapport S/P | ajustement ». Les taux « Réduction de x% » et « x% de majoration » sont proposés à la saisie du devis.",
     "texte_long", CLAUSE_AJUSTEMENT, "", None, None, 6),
]


def initialiser(apps, schema_editor):
    Formule = apps.get_model("configuration_api", "SanteFormuleMinene")
    for id_offre, ordre, option, prime, bareme in FORMULES:
        Formule.objects.get_or_create(IdOffre=id_offre, defaults=dict(
            Ordre=ordre, PrimeBase=Decimal(prime), **option, **{k: Decimal(v) for k, v in bareme.items()},
        ))
    ParametreGeneral = apps.get_model("configuration_api", "ParametreGeneral")
    for cle, groupe, libelle, aide, type_, valeur, unite, minimum, maximum, ordre in PARAMETRES:
        ParametreGeneral.objects.get_or_create(Cle=cle, defaults=dict(
            Groupe=groupe, Libelle=libelle, Aide=aide, Type=type_, Valeur=valeur, ValeurOrigine=valeur,
            Unite=unite, Minimum=minimum, Maximum=maximum, Ordre=ordre,
        ))


def retirer(apps, schema_editor):
    ParametreGeneral = apps.get_model("configuration_api", "ParametreGeneral")
    ParametreGeneral.objects.filter(Cle__in=[p[0] for p in PARAMETRES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0082_taxe_garanties_rc"),
    ]

    operations = [
        migrations.CreateModel(
            name="SanteFormuleMinene",
            fields=[
                ("IdOffre", models.IntegerField(db_column="idoffre", primary_key=True, serialize=False)),
                ("Option", models.CharField(db_column="option", max_length=40)),
                ("Composition", models.CharField(blank=True, db_column="composition", default="", max_length=200)),
                ("PersonnesMin", models.PositiveSmallIntegerField(db_column="personnesmin", default=1)),
                ("PersonnesMax", models.PositiveSmallIntegerField(db_column="personnesmax", default=1)),
                ("PrimeBase", models.DecimalField(db_column="primebase", decimal_places=2, max_digits=15)),
                ("TauxSoinsExternes", models.DecimalField(db_column="tauxsoinsexternes", decimal_places=2, max_digits=5)),
                ("TauxHospitalisation", models.DecimalField(db_column="tauxhospitalisation", decimal_places=2, max_digits=5)),
                ("ChambreParJour", models.DecimalField(db_column="chambreparjour", decimal_places=2, max_digits=15)),
                ("AmbulanceParCas", models.DecimalField(db_column="ambulanceparcas", decimal_places=2, max_digits=15)),
                ("AccouchementSimple", models.DecimalField(db_column="accouchementsimple", decimal_places=2, max_digits=15)),
                ("AccouchementGemellaire", models.DecimalField(db_column="accouchementgemellaire", decimal_places=2, max_digits=15)),
                ("AccouchementChirurgical", models.DecimalField(db_column="accouchementchirurgical", decimal_places=2, max_digits=15)),
                ("AccouchementHorsStructure", models.DecimalField(db_column="accouchementhorsstructure", decimal_places=2, max_digits=15)),
                ("OptiqueAdulte", models.DecimalField(db_column="optiqueadulte", decimal_places=2, max_digits=15)),
                ("OptiqueEnfant", models.DecimalField(db_column="optiqueenfant", decimal_places=2, max_digits=15)),
                ("DentaireParPersonne", models.DecimalField(db_column="dentaireparpersonne", decimal_places=2, max_digits=15)),
                ("PlafondAnnuel", models.DecimalField(db_column="plafondannuel", decimal_places=2, max_digits=15)),
                ("Ordre", models.PositiveSmallIntegerField(db_column="ordre", default=0)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
                ("ModifiePar", models.CharField(blank=True, db_column="modifiepar", default="", max_length=150)),
            ],
            options={
                "verbose_name": "Formule MINENE Santé",
                "verbose_name_plural": "Formules MINENE Santé",
                "db_table": "lephare_sante_formule",
                "ordering": ["Ordre", "IdOffre"],
            },
        ),
        migrations.RunPython(initialiser, retirer),
    ]
