-- Nombre maximum de personnes d'une famille pour une formule MINENE SANTÉ (Administration > Réglages
-- Santé MINENE, lephare_sante_formule) ; à défaut SOLO 1, FAMILLE 3, FAMILLE PLUS 6.
CREATE OR REPLACE FUNCTION public.fn_minene_personnes_max(p_id_offre integer)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
	v_max integer;
BEGIN
	BEGIN
		SELECT personnesmax INTO v_max FROM public.lephare_sante_formule WHERE idoffre = p_id_offre AND personnesmax > 0;
	EXCEPTION WHEN undefined_table THEN
		v_max := NULL;
	END;
	RETURN COALESCE(v_max, CASE WHEN p_id_offre IN (17, 20, 175) THEN 1 WHEN p_id_offre IN (18, 21, 176) THEN 3 ELSE 6 END);
END;
$function$;
