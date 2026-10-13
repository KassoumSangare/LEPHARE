CREATE OR REPLACE FUNCTION public.fn_garantie_offre_risques_divers(id_compagnie integer, id_offre integer, taux_prime numeric, capital_dommage_corporel numeric, capital_intoxication_alimentaire numeric, capital_dommage_materiel numeric, assiette_prime numeric, taux_reduction numeric, date_effet date, date_expiration date, id_produit integer DEFAULT 8, id_devis integer DEFAULT 0)
 RETURNS TABLE(idgarantie integer, libellegarantie character varying, idsousgarantie integer, libellesousgarantie character varying, acquise boolean, capital numeric, nombreplace integer, primeannuelle numeric, primenette numeric, taxe numeric, montantaccessoire numeric, tauxfranchise numeric, franchiseminimum numeric, franchisemaximum numeric, montantfranchise numeric, franchisetexte character varying)
 LANGUAGE plpgsql
AS $function$
DECLARE
	
	----Pour le calcul des totaux des composantes de prime
	prime_annuelle_totale numeric;
	prime_nette_totale numeric;
	v_accessoire numeric;
	v_accessoire_intermediaire numeric;
	--taux_taxe_accessoire numeric;
	taxe_accessoire numeric;
	taxe_totale numeric;
	v_prime_nette_minene_rc numeric;
	v_somme_capitaux numeric;
    v_somme_primes_arrondies numeric := 0;
    v_reliquat numeric;
    v_id_max_part integer;

BEGIN

	DROP TABLE IF EXISTS temp_garantie_offre;
	CREATE UNLOGGED TABLE temp_garantie_offre (idgar integer, libellegar varchar, idsousgar integer, libellesousgar varchar, acq boolean, cap numeric, nbreplace integer, primean numeric, primene numeric, tx numeric, montantacc numeric, txfranchise numeric, franchisemin numeric, franchisemax numeric, montfranchise numeric, franchisetxt varchar, ordreaffich smallint);
	-- TRUNCATE temp_garantie_offre;
	
	--Contrôle des paramètres
	taux_prime := COALESCE(taux_prime, 0.0);
	capital_dommage_corporel := COALESCE(capital_dommage_corporel, 0.0);
	capital_intoxication_alimentaire := COALESCE(capital_intoxication_alimentaire, 0.0);
	capital_dommage_materiel := COALESCE(capital_dommage_materiel, 0.0);
	assiette_prime := COALESCE(assiette_prime, 0.0);
	taux_reduction := COALESCE(taux_reduction, 0.0);
	

	IF (capital_dommage_corporel + capital_dommage_materiel + capital_intoxication_alimentaire) = 0 AND id_devis = 0 THEN
		SELECT CM.capitaldommagecorporel, CM.capitaldommagemateriel, CM.capitalintoxicationalimentaire
		INTO capital_dommage_corporel, capital_dommage_materiel, capital_intoxication_alimentaire
		FROM public.fn_get_capitaux_minene_rc() AS CM;
		capital_dommage_corporel := COALESCE(capital_dommage_corporel, 0.0);
		capital_dommage_materiel := COALESCE(capital_dommage_materiel, 0.0);
		capital_intoxication_alimentaire := COALESCE(capital_intoxication_alimentaire, 0.0);
	END IF;
	
	--Initialisation des cumuls
	prime_annuelle_totale := 0;
	prime_nette_totale := 0;
	v_accessoire := 0;
	v_accessoire_intermediaire := 0;
	taxe_totale := 0;
	
	INSERT INTO temp_garantie_offre (idgar, libellegar, idsousgar, libellesousgar, acq, cap, nbreplace, primean, primene, tx, montantacc, txfranchise, franchisemin, franchisemax, montfranchise, franchisetxt, ordreaffich)
	SELECT ssg.IdGarantie, sg.LibelleGarantie, sog.IdSousGarantie, ssg.LibelleSousGarantie, FALSE, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, fn_franchise_texte(0.0, 0, 0), sog.OrdreAffichage
	FROM StdOffreGarantie AS sog
	JOIN StdSousGarantie AS ssg ON ssg.IdSousGarantie = sog.IdSousGarantie
	JOIN StdGarantie AS sg ON sg.IdGarantie = ssg.IdGarantie
	WHERE sog.IdOffre = id_offre AND sog.IdCompagnie = id_compagnie
	ORDER BY sog.OrdreAffichage ASC;

	IF id_devis <> 0 THEN
		UPDATE temp_garantie_offre AS TGO
		SET acq = TRUE, primean = SDG.primeannuelle, primene = SDG.primenette, tx = SDG.taxe, cap = COALESCE(SDG.capital, TGO.cap),
			txfranchise = SDG.tauxfranchise, franchisemin = SDG.minfranchise, franchisemax = SDG.maxfranchise, montfranchise = SDG.franchise, franchisetxt = SDG.textefranchise
		FROM public.stddevisdetgarantie AS SDG
		JOIN public.stddevisdetail AS SDD ON SDG.iddevisdet = SDD.iddevisdetail
		WHERE SDD.iddevis = id_devis
		AND SDG.idgarantie = TGO.idsousgar;
	
		SELECT  COALESCE(SD.primeannuelle, 0), COALESCE(SD.primenette, 0), COALESCE(SD.taxe, 0), COALESCE(SD.accessoirecompagnie, 0), COALESCE(SD.accessoireintermediaire, 0)
		INTO prime_annuelle_totale, prime_nette_totale, taxe_totale, v_accessoire, v_accessoire_intermediaire
		FROM public.stddevis AS SD
		WHERE iddevis = id_devis;
		
		prime_annuelle_totale := COALESCE(prime_annuelle_totale, 0);
		prime_nette_totale := COALESCE(prime_nette_totale, 0);
		taxe_totale:= COALESCE(taxe_totale, 0);
		v_accessoire:= COALESCE(v_accessoire, 0);
		v_accessoire_intermediaire:= COALESCE(v_accessoire_intermediaire, 0);
	END IF;
	
	UPDATE temp_garantie_offre
	SET cap = capital_dommage_corporel
	WHERE idsousgar = 64 AND ((id_devis = 0) OR (COALESCE(capital_dommage_corporel, 0) <> 0));
			
	UPDATE temp_garantie_offre
	SET cap = capital_intoxication_alimentaire
	WHERE idsousgar = 166 AND ((id_devis = 0) OR (COALESCE(capital_intoxication_alimentaire, 0) <> 0));

	UPDATE temp_garantie_offre
	SET cap = capital_dommage_materiel
	WHERE idsousgar = 61 AND ((id_devis = 0) OR (COALESCE(capital_dommage_materiel, 0) <> 0));

	IF id_offre = 67 THEN ---Offre MINENE
		v_prime_nette_minene_rc := public.fn_get_prime_base_minene_rcc();
		-- 1. Calcul de la somme des capitaux
    	SELECT SUM(cap) INTO v_somme_capitaux FROM temp_garantie_offre WHERE idgar <> 0;

    	-- 2. Répartition initiale avec arrondi à l'unité (ou 2 décimales selon votre besoin)
    	IF COALESCE(v_somme_capitaux, 0) > 0 THEN
        	UPDATE temp_garantie_offre 
        	SET acq = True, primene = ROUND(v_prime_nette_minene_rc * (cap / v_somme_capitaux), 0)
        	WHERE idgar <> 0;
    	ELSE
        	-- Répartition équitable si capitaux à zéro
        	UPDATE temp_garantie_offre 
        	SET acq = True, primene = ROUND(v_prime_nette_minene_rc / 3.0, 0)
        	WHERE idgar <> 0;
    	END IF;

    	-- 3. Identification de la ligne ayant la part la plus élevée (pour le reliquat)
    	-- En cas d'égalité, on prend l'ID le plus petit (LIMIT 1)
    	SELECT idsousgar INTO v_id_max_part 
    	FROM temp_garantie_offre 
    	WHERE idgar <> 0
    	ORDER BY primene DESC, idsousgar ASC 
    	LIMIT 1;

    	-- 4. Calcul du reliquat d'arrondi
    	SELECT SUM(primene) INTO v_somme_primes_arrondies 
    	FROM temp_garantie_offre 
    	WHERE idgar <> 0;

    	v_reliquat := v_prime_nette_minene_rc - v_somme_primes_arrondies;

    	-- 5. Application du reliquat sur la garantie principale
    	IF v_reliquat <> 0 THEN
        	UPDATE temp_garantie_offre 
        	SET primene = primene + v_reliquat
        	WHERE idsousgar = v_id_max_part;
    	END IF;
		
		-- 6. Une franchise doit être appliquée aux dommages mtériels (Administration > Réglages Santé MINENE :
		--    10 %, minimum 20 000, maximum 200 000 à l'origine)
		UPDATE temp_garantie_offre
		SET txfranchise = fn_lephare_parametre_nombre('sante.minene.rc_franchise_taux', 10.0),
			franchisemin = fn_lephare_parametre_nombre('sante.minene.rc_franchise_minimum', 20000),
			franchisemax = fn_lephare_parametre_nombre('sante.minene.rc_franchise_maximum', 200000),
			franchisetxt = fn_franchise_texte(fn_lephare_parametre_nombre('sante.minene.rc_franchise_taux', 10.0),
											 fn_lephare_parametre_nombre('sante.minene.rc_franchise_minimum', 20000),
											 fn_lephare_parametre_nombre('sante.minene.rc_franchise_maximum', 200000))
		WHERE idsousgar = 61;
		
		-- 7. Mettre à jour la prime annuelle
		UPDATE temp_garantie_offre
		SET primean = primene
		WHERE idgar <> 0;
		
	ELSIF id_devis = 0 THEN
		IF (COALESCE(taux_prime, 0) = 0) THEN
			UPDATE temp_garantie_offre
			SET primean = assiette_prime, primene = assiette_prime, acq = True
			WHERE idsousgar = 61;
		ELSIF (COALESCE(taux_prime, 0) <> 0) THEN
			UPDATE temp_garantie_offre
			SET acq = True, primean = (COALESCE(cap, 0) * taux_prime)/100, primene = (((COALESCE(cap, 0) * taux_prime)/100) - ((((COALESCE(cap, 0) * taux_prime)/100) * taux_reduction)/100));
		END IF;
	END IF;

	---Taxe d'enregistrement
	UPDATE temp_garantie_offre AS TG
	SET tx = ROUND(primene * COALESCE(TauxTaxe,0)/100, 4)
	FROM stdtauxtaxegarantieproduit AS TTGP
	WHERE (TTGP.idproduit = id_produit) AND (TTGP.idgarantie = TG.idsousgar) AND (date_effet BETWEEN TTGP.DebutValidite AND TTGP.FinValidite);

	SELECT SUM(primene), SUM(primean), ROUND(SUM(tx), 0)
	INTO prime_nette_totale, prime_annuelle_totale, taxe_totale
	FROM temp_garantie_offre;
	
	SELECT * 
	INTO v_accessoire, v_accessoire_intermediaire, taxe_accessoire
	FROM fn_get_accessoire(prime_nette_totale, id_produit, id_offre, id_compagnie, date_effet);
	taxe_totale := taxe_totale + taxe_accessoire;
	
	INSERT INTO temp_garantie_offre (idgar, libellegar, idsousgar, libellesousgar, acq, cap, primean, primene, tx, montantacc, txfranchise, franchisemin, franchisemax, montfranchise, franchisetxt, ordreaffich)
	VALUES (0, 'TOTAL', 0, 'CUMUL DES GARANTIES', TRUE, 0, prime_annuelle_totale, prime_nette_totale, taxe_totale, (v_accessoire + v_accessoire_intermediaire), 0.0, 0, 0, 0, '', 99);
	
	RETURN QUERY SELECT idgar, libellegar, idsousgar, libellesousgar, acq, cap, nbreplace, primean, primene, tx, montantacc, txfranchise, franchisemin, franchisemax, montfranchise, franchisetxt
	FROM temp_garantie_offre
	ORDER BY ordreaffich ASC, idgar ASC, idsousgar ASC;
	
END;
$function$;
