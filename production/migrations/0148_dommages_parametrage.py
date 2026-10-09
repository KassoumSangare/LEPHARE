# Production Dommages (produit 9), toutes catégories 4xx :
#   - stdcomplementdevisdetaildommage.saisie : description du risque, taux et primes saisis ;
#   - fn_garantie_offre_dommages / sp_creation_devis_dommages : garanties de l'offre de la catégorie
#     pour la compagnie, capital x taux ou prime saisie, réduction, taxe, accessoire, commission ;
#   - garantie unique pour les 9 catégories qui n'en avaient aucune, taxe 14,5 % du produit 9 là où
#     elle manquait (garanties de la Globale de Banque comprises).
# Retour : python manage.py migrate production 0147

from django.db import migrations, models
from uranus.utils.migrations import load_sql_pair


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0147_numerotation_codes_categorie_oreole'),
    ]

    operations = [
        migrations.AddField(
            model_name='complementdevisdetaildommage',
            name='saisie',
            field=models.JSONField(blank=True, db_column='saisie', null=True, verbose_name='Saisie du devis'),
        ),
        migrations.RunSQL(
            *load_sql_pair(
                __file__,
                "raw/parametrage_dommages_garanties.sql",
                "raw/parametrage_dommages_garanties_reverse.sql",
            )
        ),
        migrations.RunSQL(
            *load_sql_pair(
                __file__,
                "functions/fn_garantie_offre_dommages.sql",
                "functions/fn_garantie_offre_dommages_reverse.sql",
            )
        ),
        migrations.RunSQL(
            *load_sql_pair(
                __file__,
                "procedures/sp_creation_devis_dommages.sql",
                "procedures/sp_creation_devis_dommages_reverse.sql",
            )
        ),
    ]
