CREATE OR REPLACE FUNCTION public.fn_get_surprime_affection_minene_sante(id_offre integer, nombre_affection integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	prime_base numeric;
BEGIN
	prime_base := fn_get_prime_base_minene_sante(id_offre);
	RETURN ROUND(prime_base * 0.30 * (CASE WHEN nombre_affection < 0 THEN 0 WHEN nombre_affection BETWEEN 0 AND 3 THEN nombre_affection ELSE 3 END),0);
END;
$function$;
