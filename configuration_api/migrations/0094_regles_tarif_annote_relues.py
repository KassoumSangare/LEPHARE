# Règles du tarif annoté NSIA (« COMMENTAIRE ANNOTE TARIF AUTOMOBILE NSIA CI », 12 feuilles, catégories 1 à 12)
# relues feuille par feuille le 2026-10-17 : la règle énoncée par le texte prime, les montants (anciens) restent
# réglables dans Administration > Réglages Automobile > Règles des garanties.
#
#   Corrigées :
#     - défense-recours 4 200 F avec les dommages ou la collision : plus en catégorie 203 (feuille « cat 3 » : 10 % de
#       la RC, « n'interagit avec aucune garantie », comme la catégorie 4) ;
#     - bris de glace offert avec les seuls dommages au véhicule (toutes les feuilles : « attribuée sans prime quand le
#       client a la garantie dommage au véhicule » ; la collision n'offre que le recours anticipé) : facturé dans une
#       offre tierce collision.
#   Ajoutées :
#     - sécurité routière « personnes transportées » (forme que prend la sécurité routière dans le barème des
#       catégories 3 et 4, fn_retenir_garantie_securite_routiere) non commercialisée là où la sécurité routière ne
#       l'est pas (3, 4, 5, 7, 8, 9, 10) ;
#     - vol et incendie vendus ensemble en catégories 3, 4 et 7 (type nouveau « COUPLEE ») ;
#     - catégorie 5 (deux roues) : vol, vol des accessoires, bris de glace, incendie, dommages, collision et
#       immobilisation non commercialisés (« - » dans la feuille) ;
#     - primes minimums des dommages (246 420 F) et de la collision (150 000 F) en catégories 3 et 4 (type nouveau
#       « PRIME_MINIMUM », appliqué par le barème : production 0165).
# Retour : python manage.py migrate configuration_api 0093

from decimal import Decimal

from django.db import migrations, models

NSIA = 1
SOURCE = "Tarif annoté NSIA (relu le 2026-10-17)"
DR_CATEGORIES_AVANT = "201,202,203,207,208,209,210,212"
DR_CATEGORIES = "201,202,207,208,209,210,212"
DR_COMMENTAIRE = (
    "Défense-recours : forfait de 4 200 F (au lieu de 7 950 F) avec les dommages au véhicule ou la collision (prime "
    "nette d'URANUS ; le tarif annoté indique 4 240 F). Catégories 3 et 4 : 10 % de la RC sans lien avec les dommages."
)
BDG_COMMENTAIRE = (
    "Bris de glace attribué sans prime avec les dommages au véhicule (compris dans leur taux) ; facturé avec la seule "
    "collision."
)
SANS_SR = "203,204,205,207,208,209,210"
DEUX_ROUES = "205"
VOL_INCENDIE = "203,204,207"
# (sous-garantie, type, garanties liées, catégories, prime annuelle, commentaire)
AJOUTS = [
    (163, "NON_PROPOSEE", "", SANS_SR, None,
     "Sécurité routière (personnes transportées, sa forme au barème des catégories 3 et 4) : non commercialisée dans "
     "cette catégorie."),
    (10, "COUPLEE", "12,13", VOL_INCENDIE, None,
     "Incendie : se vend en même temps que le vol (tarif à lecture directe vol, vol à main armée et incendie)."),
    (12, "COUPLEE", "10", VOL_INCENDIE, None, "Vol : vendu concomitamment avec l'incendie."),
    (13, "COUPLEE", "10", VOL_INCENDIE, None, "Vol à mains armées : vendu concomitamment avec l'incendie."),
    (7, "PRIME_MINIMUM", "", "203,204", Decimal("246420"), "Dommages au véhicule : prime minimum (tarif annoté)."),
    (8, "PRIME_MINIMUM", "", "203,204", Decimal("150000"), "Dommages collision : prime minimum (tarif annoté)."),
] + [
    (sg, "NON_PROPOSEE", "", DEUX_ROUES, None, f"{nom} : non commercialisé pour les deux roues.")
    for sg, nom in [
        (7, "Dommages au véhicule"), (8, "Dommages collision"), (9, "Bris de glace"),
        (172, "Bris de glace (toits ouvrants)"), (10, "Incendie"), (12, "Vol"), (13, "Vol à mains armées"),
        (14, "Vandalisme"), (15, "Vol des accessoires"), (21, "Immobilisation"),
    ]
]


def appliquer(apps, schema_editor):
    Regle = apps.get_model("configuration_api", "AutoRegleInteraction")
    regles = Regle.objects.filter(IdCompagnie=NSIA)
    if not regles.exists():
        return
    regles.filter(IdSousGarantie=4, Type="PRIME_SI", Categories=DR_CATEGORIES_AVANT).update(
        Categories=DR_CATEGORIES, Commentaire=DR_COMMENTAIRE, ModifiePar=SOURCE)
    regles.filter(IdSousGarantie=9, Type="OFFERTE_SI", Liees="7,8").update(
        Liees="7", Commentaire=BDG_COMMENTAIRE, ModifiePar=SOURCE)
    ordre = max(regles.values_list("Ordre", flat=True) or [0])
    for sg, type_, liees, categories, prime, commentaire in AJOUTS:
        if regles.filter(IdSousGarantie=sg, Type=type_, Categories=categories).exists():
            continue
        ordre += 1
        Regle.objects.create(
            IdCompagnie=NSIA, IdSousGarantie=sg, Type=type_, Liees=liees, Categories=categories, PrimeAnnuelle=prime,
            Commentaire=commentaire, Ordre=ordre, ModifiePar=SOURCE, AppliqueeBareme=type_ == "PRIME_MINIMUM",
        )


def retablir(apps, schema_editor):
    Regle = apps.get_model("configuration_api", "AutoRegleInteraction")
    regles = Regle.objects.filter(IdCompagnie=NSIA)
    for sg, type_, _, categories, *_ in AJOUTS:
        regles.filter(IdSousGarantie=sg, Type=type_, Categories=categories, ModifiePar=SOURCE).delete()
    # Types inconnus avant cette migration
    regles.filter(Type__in=["COUPLEE", "PRIME_MINIMUM"]).delete()
    regles.filter(IdSousGarantie=4, Type="PRIME_SI", Categories=DR_CATEGORIES).update(Categories=DR_CATEGORIES_AVANT)
    regles.filter(IdSousGarantie=9, Type="OFFERTE_SI", Liees="7").update(
        Liees="7,8",
        Commentaire="Bris de glace attribué sans prime avec les dommages au véhicule ou la collision (compris dans leur taux).")


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0093_reglage_part_afs_ci"),
    ]

    operations = [
        migrations.AlterField(
            model_name="autoregleinteraction",
            name="Type",
            field=models.CharField(choices=[
                ("OBLIGATOIRE", "Obligatoire"), ("REQUIERT", "Exige une des garanties liées"),
                ("EXCLUE_SI", "Exclue si une des garanties liées est souscrite"),
                ("OFFERTE_SI", "Offerte si une des garanties liées est souscrite"),
                ("PRIME_SI", "Prime forfaitaire si une des garanties liées est souscrite"),
                ("COUPLEE", "Vendue avec une des garanties liées"), ("PRIME_MINIMUM", "Prime minimum"),
                ("NON_PROPOSEE", "Non commercialisée"), ("NON_COCHEE", "Proposée sans être cochée d'office"),
            ], db_column="type", max_length=20),
        ),
        migrations.RunPython(appliquer, retablir),
    ]
