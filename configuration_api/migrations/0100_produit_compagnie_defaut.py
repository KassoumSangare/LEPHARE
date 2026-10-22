# Compagnie proposée à l'ouverture d'un nouveau devis, réglable par produit (Administration > Produits) : elle était
# écrite dans chaque écran de devis (AMSA ASSURANCES pour le Voyage, NSIA ASSURANCES ailleurs). Valeurs de départ
# identiques. Retour : python manage.py migrate configuration_api 0099

from django.db import migrations, models

DEFAUTS = {3: 21}  # Voyage : AMSA ASSURANCES (compagnie proposée par URANUS) ; autres produits : NSIA ASSURANCES (1)


def amorcer(apps, schema_editor):
    ProduitParametre = apps.get_model("configuration_api", "ProduitParametre")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT idcompagnie FROM stdcompagnie WHERE idcompagnie IN (1, 21)")
        existantes = {r[0] for r in cursor.fetchall()}
    for p in ProduitParametre.objects.exclude(ModuleSaisie=""):
        id_compagnie = DEFAUTS.get(p.IdProduit, 1)
        if id_compagnie in existantes:
            p.IdCompagnieDefaut = id_compagnie
            p.save(update_fields=["IdCompagnieDefaut"])


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0099_reglages_transport_hors_guce"),
    ]

    operations = [
        migrations.AddField(
            model_name="produitparametre",
            name="IdCompagnieDefaut",
            field=models.IntegerField(blank=True, db_column="idcompagniedefaut", null=True),
        ),
        migrations.AlterField(
            model_name="produitparametre",
            name="ModuleSaisie",
            field=models.CharField(blank=True, choices=[("", "Aucun formulaire"), ("auto", "Automobile"), ("ia", "Individuelle Accidents"), ("voyage", "Voyage"), ("mrh", "Multirisque Habitation"), ("sante", "Santé"), ("transport", "Transport"), ("rc", "Responsabilité Civile"), ("mrp", "Multirisque Professionnelle"), ("tous-dommages", "Tous Dommages")], db_column="modulesaisie", default="", max_length=30),
        ),
        migrations.RunPython(amorcer, migrations.RunPython.noop),
    ]
