# Bénéficiaires IA : part retirée quand l'assuré n'en a pas précisé (demande OREOLE du 2026-10-10,
# suite du compte rendu du 2026-10-08). Depuis le 2026-10-09 l'import et l'écran laissent la part à 0
# (non précisée, rien d'imprimé) ; les bénéficiaires enregistrés avant gardaient les parts posées
# automatiquement : 100 % pour un bénéficiaire unique, parts égales sinon (50/50, 33,34/33,33/33,33,
# 4 × 25). Elles sont remises à 0. Les parts inégales (ex. 50/25/25), précisées par l'assuré, restent.
# Sans part précisée, les bénéficiaires se partagent le capital à parts égales : rien n'est perdu.
# Les parts retirées sont gardées dans lephare_sauvegarde_part_ayant_droit_ia.
# Retour : python manage.py migrate production 0149

from django.db import migrations

RETRAIT_PARTS = """
CREATE TABLE IF NOT EXISTS lephare_sauvegarde_part_ayant_droit_ia (
    idayantdroit integer PRIMARY KEY,
    idassure integer NOT NULL,
    part numeric NOT NULL
);

WITH parts_automatiques AS (
    SELECT idassure
    FROM stdayantdroitia
    GROUP BY idassure
    HAVING bool_and(COALESCE(part, 0) > 0)
       AND MAX(part) - MIN(part) <= 0.02
       AND ABS(SUM(part) - 100) <= 0.1
)
INSERT INTO lephare_sauvegarde_part_ayant_droit_ia (idayantdroit, idassure, part)
SELECT a.idayantdroit, a.idassure, a.part
FROM stdayantdroitia AS a
JOIN parts_automatiques USING (idassure)
ON CONFLICT (idayantdroit) DO NOTHING;

UPDATE stdayantdroitia AS a
SET part = 0
FROM lephare_sauvegarde_part_ayant_droit_ia AS s
WHERE s.idayantdroit = a.idayantdroit;
"""

RETOUR_PARTS = """
UPDATE stdayantdroitia AS a
SET part = s.part
FROM lephare_sauvegarde_part_ayant_droit_ia AS s
WHERE s.idayantdroit = a.idayantdroit AND COALESCE(a.part, 0) = 0;

DROP TABLE IF EXISTS lephare_sauvegarde_part_ayant_droit_ia;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0149_minene_rc_surprime_age"),
    ]

    operations = [
        migrations.RunSQL(RETRAIT_PARTS, RETOUR_PARTS),
    ]
