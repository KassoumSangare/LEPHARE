CREATE OR REPLACE FUNCTION public.fn_get_capitaux_minene_rc()
 RETURNS TABLE(capitaldommagecorporel numeric, capitaldommagemateriel numeric, capitalintoxicationalimentaire numeric)
 LANGUAGE plpgsql
AS $function$
DECLARE
	v_capital_dommage_corporel numeric;
	v_capital_dommage_materiel numeric;
	v_capital_intoxication_alimentaire numeric;
BEGIN
	v_capital_dommage_corporel := 50000000;
	v_capital_dommage_materiel := 10000000;
	v_capital_intoxication_alimentaire := 5000000;
	
	RETURN QUERY
		SELECT v_capital_dommage_corporel AS capitaldommagecorporel, v_capital_dommage_materiel AS capitaldommagemateriel,
				v_capital_intoxication_alimentaire AS capitalintoxicationalimentaire;

END;
$function$;
