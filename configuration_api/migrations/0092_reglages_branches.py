# Admin plus autonome, toutes branches (demande du 2026-10-16 : « éviter les interventions techniques sur le code
# source », « pense aux autres branches de production ») : limites encore écrites dans les écrans de devis, réglables
# dans Administration > Le cabinet & règles de gestion, onglet Règles de gestion. Valeurs de départ = celles du code.
#   - réductions commerciales maximales : Automobile, Individuelle Accidents, Responsabilité civile (35 %, comme
#     URANUS) ; celle du Voyage existait (voyage.taux_reduction_max) mais l'écran gardait 35 % : regroupée ici ;
#   - IA NSIA (tarif « TARIF IA_NSIA CI », feuille Clauses) : âge maximum à la souscription, indemnité maximale ;
#   - Santé : gestionnaire des contrats (tiers payant), repris sur les contrats et les conditions particulières.
# Retour : python manage.py migrate configuration_api 0091

from decimal import Decimal

from django.db import migrations

PARAMETRES = [
    # (clé, groupe, libellé, aide, type, valeur, unité, min, max, ordre)
    ("devis.reduction_max_auto", "reductions", "Automobile",
     "Réduction commerciale la plus élevée acceptée à la saisie d'un devis Automobile (mono ou flotte). Une réduction "
     "accordée demande toujours l'accord de la direction (Demandes à valider).",
     "pourcentage", "35", "%", 0, 100, 1),
    ("devis.reduction_max_ia", "reductions", "Individuelle Accidents",
     "Réduction commerciale la plus élevée acceptée à la saisie d'un devis Individuelle Accidents.",
     "pourcentage", "35", "%", 0, 100, 2),
    ("devis.reduction_max_rc", "reductions", "Responsabilité civile",
     "Réduction commerciale la plus élevée acceptée à la saisie d'un devis Responsabilité civile.",
     "pourcentage", "35", "%", 0, 100, 3),
    ("ia.nsia_age_max", "ia", "Âge maximum à la souscription (NSIA)",
     "Au-delà de cet âge à la date d'effet, l'écran avertit que NSIA ne garantit pas la personne, sauf dérogation de "
     "l'assureur (tarif IA NSIA, feuille Clauses).",
     "entier", "60", "ans", 0, 120, 1),
    ("ia.nsia_indemnite_max", "ia", "Indemnité maximale par assuré et par sinistre (NSIA)",
     "Au-delà de ce capital décès ou invalidité, l'écran avertit que l'indemnité NSIA est limitée (tarif IA NSIA, "
     "feuille Clauses).",
     "montant", "200000000", "F", 0, None, 2),
    ("sante.gestionnaire", "sante", "Gestionnaire des contrats Santé",
     "Tiers gestionnaire (tiers payant, réseau de prestataires) repris sur les contrats Santé et imprimé sur les "
     "conditions particulières.",
     "texte", "VITALIS SANTE", "", None, None, 1),
]


def creer(apps, schema_editor):
    Parametre = apps.get_model("configuration_api", "ParametreGeneral")
    for cle, groupe, libelle, aide, type_, valeur, unite, minimum, maximum, ordre in PARAMETRES:
        Parametre.objects.get_or_create(Cle=cle, defaults={
            "Groupe": groupe, "Libelle": libelle, "Aide": aide, "Type": type_, "Valeur": valeur, "ValeurOrigine": valeur,
            "Unite": unite, "Minimum": None if minimum is None else Decimal(minimum),
            "Maximum": None if maximum is None else Decimal(maximum), "Ordre": ordre,
        })
    Parametre.objects.filter(Cle="voyage.taux_reduction_max").update(
        Groupe="reductions", Libelle="Voyage", Ordre=4,
        Aide="Réduction commerciale la plus élevée acceptée à la saisie et à l'enregistrement d'un devis Voyage.")


def retirer(apps, schema_editor):
    Parametre = apps.get_model("configuration_api", "ParametreGeneral")
    Parametre.objects.filter(Cle__in=[p[0] for p in PARAMETRES]).delete()
    Parametre.objects.filter(Cle="voyage.taux_reduction_max").update(
        Groupe="voyage", Libelle="Réduction commerciale maximale (Voyage)", Ordre=1,
        Aide="Taux de réduction le plus élevé accepté à l'enregistrement d'un devis Voyage.")


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0091_regles_appliquees_bareme"),
    ]

    operations = [
        migrations.RunPython(creer, retirer),
    ]
