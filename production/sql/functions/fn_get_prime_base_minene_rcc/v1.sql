CREATE OR REPLACE FUNCTION public.fn_get_prime_base_minene_rcc()
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	prime_base numeric;
BEGIN
	prime_base := 14524;
	RETURN prime_base;

END;
$function$;
