# Partage des accessoires et accessoires forfaitaires des offres IA réglables (demande du 2026-10-21 : « oui 50/50 »
# pour NSIA, SUNU et AMSA) :
#   - lephare_ia_accessoire_offre : montant de l'accessoire des offres IA CGA (154, 155, 156 : 1 000 F) et
#     CI-ÉNERGIES (162, 163, 165 à 170 : 79 F), écrits jusqu'ici dans fn_get_accessoire ;
#   - part du cabinet AMSA ASSURANCES (fiche compagnie > Reversements) mise à 50 %, comme NSIA et SUNU : les calculs
#     des devis la lisent désormais (production 0174) au lieu de compagnies écrites en dur.
# Retour : python manage.py migrate configuration_api 0101 (après production 0173)

from decimal import Decimal

from django.db import migrations, models

OFFRES = {154: 1000, 155: 1000, 156: 1000, 162: 79, 163: 79, 165: 79, 166: 79, 167: 79, 168: 79, 169: 79, 170: 79}
AMSA = 21


def amorcer(apps, schema_editor):
    Offre = apps.get_model("configuration_api", "IaAccessoireOffre")
    for id_offre, montant in OFFRES.items():
        Offre.objects.get_or_create(IdOffre=id_offre, defaults={"Montant": Decimal(montant)})
    Document = apps.get_model("configuration_api", "CompagnieDocument")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM stdcompagnie WHERE idcompagnie = %s", [AMSA])
        if not cursor.fetchone():
            return
    document, _ = Document.objects.get_or_create(IdCompagnie=AMSA)
    reversement = dict(document.Reversement or {})
    if reversement.get("PartAccessoiresCourtier") in (None, ""):
        reversement["PartAccessoiresCourtier"] = 50
        document.Reversement = reversement
        document.save(update_fields=["Reversement"])


def retirer(apps, schema_editor):
    Document = apps.get_model("configuration_api", "CompagnieDocument")
    document = Document.objects.filter(IdCompagnie=AMSA).first()
    if document and (document.Reversement or {}).get("PartAccessoiresCourtier") == 50:
        reversement = dict(document.Reversement)
        reversement.pop("PartAccessoiresCourtier")
        document.Reversement = reversement
        document.save(update_fields=["Reversement"])


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0101_reglages_transport_ia"),
    ]

    operations = [
        migrations.CreateModel(
            name="IaAccessoireOffre",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("IdOffre", models.IntegerField(db_column="idoffre", unique=True)),
                ("Montant", models.DecimalField(db_column="montant", decimal_places=2, max_digits=15)),
                ("Actif", models.BooleanField(db_column="actif", default=True)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
                ("ModifiePar", models.CharField(blank=True, db_column="modifiepar", default="", max_length=150)),
            ],
            options={"verbose_name": "Accessoire forfaitaire d'une offre IA", "verbose_name_plural": "Accessoires forfaitaires des offres IA",
                     "db_table": "lephare_ia_accessoire_offre", "ordering": ["IdOffre"]},
        ),
        migrations.RunPython(amorcer, retirer),
    ]
