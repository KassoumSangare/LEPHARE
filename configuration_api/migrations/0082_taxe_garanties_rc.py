# Taux de taxe des garanties de l'offre RC PROFESSIONNELLE (171) absentes du barème du produit RC (8) :
# « RC après travaux » (254), « RC après livraison » (255) et « Vol » (12). Sans taux, la ventilation
# d'une prime imposée (sp_calcul_devis_prime_imposee) les laissait à 0 et reportait leur part sur la
# garantie la plus forte (constaté le 2026-10-12). Même taux que toutes les autres garanties RC (14,5 %).

from django.db import migrations

GARANTIES = (254, 255, 12)
ID_PRODUIT_RC = 8

AJOUT = """
INSERT INTO stdtauxtaxegarantieproduit (tauxtaxe, debutvalidite, finvalidite, idgarantie, idproduit, tauxtaxegroupe)
SELECT 14.50, DATE '2000-01-01', DATE '2050-12-31', g, %(produit)s, 0.00
FROM unnest(ARRAY[254, 255, 12]) AS g
WHERE NOT EXISTS (SELECT 1 FROM stdtauxtaxegarantieproduit t WHERE t.idproduit = %(produit)s AND t.idgarantie = g);
""" % {"produit": ID_PRODUIT_RC}

RETRAIT = """
DELETE FROM stdtauxtaxegarantieproduit
WHERE idproduit = %(produit)s AND idgarantie IN (254, 255, 12) AND debutvalidite = DATE '2000-01-01';
""" % {"produit": ID_PRODUIT_RC}


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0081_activer_saisie_rc"),
    ]

    operations = [
        migrations.RunSQL(sql=AJOUT, reverse_sql=RETRAIT),
    ]
