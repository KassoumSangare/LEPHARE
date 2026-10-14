CREATE OR REPLACE FUNCTION public.fn_liste_objets_assures(numero_police character varying)
 RETURNS TABLE(matricule character varying, idcontrat integer, idcontratdetail integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
date_effet date;

BEGIN
	-- Objets assurés (véhicules, assurés IA…) de la période en cours de la police, avec les incorporations
	-- et modifications de la période, sans les objets retirés : une ligne par matricule, la plus récente.
	-- v1 (URANUS) ne gardait qu'une ligne par date d'effet (DISTINCT ON (SC.dateeffet)) : une flotte de
	-- 5 véhicules se renouvelait avec 1 véhicule ; elle écartait aussi un matricule retiré une fois dans
	-- l'historique de la police, même réassuré depuis. Lignes sans matricule : une seule, la plus récente.

	SELECT dateeffet
	INTO date_effet
	FROM public.stdcontrat AS SC
    INNER JOIN public.stdavenant AS SA ON (SC.idavenant = SA.idavenant)
	WHERE SC.numeropolice = numero_police AND SA.codeavenant IN ('REN', 'AFN')
	ORDER BY dateeffet DESC
	LIMIT 1;

	RETURN QUERY
		SELECT L.matricule, L.idcontrat, L.idcontratdetail
		FROM (
			SELECT DISTINCT ON (TRIM(COALESCE(SCD.matricule, '')))
				   TRIM(COALESCE(SCD.matricule, ''))::character varying AS matricule, SCD.idcontrat, SCD.idcontratdetail,
				   SC.dateeffet AS date_ligne
			FROM public.stdcontratdetail AS SCD
			INNER JOIN public.stdcontrat AS SC ON (SCD.idcontrat = SC.idcontrat)
			INNER JOIN public.stdavenant AS SA ON (SC.idavenant = SA.idavenant)
			WHERE SC.numeropolice = numero_police
					AND SC.dateeffet >= date_effet
					AND COALESCE(SC.idcontratannulation, 0) = 0
					AND SA.codeavenant IN ('AFN', 'INC', 'MOD', 'REN')
			ORDER BY TRIM(COALESCE(SCD.matricule, '')), SC.dateeffet DESC, SC.idcontrat DESC, SCD.idcontratdetail DESC
		) AS L
		WHERE NOT EXISTS (SELECT 1
						  FROM public.stdcontratdetail AS SD
						  INNER JOIN public.stdcontrat AS SR ON (SD.idcontrat = SR.idcontrat)
						  INNER JOIN public.stdavenant AS AR ON (SR.idavenant = AR.idavenant)
						  WHERE SR.numeropolice = numero_police AND AR.codeavenant IN ('ANL', 'ANP', 'RET', 'RES')
								AND TRIM(COALESCE(SD.matricule, '')) = L.matricule AND L.matricule <> ''
								AND SR.dateeffet >= L.date_ligne)
		ORDER BY L.date_ligne DESC, L.idcontratdetail;

END;
$function$;
