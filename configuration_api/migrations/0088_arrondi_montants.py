# Arrondi des primes TTC à la pièce de 5 F (demande du 2026-10-14), réglable dans l'administration :
#   - lephare_parametre (groupe « montants ») : pas de l'arrondi (5 F ; 0 ou 1 : pas d'arrondi) et reste jusqu'auquel
#     le montant est ramené au multiple inférieur (2 F) — Administration > Paramètres du cabinet > Règles de gestion ;
#   - lephare_produit_parametre.arrondittc : arrondi appliqué ou non aux primes du produit (Administration > Produits ;
#     les grilles Voyage des compagnies ont des TTC qui ne sont pas des multiples de 5).
# Appliqué par fn_lephare_arrondi_montant et le déclencheur de la migration production 0159.

from django.db import migrations, models

PARAMETRES = [
    ("montants.arrondi_pas", "montants", "Arrondi des primes TTC",
     "Les primes TTC des devis, contrats et quittances sont arrondies à ce multiple (5 F : plus petite pièce en "
     "Côte d'Ivoire). 0 ou 1 : pas d'arrondi.", "entier", "5", "F", 0, 100, 1),
    ("montants.arrondi_seuil", "montants", "Reste ramené au multiple inférieur",
     "Reste jusqu'auquel la prime est ramenée au multiple inférieur ; au-delà, elle est portée au multiple supérieur. "
     "Avec un arrondi de 5 F et 2 F ici : 13 452 F devient 13 450 F, 13 453 F devient 13 455 F.", "entier", "2", "F", 0, 99, 2),
]


def initialiser(apps, schema_editor):
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
        ("configuration_api", "0087_dommages_documents_caution"),
    ]

    operations = [
        migrations.AddField(
            model_name="produitparametre",
            name="ArrondiTtc",
            field=models.BooleanField(db_column="arrondittc", default=True),
        ),
        migrations.RunPython(initialiser, retirer),
    ]
