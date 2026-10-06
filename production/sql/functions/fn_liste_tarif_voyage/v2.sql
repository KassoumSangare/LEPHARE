CREATE OR REPLACE FUNCTION public.fn_liste_tarif_voyage(id_compagnie integer)
 RETURNS TABLE(id_tarif integer, libelle_tarif character varying, code_categorie character varying)
 LANGUAGE plpgsql
AS $function$
-- Formules Voyage de la compagnie ayant au moins une offre active proposée dans une zone.
BEGIN
		RETURN QUERY
			SELECT t.IdTarif, t.Libelle, t.CodeCategorie
			FROM public.StdTarif AS t
			WHERE (t.IdTarif <> 0) AND (t.CodeCategorie = CASE fn_liste_tarif_voyage.id_compagnie
														WHEN 1 THEN '136'
														WHEN 21 THEN '137'
														WHEN 14 THEN '138'
														ELSE '135'
														END)
				AND EXISTS (SELECT 1 FROM public.stdoffre AS o
							INNER JOIN public.stdoffrevoyagezone AS oz ON (oz.id_offre = o.idoffre)
							WHERE o.idtarif = t.IdTarif AND o.actif AND o.ppr = 'V')
			ORDER BY t.IdTarif;
END;
$function$;
