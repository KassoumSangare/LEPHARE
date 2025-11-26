-- FUNCTION: public.fn_get_valeur_venale_vehicule()

-- DROP FUNCTION IF EXISTS public.fn_get_valeur_venale_vehicule(VARCHAR, NUMERIC(19, 4), DATE, DATE);

CREATE OR REPLACE FUNCTION public.fn_get_valeur_venale_vehicule(IN p_code_genre_vehicule VARCHAR, IN p_valeur_neuve NUMERIC(19, 4), IN p_date_mec DATE, IN p_date_effet DATE DEFAULT CURRENT_DATE) 
RETURNS NUMERIC(19, 4)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
	v_valeur_venale NUMERIC(19, 4);
	v_taux_depreciation NUMERIC(4,2);
	v_age_en_mois SMALLINT;
BEGIN
	v_taux_depreciation := 0.00;
	p_date_effet := COALESCE(p_date_effet, CURRENT_DATE);
	v_age_en_mois := EXTRACT('year' FROM AGE(p_date_effet, p_date_mec)) * 12 + EXTRACT('month' FROM AGE(p_date_effet, p_date_mec));
	SELECT taux INTO v_taux_depreciation 
	FROM public.stddepreciationvehicule
	WHERE codegenrevehicule = p_code_genre_vehicule
		AND mois = (SELECT MAX(mois)
					FROM public.stddepreciationvehicule
					WHERE codegenrevehicule = p_code_genre_vehicule AND v_age_en_mois >= mois
					);
	v_taux_depreciation := COALESCE(v_taux_depreciation, 0);
	RETURN ROUND(p_valeur * (1 - v_taux_depreciation / 100), 0);
END; 
$BODY$;
ALTER FUNCTION public.fn_get_valeur_venale_vehicule(VARCHAR, NUMERIC(19, 4), DATE, DATE)
    OWNER TO uranususer;

