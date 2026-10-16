-- Migration production 0164 : âge à partir duquel NSIA Auto Plus est retenue lu dans l'admin (Réglages Automobile >
-- Dépréciation et âge des véhicules, garantie NSIA Auto Plus : âge minimum ; 5 ans à l'origine, valeur d'URANUS).
-- Offres inchangées : EBENE PREMIUM (93, 99) d'office ; tous risques (2, 46, 50, 57) jamais ; ailleurs, si demandée.
CREATE OR REPLACE FUNCTION public.fn_retenir_garantie_nsia_auto_plus(id_offre integer, age_vehicule integer, nsia_auto_plus_choisie boolean)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
DECLARE
	age_minimum integer;
BEGIN
	BEGIN
		SELECT MIN(R.ageminimum)
		INTO age_minimum
		FROM public.lephare_auto_regle_garantie AS R
		WHERE R.idcompagnie = 1 AND R.idsousgarantie = 175;
	EXCEPTION WHEN undefined_table THEN
		age_minimum := NULL;
	END;
	age_minimum := COALESCE(age_minimum, 5);

	---Retenir la garantie NSIA AUTO +
	IF (age_vehicule >= age_minimum) AND (id_offre IN (93, 99) OR (nsia_auto_plus_choisie AND id_offre NOT IN (2, 46, 50, 57))) THEN
		RETURN True;
	END IF;

	RETURN False;
END;
$function$;
