-- Frais de gestion ADEC d'un adhérent MINENE : forfait IA (produit 2) ou RC chef de famille (produit 8)
-- de la répartition de la prime Santé MINENE sans apporteur (Administration > Réglages Santé MINENE),
-- 1 500 F à défaut.
CREATE OR REPLACE FUNCTION public.fn_get_frais_gestion_minene(p_id_produit integer)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
	v_frais numeric;
BEGIN
	BEGIN
		SELECT CASE WHEN p_id_produit = 8 THEN R.frais_gestion_adec_forfait_rc ELSE R.frais_gestion_adec_forfait_ia END
		INTO v_frais
		FROM public.stdrepartitionprimesante AS R
		WHERE R.actif AND NOT R.avec_apporteur
		ORDER BY R.id
		LIMIT 1;
	EXCEPTION WHEN undefined_table THEN
		v_frais := NULL;
	END;
	RETURN COALESCE(v_frais, 1500);
END;
$function$;
