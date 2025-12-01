-- FUNCTION: public.fn_get_date_expiration(date, integer, integer, integer)

-- DROP FUNCTION IF EXISTS public.fn_get_date_expiration(date, integer, integer, integer);

CREATE OR REPLACE FUNCTION public.fn_get_date_expiration(
	p_date_effet date,
	id_duree integer,
	p_nombre_mois integer DEFAULT 0,
	p_nombre_jours integer DEFAULT 0)
    RETURNS date
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
 date_expiration date;
BEGIN

	p_nombre_mois := COALESCE(p_nombre_mois, 0);
	p_nombre_jours := COALESCE(p_nombre_jours, 0);
	p_date_effet := p_date_effet - INTERVAL '1 day';
	IF id_duree = 1 THEN -- durée mensuelle
		date_expiration := p_date_effet + INTERVAL '1 month';
	ELSIF id_duree = 2 THEN -- durée trimestrielle
		date_expiration := p_date_effet + INTERVAL '3 months';
	ELSIF id_duree = 3 THEN -- durée semestrielle
		date_expiration := p_date_effet + INTERVAL '6 months';
	ELSIF id_duree = 4 THEN -- duree annuelle
		date_expiration := p_date_effet + INTERVAL '1 year';
	ELSIF id_duree = 5 THEN --duree personnalisée
		date_expiration := p_date_effet + p_nombre_mois *  INTERVAL '1 month' + p_nombre_jours *  INTERVAL '1 day';
	END IF;
	
	RETURN date_expiration;
	

END;
$BODY$;

ALTER FUNCTION public.fn_get_date_expiration(date, integer, integer, integer)
    OWNER TO uranususer;

COMMENT ON FUNCTION public.fn_get_date_expiration(date, integer, integer, integer)
    IS 'Permet d''obtenir la date d''expiration à partir de la date d''effet et de la durée.';
