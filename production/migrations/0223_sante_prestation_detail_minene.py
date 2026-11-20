# Consommations MINENE Santé (demande du 2026-11-19) : le détail des sinistres du gestionnaire (états personnalisés MCI, feuille
# ETATS PERSONNALISES : NPrestations, MatriculeP, TypePrestation TP/RD, TypeAffection...) porte des informations que le relevé d'Oreole
# Santé n'a pas. Colonnes ajoutées aux prestations, vides pour les relevés déjà importés :
# - type_affection (CARDIO, INFECTIEUX, DIGESTIVE...), code_affection, code_acte ;
# - sexe du bénéficiaire (le relevé MINENE n'a pas d'effectif du gestionnaire) ;
# - localite_centre : commune du centre exécutant.
# Retour : python manage.py migrate production 0222

from django.db import migrations

AJOUT = """
ALTER TABLE lephare_sante_prestation
    ADD COLUMN IF NOT EXISTS type_affection varchar(80),
    ADD COLUMN IF NOT EXISTS code_affection varchar(20),
    ADD COLUMN IF NOT EXISTS code_acte varchar(30),
    ADD COLUMN IF NOT EXISTS sexe varchar(1),
    ADD COLUMN IF NOT EXISTS localite_centre varchar(80);
"""
RETRAIT = """
ALTER TABLE lephare_sante_prestation
    DROP COLUMN IF EXISTS type_affection,
    DROP COLUMN IF EXISTS code_affection,
    DROP COLUMN IF EXISTS code_acte,
    DROP COLUMN IF EXISTS sexe,
    DROP COLUMN IF EXISTS localite_centre;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0222_avenants_retrait_resiliation_immatriculation"),
    ]

    operations = [
        migrations.RunSQL(AJOUT, RETRAIT),
    ]
