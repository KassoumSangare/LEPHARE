-- Tarif du POOL TPV pour un véhicule de transport public de voyageurs (catégorie 204), réglé dans
-- Administration > Réglages Automobile > Pool TPV (lephare_pool_tpv_tranche, paramètres auto.pool_tpv.*) :
--   - tranche selon les places (hors conducteur si réglé : 5 places → « 0 à 4 places ») ;
--   - durée en mois (un mois entamé compte), de 1 à 12 ;
--   - RC = RC annuelle × fraction de la durée ; Recours = 5 % de la RC ; accessoire de la tranche pour la durée.
CREATE OR REPLACE FUNCTION public.fn_est_offre_pool_tpv(p_id_offre integer)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
	SELECT COALESCE(p_id_offre, 0) <> 0 AND p_id_offre = public.fn_lephare_parametre_nombre('auto.pool_tpv.offre', -1);
$function$;

CREATE OR REPLACE FUNCTION public.fn_pool_tpv(p_nombre_place integer, p_date_effet date, p_date_expiration date)
 RETURNS TABLE(places integer, mois integer, prime_rc_annuelle numeric, prime_rc numeric, prime_recours_annuelle numeric,
			   prime_recours numeric, accessoire numeric, tranche character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
	v_places integer;
	v_mois integer;
	v_duree interval;
	v_fractions text[];
	v_fraction numeric;
	v_taux_recours numeric;
	v_hors_conducteur boolean;
	v_tranche RECORD;
BEGIN
	v_hors_conducteur := COALESCE((SELECT LOWER(TRIM(P.valeur)) FROM public.lephare_parametre AS P WHERE P.cle = 'auto.pool_tpv.places_hors_conducteur'), 'true')
						 IN ('true', '1', 'oui', 'vrai');
	v_places := GREATEST(COALESCE(p_nombre_place, 0) - CASE WHEN v_hors_conducteur THEN 1 ELSE 0 END, 0);
	v_duree := AGE(COALESCE(p_date_expiration, (p_date_effet + INTERVAL '1 year' - INTERVAL '1 day')::date) + 1, p_date_effet);
	v_mois := (EXTRACT(year FROM v_duree) * 12 + EXTRACT(month FROM v_duree))::integer + CASE WHEN EXTRACT(day FROM v_duree) > 0 THEN 1 ELSE 0 END;
	v_mois := LEAST(GREATEST(v_mois, 1), 12);
	v_fractions := string_to_array(COALESCE((SELECT NULLIF(TRIM(P.valeur), '') FROM public.lephare_parametre AS P WHERE P.cle = 'auto.pool_tpv.fractions'),
											'10/19/28/37/45/53/61/69/77/85/93/100'), '/');
	BEGIN
		v_fraction := NULLIF(TRIM(REPLACE(v_fractions[v_mois], ',', '.')), '')::numeric;
	EXCEPTION WHEN others THEN
		v_fraction := NULL;
	END;
	v_fraction := COALESCE(v_fraction, 100);
	v_taux_recours := public.fn_lephare_parametre_nombre('auto.pool_tpv.taux_recours', 5);

	SELECT T.* INTO v_tranche
	FROM public.lephare_pool_tpv_tranche AS T
	WHERE v_places >= T.placesmin AND (T.placesmax IS NULL OR v_places <= T.placesmax)
	ORDER BY T.ordre, T.placesmin
	LIMIT 1;
	IF NOT FOUND THEN
		RETURN;
	END IF;

	RETURN QUERY
		SELECT v_places, v_mois, v_tranche.primercannuelle,
			   ROUND(v_tranche.primercannuelle * v_fraction / 100, 0),
			   ROUND(v_tranche.primercannuelle * v_taux_recours / 100, 0),
			   ROUND(ROUND(v_tranche.primercannuelle * v_fraction / 100, 0) * v_taux_recours / 100, 0),
			   COALESCE((v_tranche.accessoires ->> (v_mois - 1))::numeric, 0),
			   (CASE WHEN v_tranche.placesmax IS NULL THEN v_tranche.placesmin || ' places et plus'
					 ELSE 'de ' || v_tranche.placesmin || ' à ' || v_tranche.placesmax || ' places' END)::character varying;
END;
$function$;
