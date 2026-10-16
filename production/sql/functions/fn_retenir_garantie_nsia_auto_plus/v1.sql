-- Version d'URANUS reprise telle quelle de la base (avant la migration production 0164).
CREATE OR REPLACE FUNCTION public.fn_retenir_garantie_nsia_auto_plus(id_offre integer, age_vehicule integer, nsia_auto_plus_choisie boolean)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$

BEGIN
  ---Retenir la garantie NSIA AUTO +
	IF  (age_vehicule >= 5) AND (id_offre IN (93, 99) OR (nsia_auto_plus_choisie AND id_offre NOT IN (2, 46, 50, 57))) THEN
		RETURN True;
	END IF;

  	RETURN False;
END;
$function$;
