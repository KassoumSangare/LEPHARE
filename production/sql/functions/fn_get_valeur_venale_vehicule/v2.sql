CREATE OR REPLACE FUNCTION public.fn_get_valeur_venale_vehicule(p_code_genre_vehicule character varying, p_valeur_neuve numeric, p_date_mec date, p_date_effet date DEFAULT CURRENT_DATE)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	v_valeur numeric;
BEGIN
	-- Tableau de dépréciation de la CIEAMI réglé dans l'administration (fn_lephare_depreciation) ; la table
	-- URANUS stddepreciationvehicule, vide, rendait la valeur neuve. Genre seul : la ligne du tableau est
	-- celle du genre (sans type, carrosserie, catégorie ni charge utile) ; à défaut, valeur neuve.
	SELECT DV.valeur_venale INTO v_valeur
	FROM public.fn_lephare_depreciation((SELECT G.idgenre FROM public.stdgenrevehicule AS G WHERE G.codegenre = p_code_genre_vehicule LIMIT 1),
										NULL, NULL, NULL, 0, p_valeur_neuve, p_date_mec, COALESCE(p_date_effet, CURRENT_DATE)) AS DV;
	RETURN COALESCE(v_valeur, ROUND(p_valeur_neuve, 0));
END;
$function$;
