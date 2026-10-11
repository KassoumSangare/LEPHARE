# Répartition de la prime Santé MINENE « sans apporteur » : taux de la feuille « REPARTITION DE LA
# PRIME + GESTI » de TARIFICATION MINENE SANTE.xlsx, pris pour référence le 2026-10-11 (frais généraux
# NSIA 12,5 %, autres frais de gestion 4,5 % ; les feuilles TAUX portaient 13,5 % / 3,5 %, même total
# de 35 % : provision pour sinistres inchangée à 65 %). OREOLE 6,5 %, VITALIS 8,5 %, ADEC 3 % et la
# variante « avec apporteur » (12,5 % / 6,5 % / 8,5 % / 7 %) étaient déjà ceux du fichier.
# Une valeur déjà modifiée en Administration n'est pas écrasée.

from decimal import Decimal

from django.db import migrations

LIBELLE = "Minéné Santé — Sans apporteur d'affaires"
ANCIEN_LIBELLE = "Minéné Santé — Sans apporteur d'affaires (variante alternative 12,5% / 4,5% à confirmer)"


def feuille_repartition(apps, schema_editor):
    RepartitionPrimeSante = apps.get_model("configuration_api", "RepartitionPrimeSante")
    RepartitionPrimeSante.objects.filter(
        avec_apporteur=False,
        taux_frais_generaux_compagnie=Decimal("13.5"),
        taux_autres_frais_gestion=Decimal("3.5"),
    ).update(taux_frais_generaux_compagnie=Decimal("12.5"), taux_autres_frais_gestion=Decimal("4.5"), libelle=LIBELLE)


def retour(apps, schema_editor):
    RepartitionPrimeSante = apps.get_model("configuration_api", "RepartitionPrimeSante")
    RepartitionPrimeSante.objects.filter(
        avec_apporteur=False,
        taux_frais_generaux_compagnie=Decimal("12.5"),
        taux_autres_frais_gestion=Decimal("4.5"),
        libelle=LIBELLE,
    ).update(taux_frais_generaux_compagnie=Decimal("13.5"), taux_autres_frais_gestion=Decimal("3.5"), libelle=ANCIEN_LIBELLE)


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0078_releve_compte"),
    ]

    operations = [
        migrations.RunPython(feuille_repartition, retour),
    ]
