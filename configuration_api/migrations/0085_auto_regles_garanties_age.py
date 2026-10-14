# Compte rendu de la séance LE PHARE du 12-10-2026 (Automobile) : « Au titre de NSIA ASSURANCES, la garantie
# tous risques est admise pour les véhicules de zéro à 5 ans. Pour les véhicules de 5 à 10 ans c'est la
# garantie NSIA Auto plus qui s'applique. » Règles réglables dans Administration > Réglages Automobile >
# Dépréciation et âge des véhicules ; l'écran de devis signale les garanties non admises, le producteur
# les décoche. Âge en années révolues (minimum inclus, maximum exclu) : DOMMAGES (sous-garantie 7) de 0
# à moins de 5 ans, NSIA AUTO + (175) de 5 à moins de 10 ans.

from django.db import migrations, models

REGLES = [
    # (compagnie, sous-garantie, âge minimum, âge maximum, commentaire)
    (1, 7, None, 5, "NSIA : garantie tous risques de 0 à 5 ans"),
    (1, 175, 5, 10, "NSIA : NSIA Auto Plus de 5 à 10 ans"),
]


def initialiser(apps, schema_editor):
    Regle = apps.get_model("configuration_api", "AutoRegleGarantie")
    if not Regle.objects.exists():
        for compagnie, sg, minimum, maximum, commentaire in REGLES:
            Regle.objects.create(IdCompagnie=compagnie, IdSousGarantie=sg, AgeMinimum=minimum, AgeMaximum=maximum,
                                 Commentaire=commentaire)


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0084_depreciation_vehicules"),
    ]

    operations = [
        migrations.CreateModel(
            name="AutoRegleGarantie",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("IdCompagnie", models.IntegerField(db_column="idcompagnie")),
                ("IdSousGarantie", models.IntegerField(db_column="idsousgarantie")),
                ("AgeMinimum", models.PositiveSmallIntegerField(blank=True, db_column="ageminimum", null=True)),
                ("AgeMaximum", models.PositiveSmallIntegerField(blank=True, db_column="agemaximum", null=True)),
                ("Categories", models.CharField(blank=True, db_column="categories", default="", max_length=100)),
                ("Commentaire", models.CharField(blank=True, db_column="commentaire", default="", max_length=200)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
            ],
            options={
                "verbose_name": "Garantie admise selon l'âge du véhicule",
                "verbose_name_plural": "Garanties admises selon l'âge du véhicule",
                "db_table": "lephare_auto_regle_garantie",
                "ordering": ["IdCompagnie", "IdSousGarantie"],
            },
        ),
        migrations.RunPython(initialiser, migrations.RunPython.noop),
    ]
