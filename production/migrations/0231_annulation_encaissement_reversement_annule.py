# Annulation d'un reversement (demande du 2026-11-24) : un bordereau de reversement annulé (Reversements aux compagnies,
# droit « Annuler un reversement ») garde ses lignes dans stddetailreversement ; sp_annulation_encaissement v2 refusait
# encore d'annuler l'encaissement (« Encaissement déjà reversé. Annulation impossible. »). v3 : seul un reversement en
# cours (non annulé) bloque l'annulation. Retour : python manage.py migrate production 0230

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0230_commission_transport_guce"),
    ]

    operations = [
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_annulation_encaissement", from_version=2, to_version=3)),
    ]
