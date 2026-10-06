CREATE OR REPLACE FUNCTION public.fn_liste_tarif_voyage(id_compagnie integer)
 RETURNS TABLE(id_tarif integer, libelle_tarif character varying, code_categorie character varying)
 LANGUAGE plpgsql
AS $function$
BEGIN

		RETURN QUERY
			SELECT IdTarif AS id_tarif, Libelle AS libelle_tarif, CodeCategorie AS code_categorie
			FROM StdTarif
			WHERE (IdTarif <> 0) AND (CodeCategorie = CASE id_compagnie
														WHEN 1 THEN '136'
														WHEN 21 THEN '137'
														WHEN 14 THEN '138'
														ELSE '135'
														END);

END;
$function$;
