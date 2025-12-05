-- PROCEDURE: public.sp_enregistrement_reversement(integer, integer, integer, date, integer, numeric, character varying, character varying, character varying, character varying, character varying, character varying, integer, character varying)

DROP PROCEDURE IF EXISTS public.sp_enregistrement_reversement;

CREATE OR REPLACE PROCEDURE public.sp_enregistrement_reversement(
	IN id_utilisateur integer, --obligatoire
	IN id_compagnie integer, --obligatoire
	IN id_mode_reversement integer,
	IN date_reversement date,
	IN id_banque integer,
	IN montant_total numeric,  --obligatoire
	IN numero_cheque character varying,
	IN nom_emetteur character varying,
	IN reference_reversement character varying,
	IN reference_compensation character varying,
	IN liste_encaissement character varying,
	IN liste_montant character varying,
	INOUT id_reversement integer,
	INOUT out_message character varying)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE

	montant_total_calcule numeric;
	numero_reversement character varying;
	code_intermediaire character varying (4);
	reversement_banque boolean;
	reversement_compensation boolean;
	libelle_banque character varying (50);
	abrege_reglement character varying(3);
	encaissement_rec RECORD;
	encaissement_trop_reverse text;
	nombre_encaissement_soumis integer;
	nombre_encaissement_reel integer;
-- 	detail_encaissement_cursor NO SCROLL CURSOR (numero_quittance character varying(16)) FOR
-- 	SELECT *
-- 	FROM StdDetailEncaissement
-- 	WHERE (NumeroQuittance = numero_quittance) AND (COALESCE(MontantReglement, 0) < Montant_Encaissement)
-- 	ORDER BY (Montant_Encaissement - COALESCE(MontantReglement, 0)) ASC;
	----Gestion des erreurs
	v_state   TEXT;
    v_msg     TEXT;
    v_detail  TEXT;
    v_hint    TEXT;
    v_context TEXT;
	
BEGIN

	out_message := '';
	id_reversement := 0;
	id_banque := COALESCE(id_banque, 0); 
	montant_total := COALESCE(montant_total, 0); 
	numero_cheque := TRIM(COALESCE(numero_cheque, '')); 
	reference_reversement := TRIM(COALESCE(reference_reversement, '')); 
	reference_compensation := TRIM(COALESCE(reference_compensation, '')); 
	
	SELECT banque, compensation, UPPER(abregereglement)
	INTO reversement_banque, reversement_compensation, abrege_reglement
	FROM StdModeEncaissement
	WHERE idmodeencaissement = id_mode_reversement;
	reversement_banque := COALESCE(reversement_banque, False);
	reversement_compensation := COALESCE(reversement_compensation, False);
	abrege_reglement := COALESCE(abrege_reglement, '');
	
	IF NOT reversement_banque THEN
		numero_cheque := '';
		id_banque := 1;
	ELSE
		SELECT UPPER(Libelle)
		INTO libelle_banque
		FROM StdBanque
		WHERE IdBanque = id_banque;
		libelle_banque := TRIM(COALESCE(libelle_banque,''));
		IF libelle_banque IN ('', 'AUCUNE', 'AUCUN', 'NEANT') THEN
			out_message := 'Une banque doit être précisée pour ce mode de reversement.';
			RAISE EXCEPTION '%', out_message;
		END IF;
		IF abrege_reglement = 'CHQ' AND numero_cheque = '' THEN
			out_message := 'Le numéro de chèque doit être précisé.';
			RAISE EXCEPTION '%', out_message;
		END IF;
		reference_compensation := '';
	END IF;
	IF reversement_compensation THEN
		IF reference_compensation = '' THEN
			out_message := 'La référence de la compensation doit être précisée.';
			RAISE EXCEPTION '%', out_message;
		END IF;
		numero_cheque := '';
		id_banque := NULL;
	END IF;
	
 	CREATE TEMPORARY TABLE IF NOT EXISTS temp_data_reversement(iddetailencaissement integer, montantreversement numeric);
	
	DELETE FROM temp_data_reversement;
	
	INSERT INTO temp_data_reversement(iddetailencaissement, montantreversement)
	VALUES (CAST(UNNEST(STRING_TO_ARRAY(liste_encaissement, ';')) AS integer), CAST(UNNEST(STRING_TO_ARRAY(liste_montant,';')) AS numeric)); 
	
	SELECT SUM(montantreversement)
	INTO montant_total_calcule
	FROM temp_data_reversement;
	
	montant_total_calcule := COALESCE(montant_total_calcule,0);
	
	IF montant_total_calcule <> montant_total THEN
		out_message := 'Incohérence des données. La somme des montants de reversement est différente du montant total à reverser.';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	encaissement_trop_reverse := '';
	FOR encaissement_rec IN (SELECT TDR.IdDetailEncaissement AS IdDetailEncaissement
						  FROM temp_data_reversement AS TDR
						  INNER JOIN StdDetailEncaissement AS SDE ON (TDR.IdDetailEncaissement = SDE.IdDetailEncaissement)
						  WHERE ((COALESCE(SDE.Montant_Encaissement, 0) - COALESCE(SDE.MontantReglement, 0) - TDR.MontantReversement) < 0)
						  )
	LOOP
		encaissement_trop_reverse := encaissement_trop_reverse || encaissement_rec.IdDetailEncaissement || ';';
	END LOOP;
	IF LENGTH(encaissement_trop_reverse) > 0 THEN
		encaissement_trop_reverse := SUBSTRING(encaissement_trop_reverse, 1, LENGTH(encaissement_trop_reverse)-1);
		out_message := 'Encaissements trop reversés:' || E'\n' || encaissement_trop_reverse;
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	SELECT COUNT(IdDetailEncaissement)
	INTO nombre_encaissement_soumis
	FROM Temp_Data_Reversement;
	nombre_encaissement_soumis := COALESCE(nombre_encaissement_soumis, 0);
	
	SELECT COUNT(TDR.IdDetailEncaissement)
	INTO nombre_encaissement_reel
	FROM Temp_Data_Reversement AS TDR
	INNER JOIN StdDetailEncaissement AS SDE ON (TDR.IdDetailEncaissement = SDE.IdDetailEncaissement);
	nombre_encaissement_reel := COALESCE(nombre_encaissement_reel, 0);
	
	IF (nombre_encaissement_reel <> nombre_encaissement_soumis) THEN
		out_message := 'Incohérence des données. Certains encaissements à reverser n''existent pas dans la base de données.';
		RAISE EXCEPTION '%', out_message;
	END IF;

	SELECT TRIM(COALESCE(SI.CodeIntermediaire, '0')) 
	INTO code_intermediaire
	FROM temp_data_reversement AS TDE
	INNER JOIN StdDetailEncaissement AS SDE ON (TDE.IdDetailEncaissement = SDE.IdDetailEncaissement)
	INNER JOIN StdQuittance AS SQ ON (SDE.NumeroQuittance = SQ.NumeroQuittance)
	INNER JOIN StdIntermediaireCompagnie AS SI ON (SQ.IdIntermediaire = SI.IdIntermediaire AND SI.IdCompagnie = id_compagnie)
	ORDER BY SQ.DateEmission 
	LIMIT 1;
	
	CALL sp_generation_numero_reversement (code_intermediaire, date_reversement, numero_reversement);
	
	INSERT INTO StdReversementCompagnie(NumeroReversement, DateReversement, MontantReversement, MontantEnAttente, MontantDeduit,
										NumeroCheque, CompteCompensation, DateSaisie, PieceAnnulee, DateAnnulation, NomAnnulation,
										MotifAnnulation, DateSaisieAnnulation, NomTireurCheque, IdBanque, IdCompagnie,
										IdModeReversement, IdUtilisateur)
	VALUES (numero_reversement, date_reversement, montant_total, 0, 0,
			numero_cheque, reference_compensation, CURRENT_TIMESTAMP, False, NULL, '',
			'', NULL, nom_emetteur, id_banque, id_compagnie, id_mode_reversement, id_utilisateur)
	RETURNING IdReversement INTO id_reversement;
	
	FOR encaissement_rec IN (SELECT IdDetailEncaissement, MontantReversement
						  FROM temp_data_reversement
						  )
	LOOP
		UPDATE StdDetailEncaissement
		SET MontantReglement = COALESCE(MontantReglement, 0) + encaissement_rec.MontantReversement
		WHERE IdDetailEncaissement = encaissement_rec.IdDetailEncaissement;
		
		UPDATE StdQuittance AS SQ
		SET Mt_Regle = COALESCE(Mt_Regle, 0) + encaissement_rec.MontantReversement,
			Reglee = CASE WHEN (COALESCE(Mt_Regle, 0) + encaissement_rec.MontantReversement) = COALESCE(Mt_Encaisse, 0) THEN True ELSE False END
		FROM StdDetailEncaissement AS SDE
		WHERE (SDE.IdDetailEncaissement = encaissement_rec.IdDetailEncaissement)
			  AND (SQ.NumeroQuittance = SDE.NumeroQuittance);
			  
		INSERT INTO StdDetailReversement(soldeinitial, montantreverse, dedcommission_intermediaire, dedcommission_gestionnaire,
								 dedcommission_coassurance, dedaccessoireintermediaire, dedaccessoiregestionnaire,
								 dedtaxecommission, dedtaxeaccessoire, comintermediaire, comgestionnaire, comconseiller,
								 comcoassurance, accintermediaire, accgestionnaire, dedcoassurance, primecedee,
								 taxe_commission_deduit, taxeaccessoire_deduit, iddetailencaissement, idreversement)				 
		SELECT soldeinitial, encaissement_rec.MontantReversement AS montantreverse, dedcommission_intermediaire, dedcommission_gestionnaire,
				dedcommission_coassurance, dedaccessoireintermediaire, dedaccessoiregestionnaire,
				dedtaxecommission, dedtaxeaccessoire, comintermediaire, comgestionnaire, comconseiller,
				comcoassurance, accintermediaire, accgestionnaire, dedcoassurance, primecedee, 
				taxe_commission_deduit, taxeaccessoire_deduit, iddetailencaissement, id_reversement
		FROM stddetailencaissement
		WHERE IdDetailEncaissement = encaissement_rec.IdDetailEncaissement;
	END LOOP;
	
	DROP TABLE IF EXISTS temp_data_reversement;
															   
	IF id_reversement <> 0 THEN
		out_message := 'Reversement enregistré avec succès.';
	END IF;
															   
	EXCEPTION WHEN others THEN
		get stacked diagnostics
        	v_state   = returned_sqlstate,
        	v_msg     = message_text,
        	v_detail  = pg_exception_detail,
        	v_hint    = pg_exception_hint,
        	v_context = pg_exception_context;
			
		id_reversement := 0;
		out_message := v_msg || ' : ' || v_context; -- 'Problème rencontré lors de l'enregistrement du reversement;
		
    		RAISE EXCEPTION E'Got exception:
        	state  : %
        	message: %
        	detail : %
        	hint   : %
        	context: %
        	SQLSTATE: % 
        	SQLERRM: %', v_state, v_msg, v_detail, v_hint, v_context, SQLSTATE, SQLERRM;

END; 
$BODY$;
ALTER PROCEDURE public.sp_enregistrement_reversement(integer, integer, integer, date, integer, numeric, character varying, character varying, character varying, character varying, character varying, character varying, integer, character varying)
    OWNER TO uranususer;

