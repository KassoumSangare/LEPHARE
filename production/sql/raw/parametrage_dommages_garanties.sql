-- Branche Dommages (produit 9) : garanties des catégories qui n'en avaient aucune et taxes manquantes.
--
-- Constat du 2026-10-08 : sur les 12 catégories Dommages (tarifs 4xx), seules Tous Risques
-- Informatiques (offre 32), Globale de Banque (33) et Assurance Caution (135) ont des garanties
-- (NSIA, SUNU, AMSA). Les offres 119 à 127 n'en ont aucune : un devis y valait 0 F. Faute de
-- document OREOLE sur ces produits, chacune reçoit UNE garantie qui porte le nom de la catégorie
-- (comme la Caution, garantie unique « CAUTION »), pour les mêmes compagnies ; le détail des
-- garanties se règle ensuite dans l'admin (Réglages Dommages).
-- Taxes : toutes les garanties Dommages paramétrées sont à 14,5 % ; les garanties de la Globale de
-- Banque n'en avaient pas pour le produit 9 (taxe 0 et quittance sans détail) : 14,5 % aussi.

-- Garanties nommées comme leur catégorie, rangées sous « TOUS RISQUES » (19) ;
-- Bris de Machines reprend la garantie existante « BRIS DE MACHINE » (240).
INSERT INTO stdsousgarantie (codesousgarantie, libellesousgarantie, active, ordre, saisieauto, saisierd, saisiesante, saisietransport, idgarantie)
SELECT v.code, v.libelle, TRUE, v.ordre, FALSE, TRUE, FALSE, FALSE, 19
FROM (VALUES
	('19003', 'TOUS RISQUES CHANTIERS', 101),
	('19004', 'TOUS RISQUES MONTAGE', 102),
	('19005', 'PERTE D''EXPLOITATION', 103),
	('19006', 'DOMMAGE OUVRAGE', 104),
	('19007', 'TOUS RISQUES BIJOUTIER', 105),
	('19008', 'RISQUES EXCEPTIONNELS', 106),
	('19009', 'DOMMAGES EN TOUS LIEUX', 107),
	('19010', 'GLOBALE DOMMAGE', 108)
) AS v(code, libelle, ordre)
WHERE NOT EXISTS (SELECT 1 FROM stdsousgarantie AS s WHERE s.codesousgarantie = v.code);

-- Rattachement aux offres des catégories, pour NSIA (1), SUNU (14) et AMSA (21), sans franchise
INSERT INTO stdoffregarantie (idoffre, idsousgarantie, franchisemaximum, franchiseminimum, idcompagnie, tauxfranchise, ordreaffichage)
SELECT v.idoffre, sg.idsousgarantie, 0, 0, c.idcompagnie, 0, 0
FROM (VALUES
	(119, '19003'),
	(120, '19004'),
	(121, '30013'),
	(122, '19005'),
	(123, '19006'),
	(124, '19007'),
	(125, '19008'),
	(126, '19009'),
	(127, '19010')
) AS v(idoffre, code)
JOIN stdsousgarantie AS sg ON sg.codesousgarantie = v.code
CROSS JOIN (VALUES (1), (14), (21)) AS c(idcompagnie)
WHERE NOT EXISTS (SELECT 1 FROM stdoffregarantie AS og WHERE og.idoffre = v.idoffre)
  AND EXISTS (SELECT 1 FROM stdcompagnie AS sc WHERE sc.idcompagnie = c.idcompagnie);

-- Taxe d'enregistrement du produit 9 pour toute garantie d'une offre Dommages qui n'en a pas
INSERT INTO stdtauxtaxegarantieproduit (tauxtaxe, debutvalidite, finvalidite, idgarantie, idproduit, tauxtaxegroupe)
SELECT DISTINCT 14.50, DATE '2000-01-01', DATE '2050-12-31', og.idsousgarantie, 9, 0
FROM stdoffregarantie AS og
JOIN stdoffre AS o ON o.idoffre = og.idoffre
JOIN stdtarif AS t ON t.idtarif = o.idtarif AND t.codecategorie LIKE '4%'
WHERE og.idsousgarantie IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM stdtauxtaxegarantieproduit AS tt WHERE tt.idgarantie = og.idsousgarantie AND tt.idproduit = 9);
