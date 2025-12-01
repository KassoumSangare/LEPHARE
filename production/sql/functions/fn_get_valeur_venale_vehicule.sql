-- FUNCTION: public.fn_get_valeur_venale_vehicule(character varying, numeric, date, date)

-- DROP FUNCTION IF EXISTS public.fn_get_valeur_venale_vehicule(character varying, numeric, date, date);

CREATE OR REPLACE FUNCTION public.fn_get_valeur_venale_vehicule(
	p_code_genre_vehicule character varying,
	p_valeur_neuve numeric,
	p_date_mec date,
	p_date_effet date DEFAULT CURRENT_DATE)
    RETURNS numeric
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
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
	RETURN ROUND(p_valeur_neuve * (1 - v_taux_depreciation / 100), 0);
END; 
$BODY$;

ALTER FUNCTION public.fn_get_valeur_venale_vehicule(character varying, numeric, date, date)
    OWNER TO uranususer;
