# Courriers à NSIA-CI (demande du 2026-10-21) : « À l'attention du Directeur du Courtage » au lieu de « … du
# Directeur de Courtage » (0097). Le réglage n'est changé que s'il porte encore la valeur de 0097 (une saisie faite
# depuis dans l'administration est gardée).

from django.db import migrations

ID_NSIA = 1
ANCIEN = "du Directeur de Courtage"
NOUVEAU = "du Directeur du Courtage"


def remplacer(apps, ancien, nouveau):
    CompagnieDocument = apps.get_model("configuration_api", "CompagnieDocument")
    document = CompagnieDocument.objects.filter(IdCompagnie=ID_NSIA).first()
    if document and (document.Reversement or {}).get("AttentionDe") == ancien:
        document.Reversement = {**document.Reversement, "AttentionDe": nouveau}
        document.save(update_fields=["Reversement"])


def appliquer(apps, schema_editor):
    remplacer(apps, ANCIEN, NOUVEAU)


def retirer(apps, schema_editor):
    remplacer(apps, NOUVEAU, ANCIEN)


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0097_courrier_attention_directeur_courtage"),
    ]

    operations = [
        migrations.RunPython(appliquer, retirer),
    ]
