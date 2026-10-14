# Arrondi des primes TTC à la pièce de 5 F (demande du 2026-10-14 : « la monnaie en Côte d'Ivoire commence à 5 F ;
# un montant qui n'excède pas 2 F est ramené à 0, au-delà on le met à 5 F »).
#
#   - fn_lephare_arrondi_montant(montant, produit) : multiple de 5 le plus proche (reste <= 2 F ramené à
#     l'inférieur, au-delà porté au supérieur) ; pas et seuil dans Administration > Paramètres du cabinet > Règles de
#     gestion > Arrondi des montants (configuration_api 0088), arrondi désactivable par produit (Administration >
#     Produits).
#   - Déclencheur avant écriture de la prime TTC sur stddevis, stdcontrat et stdquittance : toutes les branches
#     (procédures d'URANUS et de LE PHARE) et tous les documents, qui lisent la TTC enregistrée. Remplace l'arrondi
#     NSIA au multiple de 5 supérieur d'URANUS (fn_calculer_primettc), qui n'était plus rattaché à aucune table.
#   - Montants déjà enregistrés inchangés (arrondis à leur prochaine mise à jour) ; encaissements non concernés.
# Retour : python manage.py migrate production 0158

from django.db import migrations

from uranus.utils.migrations import load_sql_version

TABLES = ("stddevis", "stdcontrat", "stdquittance")
DECLENCHEURS = " ".join(
    f"DROP TRIGGER IF EXISTS trg_lephare_arrondi_primettc ON public.{t};"
    f" CREATE TRIGGER trg_lephare_arrondi_primettc BEFORE INSERT OR UPDATE OF primettc ON public.{t}"
    f" FOR EACH ROW EXECUTE FUNCTION public.trg_fn_lephare_arrondi_primettc();"
    for t in TABLES
)
RETRAIT = " ".join(f"DROP TRIGGER IF EXISTS trg_lephare_arrondi_primettc ON public.{t};" for t in TABLES) + (
    " DROP FUNCTION IF EXISTS public.trg_fn_lephare_arrondi_primettc();"
    " DROP FUNCTION IF EXISTS public.fn_lephare_arrondi_montant(numeric, integer);"
)


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0158_renouvellement_sante_rc"),
        ("configuration_api", "0088_arrondi_montants"),
    ]

    operations = [
        migrations.RunSQL(load_sql_version(__file__, "functions/fn_lephare_arrondi_montant", 1) + "\n" + DECLENCHEURS, RETRAIT),
    ]
