-- PROCEDURE: public.sp_finalisation_devis(integer, integer, integer, boolean, character varying)

-- DROP PROCEDURE IF EXISTS public.sp_finalisation_devis(integer, integer, integer, boolean, character varying);

CREATE OR REPLACE PROCEDURE public.sp_finalisation_devis(
	IN id_devis integer,
	IN id_client integer,
	IN id_assure integer,
	IN flotte boolean,
	INOUT out_message character varying)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
	numero_devis varchar(16);
	id_produit integer;
	id_offre integer;
	id_compagnie integer;
	date_emission date;
	date_effet date;
	prime_nette numeric;
	taux_commission numeric;
	--Pour le calcul des taxes relatives aux accessoires
	var_accessoire numeric;
	var_accessoire_intermediaire numeric;
	taxe_accessoire numeric;
	devis_rec RECORD;
	conducteur_rec RECORD;
	effectif_assure integer;
	nombre_moto integer;
	----Gestion des erreurs
	v_state   TEXT;
    v_msg     TEXT;
    v_detail  TEXT;
    v_hint    TEXT;
    v_context TEXT;
	
BEGIN
    	out_message := '';
		effectif_assure := 1;
		nombre_moto := 1;
		
		SELECT idproduit, idcompagnie, numerodevis, dateemission, dateeffet
		INTO devis_rec
		FROM StdDevis
		WHERE iddevis = id_devis;
		id_produit := COALESCE(devis_rec.idproduit, 0);
		id_compagnie := COALESCE(devis_rec.idcompagnie, 0);
		numero_devis := COALESCE(devis_rec.numerodevis, '');
		date_emission := COALESCE(devis_rec.dateemission, CURRENT_DATE);
		date_effet := COALESCE(devis_rec.dateeffet, CURRENT_DATE);
		
		SELECT MAX(IdOffre)
		INTO id_offre
		FROM StdDevisDetail
		WHERE IdDevis = id_devis;
		id_offre := COALESCE(id_offre, 0);
		
		IF flotte AND id_produit = 1 THEN
			SELECT TRIM(Nom) || TRIM(COALESCE(Prenoms,'')) AS nomconducteur,
				   TRIM(COALESCE(Adresse1,'')) AS adresseconducteur
			INTO conducteur_rec
			FROM StdClient
			WHERE IdClient = id_assure;

			UPDATE StdDevisDetail
			SET conducteur = COALESCE(conducteur_rec.nomconducteur,''),
			    adressecnd = COALESCE(conducteur_rec.adresseconducteur,'')
			WHERE iddevis = id_devis;
		END IF;
		
		taux_commission := fn_get_taux_commission(id_produit, id_compagnie, date_emission);
 
		IF flotte THEN
			UPDATE StdDevis
			SET idclient = id_client, idassure = id_assure
			WHERE iddevis = id_devis;
			
			---Application de la réduction flotte
			SELECT COUNT(iddevisdetail), SUM(CASE WHEN CodeCategorie = '205' THEN 1 ELSE 0 END)
			INTO effectif_assure, nombre_moto
			FROM StdDevisDetail AS SDD 
			INNER JOIN StdTarif AS ST ON (SDD.IdTarif = ST.IdTarif)
			WHERE iddevis = id_devis;
			effectif_assure := COALESCE(effectif_assure, 0);
			nombre_moto := COALESCE(nombre_moto, 0);
-- 			IF effectif_assure > 1 THEN
-- 				CALL sp_application_reduction_flotte(id_devis, out_message);
-- 			END IF;
		ELSE
			effectif_assure := 1;
			nombre_moto := 0;
			IF EXISTS (SELECT 1 FROM StdDevisDetail AS SDD 
					            INNER JOIN StdTarif AS ST ON (SDD.IdTarif = ST.IdTarif)
					            WHERE IdDevis = id_devis AND CodeCategorie = '205') THEN
				nombre_moto := 1;
			END IF;
		END IF;

		IF id_offre <> 66 THEN --Offres autres que l'offre IA MINENE
			UPDATE StdDevis AS DD
			SET primeannuelle = M.primeannuelle, primenette = M.primenette, fga = M.fga, cedeao = CASE WHEN DD.idproduit = 1 THEN COALESCE(M.primecedeao, 0) ELSE 0 END,
				taxe = M.taxeenregistrement, CommissionIntermediaire = ROUND((M.primenette*COALESCE(taux_commission,0))/100,0)
			FROM (SELECT iddevis, SUM(fn_get_prime_cedeo(idtarif, puissancefiscale, chargeutile)) AS primecedeao, SUM(primeannuelle) AS primeannuelle, SUM(primenette) AS primenette, SUM(fga) AS fga, SUM(taxeenregistrement) AS taxeenregistrement
				  FROM StdDevisDetail
				  WHERE iddevis=id_devis
				  GROUP BY iddevis) AS M
			WHERE (M.iddevis=DD.iddevis) AND (DD.iddevis=id_devis) AND (DD.numerodevis=numero_devis);
			
			SELECT primenette 
			INTO prime_nette
			FROM StdDevis 
			WHERE iddevis = id_devis;
			prime_nette := COALESCE(prime_nette, 0);
			
			IF (effectif_assure = nombre_moto) THEN
				SELECT * 
				INTO var_accessoire, var_accessoire_intermediaire, taxe_accessoire
				FROM fn_get_accessoire_moto(prime_nette, id_produit, id_offre, id_compagnie, date_effet, effectif_assure);
			ELSE
				SELECT * 
				INTO var_accessoire, var_accessoire_intermediaire, taxe_accessoire
				FROM fn_get_accessoire(prime_nette, id_produit, id_offre, id_compagnie, date_effet);
			END IF;
			
			UPDATE StdDevis
			SET AccessoireCompagnie = var_accessoire, AccessoireIntermediaire = var_accessoire_intermediaire,
				Accessoire = var_accessoire + var_accessoire_intermediaire, taxe = taxe + taxe_accessoire
			WHERE IdDevis = id_devis;
		
			UPDATE StdDevis
			SET primettc = ROUND((primenette+accessoire+taxe), 0)
			WHERE iddevis=id_devis;
		ELSE
			UPDATE StdDevis
			SET primeannuelle = 0, primenette = 0, fga = 0, cedeao = 0, taxe = 0, CommissionIntermediaire = 0
			WHERE (iddevis=id_devis) AND (numerodevis=numero_devis);
			
			UPDATE StdDevis
			SET AccessoireCompagnie = 0, AccessoireIntermediaire = 0,
				Accessoire = 0, taxe = 0
			WHERE IdDevis = id_devis;
		
			UPDATE StdDevis
			SET primettc = 0
			WHERE iddevis=id_devis;
		END IF;

		IF flotte THEN
			out_message := 'Devis finalisé avec succès.';
		ELSE
			out_message := 'Devis enregistré avec succès.';
		END IF;
	
		EXCEPTION WHEN others THEN
			get stacked diagnostics
        		v_state   = returned_sqlstate,
        		v_msg     = message_text,
        		v_detail  = pg_exception_detail,
        		v_hint    = pg_exception_hint,
        		v_context = pg_exception_context;
				
			out_message := v_msg; -- || ' : ' || v_context; -- 'Problème rencontré lors de la finalisation du devis';
    		/*
			RAISE EXCEPTION E'Got exception:
        	state  : %
        	message: %
        	detail : %
        	hint   : %
        	context: %
        	SQLSTATE: % 
        	SQLERRM: %', v_state, v_msg, v_detail, v_hint, v_context, SQLSTATE, SQLERRM;
			*/

END; 
$BODY$;
ALTER PROCEDURE public.sp_finalisation_devis(integer, integer, integer, boolean, character varying)
    OWNER TO uranususer;

