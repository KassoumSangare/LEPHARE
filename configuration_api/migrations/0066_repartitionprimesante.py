from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0065_demandegarantierisquesdivers_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="RepartitionPrimeSante",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("libelle", models.CharField(max_length=150, verbose_name="Libellé du barème")),
                (
                    "avec_apporteur",
                    models.BooleanField(
                        default=False,
                        help_text="Les taux de commission changent lorsque le contrat est apporté par un tiers.",
                        verbose_name="Variante avec apporteur d'affaires",
                    ),
                ),
                (
                    "taux_frais_generaux_compagnie",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=5,
                        verbose_name="Frais généraux compagnie (NSIA CI) %",
                    ),
                ),
                (
                    "taux_commission_courtier",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=5,
                        verbose_name="Commission courtier (OREOLE ASSURANCES) %",
                    ),
                ),
                (
                    "taux_honoraire_gestionnaire",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=5,
                        verbose_name="Honoraires de gestion (VITALIS) %",
                    ),
                ),
                (
                    "taux_frais_gestion_adec",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=5,
                        null=True,
                        help_text="Renseigné uniquement pour la variante sans apporteur.",
                        verbose_name="Frais de gestion (ADEC) %",
                    ),
                ),
                (
                    "taux_autres_frais_gestion",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=5,
                        null=True,
                        help_text="Renseigné uniquement pour la variante sans apporteur.",
                        verbose_name="Autres frais de gestion %",
                    ),
                ),
                (
                    "taux_commission_commerciaux",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=5,
                        null=True,
                        help_text="Renseigné uniquement pour la variante avec apporteur.",
                        verbose_name="Commission commerciaux compagnie %",
                    ),
                ),
                (
                    "frais_gestion_adec_forfait_ia",
                    models.DecimalField(
                        decimal_places=4,
                        default="1500",
                        max_digits=19,
                        verbose_name="Frais de gestion ADEC forfaitaires — Individuelle Accidents (FCFA)",
                    ),
                ),
                (
                    "frais_gestion_adec_forfait_rc",
                    models.DecimalField(
                        decimal_places=4,
                        default="1500",
                        max_digits=19,
                        verbose_name="Frais de gestion ADEC forfaitaires — RC Chef de Famille (FCFA)",
                    ),
                ),
                ("actif", models.BooleanField(default=True, verbose_name="Actif")),
                (
                    "date_creation",
                    models.DateTimeField(auto_now_add=True, verbose_name="Date de création"),
                ),
                (
                    "date_modification",
                    models.DateTimeField(auto_now=True, verbose_name="Date de modification"),
                ),
            ],
            options={
                "verbose_name": "Répartition de la prime Santé",
                "verbose_name_plural": "Répartitions de la prime Santé",
                "db_table": "stdrepartitionprimesante",
            },
        ),
    ]
