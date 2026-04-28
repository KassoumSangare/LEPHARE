--SELECT EXTRACT('month' FROM AGE('2025-02-01'::DATE + 1, '2025-01-02'::DATE));
-- FUNCTION: public.fn_get_nouvelle_periode_couverture(integer, date, date)

DROP FUNCTION IF EXISTS public.fn_get_nouvelle_periode_couverture(integer, date, date);

CREATE OR REPLACE FUNCTION public.fn_get_nouvelle_periode_couverture(
	id_duree integer,
	p_ancienne_date_effet date,
	p_ancienne_date_expiration date)
    RETURNS TABLE(date_effet date, date_expiration date) 
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
DECLARE
 nouvelle_date_effet date;
 nouvelle_date_expiration date;
 v_nombre_mois integer;
 v_nombre_jours integer;
 
BEGIN
	nouvelle_date_effet := p_ancienne_date_expiration + INTERVAL '1 day';
	v_nombre_mois := 0;
    v_nombre_jours := 0;
	IF id_duree = 5 THEN
		v_nombre_mois := EXTRACT ('month' FROM AGE(p_ancienne_date_expiration + 1, p_ancienne_date_effet));
		v_nombre_jours := EXTRACT ('day' FROM AGE(p_ancienne_date_expiration + 1, p_ancienne_date_effet));
	END IF;
	nouvelle_date_expiration := public.fn_get_date_expiration(nouvelle_date_effet, id_duree, v_nombre_jours, v_nombre_jours);
	
	RETURN QUERY
		SELECT nouvelle_date_effet, nouvelle_date_expiration;
	

END;
$BODY$;

ALTER FUNCTION public.fn_get_nouvelle_periode_couverture(integer, date, date)
    OWNER TO uranususer;

COMMENT ON FUNCTION public.fn_get_nouvelle_periode_couverture(integer, date, date)
    IS 'Permet d''obtenir la période de couverture par défaut d''un nouvel avenant à partir de l''avenant de base.';
