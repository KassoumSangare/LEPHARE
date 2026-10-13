CREATE OR REPLACE FUNCTION public.fn_get_capitaux_minene_rc()
 RETURNS TABLE(capitaldommagecorporel numeric, capitaldommagemateriel numeric, capitalintoxicationalimentaire numeric)
 LANGUAGE plpgsql
AS $function$
BEGIN
	-- Réglages Santé MINENE (50 000 000 / 10 000 000 / 5 000 000 à l'origine)
	RETURN QUERY
		SELECT fn_lephare_parametre_nombre('sante.minene.rc_dommages_corporels', 50000000) AS capitaldommagecorporel,
			   fn_lephare_parametre_nombre('sante.minene.rc_dommages_materiels', 10000000) AS capitaldommagemateriel,
			   fn_lephare_parametre_nombre('sante.minene.rc_intoxications', 5000000) AS capitalintoxicationalimentaire;
END;
$function$;
