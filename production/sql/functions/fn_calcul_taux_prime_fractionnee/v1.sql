-- Coefficient de prime d'un contrat de moins d'un an (version d'URANUS, coefficients écrits dans la fonction).
-- Appelée par fn_calcul_prime_prorata (moteurs Automobile NSIA).
CREATE OR REPLACE FUNCTION public.fn_calcul_taux_prime_fractionnee(p_days integer, p_start_date date)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	taux_prime numeric;
    interval_diff INTERVAL;
	months INTEGER;
	days INTEGER;
BEGIN
    months := 0;
    taux_prime := 1.00;
    interval_diff := age(p_start_date + (p_days - 1), p_start_date);
    
    -- Extract the number of months and days from the interval
    months := EXTRACT(MONTH FROM interval_diff) + (EXTRACT(YEAR FROM interval_diff) * 12);
    days := EXTRACT(DAY FROM interval_diff);

	IF months = 0 THEN
		IF days <= 15 THEN
			taux_prime := 0.05;
		ELSE
			taux_prime := 0.10;
		END IF;
	ELSEIF months = 1 THEN
		IF days = 0 THEN
			taux_prime := 0.10;
		ELSE
			taux_prime := 0.19;
		END IF;
	ELSEIF months = 2 THEN
		IF days = 0 THEN
			taux_prime := 0.19;
		ELSE
			taux_prime := 0.28;
		END IF;
	ELSEIF months = 3 THEN
		IF days = 0 THEN
			taux_prime := 0.28;
		ELSE
			taux_prime := 0.37;
		END IF;
	ELSEIF months = 4 THEN
		IF days = 0 THEN
			taux_prime := 0.37;
		ELSE
			taux_prime := 0.45;
		END IF;
	ELSEIF months = 5 THEN
		IF days = 0 THEN
			taux_prime := 0.45;
		ELSE
			taux_prime := 0.53;
		END IF;
	ELSEIF months = 6 THEN
		IF days = 0 THEN
			taux_prime := 0.53;
		ELSE
			taux_prime := 0.61;
		END IF;
	ELSEIF months = 7 THEN
		IF days = 0 THEN
			taux_prime := 0.61;
		ELSE
			taux_prime := 0.69;
		END IF;
	ELSEIF months = 8 THEN
		IF days = 0 THEN
			taux_prime := 0.69;
		ELSE
			taux_prime := 0.77;
		END IF;
	ELSEIF months = 9 THEN
		IF days = 0 THEN
			taux_prime := 0.77;
		ELSE
			taux_prime := 0.85;
		END IF;
	ELSEIF months = 10 THEN
		IF days = 0 THEN
			taux_prime := 0.85;
		ELSE
			taux_prime := 0.93;
		END IF;
	ELSEIF months = 11 THEN
		IF days = 0 THEN
			taux_prime := 0.93;
		ELSE
			taux_prime := 1.00;
		END IF;
	END IF;

	RETURN taux_prime;
	
END;
$function$;
