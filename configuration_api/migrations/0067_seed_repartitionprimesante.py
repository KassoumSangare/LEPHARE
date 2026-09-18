from django.db import migrations


def seed_repartition_prime_sante(apps, schema_editor):
    RepartitionPrimeSante = apps.get_model("configuration_api", "RepartitionPrimeSante")

    # Valeurs extraites de SANTE\TARIFICATION MINENE SANTE.xlsx (feuille
    # "REPARTITION DE LA PRIME + GESTI"). ATTENTION : le fichier source
    # contient deux lectures possibles pour "Frais généraux NSIA CI"
    # (13,5% ou 12,5%) et "Autres frais de gestion" (3,5% ou 4,5%) selon la
    # feuille consultée — à confirmer avec OREOLE ASSURANCES avant mise en
    # production. Les valeurs ci-dessous reprennent la lecture principale ;
    # elles restent modifiables via l'écran de paramétrage.
    RepartitionPrimeSante.objects.get_or_create(
        avec_apporteur=False,
        defaults=dict(
            libelle=(
                "Minéné Santé — Sans apporteur d'affaires "
                "(variante alternative 12,5% / 4,5% à confirmer)"
            ),
            taux_frais_generaux_compagnie="13.5",
            taux_commission_courtier="6.5",
            taux_honoraire_gestionnaire="8.5",
            taux_frais_gestion_adec="3.0",
            taux_autres_frais_gestion="3.5",
            taux_commission_commerciaux=None,
            frais_gestion_adec_forfait_ia="1500",
            frais_gestion_adec_forfait_rc="1500",
            actif=True,
        ),
    )

    RepartitionPrimeSante.objects.get_or_create(
        avec_apporteur=True,
        defaults=dict(
            libelle="Minéné Santé — Avec apporteur d'affaires",
            taux_frais_generaux_compagnie="12.5",
            taux_commission_courtier="6.5",
            taux_honoraire_gestionnaire="8.5",
            taux_frais_gestion_adec=None,
            taux_autres_frais_gestion=None,
            taux_commission_commerciaux="7.0",
            frais_gestion_adec_forfait_ia="1500",
            frais_gestion_adec_forfait_rc="1500",
            actif=True,
        ),
    )


def remove_repartition_prime_sante(apps, schema_editor):
    RepartitionPrimeSante = apps.get_model("configuration_api", "RepartitionPrimeSante")
    RepartitionPrimeSante.objects.filter(
        libelle__startswith="Minéné Santé"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0066_repartitionprimesante"),
    ]

    operations = [
        migrations.RunPython(seed_repartition_prime_sante, remove_repartition_prime_sante),
    ]
