CREATE OR REPLACE FUNCTION public.fn_get_surprime_age_minene_sante(id_offre integer, age integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	prime_base numeric;
BEGIN
	-- Barème MINENE 70 %-80 % (OREOLE) : 61 à 64 ans 30 %, 65 à 69 ans 50 %
	prime_base := fn_get_prime_base_minene_sante(id_offre);
	RETURN ROUND(prime_base * (CASE WHEN age <= 60 THEN 0 WHEN age >= 61 AND age < 65 THEN 0.30 WHEN age >= 65 AND age < 70 THEN 0.50 ELSE 0 END),0);
END;
$function$
