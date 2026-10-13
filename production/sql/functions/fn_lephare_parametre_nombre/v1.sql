-- Valeur numérique d'un paramètre réglé dans l'administration LE PHARE (lephare_parametre), ou
-- p_defaut si le paramètre manque, est vide ou illisible (base sans les tables LE PHARE comprise).
CREATE OR REPLACE FUNCTION public.fn_lephare_parametre_nombre(p_cle character varying, p_defaut numeric)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
	v_valeur text;
BEGIN
	SELECT NULLIF(TRIM(valeur), '') INTO v_valeur FROM public.lephare_parametre WHERE cle = p_cle;
	IF v_valeur IS NULL THEN
		RETURN p_defaut;
	END IF;
	RETURN REPLACE(v_valeur, ',', '.')::numeric;
EXCEPTION WHEN others THEN
	RETURN p_defaut;
END;
$function$;
