CREATE OR REPLACE FUNCTION public.fn_get_prime_base_minene_sante(id_offre integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	prime_base numeric;
BEGIN
	prime_base := 0;
	IF id_offre IN (17, 20) THEN -- OPTION SOLO (70% - 80%)
				prime_base := 349148;
	ELSIF id_offre IN (18, 21) THEN -- OPTION FAMILLE (70% - 80%)
				prime_base := 543556;
	ELSIF id_offre IN (19, 22) THEN -- OPTION FAMILLE PLUS (70% - 80%)
				prime_base := 728741;
	ELSIF id_offre = 175 THEN -- OPTION SOLO (80% - 80%)
				prime_base := 523722;
	ELSEIF id_offre = 176 THEN -- OPTION FAMILLE (80% - 80%)
				prime_base := 760978;
	ELSIF id_offre = 181 THEN -- OPTION FAMILLE PLUS (80% - 80%)
				prime_base := 1039122;
	END IF;
	
	RETURN prime_base;
END;
$function$;
