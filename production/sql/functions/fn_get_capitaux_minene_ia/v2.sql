CREATE OR REPLACE FUNCTION public.fn_get_capitaux_minene_ia()
 RETURNS TABLE(capitaldeces numeric, capitalipp numeric, capitalfraistraitement numeric)
 LANGUAGE plpgsql
AS $function$
BEGIN
	-- Réglages Santé MINENE (2 000 000 / 2 000 000 / 100 000 à l'origine)
	RETURN QUERY
		SELECT fn_lephare_parametre_nombre('sante.minene.ia_capital_deces', 2000000),
			   fn_lephare_parametre_nombre('sante.minene.ia_capital_ipt', 2000000),
			   fn_lephare_parametre_nombre('sante.minene.ia_frais_medicaux', 100000);
END;
$function$;
