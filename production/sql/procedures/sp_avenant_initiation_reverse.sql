-- PROCEDURE: public.sp_avenant_initiation(integer, integer, integer, date, date, character varying, integer, character varying)

DROP PROCEDURE IF EXISTS public.sp_avenant_initiation;

CREATE OR REPLACE PROCEDURE public.sp_avenant_initiation(
	IN user_id integer,
	IN id_contrat integer,
	IN id_avenant integer,
	IN date_emission date,
	IN date_effet date,
	IN motif_annulation character varying,
	INOUT id_devis integer,
	INOUT out_message character varying)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE

	code_avenant char(3);
	id_old_hist integer; --contrat de base pour le contrat courant (ou encore contrat précédent)
	numero_police character varying;
	date_effet_afn_ren date; --Date effet de l'affaire nouvelle ou du renouvellement antérieur
	date_effet_contrat date; --Date effet du contrat sur lequel le mouvement actuel s'effectue
	id_old_avenant integer; --Avenant du contrat à renouveler.
	code_old_avenant char(3); --Avenant du contrat à renouveler.
	
	----Gestion des erreurs
	v_state   TEXT;
    v_msg     TEXT;
    v_detail  TEXT;
    v_hint    TEXT;
    v_context TEXT;
	
BEGIN
   
		
		id_devis := COALESCE(id_devis,0);
		out_message := '';
		id_old_hist := id_contrat;
		IF EXISTS (SELECT 1 FROM StdContrat WHERE IdContrat = id_contrat AND COALESCE(IdContratAnnulation,0) <> 0) THEN
			out_message := 'Contrat déjà annulé ou résilié. Opération impossible.';
			RAISE EXCEPTION '%', out_message;
		END IF;

		---Nouvel avenant en cours de traitement
		SELECT CodeAvenant
		INTO code_avenant
		FROM StdAvenant
		WHERE IdAvenant = id_avenant;
		IF code_avenant IN ('AFN', 'RPP') THEN
			out_message := 'Erreur logicielle. Code avenant incorrect.';
			RAISE EXCEPTION '%', out_message;
		END IF;

		SELECT numeropolice, dateeffet, idavenant INTO numero_police, date_effet_contrat, id_old_avenant
		FROM public.stdcontrat AS SC
		WHERE idcontrat = id_contrat;
		
		IF numero_police IS NULL THEN
			out_message := 'Erreur logicielle: police inexistante!';
			RAISE EXCEPTION '%', out_message;
		END IF;
		
		SELECT dateeffet INTO date_effet_afn_ren
		FROM public.stdcontrat AS SC
		INNER JOIN public.stdavenant AS SA ON (SC.idavenant = SA.idavenant)
		WHERE numeropolice = numero_police AND SA.codeavenant IN ('AFN', 'REN', 'RPP') AND COALESCE(IdContratAnnulation,0) <> 0
		ORDER BY dateeffet DESC
		LIMIT 1;

		IF date_effet_afn_ren > date_effet_contrat THEN
			out_message := 'Cet avenant a été déjà renouvellé';
			RAISE EXCEPTION '%', out_message; 
		END IF;
		
		IF code_avenant = 'ANL' THEN
			CALL sp_avenant_annulation(user_id, id_contrat, id_avenant, date_emission, date_effet, motif_annulation, id_devis, out_message);
		ELSIF code_avenant = 'REN' THEN
			CALL sp_avenant_renouvellement(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
		ELSIF code_avenant = 'MPE' THEN
			CALL sp_avenant_modification_effet(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'RET' THEN
			CALL sp_avenant_retrait(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'INC' THEN
			CALL sp_avenant_incorporation(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
		ELSIF code_avenant = 'ANP' THEN
			CALL sp_avenant_annulation_pure(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'RES' THEN
			CALL sp_avenant_resiliation(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'CHI' THEN
			CALL sp_avenant_changement_immatriculation(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'MOD' THEN
			CALL sp_avenant_modification(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'CHV' THEN
			CALL sp_avenant_changement_vehicule(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'SUS' THEN
			CALL sp_avenant_suspension(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'REV' THEN
			CALL sp_avenant_remise_vigueur(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'TRP' THEN
			CALL sp_avenant_transfert_portefeuille(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'PRG' THEN
			CALL sp_avenant_prorogation(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'ATP' THEN
			CALL sp_avenant_attestation_provisoire(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        ELSIF code_avenant = 'ECT' THEN
			CALL sp_avenant_emission_certificat(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);
        END IF;
		EXCEPTION WHEN others THEN
			get stacked diagnostics
        		v_state   = returned_sqlstate,
        		v_msg     = message_text,
        		v_detail  = pg_exception_detail,
        		v_hint    = pg_exception_hint,
        		v_context = pg_exception_context;

			id_devis := 0;
			out_message := v_msg; -- || ' : ' || v_context;
    		RAISE EXCEPTION E'%
        	state  : %
        	detail : %
        	hint   : %
        	context: %
        	SQLSTATE: % 
        	SQLERRM: %', v_msg, v_state, v_detail, v_hint, v_context, SQLSTATE, SQLERRM;

END; 
$BODY$;
ALTER PROCEDURE public.sp_avenant_initiation(integer, integer, integer, date, date, character varying, integer, character varying)
    OWNER TO uranususer;

