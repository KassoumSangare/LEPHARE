# Encaissement par chèque (demande du 2026-10-20) : date de réception du chèque à OREOLE, après la date d'émission
# (datecheque) ; la date de saisie (dateencaissement) est toujours la date du jour (save_premium_collection).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0169_numerotation_bordereaux"),
    ]

    operations = [
        migrations.AddField(
            model_name="encaissement",
            name="date_reception_cheque",
            field=models.DateField(blank=True, null=True, db_column="datereceptioncheque"),
        ),
    ]
