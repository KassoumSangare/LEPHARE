# Compte rendu de la séance LE PHARE du 12-10-2026 (Automobile, catégorie 204 « TRANSPORT PUBLIC DE
# VOYAGEURS ») : la prime des garanties obligatoires RC et Recours d'un véhicule TPV peut relever du POOL TPV,
# au tarif joint (« TARIFS POOL TPV.pdf », tarif actuel). Toute la RC + Recours est alors due au Pool
# (décision de l'utilisateur du 2026-10-13). Réglable dans Administration > Réglages Automobile > Pool TPV.
#
#   - lephare_pool_tpv_tranche : RC annuelle par nombre de places (0-4, 5-8, 9-22, 23-40, 41 et plus) et
#     accessoires par durée (le document en donne une ligne par tranche : 1 024 / 1 000 / 550 F à 1 mois).
#   - lephare_parametre (groupe auto_pool_tpv) : Recours = 5 % de la RC, fractions de la prime annuelle par
#     durée (10 % à 1 mois … 100 % à 12 mois), places comptées hors conducteur (contrats TPV repris
#     d'URANUS : 5 places au tarif « 0 à 4 places »), offre « POOL TPV (CAT 204) » (renseignée par la
#     migration production 0157).

from decimal import Decimal

from django.db import migrations, models

ACC = [2000, 2000, 3000, 3000, 3000, 5000, 5000, 5000, 5000, 5000, 5000]  # 2 à 12 mois
TRANCHES = [
    # (places min, places max, prime RC annuelle, accessoire à 1 mois)
    (0, 4, 139968, 1024),
    (5, 8, 259200, 1000),
    (9, 22, 362005, 550),
    (23, 40, 459054, 1000),
    (41, None, 684000, 1000),
]
FRACTIONS = "10/19/28/37/45/53/61/69/77/85/93/100"

PARAMETRES = [
    ("auto.pool_tpv.taux_recours", "auto_pool_tpv", "Recours (défense recours) en % de la RC",
     "Prime Recours = ce pourcentage de la prime RC de la durée (« DR = 5 % RC »).", "pourcentage", "5", "%", 0, 100, 1),
    ("auto.pool_tpv.fractions", "auto_pool_tpv", "Fraction de la prime annuelle selon la durée",
     "Douze pourcentages séparés par « / », de 1 à 12 mois (une durée entamée compte pour un mois).",
     "texte", FRACTIONS, "", None, None, 2),
    ("auto.pool_tpv.places_hors_conducteur", "auto_pool_tpv", "Places comptées hors conducteur",
     "Oui : un véhicule de 5 places (conducteur compris) relève de la tranche « 0 à 4 places ».", "booleen", "true", "", None, None, 3),
    ("auto.pool_tpv.offre", "auto_pool_tpv", "Offre « POOL TPV » de la catégorie 204",
     "Identifiant de l'offre tarifée au Pool (créée par la migration production 0157).", "entier", "", "", None, None, 4),
]


def initialiser(apps, schema_editor):
    Tranche = apps.get_model("configuration_api", "PoolTpvTranche")
    if not Tranche.objects.exists():
        for ordre, (mini, maxi, rc, acc1) in enumerate(TRANCHES, start=1):
            Tranche.objects.create(PlacesMin=mini, PlacesMax=maxi, PrimeRcAnnuelle=Decimal(rc), Accessoires=[acc1] + ACC, Ordre=ordre)
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
        ("configuration_api", "0085_auto_regles_garanties_age"),
    ]

    operations = [
        migrations.CreateModel(
            name="PoolTpvTranche",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("PlacesMin", models.PositiveSmallIntegerField(db_column="placesmin")),
                ("PlacesMax", models.PositiveSmallIntegerField(blank=True, db_column="placesmax", null=True)),
                ("PrimeRcAnnuelle", models.DecimalField(db_column="primercannuelle", decimal_places=2, max_digits=15)),
                ("Accessoires", models.JSONField(blank=True, db_column="accessoires", default=list)),
                ("Ordre", models.PositiveSmallIntegerField(db_column="ordre", default=0)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
                ("ModifiePar", models.CharField(blank=True, db_column="modifiepar", default="", max_length=150)),
            ],
            options={
                "verbose_name": "Tranche du tarif Pool TPV",
                "verbose_name_plural": "Tarif Pool TPV",
                "db_table": "lephare_pool_tpv_tranche",
                "ordering": ["Ordre", "PlacesMin"],
            },
        ),
        migrations.RunPython(initialiser, retirer),
    ]
