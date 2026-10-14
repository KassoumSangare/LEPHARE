# Compte rendu de la séance LE PHARE du 12-10-2026 (Automobile) : catégorie 204 « TRANSPORT PUBLIC DE
# VOYAGEURS », deux possibilités de saisie : Pool TPV (tarif joint) ou assureur.
#
#   - Offre « POOL TPV (CAT 204) » (tarif 92) : RC, CEDEAO et Recours pour NSIA, SUNU et AMSA, copiées de
#     l'offre 149 ; son identifiant est inscrit dans le paramètre auto.pool_tpv.offre.
#   - CEDEAO de la catégorie 204 : 1 000 F (stdtarifdetail n'avait aucune ligne pour le tarif 92 ; les
#     contrats TPV repris d'URANUS portent 1 000 F).
#   - fn_pool_tpv, fn_est_offre_pool_tpv, fn_garantie_offre_tpv (nouvelles) ; fn_garantie_offre v2 : branche
#     204 (v1 = définition en base, sans branche 204 : le moteur ne rendait rien, les devis TPV d'URANUS
#     étaient en primes imposées) ; sp_finalisation_devis v6 : accessoire du Pool pour la durée.
# Retour : python manage.py migrate production 0156

from django.db import migrations

from uranus.utils.migrations import load_sql_upgrade, load_sql_version

LIBELLE = "POOL TPV (CAT 204)"

CREATION_OFFRE = f"""
SELECT setval(pg_get_serial_sequence('stdoffre', 'idoffre'), (SELECT MAX(idoffre) FROM stdoffre));
SELECT setval(pg_get_serial_sequence('stdoffregarantie', 'idoffregarantie'), (SELECT MAX(idoffregarantie) FROM stdoffregarantie));
SELECT setval(pg_get_serial_sequence('stdtarifdetail', 'iddetail'), (SELECT MAX(iddetail) FROM stdtarifdetail));

INSERT INTO stdoffre (actif, anticipation, differe, echeance, entreprise, exoneredeaccess, exoneredetaxes, flotte, gestion,
                      jpaiement, libelleoffre, majfract, payement, ppr, renouvelable, visibilite, idtarif, idzonecouverture)
SELECT actif, anticipation, differe, echeance, entreprise, exoneredeaccess, exoneredetaxes, flotte, gestion,
       jpaiement, '{LIBELLE}', majfract, payement, ppr, renouvelable, visibilite, idtarif, idzonecouverture
FROM stdoffre
WHERE idoffre = 149 AND NOT EXISTS (SELECT 1 FROM stdoffre WHERE libelleoffre = '{LIBELLE}');

INSERT INTO stdoffregarantie (idoffre, idsousgarantie, franchisemaximum, franchiseminimum, idcompagnie, tauxfranchise, ordreaffichage)
SELECT (SELECT MAX(idoffre) FROM stdoffre WHERE libelleoffre = '{LIBELLE}'), og.idsousgarantie, og.franchisemaximum,
       og.franchiseminimum, og.idcompagnie, og.tauxfranchise, og.ordreaffichage
FROM stdoffregarantie AS og
WHERE og.idoffre = 149 AND og.idsousgarantie IN (1, 3, 4)
  AND NOT EXISTS (SELECT 1 FROM stdoffregarantie AS x
                  WHERE x.idoffre = (SELECT MAX(idoffre) FROM stdoffre WHERE libelleoffre = '{LIBELLE}')
                    AND x.idsousgarantie = og.idsousgarantie AND x.idcompagnie = og.idcompagnie);

UPDATE lephare_parametre
SET valeur = (SELECT MAX(idoffre) FROM stdoffre WHERE libelleoffre = '{LIBELLE}')::text,
    valeurorigine = (SELECT MAX(idoffre) FROM stdoffre WHERE libelleoffre = '{LIBELLE}')::text
WHERE cle = 'auto.pool_tpv.offre';

INSERT INTO stdtarifdetail (puissancemin, puissancemax, tonnagemin, tonnagemax, capitalmin, capitalmax, franchisemin, franchisemax,
                            franchiseminimale, agevehiculemin, agevehiculemax, ageconducteurmin, ageconducteurmax, nombreplacesmin,
                            nombreplacesmax, taux, primemin, placesgrat, primeplace, primegar, deces, ipp, fraismed, minprorata,
                            codecarburant, idgarantie, idtarif)
SELECT puissancemin, puissancemax, tonnagemin, tonnagemax, capitalmin, capitalmax, franchisemin, franchisemax,
       franchiseminimale, agevehiculemin, agevehiculemax, ageconducteurmin, ageconducteurmax, nombreplacesmin,
       nombreplacesmax, taux, primemin, placesgrat, primeplace, primegar, deces, ipp, fraismed, minprorata,
       codecarburant, idgarantie, 92
FROM stdtarifdetail
WHERE iddetail = 55 AND idgarantie = 3
  AND NOT EXISTS (SELECT 1 FROM stdtarifdetail WHERE idtarif = 92 AND idgarantie = 3);
"""

RETOUR_OFFRE = f"""
DELETE FROM stdtarifdetail WHERE idtarif = 92 AND idgarantie = 3 AND primegar = 1000;
DELETE FROM stdoffregarantie
WHERE idoffre IN (SELECT idoffre FROM stdoffre WHERE libelleoffre = '{LIBELLE}')
  AND NOT EXISTS (SELECT 1 FROM stddevisdetail AS d WHERE d.idoffre = stdoffregarantie.idoffre);
DELETE FROM stdoffre
WHERE libelleoffre = '{LIBELLE}' AND NOT EXISTS (SELECT 1 FROM stddevisdetail AS d WHERE d.idoffre = stdoffre.idoffre);
UPDATE lephare_parametre SET valeur = '', valeurorigine = '' WHERE cle = 'auto.pool_tpv.offre';
"""


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0156_depreciation_et_renouvellement"),
        ("configuration_api", "0086_pool_tpv"),
    ]

    operations = [
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_pool_tpv", 1),
            "DROP FUNCTION IF EXISTS public.fn_pool_tpv(integer, date, date); DROP FUNCTION IF EXISTS public.fn_est_offre_pool_tpv(integer);",
        ),
        migrations.RunSQL(
            load_sql_version(__file__, "functions/fn_garantie_offre_tpv", 1),
            "DROP FUNCTION IF EXISTS public.fn_garantie_offre_tpv(integer, integer, integer, integer, integer, integer, date, date);",
        ),
        migrations.RunSQL(*load_sql_upgrade(__file__, "functions/fn_garantie_offre", from_version=1, to_version=2)),
        migrations.RunSQL(*load_sql_upgrade(__file__, "procedures/sp_finalisation_devis", from_version=5, to_version=6)),
        migrations.RunSQL(CREATION_OFFRE, RETOUR_OFFRE),
    ]
