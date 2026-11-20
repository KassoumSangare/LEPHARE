# AMSA ASSURANCES ne partage pas ses accessoires (correction de l'utilisateur du 2026-11-20, qui revient sur le « oui 50/50 »
# du 2026-10-21 pour AMSA) : part du cabinet mise à 0 % sur la fiche de la compagnie (Administration > Compagnies >
# Reversements). L'accessoire reste entier à AMSA ; NSIA et SUNU gardent leur partage 50/50. Comme les contrats d'URANUS
# de 2013 à 2025 (accessoire à 100 % compagnie).
# Une part déjà réglée à une autre valeur que 50 depuis l'administration est laissée telle quelle.
# Retour : python manage.py migrate configuration_api 0110 (remet 50 %).

from django.db import migrations

AMSA = 21


def sans_partage(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM stdcompagnie WHERE idcompagnie = %s", [AMSA])
        if not cursor.fetchone():
            return
    Document = apps.get_model("configuration_api", "CompagnieDocument")
    document, _ = Document.objects.get_or_create(IdCompagnie=AMSA)
    reversement = dict(document.Reversement or {})
    if reversement.get("PartAccessoiresCourtier") in (None, "", 50, "50"):
        reversement["PartAccessoiresCourtier"] = 0
        document.Reversement = reversement
        document.save(update_fields=["Reversement"])


def partage_moitie(apps, schema_editor):
    Document = apps.get_model("configuration_api", "CompagnieDocument")
    document = Document.objects.filter(IdCompagnie=AMSA).first()
    if document and (document.Reversement or {}).get("PartAccessoiresCourtier") == 0:
        reversement = dict(document.Reversement)
        reversement["PartAccessoiresCourtier"] = 50
        document.Reversement = reversement
        document.save(update_fields=["Reversement"])


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0110_apporteur_montant_par_assure"),
    ]

    operations = [
        migrations.RunPython(sans_partage, partage_moitie),
    ]
