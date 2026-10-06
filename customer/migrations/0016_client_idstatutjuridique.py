from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customer", "0015_alter_client_fonction"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="IdStatutJuridique",
            field=models.IntegerField(
                blank=True, db_column="idstatutjuridique", null=True
            ),
        ),
    ]
