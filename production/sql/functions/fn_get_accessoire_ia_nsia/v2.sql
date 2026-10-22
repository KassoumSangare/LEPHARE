-- Accessoires Individuelle Accidents NSIA ASSURANCES selon la prime nette, lus dans les réglages
-- (Administration > Réglages par branche > Individuelle Accidents, table lephare_ia_accessoire_tranche) au lieu
-- d'être écrits ici (v1) : montant de la première tranche dont le plafond n'est pas dépassé ; au-delà de la
-- dernière, pourcentage de la prime nette + montant (ligne sans plafond). Prime nulle : 0.
-- Montant total (part compagnie + part courtier), réparti par fn_get_accessoire.
CREATE OR REPLACE FUNCTION public.fn_get_accessoire_ia_nsia(prime_nette numeric)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	v_montant numeric;
	v_taux numeric;
BEGIN
	prime_nette := COALESCE(prime_nette, 0);
	IF prime_nette <= 0 THEN
		RETURN 0;
	END IF;

	SELECT t.montant INTO v_montant
	FROM public.lephare_ia_accessoire_tranche AS t
	WHERE t.idcompagnie = 1 AND t.primemax IS NOT NULL AND prime_nette <= t.primemax
	ORDER BY t.primemax
	LIMIT 1;
	IF FOUND THEN
		RETURN ROUND(v_montant, 0);
	END IF;

	SELECT t.montant, t.tauxaudela INTO v_montant, v_taux
	FROM public.lephare_ia_accessoire_tranche AS t
	WHERE t.idcompagnie = 1 AND t.primemax IS NULL
	LIMIT 1;
	IF FOUND THEN
		RETURN ROUND(prime_nette * COALESCE(v_taux, 0) / 100, 0) + ROUND(COALESCE(v_montant, 0), 0);
	END IF;
	RETURN 0;
END;
$function$;
