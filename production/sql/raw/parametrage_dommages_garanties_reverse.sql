-- Retour avant le paramétrage Dommages de la migration production 0148

DELETE FROM stdtauxtaxegarantieproduit AS tt
USING stdsousgarantie AS sg
WHERE tt.idgarantie = sg.idsousgarantie AND tt.idproduit = 9
  -- garanties créées, Bris de Machine (240) et garanties de la Globale de Banque (56, 83 à 88, 110, 139)
  AND sg.codesousgarantie IN ('19003', '19004', '19005', '19006', '19007', '19008', '19009', '19010', '30013',
                              '80003', '50012', '50013', '50014', '50015', '50016', '50017', '10004', '50031')
  AND tt.debutvalidite = DATE '2000-01-01' AND tt.finvalidite = DATE '2050-12-31';

DELETE FROM stdoffregarantie AS og
USING stdsousgarantie AS sg
WHERE og.idsousgarantie = sg.idsousgarantie
  AND og.idoffre IN (119, 120, 121, 122, 123, 124, 125, 126, 127)
  AND sg.codesousgarantie IN ('19003', '19004', '19005', '19006', '19007', '19008', '19009', '19010', '30013');

DELETE FROM stdsousgarantie AS sg
WHERE sg.codesousgarantie IN ('19003', '19004', '19005', '19006', '19007', '19008', '19009', '19010')
  AND NOT EXISTS (SELECT 1 FROM stddevisdetgarantie AS g WHERE g.idgarantie = sg.idsousgarantie)
  AND NOT EXISTS (SELECT 1 FROM stdcontratdetgarantie AS g WHERE g.idgarantie = sg.idsousgarantie)
  AND NOT EXISTS (SELECT 1 FROM stdoffregarantie AS og WHERE og.idsousgarantie = sg.idsousgarantie);
