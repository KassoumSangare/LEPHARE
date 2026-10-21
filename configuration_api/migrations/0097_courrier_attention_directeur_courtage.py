# Courriers à NSIA-CI (demande du 2026-10-20) : « À l'attention du Directeur de Courtage » au lieu de « À l'attention
# de Monsieur TANO FULGENCE ». Le réglage n'est changé que s'il porte encore la valeur de la migration 0095 (une saisie
# faite depuis dans l'administration est gardée). La ligne « À l'attention … » accorde l'article : ligne_attention,
# production/views_bordereaux.py.

from django.db import migrations

ID_NSIA = 1
ANCIEN = "Monsieur TANO FULGENCE"
NOUVEAU = "du Directeur de Courtage"


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
        ("configuration_api", "0096_retrait_premier_numero_bordereau"),
    ]

    operations = [
        migrations.RunPython(appliquer, retirer),
    ]
