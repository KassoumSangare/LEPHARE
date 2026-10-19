from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0167_prime_imposee_garanties_nsia_auto_plus"),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE public.stdencaissement "
            "ALTER COLUMN ordrereglement SET DEFAULT 'CABINET';",
            "ALTER TABLE public.stdencaissement "
            "ALTER COLUMN ordrereglement DROP DEFAULT;",
        ),
    ]
