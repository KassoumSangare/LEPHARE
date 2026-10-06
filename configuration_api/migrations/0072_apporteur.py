"""Référentiel des apporteurs d'affaires auxquels le cabinet peut verser des commissions."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0071_voyage_ttc_documents"),
    ]

    operations = [
        migrations.CreateModel(
            name="Apporteur",
            fields=[
                ("IdApporteur", models.AutoField(db_column="idapporteur", primary_key=True, serialize=False, verbose_name="Id Apporteur")),
                ("Code", models.CharField(db_column="code", max_length=20, unique=True, verbose_name="Code apporteur")),
                ("Nom", models.CharField(db_column="nom", max_length=150, verbose_name="Nom ou raison sociale")),
                ("TypePersonne", models.CharField(choices=[("P", "Personne physique"), ("M", "Personne morale")], db_column="typepersonne", default="P", max_length=1)),
                ("PieceIdentite", models.CharField(blank=True, db_column="pieceidentite", default="", max_length=50, verbose_name="CNI / RCCM")),
                ("Telephone", models.CharField(blank=True, db_column="telephone", default="", max_length=30)),
                ("Email", models.EmailField(blank=True, db_column="email", default="", max_length=254)),
                ("Adresse", models.CharField(blank=True, db_column="adresse", default="", max_length=200)),
                ("TauxRetrocession", models.DecimalField(blank=True, db_column="tauxretrocession", decimal_places=2, max_digits=5, null=True, verbose_name="Taux de rétrocession (%)")),
                ("Actif", models.BooleanField(db_column="actif", default=True)),
                ("DateCreation", models.DateTimeField(auto_now_add=True, db_column="datecreation")),
            ],
            options={
                "verbose_name": "Apporteur",
                "verbose_name_plural": "Apporteurs",
                "db_table": "stdapporteur",
                "ordering": ["Code"],
            },
        ),
    ]
