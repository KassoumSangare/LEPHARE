# Oreole Santé (demande du 2026-11-23) : « on peut déjà faire une surprime, on doit pouvoir faire une réduction et la réduction peut
# être en montant ou en pourcentage ». Réduction saisie par famille (sante/oreole.py, montant_reduction) :
#  - reductiontype : 'M' (montant) ou 'P' (pourcentage), '' sans réduction ;
#  - reductionvaleur : le montant ou le taux saisi ;
#  - montantreduction : la réduction calculée, retirée de la cotisation hors cartes (et des frais courtiers : prime HT, IA et AFA inchangées).
# Devis et contrats existants : sans réduction (valeurs par défaut).
# Retour : python manage.py migrate production 0227 (supprime les colonnes ; les cotisations enregistrées ne changent pas).

from django.db import migrations

AJOUT = """
ALTER TABLE public.lephare_oreole_adherent
    ADD COLUMN reductiontype varchar(1) NOT NULL DEFAULT '' CHECK (reductiontype IN ('', 'M', 'P')),
    ADD COLUMN reductionvaleur numeric(14, 2) NOT NULL DEFAULT 0 CHECK (reductionvaleur >= 0),
    ADD COLUMN montantreduction numeric(14, 2) NOT NULL DEFAULT 0 CHECK (montantreduction >= 0);
COMMENT ON COLUMN public.lephare_oreole_adherent.reductiontype IS 'Réduction de la famille : M montant, P pourcentage, vide sans réduction';
COMMENT ON COLUMN public.lephare_oreole_adherent.montantreduction IS 'Réduction retirée de la cotisation hors cartes (frais courtiers)';
"""

RETRAIT = """
ALTER TABLE public.lephare_oreole_adherent
    DROP COLUMN IF EXISTS montantreduction,
    DROP COLUMN IF EXISTS reductionvaleur,
    DROP COLUMN IF EXISTS reductiontype;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0227_cp_auto_bns_reductions"),
    ]

    operations = [migrations.RunSQL(AJOUT, RETRAIT)]
