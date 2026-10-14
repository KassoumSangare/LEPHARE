CREATE OR REPLACE FUNCTION public.fn_liste_objets_assures(numero_police character varying)
 RETURNS TABLE(matricule character varying, idcontrat integer, idcontratdetail integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
date_effet date;

BEGIN

	SELECT dateeffet
	INTO date_effet
	FROM public.stdcontrat AS SC
    INNER JOIN public.stdavenant AS SA ON (SC.idavenant = SA.idavenant)
	WHERE SC.numeropolice = numero_police AND SA.codeavenant IN ('REN', 'AFN')
	ORDER BY dateeffet DESC 
	LIMIT 1;
	
	RETURN QUERY
		SELECT DISTINCT ON (SC.dateeffet) SCD.matricule, SCD.idcontrat, SCD.idcontratdetail
		FROM public.stdcontratdetail AS SCD
		INNER JOIN public.stdcontrat AS SC ON (SCD.idcontrat = SC.idcontrat)
		INNER JOIN public.stdavenant AS SA ON (SC.idavenant = SA.idavenant)
		WHERE SC.numeropolice = numero_police
				AND SC.dateeffet >= date_effet
				AND COALESCE(SC.idcontratannulation, 0) = 0
				AND SA.codeavenant IN ('AFN', 'INC', 'MOD', 'REN')
				AND SCD.matricule NOT IN (SELECT SD.matricule
											FROM public.stdcontratdetail AS SD
											INNER JOIN public.stdcontrat AS SC ON (SD.idcontrat = SC.idcontrat)
											INNER JOIN public.stdavenant AS SA ON (SC.idavenant = SA.idavenant)
											WHERE SC.numeropolice = numero_police AND SA.codeavenant IN ('ANL', 'ANP', 'RET', 'RES')
											)
		ORDER BY SC.dateeffet DESC;
			
END; 
$function$;
