CREATE OR REPLACE FUNCTION public.fn_get_frais_gestion_minene()
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
BEGIN
	-- Forfait IA de la répartition de la prime Santé MINENE (voir fn_get_frais_gestion_minene(integer))
	RETURN fn_get_frais_gestion_minene(2);
END;
$function$;
