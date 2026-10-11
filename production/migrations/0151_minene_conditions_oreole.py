# MINENE Santé + IA + RC : conditions des documents OREOLE (Desktop\_OREOLE ASSURANCE\SANTE :
# TARIFICATION MINENE SANTE.xlsx, BAREME_70-80.pdf, cp_MINENE.pdf), vérification du 2026-10-10.
#
#   - sp_creation_devis_sante (v4) : chaque famille est tarifée selon la formule de sa couverture
#     (SOLO / FAMILLE / FAMILLE PLUS) et non selon celle du devis ; surprimes d'âge et d'affection sur
#     la prime de base de cette formule, âge atteint à la date d'effet ; accessoire de la grille de la
#     compagnie par famille (9 000 / 12 000 / 24 000 F) au lieu de la grille appliquée à la prime de
#     tout le devis puis multipliée par le nombre de familles ; taille des familles contrôlée à la
#     création (SOLO 1, FAMILLE 3, FAMILLE PLUS 6).
#   - sp_saisie_affilie_sante (v3) : taille des familles et âge limite (69 ans) aussi pour le
#     80 %-80 % (offres 175, 176, 181) ; enfants admis jusqu'à 21 ans révolus sans certificat
#     (25 ans avec certificat de scolarité ou rapport médical), au lieu de 20.
#   - sp_saisie_adherent_sante (v2, procédure jusqu'ici absente du dépôt) : âge limite 80 %-80 %.
#   - sp_finalisation_devis (v4) et sp_creation_devis_risques_divers (v2) : commission IA MINENE
#     (24 %) et RC MINENE (23 %) calculées sur la prime de tous les adhérents, et non d'un seul.
#
# Retour : python manage.py migrate production 0150

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade


def procedure(chemin, de, vers):
    return migrations.RunSQL(*load_sql_upgrade(__file__, chemin, from_version=de, to_version=vers))


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0150_parts_ayants_droit_ia_non_precisees"),
    ]

    operations = [
        procedure("procedures/sp_creation_devis_sante", 3, 4),
        procedure("procedures/sp_saisie_affilie_sante", 2, 3),
        procedure("procedures/sp_saisie_adherent_sante", 1, 2),
        procedure("procedures/sp_finalisation_devis", 3, 4),
        procedure("procedures/sp_creation_devis_risques_divers", 1, 2),
    ]
