# Commission du cabinet sur les contrats Transport importés du GUCE (constat du 2026-11-24 : « certaines commissions dues au
# cabinet sont à 0 ») : sp_generation_devis_transport_client lisait le taux du barème sans l'écrire et
# sp_generation_contrat_transport ne recopie pas la commission. L'import pose désormais taux et commission
# (views_transport_guce.poser_commission_transport, même requête) ; cette migration fait de même pour les contrats déjà
# émis à 0 F : taux du barème de la compagnie à la date d'émission, commission = prime nette x taux (ni FGA ni CEDEAO en
# Transport), devis et quittance alignés. Base locale au 2026-11-24 : 14 contrats SUNU (police 2431611260354K), 21 %,
# 14 737 072 F.
# Retour sans effet sur les données : une commission se corrige ensuite contrat par contrat (Modifier les contrats, taux
# de commission), une remise à 0 en bloc écraserait les corrections faites à la main.

from django.db import migrations

SQL = """
    WITH t AS (
        SELECT c.idcontrat, c.iddevis, c.idquittance,
               COALESCE(fn_get_taux_commission_offre(c.idproduit, c.idcompagnie,
                   COALESCE((SELECT MAX(dd.idoffre) FROM stddevisdetail dd WHERE dd.iddevis = c.iddevis), 0),
                   c.dateemission::date), 0) AS taux
        FROM stdcontrat c
        WHERE c.idproduit = 6 AND COALESCE(c.commissionintermediaire, 0) = 0 AND COALESCE(c.taux_commission, 0) = 0
          AND COALESCE(c.primenette, 0) > 0
          AND EXISTS (SELECT 1 FROM stdimportationcertificatdevis i WHERE i.iddevis = c.iddevis)
    ), contrats AS (
        UPDATE stdcontrat c SET taux_commission = t.taux, commissionintermediaire = ROUND(COALESCE(c.primenette, 0) * t.taux / 100, 0)
        FROM t WHERE c.idcontrat = t.idcontrat
        RETURNING c.idcontrat
    ), devis AS (
        UPDATE stddevis d SET commissionintermediaire = ROUND(COALESCE(d.primenette, 0) * t.taux / 100, 0)
        FROM t WHERE d.iddevis = t.iddevis
        RETURNING d.iddevis
    )
    UPDATE stdquittance q SET taux_commission = t.taux
    FROM t WHERE q.idquittance = t.idquittance
"""


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0229_brouillon_tous_devis"),
    ]

    operations = [migrations.RunSQL(SQL, migrations.RunSQL.noop)]
