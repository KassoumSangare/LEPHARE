# Saisie et impression Dommages sur le modèle de la fiche « Cotation d'assurance Caution » de NSIA
# (document reçu d'OREOLE le 2026-10-08 : cotation STEP BY STEP, cautionnement 1 500 000) :
#   - trois textes de fiche par catégorie : objet de la garantie, contre-garanties et mesures
#     préalables, exclusions (réglables dans Réglages Dommages) ;
#   - Caution : rubriques du prospect de la fiche (type de cautionnement, nature des travaux, montant
#     du marché) et ses textes. La liste des types de cautionnement reprend celui de la fiche et les
#     autres cautions de marché usuelles ; elle se modifie dans Réglages Dommages.
# Les catégories déjà retouchées dans l'admin ne sont pas modifiées.
# Retour : python manage.py migrate configuration_api 0076

from django.db import migrations, models

ID_CAUTION = 144

CHAMPS_CAUTION = [
    {"Cle": "nature_travaux", "Libelle": "Nature des travaux objet du cautionnement", "Type": "texte_long", "Obligatoire": False},
    {"Cle": "montant_marche", "Libelle": "Montant du marché objet du cautionnement", "Type": "montant", "Obligatoire": False},
    {
        "Cle": "type_cautionnement", "Libelle": "Type de cautionnement", "Type": "liste", "Obligatoire": False,
        "Options": [
            "CAUTION DE SOUMISSION OU CAUTION PROVISOIRE",
            "CAUTION DE BONNE EXECUTION OU CAUTION DEFINITIVE",
            "CAUTION D'AVANCE DE DEMARRAGE",
            "CAUTION DE RETENUE DE GARANTIE",
        ],
    },
]

TEXTES_CAUTION = {
    "ObjetGarantie": "Toutes pertes ou dommages matériels causés directement aux biens assurés du fait de la "
                     "survenance d'un évènement soudain et/ou accidentel garanti.",
    "ContreGaranties": "La copie du registre de commerce et de crédit mobilier (RCCM)\n"
                       "La copie des statuts de l'entreprise\n"
                       "Le marché signé",
    "Exclusions": "Les maladies infectieuses et pandémiques\n"
                  "Les dommages et pertes découlant directement ou indirectement des risques et violences politiques\n"
                  "Toutes pertes ou défaillances du fait de l'employeur ou de son représentant",
}


def installer(apps, schema_editor):
    DommageCategorie = apps.get_model("configuration_api", "DommageCategorie")
    caution = DommageCategorie.objects.filter(IdTarif=ID_CAUTION).first()
    if not caution:
        return
    if not caution.ChampsRisque:
        caution.ChampsRisque = CHAMPS_CAUTION
    for champ, texte in TEXTES_CAUTION.items():
        if not getattr(caution, champ):
            setattr(caution, champ, texte)
    caution.save()


def retirer(apps, schema_editor):
    DommageCategorie = apps.get_model("configuration_api", "DommageCategorie")
    DommageCategorie.objects.filter(IdTarif=ID_CAUTION, ChampsRisque=CHAMPS_CAUTION).update(ChampsRisque=[])


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0076_dommages_champs_uranus"),
    ]

    operations = [
        migrations.AddField(
            model_name="dommagecategorie",
            name="ObjetGarantie",
            field=models.TextField(blank=True, db_column="objetgarantie", default=""),
        ),
        migrations.AddField(
            model_name="dommagecategorie",
            name="ContreGaranties",
            field=models.TextField(blank=True, db_column="contregaranties", default=""),
        ),
        migrations.AddField(
            model_name="dommagecategorie",
            name="Exclusions",
            field=models.TextField(blank=True, db_column="exclusions", default=""),
        ),
        migrations.RunPython(installer, retirer),
    ]
