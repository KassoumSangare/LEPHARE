# Tableau de dépréciation des véhicules (compte rendu de la séance LE PHARE du 12-10-2026, Automobile) :
# « TABLEAU DE DEPRECIATION APPLICABLE AUX VEHICULES TERRESTRES A MOTEUR EN CI » de la CIEAMI (Chambre
# ivoirienne des experts en automobile et matériels industriels, comtec 20/12/06), relevé sur le scan joint.
# Réglable dans Administration > Réglages Automobile > Dépréciation des véhicules.
#
#   - lephare_depreciation_classe : une ligne du tableau par genre de véhicule, taux par âge (mois) ;
#     « 30/35 » = deux taux, le plus faible appliqué (décision de l'utilisateur du 2026-10-13).
#   - lephare_depreciation_regle : ligne retenue selon le genre, le type, la carrosserie, la catégorie
#     tarifaire (seule donnée des véhicules repris d'URANUS) et la charge utile.
#   - lephare_parametre (groupe auto_depreciation) : taux retenu, valeur au-delà de 10 ans (10 % de la
#     valeur neuve), valeur minimum d'un véhicule en état standard (1 000 000 F).
# La table URANUS stddepreciationvehicule, vide, n'est plus lue (fn_get_valeur_venale_vehicule v2).

from django.db import migrations, models
import django.db.models.deletion

AGES = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84, 96, 108, 120]
FIN = [[80, 85], [85], [85, 90], [85, 90], [85, 90]]  # 78 mois à 10 ans des véhicules utilitaires et lourds

CLASSES = [
    # (code, libellé, kilométrage de référence, taux de 6 mois à 10 ans)
    ("CYCLO_MOTO", "Cyclo + moto", "5 000 km/an",
     [[10], [15], [20], [25], [30], [35], [40], [45], [50], [55], [60], [65], [70], [75], [80], [85], [85, 90]]),
    ("TAXI", "Taxi compteur", "",
     [[20], [40], [50], [60], [70], [75], [80], [85], [87.5], [90]]),
    ("VP", "Voiture particulière", "essence 20 000 km/an, diesel 35 000 km/an",
     [[17.5], [25], [30, 35], [40], [50], [55], [60], [65], [65, 70], [70], [70, 75], [75], [75, 80], [80], [80, 85], [85], [85, 90]]),
    ("UTILITAIRE", "Utilitaire / pick-up / camionnette et 4 x 4", "40 000 km/an",
     [[20], [30], [35, 40], [45], [55], [60], [65], [70], [70, 75], [75], [75, 80], [80]] + FIN),
    ("CAMION_5T", "Camion de 2,5 t à 5 t", "70 000 km/an",
     [[20], [35], [45], [50], [60], [65], [65, 70], [70], [70, 75], [75], [75, 80], [80]] + FIN),
    ("CAMION_PLUS_5T", "Camion de plus de 5 t", "60 000 km/an",
     [[20], [30], [40], [50], [55], [60], [65], [70], [70, 75], [75], [75, 80], [80]] + FIN),
    ("BUS", "Bus / TPV / minibus", "70 000 km/an",
     [[20], [35], [45], [50], [60], [65], [65, 70], [70], [70, 75], [75], [75, 80], [80]] + FIN),
    ("TRACTEUR_ROUTIER", "Tracteur routier", "80 000 km/an",
     [[20], [30], [40], [45], [55], [60], [65], [70], [70, 75], [75], [75, 80], [80]] + FIN),
    ("SEMI_REMORQUE", "Semi-remorque", "",
     [[10], [15], [20], [25], [30], [35], [40], [45], [55], [60], [65], [70], [80], [85], [85, 90], [85, 90], [85, 90]]),
]

# (classe, genre, type, carrosserie, catégorie, charge utile > kg) — première correspondance retenue
GV = {"camion": 1, "camionnette": 2, "cyclo": 3, "voiture": 4, "car": 6, "fourgonnette": 7, "remorque": 8,
      "scooter": 9, "semi": 10, "tracteur_routier": 12}
REGLES = [
    ("TAXI", None, 5, None, "", None),        # Taxi communaux
    ("TAXI", None, 6, None, "", None),        # Taxi urbain (MATCA, VTC…)
    ("TAXI", None, None, 26, "", None),       # carrosserie TAXI COMPTEUR
    ("TAXI", None, None, 34, "", None),       # carrosserie WÔRÔ-WÔRÔ
    ("BUS", GV["car"], None, None, "", None),
    ("BUS", None, 2, None, "", None),         # Auto car (plus de 41 places)
    ("BUS", None, 4, None, "", None),         # Mini car (9 à 40 places)
    ("BUS", None, None, 7, "", None),         # BUS
    ("BUS", None, None, 10, "", None),        # CAR
    ("BUS", None, None, 20, "", None),        # MINI-BUS
    ("TRACTEUR_ROUTIER", GV["tracteur_routier"], None, None, "", None),
    ("TRACTEUR_ROUTIER", None, None, 28, "", None),
    ("SEMI_REMORQUE", GV["semi"], None, None, "", None),
    ("SEMI_REMORQUE", GV["remorque"], None, None, "", None),
    ("SEMI_REMORQUE", None, None, 23, "", None),
    ("SEMI_REMORQUE", None, None, 25, "", None),
    ("CAMION_PLUS_5T", GV["camion"], None, None, "", 5000),
    ("CAMION_5T", GV["camion"], None, None, "", None),
    ("CAMION_PLUS_5T", None, None, 8, "", 5000),
    ("CAMION_5T", None, None, 8, "", None),   # CAMION
    ("UTILITAIRE", GV["camionnette"], None, None, "", None),
    ("UTILITAIRE", GV["fourgonnette"], None, None, "", None),
    ("UTILITAIRE", None, None, 4, "", None),  # BACHEE
    ("UTILITAIRE", None, None, 9, "", None),  # CAMIONNETTE
    ("UTILITAIRE", None, None, 18, "", None),  # FOURGONNETTE
    ("UTILITAIRE", None, None, 22, "", None),  # PLATEAU
    ("CYCLO_MOTO", GV["cyclo"], None, None, "", None),
    ("CYCLO_MOTO", GV["scooter"], None, None, "", None),
    ("VP", GV["voiture"], None, None, "", None),
    # Véhicules sans genre (repris d'URANUS) : d'après la catégorie tarifaire
    ("BUS", None, None, None, "204", None),
    ("CYCLO_MOTO", None, None, None, "205", None),
    ("CAMION_PLUS_5T", None, None, None, "203", 5000),
    ("CAMION_5T", None, None, None, "203", None),
    ("UTILITAIRE", None, None, None, "202", None),
    ("VP", None, None, None, "201", None),
    ("VP", None, None, None, "208", None),
    ("VP", None, None, None, "212", None),
]

PARAMETRES = [
    # (clé, groupe, libellé, aide, type, valeur, unité, min, max, ordre)
    ("auto.depreciation.taux_retenu", "auto_depreciation", "Taux retenu quand le tableau en donne deux",
     "« plus_faible » (ex. 30 % pour « 30/35 », valeur vénale la plus haute), « plus_eleve » ou « moyenne ».",
     "texte", "plus_faible", "", None, None, 1),
    ("auto.depreciation.pourcentage_au_dela", "auto_depreciation", "Valeur au-delà de la dernière colonne (10 ans)",
     "Pourcentage de la valeur neuve catalogue TTC ou de remplacement.", "pourcentage", "10", "%", 0, 100, 2),
    ("auto.depreciation.valeur_minimum", "auto_depreciation", "Valeur minimum d'un véhicule",
     "Véhicule en état standard ayant sa visite technique (0 : aucune). Jamais au-dessus de la valeur neuve.",
     "montant", "1000000", "F", 0, None, 3),
]


def initialiser(apps, schema_editor):
    Classe = apps.get_model("configuration_api", "DepreciationClasse")
    Regle = apps.get_model("configuration_api", "DepreciationRegle")
    for ordre, (code, libelle, km, taux) in enumerate(CLASSES, start=1):
        Classe.objects.get_or_create(Code=code, defaults=dict(
            Libelle=libelle, Kilometrage=km, Ordre=ordre, Taux={str(a): t for a, t in zip(AGES, taux)},
        ))
    if not Regle.objects.exists():
        for ordre, (classe, genre, type_, carrosserie, categorie, charge) in enumerate(REGLES, start=1):
            Regle.objects.create(Ordre=ordre, Classe_id=classe, IdGenre=genre, IdTypeVehicule=type_,
                                 IdCarrosserie=carrosserie, CodeCategorie=categorie, ChargeUtileSuperieureA=charge)
    ParametreGeneral = apps.get_model("configuration_api", "ParametreGeneral")
    for cle, groupe, libelle, aide, type_, valeur, unite, minimum, maximum, ordre in PARAMETRES:
        ParametreGeneral.objects.get_or_create(Cle=cle, defaults=dict(
            Groupe=groupe, Libelle=libelle, Aide=aide, Type=type_, Valeur=valeur, ValeurOrigine=valeur,
            Unite=unite, Minimum=minimum, Maximum=maximum, Ordre=ordre,
        ))


def retirer(apps, schema_editor):
    apps.get_model("configuration_api", "ParametreGeneral").objects.filter(Cle__in=[p[0] for p in PARAMETRES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0083_sante_minene_parametrage"),
    ]

    operations = [
        migrations.CreateModel(
            name="DepreciationClasse",
            fields=[
                ("Code", models.CharField(db_column="code", max_length=30, primary_key=True, serialize=False)),
                ("Libelle", models.CharField(db_column="libelle", max_length=100)),
                ("Kilometrage", models.CharField(blank=True, db_column="kilometrage", default="", max_length=100)),
                ("Taux", models.JSONField(blank=True, db_column="taux", default=dict)),
                ("Ordre", models.PositiveSmallIntegerField(db_column="ordre", default=0)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
                ("ModifiePar", models.CharField(blank=True, db_column="modifiepar", default="", max_length=150)),
            ],
            options={
                "verbose_name": "Ligne du tableau de dépréciation",
                "verbose_name_plural": "Tableau de dépréciation",
                "db_table": "lephare_depreciation_classe",
                "ordering": ["Ordre", "Code"],
            },
        ),
        migrations.CreateModel(
            name="DepreciationRegle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("Ordre", models.PositiveSmallIntegerField(db_column="ordre", default=0)),
                ("IdGenre", models.IntegerField(blank=True, db_column="idgenre", null=True)),
                ("IdTypeVehicule", models.IntegerField(blank=True, db_column="idtypevehicule", null=True)),
                ("IdCarrosserie", models.IntegerField(blank=True, db_column="idcarrosserie", null=True)),
                ("CodeCategorie", models.CharField(blank=True, db_column="codecategorie", default="", max_length=3)),
                ("ChargeUtileSuperieureA", models.IntegerField(blank=True, db_column="chargeutilesuperieurea", null=True)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
                ("Classe", models.ForeignKey(db_column="classe", on_delete=django.db.models.deletion.CASCADE,
                                             related_name="regles", to="configuration_api.depreciationclasse")),
            ],
            options={
                "verbose_name": "Règle de classement (dépréciation)",
                "verbose_name_plural": "Règles de classement (dépréciation)",
                "db_table": "lephare_depreciation_regle",
                "ordering": ["Ordre", "id"],
            },
        ),
        migrations.RunPython(initialiser, retirer),
    ]
