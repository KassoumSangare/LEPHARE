CREATE OR REPLACE FUNCTION public.fn_get_surprime_age_minene_sante(id_offre integer, age integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	prime_base numeric;
BEGIN
	prime_base := fn_get_prime_base_minene_sante(id_offre);
	RETURN ROUND(prime_base * (CASE WHEN age <= 59 THEN 0 WHEN age >= 60 AND age < 65 THEN 0.30 WHEN age >= 65 AND age < 70 THEN 0.50 ELSE 0 END),0);
END;
$function$
