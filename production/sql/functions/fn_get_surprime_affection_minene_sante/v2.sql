CREATE OR REPLACE FUNCTION public.fn_get_surprime_affection_minene_sante(id_offre integer, nombre_affection integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	prime_base numeric;
	v_taux numeric;
	v_maximum integer;
BEGIN
	-- Réglages Santé MINENE : surprime par affection (30 % à l'origine), affections retenues (3 au plus)
	prime_base := fn_get_prime_base_minene_sante(id_offre);
	v_taux := fn_lephare_parametre_nombre('sante.minene.surprime_affection', 30) / 100.0;
	v_maximum := fn_lephare_parametre_nombre('sante.minene.affections_max', 3)::integer;
	RETURN ROUND(prime_base * v_taux * (CASE WHEN nombre_affection < 0 THEN 0 WHEN nombre_affection <= v_maximum THEN nombre_affection ELSE v_maximum END),0);
END;
$function$;
