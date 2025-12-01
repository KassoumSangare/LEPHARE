-- FUNCTION: public.fn_get_nouvelle_periode_couverture(integer, date, date)

-- DROP FUNCTION IF EXISTS public.fn_get_nouvelle_periode_couverture(integer, date, date);

CREATE OR REPLACE FUNCTION public.fn_get_nouvelle_periode_couverture(
	id_duree integer,
	p_date_effet date,
	p_date_expiration date)
    RETURNS TABLE(date_effet date, date_expiration date) 
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
DECLARE
 nouvelle_date_effet date;
 nouvelle_date_expiration date;
BEGIN
	nouvelle_date_effet := p_date_expiration + INTERVAL '1 day';
	nouvelle_date_expiration := p_date_expiration;
	IF id_duree = 1 THEN -- durée mensuelle
		nouvelle_date_expiration := nouvelle_date_expiration + INTERVAL '1 month';
	ELSIF id_duree = 2 THEN -- durée trimestrielle
		nouvelle_date_expiration := nouvelle_date_expiration + INTERVAL '3 months';
	ELSIF id_duree = 3 THEN -- durée semestrielle
		nouvelle_date_expiration := nouvelle_date_expiration + INTERVAL '6 months';
	ELSIF id_duree = 4 THEN -- duree annuelle
		nouvelle_date_expiration := nouvelle_date_expiration + INTERVAL '1 year';
	ELSIF id_duree = 5 THEN --duree personnalisée
		nouvelle_date_expiration := nouvelle_date_expiration + ((p_date_expiration + INTERVAL '1 day')::date - p_date_effet);
	END IF;
	
	RETURN QUERY
		SELECT nouvelle_date_effet, nouvelle_date_expiration;
	

END;
$BODY$;

ALTER FUNCTION public.fn_get_nouvelle_periode_couverture(integer, date, date)
    OWNER TO uranususer;

COMMENT ON FUNCTION public.fn_get_nouvelle_periode_couverture(integer, date, date)
    IS 'Permet d''obtenir la période de couverture par défaut d''un nouvel avenant à partir de l''avenant de base.';
