CREATE FUNCTION public.fn_calcul_prime_voyage_by_age(age integer, duree_voyage integer, id_zone_voyage integer, id_tarif integer, id_offre integer) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
DECLARE
	id_compagnie_v integer;
BEGIN  
	
	SELECT id_compagnie
	INTO id_compagnie_v
	FROM StdZoneVoyage
	WHERE id_zone = id_zone_voyage;
	id_compagnie_v = COALESCE(id_compagnie_v, 0);
	
	IF id_compagnie_v = 1 THEN --NSIA ASSURANCES
		RETURN public.fn_calcul_prime_voyage_by_age_nsia(age, duree_voyage, id_zone_voyage, id_offre);
	ELSIF id_compagnie_v = 21 THEN --AMSA ASSURANCES
		RETURN public.fn_calcul_prime_voyage_by_age_amsa(age, duree_voyage, id_zone_voyage, id_tarif);
	ELSE
		RETURN -1; --NON PARAMETRE
	END IF;
		
END;
$$;



CREATE FUNCTION public.fn_calcul_prime_voyage_by_age_amsa(age integer, duree_voyage integer, id_zone_voyage integer, id_tarif_voyage integer) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
DECLARE
	prime_voyage numeric;
BEGIN  
	
	SELECT prime_nette 
	INTO prime_voyage
	FROM StdZoneVoyagePrime
	WHERE id_tarif = id_tarif_voyage
	      AND id_zone = id_zone_voyage
		  AND duree_voyage BETWEEN duree_minimum AND duree_maximum
		  AND age BETWEEN age_minimum AND age_maximum;
	prime_voyage := COALESCE(prime_voyage, 0);
	RETURN prime_voyage;
	
END;
$$;



CREATE FUNCTION public.fn_calcul_prime_voyage_by_age_nsia(age integer, duree_voyage integer, id_zone_voyage integer, id_offre_voyage integer) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
DECLARE
	prime_voyage numeric;
BEGIN  
	
	SELECT prime_nette 
	INTO prime_voyage
	FROM StdZoneVoyagePrimeNsia
	WHERE id_offre = id_offre_voyage
	      AND id_zone = id_zone_voyage
		  AND duree_voyage BETWEEN duree_minimum AND duree_maximum
		  AND age BETWEEN age_minimum AND age_maximum;
	prime_voyage := COALESCE(prime_voyage, 0);
	RETURN prime_voyage;
	
END;
$$;



