# Branche de production RC ouverte à la saisie (demande de l'utilisateur du 2026-10-12) : bouton « Devis RC »
# du registre et formulaire /user/quotes/rc. Rejouée après une nouvelle reprise URANUS, la migration 0074
# remettant la saisie RC fermée.

from django.db import migrations

ID_PRODUIT_RC = 8


def ouvrir(apps, schema_editor):
    ProduitParametre = apps.get_model("configuration_api", "ProduitParametre")
    ProduitParametre.objects.filter(IdProduit=ID_PRODUIT_RC).update(SaisieOuverte=True, ModuleSaisie="rc")


def fermer(apps, schema_editor):
    ProduitParametre = apps.get_model("configuration_api", "ProduitParametre")
    ProduitParametre.objects.filter(IdProduit=ID_PRODUIT_RC).update(SaisieOuverte=False)


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0080_attestation_voyage_qr_portail"),
    ]

    operations = [
        migrations.RunPython(ouvrir, fermer),
    ]
