"""Référentiel des statuts juridiques des clients personnes morales (formes OHADA et
statuts courants en Côte d'Ivoire), proposé dans la fiche client à côté du type d'entreprise."""

from django.db import migrations, models


STATUTS_JURIDIQUES = [
    ("SA", "Société anonyme (SA)"),
    ("SAS", "Société par actions simplifiée (SAS)"),
    ("SASU", "Société par actions simplifiée unipersonnelle (SASU)"),
    ("SARL", "Société à responsabilité limitée (SARL)"),
    ("SARLU", "Société à responsabilité limitée unipersonnelle (SARLU)"),
    ("SNC", "Société en nom collectif (SNC)"),
    ("SCS", "Société en commandite simple (SCS)"),
    ("SC", "Société civile (SCI, SCP…)"),
    ("GIE", "Groupement d'intérêt économique (GIE)"),
    ("SCOOPS", "Société coopérative simplifiée (SCOOPS)"),
    ("COOP-CA", "Société coopérative avec conseil d'administration (COOP-CA)"),
    ("EI", "Entreprise individuelle"),
    ("SUCC", "Succursale de société étrangère"),
    ("SE", "Société d'État"),
    ("SPFP", "Société à participation financière publique"),
    ("EPN", "Établissement public national"),
    ("ASSO", "Association"),
    ("ONG", "Organisation non gouvernementale (ONG)"),
    ("FOND", "Fondation"),
    ("MUT", "Mutuelle"),
    ("AUTRE", "Autre"),
]


def charger_statuts(apps, schema_editor):
    StatutJuridique = apps.get_model("configuration_api", "StatutJuridique")
    for code, libelle in STATUTS_JURIDIQUES:
        StatutJuridique.objects.get_or_create(CodeStatut=code, defaults={"Libelle": libelle})


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0069_grilles_voyage_oreole_2026"),
    ]

    operations = [
        migrations.CreateModel(
            name="StatutJuridique",
            fields=[
                (
                    "IdStatutJuridique",
                    models.AutoField(
                        db_column="idstatutjuridique",
                        primary_key=True,
                        serialize=False,
                        verbose_name="Id Statut Juridique",
                    ),
                ),
                (
                    "CodeStatut",
                    models.CharField(
                        db_column="codestatut",
                        max_length=10,
                        unique=True,
                        verbose_name="Code Statut",
                    ),
                ),
                (
                    "Libelle",
                    models.CharField(
                        db_column="libelle", max_length=100, verbose_name="Libellé"
                    ),
                ),
            ],
            options={
                "verbose_name": "Statut Juridique",
                "verbose_name_plural": "Statuts Juridiques",
                "db_table": "stdstatutjuridique",
            },
        ),
        migrations.RunPython(charger_statuts, migrations.RunPython.noop),
    ]
