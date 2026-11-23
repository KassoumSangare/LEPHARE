CREATE OR REPLACE FUNCTION public.fn_lephare_auto_taux_reduction_cp(id_compagnie integer, code_categorie character varying, id_sous_garantie integer, nature character varying, taux numeric)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Taux imprimé dans les colonnes « BNS » et « Autres » (réduction commerciale) d'une ligne de garantie des Conditions
-- Particulières Auto (fn_liste_garanties_souscrites) : le taux du véhicule sur les garanties où le moteur
-- (fn_garantie_offre) l'applique, 0 ailleurs. Mêmes exclusions que le moteur :
--   NSIA (et compagnies sans moteur, CP au modèle NSIA) : fn_calcul_reduction_commerciale (jamais sur le groupe RC) et
--     fn_calcul_prime_prorata v2 (BNS appliqué au bris de glace toits ouvrants, 172) ;
--   AMSA (21) et SUNU (14) : fn_garantie_offre_cat*_amsa / _sunu ;
--   Pool TPV (catégorie 204, fn_garantie_offre_tpv) : ni BNS ni réduction.
-- FGA (2) et CEDEAO (3) : jamais.
DECLARE
	id_groupe integer;
BEGIN
	IF COALESCE(taux, 0) = 0 OR id_sous_garantie IN (2, 3) OR TRIM(COALESCE(code_categorie, '')) = '204' THEN
		RETURN 0.0;
	END IF;

	IF UPPER(COALESCE(nature, '')) = 'BNS' THEN
		IF id_compagnie IN (14, 21) THEN
			RETURN CASE WHEN id_sous_garantie NOT IN (3, 22) THEN taux ELSE 0.0 END;
		END IF;
		RETURN CASE WHEN id_sous_garantie NOT IN (3, 17, 18, 19, 20, 22, 163, 164, 169, 173, 176, 177, 178, 179) THEN taux ELSE 0.0 END;
	END IF;

	-- Réduction commerciale : jamais sur les garanties du groupe responsabilité civile
	SELECT SG.IdGarantie
	INTO id_groupe
	FROM StdSousGarantie AS SG
	WHERE SG.IdSousGarantie = id_sous_garantie;
	IF COALESCE(id_groupe, 0) = 1 THEN
		RETURN 0.0;
	END IF;
	IF id_compagnie IN (14, 21) THEN
		RETURN CASE WHEN id_sous_garantie NOT IN (3, 4, 22) THEN taux ELSE 0.0 END;
	END IF;
	RETURN CASE WHEN id_sous_garantie NOT IN (3, 17, 18, 19, 20, 163, 164, 169, 172, 173, 174, 175, 178, 179) THEN taux ELSE 0.0 END;
END;
$function$
