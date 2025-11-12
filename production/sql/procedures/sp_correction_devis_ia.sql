-- PROCEDURE: public.sp_correction_devis_ia(integer, numeric, numeric, character varying)

-- DROP PROCEDURE IF EXISTS public.sp_correction_devis_ia(integer, numeric, numeric, character varying);

CREATE OR REPLACE PROCEDURE public.sp_correction_devis_ia(
	IN p_id_devis integer,
	IN p_prime_annuelle numeric,
	IN p_prime_nette numeric,
	INOUT p_output_message character varying DEFAULT ''::character varying)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
	-- Déclare des variables pour stocker les valeurs extraites du JSON
    v_date_effet DATE;
    v_date_expiration DATE;
    v_numero_police VARCHAR;
    v_reduction_commerciale NUMERIC;
    v_reduction_bns NUMERIC;
    v_reduction_flotte NUMERIC;
	v_nombre_assures INTEGER;
    
	--------------------
	v_id_client integer;
	v_id_assure integer;
	v_flotte boolean;
	v_id_produit integer;
	v_id_devis_detail integer;
	
	----Gestion des erreurs
	v_state   text;
    v_msg     text;
    v_detail  text;
    v_hint    text;
    v_context text;

BEGIN
		
		SELECT idproduit, idclient, idassure, flotte, dateeffet
		INTO v_id_produit, v_id_client, v_id_assure, v_flotte, v_date_effet
		FROM public.stddevis
		WHERE iddevis = p_id_devis;
		v_id_produit := COALESCE(v_id_produit, 0);
		v_id_client := COALESCE(v_id_client, 0);
		v_id_assure := COALESCE(v_id_assure, 0);
		IF v_id_produit = 0 THEN
			p_output_message := 'Erreur logicelle. Produit non défini pour ce devis.';
		ELSIF v_id_client = 0 THEN
			p_output_message := 'Erreur logicelle. Client non défini pour ce devis.';
		ELSIF v_id_assure = 0 THEN
			p_output_message := 'Erreur logicelle. Assuré non défini pour ce devis.';
		ELSIF v_date_effet IS NULL THEN
			p_output_message := 'Erreur logicelle. Date effet non définie pour ce devis.';
		END IF;
		IF p_output_message <> '' THEN
			RAISE EXCEPTION '%', p_output_message;
		END IF;
		
		SELECT COUNT(iddevisdetail)
		INTO v_nombre_assures
		FROM public.stddevisdetail
		WHERE iddevis = p_id_devis;
		v_nombre_assures := COALESCE(v_nombre_assures, 0);
		IF v_nombre_assures = 0 THEN
			p_output_message := 'Erreur logicielle: ce devis ne comporte aucun assuré.';
			RAISE EXCEPTION '%', p_output_message;
		END IF;
		
		FOR v_id_devis_detail IN (SELECT iddevisdetail FROM public.stddevisdetail WHERE iddevis = p_id_devis)
		LOOP
			--Réparation des primes annuelle et nette imposées comme suit:
			-- Décès (IdSousGarantie=19): 40% ==> Taux: 2/5
			-- Infirmité Permanente (IdSousGarantie=17): 35% ==> Taux: 7/20
			-- Frais de traitement (IdSousGarantie=20): 25%  ==> Taux: 1/4
			-- Ensuite diviser les valeurs des primes annuelle et nette imposées par le nombre d'assurés
			UPDATE public.StdDevisDetGarantie
			SET primeannuelle = CASE WHEN IdGarantie = 17 THEN ROUND (p_prime_annuelle * 7.0 / (20.0 * v_nombre_assures), 0)
								  WHEN IdGarantie = 19 THEN ROUND (p_prime_annuelle * 2.0 / (5.0 * v_nombre_assures), 0)
								  WHEN IdGarantie = 20 THEN ROUND (p_prime_annuelle / (4.0 * v_nombre_assures), 0)
							 ELSE 0
							 END,
				primenette = CASE WHEN IdGarantie = 17 THEN ROUND (p_prime_nette * 7.0 / (20.0 * v_nombre_assures), 0)
								  WHEN IdGarantie = 19 THEN ROUND (p_prime_nette * 2.0 / (5.0 * v_nombre_assures), 0)
								  WHEN IdGarantie = 20 THEN ROUND (p_prime_nette / (4.0 * v_nombre_assures), 0)
							 ELSE 0
							 END
			WHERE IdDevisDet = v_id_devis_detail;
			
			UPDATE public.StdDevisDetGarantie AS DD
			SET taxe = ROUND(primenette * tauxtaxe / 100, 0)
			FROM public.stdtauxtaxegarantieproduit AS TT
			WHERE (DD.IdDevisDet=v_id_devis_detail) AND (TT.idgarantie=DD.IdGarantie) AND (TT.idproduit = v_id_produit) AND (v_date_effet BETWEEN TT.DebutValidite AND TT.FinValidite);

			UPDATE public.StdDevisDetail AS DD
			SET primeannuelle = M.primeannuelle, primenette = M.primenette, fga = 0, taxeenregistrement = taxe
			FROM (SELECT IdDevisDet, SUM(primeannuelle) AS primeannuelle, SUM(PrimeNette) AS primenette, SUM(taxe) AS taxe
				  FROM public.StdDevisDetGarantie
				  WHERE IdDevisDet = v_id_devis_detail
			 	  GROUP BY IdDevisDet) AS M
			WHERE (M.IdDevisDet=DD.iddevisdetail) AND (IdDevisDet = v_id_devis_detail);	
			
		END LOOP;
		
		CALL public.sp_finalisation_devis(p_id_devis, v_id_client, v_id_assure, v_flotte, p_output_message);
		
		UPDATE public.stddevis
		SET primeimposee = True
		WHERE iddevis = p_id_devis;

		EXCEPTION WHEN others THEN
			get stacked diagnostics
        		v_state   = returned_sqlstate,
        		v_msg     = message_text,
        		v_detail  = pg_exception_detail,
        		v_hint    = pg_exception_hint,
        		v_context = pg_exception_context;
			p_output_message := v_msg || ' :' || E'\n' || v_context; -- 'Problème rencontré lors de la correction du devis';  || E'\n' || 

			RAISE EXCEPTION '%', p_output_message;
END;
$BODY$;
ALTER PROCEDURE public.sp_correction_devis_ia(integer, numeric, numeric, character varying)
    OWNER TO uranususer;
