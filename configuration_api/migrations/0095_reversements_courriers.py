# Reversements aux compagnies (dossier FInance_LEPHARE, 2026-10-19) :
#   - lephare_compagnie_document.reversement : part du cabinet dans les accessoires (NSIA et SUNU : 50/50, demande du
#     2026-10-19 ; vide : barème « Accessoires du cabinet ») et destinataire des courriers de règlement de prime
#     (NSIA-CI, Direction Courtage, à l'attention de M. TANO FULGENCE, d'après les courriers JCW et KOUMOUE) ;
#   - lephare_parametre (groupe « finance ») : signataire des courriers et numéro du prochain bordereau (suite de la
#     numérotation d'OREOLE : dernier connu 2117 du 19/06/2026).
# La part des accessoires est appliquée par le déclencheur de la migration production 0166.

from django.db import migrations, models

REVERSEMENT = {
    1: {"PartAccessoiresCourtier": 50, "NomBordereau": "NSIA CI", "Destinataire": "NSIA-CI", "Service": "DIRECTION COURTAGE",
        "Ville": "ABIDJAN", "AttentionDe": "Monsieur TANO FULGENCE", "Appellation": "Monsieur"},
    14: {"PartAccessoiresCourtier": 50, "NomBordereau": "SUNU ASSURANCES", "Destinataire": "SUNU ASSURANCES", "Service": "",
         "Ville": "ABIDJAN", "AttentionDe": "", "Appellation": "Monsieur"},
}

PARAMETRES = [
    ("finance.courrier_signataire", "finance", "Signataire des courriers aux compagnies",
     "Nom imprimé sous la signature des courriers de règlement de prime et de réclamation de commission.",
     "texte", "Yvette DA", "", None, None, 2),
    ("finance.courrier_fonction", "finance", "Fonction du signataire",
     "Imprimée au-dessus du nom du signataire (ex. LE DIRECTEUR GENERAL).", "texte", "LE DIRECTEUR GENERAL", "", None, None, 3),
    ("finance.premier_numero_bordereau", "finance", "Numéro du prochain bordereau",
     "Les bordereaux de reversement et de réclamation suivent la numérotation d'OREOLE (dernier connu : 2117 du "
     "19/06/2026). Le numéro proposé est le plus grand de ce réglage et du dernier bordereau émis + 1 ; il reste "
     "modifiable à l'émission.", "entier", "2118", "", 1, 999999, 4),
]


def initialiser(apps, schema_editor):
    CompagnieDocument = apps.get_model("configuration_api", "CompagnieDocument")
    for id_compagnie, reglages in REVERSEMENT.items():
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM stdcompagnie WHERE idcompagnie = %s", [id_compagnie])
            if not cursor.fetchone():
                continue
        document, _ = CompagnieDocument.objects.get_or_create(IdCompagnie=id_compagnie)
        if not document.Reversement:
            document.Reversement = reglages
            document.save(update_fields=["Reversement"])
    ParametreGeneral = apps.get_model("configuration_api", "ParametreGeneral")
    for cle, groupe, libelle, aide, type_, valeur, unite, minimum, maximum, ordre in PARAMETRES:
        ParametreGeneral.objects.get_or_create(Cle=cle, defaults=dict(
            Groupe=groupe, Libelle=libelle, Aide=aide, Type=type_, Valeur=valeur, ValeurOrigine=valeur,
            Unite=unite, Minimum=minimum, Maximum=maximum, Ordre=ordre,
        ))


def retirer(apps, schema_editor):
    apps.get_model("configuration_api", "ParametreGeneral").objects.filter(Cle__in=[p[0] for p in PARAMETRES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0094_regles_tarif_annote_relues"),
    ]

    operations = [
        migrations.AddField(
            model_name="compagniedocument",
            name="Reversement",
            field=models.JSONField(blank=True, db_column="reversement", default=dict),
        ),
        migrations.RunPython(initialiser, retirer),
    ]
