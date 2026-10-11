CREATE OR REPLACE FUNCTION public.fn_get_taux_commission_offre(id_produit integer, id_compagnie integer, id_offre integer, date_emission date)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	v_taux numeric;
BEGIN
	-- MINENE Santé (formules 70 %-80 %, VTC et 80 %-80 %) : commission du cabinet du barème OREOLE
	-- (TARIFICATION MINENE SANTE.xlsx : « Taux de commission OREOLE ASSURANCES 6,5 % de la prime HT »),
	-- réglée dans la répartition de la prime Santé MINENE (Administration). Autres offres : taux du
	-- produit et de la compagnie.
	IF id_produit = 5 AND id_offre IN (17, 18, 19, 20, 21, 22, 175, 176, 181) THEN
		SELECT taux_commission_courtier
		INTO v_taux
		FROM public.stdrepartitionprimesante
		WHERE actif AND NOT avec_apporteur AND taux_commission_courtier IS NOT NULL
		ORDER BY id
		LIMIT 1;
		IF v_taux IS NOT NULL THEN
			RETURN v_taux;
		END IF;
	END IF;
	RETURN public.fn_get_taux_commission(id_produit, id_compagnie, date_emission);
END;
$function$
