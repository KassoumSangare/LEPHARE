-- Tarif Individuelle Accidents NSIA ASSURANCES lu dans les réglages (Administration > Réglages par branche >
-- Individuelle Accidents, table lephare_ia_taux_classe) au lieu d'être écrit ici (v1) :
--   prime décès        = taux décès (‰) de la classe × capital décès
--   prime invalidité   = taux invalidité (‰) de la classe × capital invalidité permanente
--   prime frais médic. = taux frais médicaux (%) de la classe × capital frais de traitement
-- Valeurs d'origine (document « TARIF IA_NSIA CI.xlsx ») : taux invalidité = taux décès, comme la v1.
-- Aucune majoration d'âge (clause d'âge contrôlée à l'écran). Mêmes colonnes de retour que la v1.
CREATE OR REPLACE FUNCTION public.fn_calcul_prime_ia_nsia(code_activite character varying, capital_deces numeric, capital_infirmite_permanente numeric, capital_frais_traitement numeric)
 RETURNS TABLE(primedeces numeric, primeinfirmite numeric, primefraistraitement numeric, outmessage character varying)
 LANGUAGE plpgsql
AS $function$
DECLARE
	v_taux RECORD;
BEGIN
	SELECT t.tauxdeces, t.tauxinvalidite, t.tauxfraismedicaux
	INTO v_taux
	FROM public.lephare_ia_taux_classe AS t
	WHERE t.idcompagnie = 1 AND t.classe = code_activite;
	IF NOT FOUND THEN
		RAISE EXCEPTION 'Classe d''activité IA inconnue (%) : tarif NSIA non applicable.', code_activite;
	END IF;

	RETURN QUERY
		SELECT ROUND(COALESCE(capital_deces, 0) * v_taux.tauxdeces / 1000, 0),
		       ROUND(COALESCE(capital_infirmite_permanente, 0) * v_taux.tauxinvalidite / 1000, 0),
		       ROUND(COALESCE(capital_frais_traitement, 0) * v_taux.tauxfraismedicaux / 100, 0),
		       ''::character varying;
END;
$function$;
