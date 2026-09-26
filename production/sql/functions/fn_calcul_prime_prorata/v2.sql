CREATE OR REPLACE FUNCTION public.fn_calcul_prime_prorata(id_sous_garantie integer, prime_nette numeric, bns numeric, duree_contrat integer, date_effet date)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	taux_prime numeric;
BEGIN

	prime_nette := COALESCE(prime_nette, 0.0);
	taux_prime := fn_calcul_taux_prime_fractionnee(duree_contrat, date_effet);
	-- 172 (Bris de glace avec prise en compte des toits ouvrants) n'est plus exclu :
	-- NSIA applique le BNS sur cette garantie (mais pas la réduction commerciale),
	-- cf. conditions particulières NSIA EBENE PREMIUM TPC (90 210 x 0,70 = 63 147).
  	IF id_sous_garantie NOT IN (3, 17, 18, 19, 20, 22, 163, 164, 169, 173, 176, 177, 178, 179) THEN
			prime_nette := prime_nette * bns;
	END IF;

	IF (id_sous_garantie <> 3) THEN
		prime_nette := prime_nette * taux_prime;
	END IF;

  	RETURN ROUND(prime_nette, 0);

END;
$function$
