# Transport hors GUCE (document OREOLE « TRANSPORTS.docx », 2026-10-21) : taux et montants du tarif, réglables dans
# Administration > Le cabinet & règles de gestion > Transport. Le document donne le FAP Sauf (taux minimum
# réglementaire 0,15 %), la surprime de transbordement et la couverture de l'emballage (0,10 % chacune) ; le barème
# Tous risques, la guerre, les grèves, les primes minimums et les coûts de police y sont laissés en blanc : vides
# ici, le taux est alors saisi dans la cotation. Taxe : 7 % de la prime nette et des accessoires, taux des
# certificats GUCE. Retour : python manage.py migrate configuration_api 0098

from decimal import Decimal

from django.db import migrations

POURCENT = ("pourcentage", "%", Decimal("0"), Decimal("100"))
MONTANT = ("montant", "F", Decimal("0"), None)

PARAMETRES = [
    # clé, libellé, aide, (type, unité, minimum, maximum), valeur
    ("transport.taux_tous_risques_maritime", "Tous risques — maritime",
     "Taux proposé dans la cotation pour la garantie Tous risques (barème de la compagnie). Vide : saisi dans la cotation.",
     POURCENT, ""),
    ("transport.taux_tous_risques_aerien", "Tous risques — aérien", "Même usage, transport aérien.", POURCENT, ""),
    ("transport.taux_tous_risques_terrestre", "Tous risques — terrestre", "Même usage, transport par route.", POURCENT, ""),
    ("transport.taux_tous_risques_ferroviaire", "Tous risques — ferroviaire", "Même usage, transport par rail.", POURCENT, ""),
    ("transport.taux_tous_risques_fluvial", "Tous risques — fluvial", "Même usage, transport fluvial ou lagunaire.", POURCENT, ""),
    ("transport.taux_fap_sauf", "FAP Sauf — taux minimum réglementaire",
     "Taux proposé pour la garantie FAP Sauf (accidents majeurs) ; un taux inférieur est refusé.", POURCENT, "0.15"),
    ("transport.taux_accidents_caracterises", "Accidents caractérisés et vols consécutifs",
     "Taux proposé pour cette garantie, usuelle en transport terrestre. Vide : saisi dans la cotation.", POURCENT, ""),
    ("transport.taux_guerre", "Risques de guerre et assimilés — taux unique",
     "Ajouté au taux de la garantie de base quand l'extension est retenue. Vide : saisi dans la cotation.", POURCENT, ""),
    ("transport.taux_greves", "Risques de grèves et émeutes",
     "Ajouté au taux de la garantie de base quand l'extension est retenue. Vide : saisi dans la cotation.", POURCENT, ""),
    ("transport.surprime_transbordement", "Surprime pour transbordement", "Marchandise transbordée en cours de route.",
     POURCENT, "0.10"),
    ("transport.surprime_emballage", "Couverture de l'emballage — clause 53",
     "Surprime quand l'emballage lui-même est assuré.", POURCENT, "0.10"),
    ("transport.taux_chargement", "Risques de chargement et de déchargement",
     "Extension demandée au questionnaire des facultés terrestres. Vide : saisi dans la cotation.", POURCENT, ""),
    ("transport.prime_minimum", "Prime minimum exigible",
     "Prime nette minimale d'une police annuelle et de chaque voyage déclaré sur une police d'abonnement.", MONTANT, ""),
    ("transport.prime_minimum_police_voyage", "Prime minimum par police au voyage",
     "Prime nette minimale d'une police au voyage (vide : prime minimum exigible).", MONTANT, ""),
    ("transport.cout_police_voyage", "Coût de police — police au voyage",
     "Accessoires d'une police au voyage, proposés dans la cotation.", MONTANT, ""),
    ("transport.cout_par_voyage", "Coût par voyage — police d'abonnement",
     "Accessoires de chaque voyage déclaré sur une police d'abonnement, facturés avec la ressortie du mois.", MONTANT, ""),
    ("transport.cout_police_annuelle", "Coût de police — police annuelle",
     "Accessoires d'une police annuelle, proposés dans la cotation (non donné par le document OREOLE).", MONTANT, ""),
    ("transport.taux_taxe", "Taxe sur les contrats Transport",
     "Appliquée à la prime nette et aux accessoires (7 % sur les certificats GUCE), sauf affaire exonérée.", POURCENT, "7"),
]


def creer(apps, schema_editor):
    Parametre = apps.get_model("configuration_api", "ParametreGeneral")
    for ordre, (cle, libelle, aide, (type_, unite, minimum, maximum), valeur) in enumerate(PARAMETRES, start=2):
        Parametre.objects.get_or_create(Cle=cle, defaults={
            "Groupe": "transport", "Libelle": libelle, "Aide": aide, "Type": type_, "Valeur": valeur,
            "ValeurOrigine": valeur, "Unite": unite, "Minimum": minimum, "Maximum": maximum, "Ordre": ordre,
        })


def retirer(apps, schema_editor):
    apps.get_model("configuration_api", "ParametreGeneral").objects.filter(Cle__in=[p[0] for p in PARAMETRES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0098_courrier_attention_directeur_du_courtage"),
    ]

    operations = [
        migrations.RunPython(creer, retirer),
    ]
