-- Document OREOLE « Codes catégorie - Numérotation » (TRANSPORT) : Facultés terrestres = 614 (et non 618).
-- Aucun devis ni contrat n'a été numéroté en 618 : seul le référentiel change.
UPDATE public.stdcategorie SET codecategorie = '614' WHERE idcategorie = 53 AND codecategorie = '618';
UPDATE public.stdtarif SET codecategorie = '614' WHERE idtarif = 126 AND codecategorie = '618';
