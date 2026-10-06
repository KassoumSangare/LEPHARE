DROP FUNCTION IF EXISTS public.fn_grille_voyage(integer, integer, integer, integer, integer);
CREATE FUNCTION public.fn_grille_voyage(p_id_tarif integer, p_id_offre integer, p_id_zone integer, p_age integer, p_duree integer)
 RETURNS TABLE(prime_nette numeric, accessoire numeric, taux_taxe numeric, prime_ttc numeric,
               duree_minimum integer, duree_maximum integer, age_minimum integer, age_maximum integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- v2 : renvoie aussi la prime TTC du document tarifaire et les bornes (durée, âge) de la ligne
-- retenue, affichées à l'écran pour rapprocher la prime du document.
-- Ligne de grille Voyage : prime nette, accessoire et taux de taxe de la ligne.
--   1. grille par offre (stdzonevoyageprimensia, NSIA) : ligne de la zone, sinon ligne sans zone
--      (valable dans toutes les zones où l'offre est proposée) ;
--   2. sinon grille par formule et par zone (stdzonevoyageprime, AMSA).
-- L'offre doit être proposée dans la zone de destination (stdoffrevoyagezone).
-- p_duree : jours de couverture, date d'effet et date d'expiration comprises.
BEGIN
	IF NOT EXISTS (SELECT 1 FROM public.stdoffrevoyagezone AS oz WHERE oz.id_offre = p_id_offre AND oz.id_zone = p_id_zone) THEN
		RETURN;
	END IF;

	RETURN QUERY
		SELECT g.prime_nette, g.accessoire, g.taux_taxe, g.prime_ttc,
			g.duree_minimum, g.duree_maximum, g.age_minimum, g.age_maximum
		FROM public.stdzonevoyageprimensia AS g
		WHERE g.id_offre = p_id_offre
			AND (g.id_zone = p_id_zone OR g.id_zone IS NULL)
			AND p_duree BETWEEN g.duree_minimum AND g.duree_maximum
			AND p_age BETWEEN g.age_minimum AND g.age_maximum
		ORDER BY g.id_zone NULLS LAST, g.id
		LIMIT 1;
	IF FOUND THEN
		RETURN;
	END IF;

	RETURN QUERY
		SELECT g.prime_nette, g.accessoire, g.taux_taxe, g.prime_ttc,
			g.duree_minimum, g.duree_maximum, g.age_minimum, g.age_maximum
		FROM public.stdzonevoyageprime AS g
		WHERE g.id_tarif = p_id_tarif
			AND g.id_zone = p_id_zone
			AND p_duree BETWEEN g.duree_minimum AND g.duree_maximum
			AND p_age BETWEEN g.age_minimum AND g.age_maximum
		ORDER BY g.id
		LIMIT 1;
END;
$function$;
