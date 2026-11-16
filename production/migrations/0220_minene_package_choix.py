# MINENE en package (production/minene_package.py), demande du 2026-11-16 : « à la création d'un devis ou au renouvellement
# d'un contrat en MINENE, on doit pouvoir cocher ou décocher IA et RC ».
# - lephare_minene_package : pour chaque devis Santé MINENE (affaire nouvelle ou renouvellement), l'Individuelle Accidents et
#   la RC chef de famille souscrites avec la Santé. Une case décochée : son devis lié est archivé et elle n'est ni créée, ni
#   renouvelée, ni émise à la confirmation. Sans ligne pour un devis, les deux sont souscrites (comportement d'avant).
# Retour : python manage.py migrate production 0219 (table supprimée : IA et RC de nouveau toujours souscrites).

from django.db import migrations

CREATION = """
CREATE TABLE IF NOT EXISTS public.lephare_minene_package (
    iddevis_sante integer PRIMARY KEY,
    ia boolean NOT NULL DEFAULT TRUE,
    rc boolean NOT NULL DEFAULT TRUE,
    idoperateur integer,
    datecreation timestamptz NOT NULL DEFAULT now(),
    datemodification timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.lephare_minene_package IS 'MINENE : IA et RC chef de famille souscrites avec chaque devis Santé (cases de l''écran Santé)';
"""

SUPPRESSION = "DROP TABLE IF EXISTS public.lephare_minene_package;"


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0219_vie_offres_commerciales"),
    ]

    operations = [migrations.RunSQL(CREATION, SUPPRESSION)]
