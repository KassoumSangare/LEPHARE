CREATE OR REPLACE FUNCTION public.fn_get_prime_base_minene_ia()
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
BEGIN
	-- Réglages Santé MINENE (14 524 à l'origine)
	RETURN fn_lephare_parametre_nombre('sante.minene.ia_prime_nette', 14524);
END;
$function$;
