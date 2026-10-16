# Règles de gestion Automobile entre garanties (document « COMMENTAIRE ANNOTE TARIF AUTOMOBILE NSIA CI », reçu
# d'OREOLE le 2026-10-16, colonne « Interaction avec les autres garanties », catégories 1 à 12 ; montants anciens,
# réglables dans l'admin) : les garanties apparaissent, sont offertes ou changent de prime selon celles qui sont
# souscrites et la catégorie du véhicule.
#
#   - lephare_auto_regle_interaction : une règle par garantie, compagnie et type (obligatoire, exige, exclue si,
#     offerte si, prime forfaitaire si, non commercialisée, non cochée d'office).
#   - Règles NSIA amorcées :
#       RC et Défense-recours obligatoires ; Défense-recours 4 200 F (URANUS ; 4 240 F au tarif annoté) avec les dommages ou la collision (cat. 1, 2, 7 à
#       10, 12 ; 3 et 4 : 10 % de la RC, déjà au barème) ; recours anticipé offert avec les dommages ou la collision ;
#       collision et bris de glace offerts avec les dommages (bris de glace des toits ouvrants exclu : facturé avec les
#       dommages sur la CP EBENE PREMIUM TPC de 2026) ; vol des accessoires et vandalisme exigent le vol ou le vol à
#       mains armées ; protection conducteur non commercialisée en catégories 1 et 12 ; sécurité routière non
#       commercialisée en catégories 3, 4, 5, 7, 8, 9, 10 ; immobilisation réservée au leasing (non cochée d'office) ;
#       NSIA Auto + exclue avec les dommages ou la collision (fiche « NSIA AUTO PLUS » : véhicules inéligibles aux
#       dommages).
#   - Franchise NSIA Auto + : 10 % (fiche « NSIA AUTO PLUS »), au lieu de 0 dans les offres NSIA.
# Retour : python manage.py migrate configuration_api 0089

from decimal import Decimal

from django.db import migrations, models

NSIA = 1
SOURCE = "Tarif annoté NSIA"
# (sous-garantie, type, garanties liées, catégories, prime annuelle, commentaire)
REGLES = [
    (1, "OBLIGATOIRE", "", "", None, "Responsabilité civile : garantie obligatoire."),
    (4, "OBLIGATOIRE", "", "", None, "Défense-recours : garantie obligatoire."),
    (4, "PRIME_SI", "7,8", "201,202,207,208,209,210,212", Decimal("4200"),
     "Défense-recours : forfait de 4 200 F (au lieu de 7 950 F) avec les dommages au véhicule ou la collision "
     "(prime nette d'URANUS ; le tarif annoté indique 4 240 F)."),
    (5, "OFFERTE_SI", "7,8", "", None, "Recours anticipé attribué sans prime avec les dommages au véhicule ou la collision."),
    (8, "OFFERTE_SI", "7", "", None, "Dommages collision attribués sans prime avec les dommages au véhicule."),
    (9, "OFFERTE_SI", "7", "", None, "Bris de glace attribué sans prime avec les dommages au véhicule (compris dans leur taux)."),
    (15, "REQUIERT", "12,13", "", None, "Vol des accessoires : ne peut être souscrit sans la garantie vol."),
    (14, "REQUIERT", "12,13", "", None, "Vandalisme (avec le vol des accessoires) : ne peut être souscrit sans la garantie vol."),
    (170, "NON_PROPOSEE", "", "201,212", None, "Protection conducteur : non commercialisée pour les véhicules de tourisme."),
    (169, "NON_PROPOSEE", "", "203,204,205,207,208,209,210", None, "Sécurité routière : non commercialisée dans cette catégorie."),
    (21, "NON_COCHEE", "", "", None, "Immobilisation : accordée uniquement en leasing."),
    (175, "EXCLUE_SI", "7,8", "", None, "NSIA Auto + : réservée aux véhicules sans garantie dommages (5 à 10 ans)."),
]


def initialiser(apps, schema_editor):
    Regle = apps.get_model("configuration_api", "AutoRegleInteraction")
    if Regle.objects.filter(IdCompagnie=NSIA).exists():
        return
    Regle.objects.bulk_create([
        Regle(IdCompagnie=NSIA, IdSousGarantie=sg, Type=type_, Liees=liees, Categories=categories, PrimeAnnuelle=prime,
              Commentaire=commentaire, Ordre=i, ModifiePar=SOURCE)
        for i, (sg, type_, liees, categories, prime, commentaire) in enumerate(REGLES, start=1)
    ])


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0089_tarifs_auto_lecture_directe"),
    ]

    operations = [
        migrations.CreateModel(
            name="AutoRegleInteraction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("IdCompagnie", models.IntegerField(db_column="idcompagnie")),
                ("IdSousGarantie", models.IntegerField(db_column="idsousgarantie")),
                ("Type", models.CharField(choices=[("OBLIGATOIRE", "Obligatoire"), ("REQUIERT", "Exige une des garanties liées"), ("EXCLUE_SI", "Exclue si une des garanties liées est souscrite"), ("OFFERTE_SI", "Offerte si une des garanties liées est souscrite"), ("PRIME_SI", "Prime forfaitaire si une des garanties liées est souscrite"), ("NON_PROPOSEE", "Non commercialisée"), ("NON_COCHEE", "Proposée sans être cochée d'office")], db_column="type", max_length=20)),
                ("Liees", models.CharField(blank=True, db_column="liees", default="", max_length=100)),
                ("Categories", models.CharField(blank=True, db_column="categories", default="", max_length=100)),
                ("PrimeAnnuelle", models.DecimalField(blank=True, db_column="primeannuelle", decimal_places=2, max_digits=15, null=True)),
                ("Commentaire", models.CharField(blank=True, db_column="commentaire", default="", max_length=300)),
                ("Actif", models.BooleanField(db_column="actif", default=True)),
                ("Ordre", models.PositiveSmallIntegerField(db_column="ordre", default=0)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
                ("ModifiePar", models.CharField(blank=True, db_column="modifiepar", default="", max_length=150)),
            ],
            options={
                "verbose_name": "Règle entre garanties (Automobile)",
                "verbose_name_plural": "Règles entre garanties (Automobile)",
                "db_table": "lephare_auto_regle_interaction",
                "ordering": ["IdCompagnie", "Ordre", "id"],
            },
        ),
        migrations.RunPython(initialiser, migrations.RunPython.noop),
        migrations.RunSQL(
            "UPDATE stdoffregarantie SET tauxfranchise = 10 WHERE idcompagnie = 1 AND idsousgarantie = 175 "
            "AND COALESCE(tauxfranchise, 0) = 0;",
            "UPDATE stdoffregarantie SET tauxfranchise = 0 WHERE idcompagnie = 1 AND idsousgarantie = 175 "
            "AND tauxfranchise = 10;",
        ),
    ]
