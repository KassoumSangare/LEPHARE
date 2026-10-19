-- Migration production 0167 (demande du 2026-10-19 : « quand le bouton NSIA Auto Plus est coché, faire apparaître NSIA
-- Auto+ dans les garanties ») : case cochée = garantie toujours retenue, quels que soient l'âge du véhicule et l'offre
-- (avant : jamais sur les offres tous risques 2, 46, 50, 57, ni avant l'âge minimum, même cochée). Sa prime reste celle
-- de fn_calcul_prime_nsia_auto_plus (offres tous risques et EBENE PREMIUM : 0 F, comprise ; ailleurs valeur vénale x taux
-- de la grille, 0 F si la grille n'a pas de taux NSIA Auto Plus).
-- Case non cochée : inchangé, d'office dans les offres EBENE PREMIUM (93, 99) à partir de l'âge minimum (Réglages
-- Automobile > Dépréciation et âge des véhicules, 5 ans à l'origine).
CREATE OR REPLACE FUNCTION public.fn_retenir_garantie_nsia_auto_plus(id_offre integer, age_vehicule integer, nsia_auto_plus_choisie boolean)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
DECLARE
	age_minimum integer;
BEGIN
	---Case « NSIA Auto Plus » cochée : la garantie est demandée, elle est retenue
	IF COALESCE(nsia_auto_plus_choisie, FALSE) THEN
		RETURN True;
	END IF;

	BEGIN
		SELECT MIN(R.ageminimum)
		INTO age_minimum
		FROM public.lephare_auto_regle_garantie AS R
		WHERE R.idcompagnie = 1 AND R.idsousgarantie = 175;
	EXCEPTION WHEN undefined_table THEN
		age_minimum := NULL;
	END;
	age_minimum := COALESCE(age_minimum, 5);

	---D'office dans les offres EBENE PREMIUM à partir de l'âge minimum
	IF (COALESCE(age_vehicule, 0) >= age_minimum) AND id_offre IN (93, 99) THEN
		RETURN True;
	END IF;

	RETURN False;
END;
$function$;
