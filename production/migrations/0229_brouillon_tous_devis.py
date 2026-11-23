# Brouillons (demande du 2026-11-23 : « pour toute saisie permettre de la mettre en brouillon ») : tous les écrans de devis
# peuvent enregistrer leur saisie en cours dans lephare_brouillon (frontend/src/utils/brouillons.jsx), plus seulement Auto et IA.
# Seuls les choix du champ type_brouillon changent : aucune modification de la table.
# Retour : python manage.py migrate production 0228 (supprimez d'abord les brouillons des nouveaux types).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0228_oreole_reduction_famille"),
    ]

    operations = [
        migrations.AlterField(
            model_name="brouillon",
            name="type_brouillon",
            field=models.CharField(
                choices=[
                    ("DEVIS_AUTO", "Devis automobile"),
                    ("DEVIS_IA", "Devis Individuelle Accidents"),
                    ("DEVIS_SANTE", "Devis Santé"),
                    ("DEVIS_OREOLE", "Devis Oreole Santé"),
                    ("DEVIS_AFA", "Devis Assistance funéraire"),
                    ("DEVIS_MRH", "Devis Multirisque habitation"),
                    ("DEVIS_RC", "Devis Responsabilité civile"),
                    ("DEVIS_MRP", "Devis Multirisque professionnelle"),
                    ("DEVIS_TOUS_DOMMAGES", "Devis Tous dommages"),
                    ("DEVIS_VOYAGE", "Devis Voyage"),
                    ("DEVIS_TRANSPORT", "Devis Transport GUCE"),
                    ("DEVIS_TRANSPORT_HORS_GUCE", "Devis Transport hors GUCE"),
                    ("AVENANT", "Modification de contrat"),
                ],
                default="DEVIS_AUTO",
                max_length=30,
            ),
        ),
    ]
