CREATE OR REPLACE FUNCTION public.fn_get_frais_gestion_minene()
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	frais_gestion numeric;
BEGIN
	frais_gestion := 1500;
	RETURN frais_gestion;

END;
$function$;
