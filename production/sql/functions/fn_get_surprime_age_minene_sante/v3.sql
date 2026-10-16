CREATE OR REPLACE FUNCTION public.fn_get_surprime_age_minene_sante(id_offre integer, age integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	prime_base numeric;
	v_debut_1 integer;
	v_debut_2 integer;
BEGIN
	-- Réglages Santé MINENE (barème d'origine : 61 à 64 ans 30 %, 65 à 69 ans 50 %) ; au-delà de l'âge maximum
	-- (assuré admis par dérogation), taux de la dernière tranche
	prime_base := fn_get_prime_base_minene_sante(id_offre);
	v_debut_1 := fn_lephare_parametre_nombre('sante.minene.surprime_age_1_debut', 61)::integer;
	v_debut_2 := fn_lephare_parametre_nombre('sante.minene.surprime_age_2_debut', 65)::integer;
	RETURN ROUND(prime_base * (CASE WHEN age >= v_debut_1 AND age < v_debut_2 THEN fn_lephare_parametre_nombre('sante.minene.surprime_age_1_taux', 30)
									 WHEN age >= v_debut_2 THEN fn_lephare_parametre_nombre('sante.minene.surprime_age_2_taux', 50)
									 ELSE 0 END) / 100.0, 0);
END;
$function$;
