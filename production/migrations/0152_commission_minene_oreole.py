# MINENE Santé : taux de commission du cabinet = celui de TARIFICATION MINENE SANTE.xlsx (« Taux de
# commission OREOLE ASSURANCES 6,5 % de la prime HT »), décision de l'utilisateur du 2026-10-11 de
# prendre le fichier pour référence. Jusqu'ici le taux de la Santé NSIA (15 %, toutes offres) était
# appliqué au devis et à la confirmation (contrat, quittance).
#
#   - fn_get_taux_commission_offre : pour les formules MINENE (17-22, 175, 176, 181), taux du cabinet de
#     la répartition de la prime Santé MINENE (stdrepartitionprimesante, réglable en Administration,
#     6,5 %) ; sinon fn_get_taux_commission (produit, compagnie).
#   - sp_creation_devis_sante (v5) et sp_confirmation_devis (v2 ; v1 = définition en base, jusqu'ici
#     absente du dépôt) l'utilisent.
#   - Devis MINENE non confirmés : commission recalculée (anciennes valeurs dans
#     lephare_sauvegarde_commission_minene). Les contrats émis ne sont pas modifiés.
#
# IA MINENE (24 %) et RC MINENE (23 %) : déjà les taux du fichier (produit et compagnie).
# Retour : python manage.py migrate production 0151

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade, load_sql_version

OFFRES_MINENE = "17, 18, 19, 20, 21, 22, 175, 176, 181"

RECALCUL_DEVIS = f"""
CREATE TABLE IF NOT EXISTS lephare_sauvegarde_commission_minene (
    iddevis integer PRIMARY KEY,
    commissionintermediaire numeric
);

INSERT INTO lephare_sauvegarde_commission_minene (iddevis, commissionintermediaire)
SELECT d.iddevis, d.commissionintermediaire
FROM stddevis AS d
WHERE d.idproduit = 5 AND NOT COALESCE(d.confirme, false)
  AND EXISTS (SELECT 1 FROM stddevisdetail AS dd WHERE dd.iddevis = d.iddevis AND dd.idoffre IN ({OFFRES_MINENE}))
ON CONFLICT (iddevis) DO NOTHING;

UPDATE stddevis AS d
SET commissionintermediaire = ROUND(COALESCE(d.primenette, 0) * fn_get_taux_commission_offre(
        5, d.idcompagnie, (SELECT MAX(dd.idoffre) FROM stddevisdetail AS dd WHERE dd.iddevis = d.iddevis),
        COALESCE(d.dateemission::date, CURRENT_DATE)) / 100, 0)
FROM lephare_sauvegarde_commission_minene AS s
WHERE s.iddevis = d.iddevis;
"""

RETOUR_DEVIS = """
UPDATE stddevis AS d
SET commissionintermediaire = s.commissionintermediaire
FROM lephare_sauvegarde_commission_minene AS s
WHERE s.iddevis = d.iddevis;

DROP TABLE IF EXISTS lephare_sauvegarde_commission_minene;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0151_minene_conditions_oreole"),
        ("configuration_api", "0067_seed_repartitionprimesante"),
    ]

    operations = [
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_get_taux_commission_offre", 1),
            "DROP FUNCTION IF EXISTS public.fn_get_taux_commission_offre(integer, integer, integer, date);",
        ),
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_creation_devis_sante", from_version=4, to_version=5)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_confirmation_devis", from_version=1, to_version=2)),
        migrations.RunSQL(RECALCUL_DEVIS, RETOUR_DEVIS),
    ]
