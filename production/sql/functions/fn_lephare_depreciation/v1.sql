-- Valeur vénale d'un véhicule d'après le tableau de dépréciation de la CIEAMI réglé dans l'administration
-- (Réglages Automobile > Dépréciation des véhicules : lephare_depreciation_classe, lephare_depreciation_regle,
-- paramètres auto.depreciation.*).
--   - Ligne du tableau : première règle dont les critères renseignés correspondent au véhicule.
--   - Âge : mois révolus entre la mise en circulation et la date d'effet ; colonne retenue = la dernière
--     atteinte (moins de 6 mois : pas de dépréciation) ; au-delà de 10 ans : pourcentage de la valeur neuve.
--   - Deux taux (« 30/35 ») : le plus faible, le plus élevé ou la moyenne selon le réglage.
--   - Valeur minimum (1 000 000 F) pour les véhicules dont la valeur neuve la dépasse.
-- Valeur vénale NULL si la valeur neuve, la date de mise en circulation ou la ligne du tableau manque.
-- Nombre en texte à la française, sans zéros inutiles (17,5 ; 85)
CREATE OR REPLACE FUNCTION public.fn_lephare_nombre_texte(p numeric)
 RETURNS character varying
 LANGUAGE sql
 IMMUTABLE
AS $function$
	SELECT REPLACE(RTRIM(RTRIM(ROUND(p, 2)::text, '0'), '.'), '.', ',')::character varying;
$function$;

CREATE OR REPLACE FUNCTION public.fn_lephare_depreciation(
	p_id_genre integer, p_id_type_vehicule integer, p_id_carrosserie integer, p_code_categorie character varying,
	p_charge_utile numeric, p_valeur_neuve numeric, p_date_mec date, p_date_effet date DEFAULT CURRENT_DATE)
 RETURNS TABLE(classe character varying, libelle character varying, age_mois integer, taux_minimum numeric,
			   taux_maximum numeric, taux numeric, valeur_venale numeric, explication character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
	v_classe varchar; v_libelle varchar; v_taux jsonb; v_age integer; v_cle integer; v_derniere integer; v_premiere integer;
	v_min numeric; v_max numeric; v_retenu numeric; v_valeur numeric; v_choix varchar; v_minimum numeric;
	v_pct_au_dela numeric; v_expl varchar;
BEGIN
	p_date_effet := COALESCE(p_date_effet, CURRENT_DATE);
	IF p_date_mec IS NULL OR p_date_mec < DATE '1900-01-01' OR COALESCE(p_valeur_neuve, 0) <= 0 THEN
		RETURN QUERY SELECT NULL::varchar, NULL::varchar, NULL::integer, NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric,
			'Valeur neuve ou date de première mise en circulation manquante'::varchar;
		RETURN;
	END IF;
	v_age := GREATEST((EXTRACT(year FROM AGE(p_date_effet, p_date_mec)) * 12 + EXTRACT(month FROM AGE(p_date_effet, p_date_mec)))::integer, 0);

	SELECT C.code, C.libelle, C.taux INTO v_classe, v_libelle, v_taux
	FROM public.lephare_depreciation_regle AS R
	INNER JOIN public.lephare_depreciation_classe AS C ON (C.code = R.classe)
	WHERE (R.idgenre IS NULL OR R.idgenre = p_id_genre)
		AND (R.idtypevehicule IS NULL OR R.idtypevehicule = p_id_type_vehicule)
		AND (R.idcarrosserie IS NULL OR R.idcarrosserie = p_id_carrosserie)
		AND (COALESCE(R.codecategorie, '') = '' OR R.codecategorie = p_code_categorie)
		AND (R.chargeutilesuperieurea IS NULL OR COALESCE(p_charge_utile, 0) > R.chargeutilesuperieurea)
	ORDER BY R.ordre, R.id
	LIMIT 1;
	IF v_classe IS NULL THEN
		RETURN QUERY SELECT NULL::varchar, NULL::varchar, v_age, NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric,
			'Aucune ligne du tableau de dépréciation pour ce véhicule (genre, carrosserie ou catégorie)'::varchar;
		RETURN;
	END IF;

	SELECT MAX(k::integer) FILTER (WHERE k::integer <= v_age), MAX(k::integer), MIN(k::integer)
	INTO v_cle, v_derniere, v_premiere
	FROM jsonb_object_keys(v_taux) AS k;
	v_choix := COALESCE((SELECT NULLIF(TRIM(P.valeur), '') FROM public.lephare_parametre AS P WHERE P.cle = 'auto.depreciation.taux_retenu'), 'plus_faible');
	v_pct_au_dela := public.fn_lephare_parametre_nombre('auto.depreciation.pourcentage_au_dela', 10);
	v_minimum := public.fn_lephare_parametre_nombre('auto.depreciation.valeur_minimum', 1000000);

	IF v_age > GREATEST(COALESCE(v_derniere, 0), 120) THEN
		v_min := 100 - v_pct_au_dela; v_max := v_min; v_retenu := v_min;
		v_expl := v_libelle || ', plus de 10 ans : ' || public.fn_lephare_nombre_texte(v_pct_au_dela) || ' % de la valeur neuve';
	ELSIF v_cle IS NULL THEN
		v_min := 0; v_max := 0; v_retenu := 0;
		v_expl := v_libelle || ', moins de ' || COALESCE(v_premiere, 6) || ' mois : pas de dépréciation';
	ELSE
		SELECT MIN(x::numeric), MAX(x::numeric) INTO v_min, v_max
		FROM jsonb_array_elements_text(v_taux -> v_cle::text) AS x;
		v_retenu := CASE v_choix WHEN 'plus_eleve' THEN v_max WHEN 'moyenne' THEN (v_min + v_max) / 2 ELSE v_min END;
		v_expl := v_libelle || ', colonne ' || CASE WHEN v_cle % 12 = 0 THEN (v_cle / 12) || CASE WHEN v_cle = 12 THEN ' an' ELSE ' ans' END ELSE v_cle || ' mois' END
			|| ' : ' || public.fn_lephare_nombre_texte(v_retenu) || ' %'
			|| CASE WHEN v_max <> v_min THEN ' (tableau : ' || public.fn_lephare_nombre_texte(v_min) || '/' || public.fn_lephare_nombre_texte(v_max) || ')' ELSE '' END;
	END IF;

	v_valeur := ROUND(p_valeur_neuve * (1 - COALESCE(v_retenu, 0) / 100), 0);
	-- Valeur minimum : véhicules dont la valeur neuve la dépasse (une moto de 800 000 F garde sa valeur)
	IF COALESCE(v_minimum, 0) > 0 AND p_valeur_neuve > v_minimum AND v_valeur < v_minimum THEN
		v_valeur := v_minimum;
		v_expl := v_expl || ' ; valeur minimum de ' || REPLACE(TO_CHAR(v_minimum, 'FM999,999,999'), ',', ' ') || ' F appliquée';
	END IF;

	RETURN QUERY SELECT v_classe, v_libelle, v_age, v_min, v_max, v_retenu, v_valeur, v_expl;
END;
$function$;
