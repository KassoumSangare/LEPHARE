# Relevé de compte (quittance remise au client à la confirmation d'un devis Dommages), sur le modèle du
# relevé OREOLE reçu le 2026-10-08 (STEP BY STEP, 13/01/2026) :
#   - « Chèque à l'ordre de » propre à chaque compagnie (lephare_compagnie_document.ordrecheque) ;
#     NSIA ASSURANCES : « NSIA CI », comme sur le relevé ; vide = raison sociale de la compagnie ;
#   - pied de page du relevé : mentions légales du cabinet et mention de marque (marge gauche),
#     recopiées du relevé scanné (à vérifier : une partie est recouverte par le cachet).
# Retour : python manage.py migrate configuration_api 0077

from django.db import migrations, models

ID_NSIA = 1
ORDRE_NSIA = "NSIA CI"

MENTIONS_LEGALES = (
    "SARL Unipersonnelle au capital de 5 000 000 FCFA | C.B : SGCI : CI008 01111 011157481298 32 | "
    "C.C : 0807891Y RCCM : CI-ABJ-01-2009-B13-06768 Centre des impôts de Cocody Contrat R C N°1186583100012N | "
    "Siège social : Cocody cité des arts, Bd Latrille, face SODEMI, Imm. « LES 7 COLONNES » BP : 27 B.P 112 Abj 27 "
    "Agrément N° 141/MEF/DGTCP/DA du 24 MARS 2010 Tél : +225 27 22 48 76 86 / +225 27 22 48 73 49 / "
    "+225 27 22 48 71 24 / +225 27 22 22 13 57 Cel : +2250102938218 Site web : oreoleassurances-ci.com."
)
MENTION_MARQUE = "Marque officiellement enregistrée à l'OAPI"

PARAMETRES = [
    ("documents.mentions_legales", "Mentions légales du cabinet (pied du relevé de compte)",
     "Imprimées en bas du relevé de compte, à côté du logo du cabinet. Retours à la ligne conservés. "
     "Vide : rien n'est imprimé.", "texte_long", MENTIONS_LEGALES, 5),
    ("documents.mention_marque", "Mention de marque (marge du relevé de compte)",
     "Imprimée verticalement dans la marge gauche du relevé de compte. Vide : rien n'est imprimé.",
     "texte", MENTION_MARQUE, 6),
]


def ajouter(apps, schema_editor):
    ParametreGeneral = apps.get_model("configuration_api", "ParametreGeneral")
    for cle, libelle, aide, type_, valeur, ordre in PARAMETRES:
        ParametreGeneral.objects.get_or_create(Cle=cle, defaults=dict(
            Groupe="documents", Libelle=libelle, Aide=aide, Type=type_, Valeur=valeur, ValeurOrigine=valeur, Ordre=ordre,
        ))
    CompagnieDocument = apps.get_model("configuration_api", "CompagnieDocument")
    document, _ = CompagnieDocument.objects.get_or_create(IdCompagnie=ID_NSIA)
    if not document.OrdreCheque:
        document.OrdreCheque = ORDRE_NSIA
        document.save(update_fields=["OrdreCheque"])


def retirer(apps, schema_editor):
    apps.get_model("configuration_api", "ParametreGeneral").objects.filter(Cle__in=[p[0] for p in PARAMETRES]).delete()


class Migration(migrations.Migration):

    dependencies = [("configuration_api", "0077_dommages_fiche_cotation")]

    operations = [
        migrations.AddField(
            model_name="compagniedocument",
            name="OrdreCheque",
            field=models.CharField(blank=True, db_column="ordrecheque", default="", max_length=100),
        ),
        migrations.RunPython(ajouter, retirer),
    ]
