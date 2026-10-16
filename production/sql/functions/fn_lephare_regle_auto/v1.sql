-- Migration production 0164 : règle entre garanties Automobile appliquée par le barème (Administration > Réglages
-- Automobile > Règles des garanties, case « Appliquée aussi par le barème »). Pour une garantie de l'offre :
--   OFFERTE_SI : 0 quand l'offre contient une des garanties liées (ex. NSIA : bris de glace, recours anticipé avec
--                les dommages ou la collision) ;
--   PRIME_SI   : prime forfaitaire de la règle (ex. NSIA : défense-recours 4 200 F avec les dommages ou la collision).
-- NULL : aucune règle active pour cette compagnie, garantie, catégorie (code du tarif) et offre ; le barème s'applique.
CREATE OR REPLACE FUNCTION public.fn_lephare_regle_auto(p_idcompagnie integer, p_idoffre integer, p_idtarif integer,
	p_idsousgarantie integer, p_type character varying)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
	v_categorie varchar;
	v_resultat numeric;
BEGIN
	SELECT TRIM(T.codecategorie) INTO v_categorie FROM public.stdtarif AS T WHERE T.idtarif = p_idtarif;
	BEGIN
		SELECT CASE WHEN p_type = 'OFFERTE_SI' THEN 0 ELSE R.primeannuelle END
		INTO v_resultat
		FROM public.lephare_auto_regle_interaction AS R
		WHERE R.actif AND R.appliqueebareme AND R.type = p_type
		  AND R.idcompagnie = p_idcompagnie AND R.idsousgarantie = p_idsousgarantie
		  AND (p_type = 'OFFERTE_SI' OR R.primeannuelle IS NOT NULL)
		  AND (COALESCE(TRIM(R.categories), '') = ''
		       OR COALESCE(v_categorie, '') = ANY (string_to_array(replace(R.categories, ' ', ''), ',')))
		  AND EXISTS (SELECT 1 FROM public.stdoffregarantie AS G
		              WHERE G.idoffre = p_idoffre AND G.idcompagnie = p_idcompagnie
		                AND G.idsousgarantie::text = ANY (string_to_array(replace(R.liees, ' ', ''), ',')))
		ORDER BY R.ordre, R.id
		LIMIT 1;
	EXCEPTION WHEN undefined_table OR undefined_column THEN
		v_resultat := NULL;
	END;
	RETURN v_resultat;
END;
$function$;
