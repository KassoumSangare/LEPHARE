CREATE OR REPLACE FUNCTION public.fn_get_capitaux_minene_ia()
 RETURNS TABLE(capitaldeces numeric, capitalipp numeric, capitalfraistraitement numeric)
 LANGUAGE plpgsql
AS $function$
DECLARE
	capital_deces numeric;
	capital_ipp numeric;
	capital_frais_traitement numeric;
BEGIN
	capital_deces := 2000000;
	capital_ipp := 2000000;
	capital_frais_traitement := 100000;
	
	RETURN QUERY
		SELECT capital_deces, capital_ipp, capital_frais_traitement;

END;
$function$;
