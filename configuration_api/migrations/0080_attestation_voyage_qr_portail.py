# Attestation d'assurance et d'assistance voyage (modèle AMSA, scan fourni par l'utilisateur) :
# adresse du QR code « Scanner le QR code ci-contre pour accéder au (Portail en ligne, WhatsApp Form) »,
# lue sur l'imprimé (QR décodé le 2026-10-11) : portail d'assistance COVER-EDGE, identique sur toutes
# les attestations. Renseignée pour les modèles dont l'assistance est COVER-EDGE et qui n'en ont pas.
# Le QR code de vérification du certificat (propre à chaque certificat, système AMSA) n'est pas lisible
# sur le scan : son adresse reste à fournir par la compagnie (Administration > Compagnies partenaires).

from django.db import migrations

PORTAIL_COVER_EDGE = "https://claims.cover-edge.com/links/"


def ajouter_portail(apps, schema_editor):
    CompagnieDocument = apps.get_model("configuration_api", "CompagnieDocument")
    for document in CompagnieDocument.objects.all():
        attestation = dict(document.AttestationVoyage or {})
        if "cover-edge.com" in str(attestation.get("Email", "")).lower() and not attestation.get("PortailAssistance"):
            attestation["PortailAssistance"] = PORTAIL_COVER_EDGE
            document.AttestationVoyage = attestation
            document.save(update_fields=["AttestationVoyage"])


def retirer_portail(apps, schema_editor):
    CompagnieDocument = apps.get_model("configuration_api", "CompagnieDocument")
    for document in CompagnieDocument.objects.all():
        attestation = dict(document.AttestationVoyage or {})
        if attestation.get("PortailAssistance") == PORTAIL_COVER_EDGE:
            attestation.pop("PortailAssistance")
            document.AttestationVoyage = attestation
            document.save(update_fields=["AttestationVoyage"])


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0079_repartition_minene_feuille_repartition"),
    ]

    operations = [
        migrations.RunPython(ajouter_portail, retirer_portail),
    ]
