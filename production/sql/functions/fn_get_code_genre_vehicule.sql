CREATE OR REPLACE FUNCTION fn_get_code_genre_vehicule(IN p_id_genre_vehicule INTEGER)
RETURNS VARCHAR
LANGUAGE 'plpgsql'
AS
$$
DECLARE
	code_genre_vehicule VARCHAR;
BEGIN
		SELECT codegenre
		INTO code_genre_vehicule
		FROM public.stdgenrevehicule
		WHERE idgenre = p_id_genre_vehicule;
		
		RETURN COALESCE(code_genre_vehicule, '');
END;
$$;
ALTER FUNCTION fn_get_code_genre_vehicule(INTEGER) OWNER TO uranususer;