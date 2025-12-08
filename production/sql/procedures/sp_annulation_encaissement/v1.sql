-- PROCEDURE: public.sp_annulation_encaissement(integer, integer, date, character varying, integer, character varying)

DROP PROCEDURE IF EXISTS public.sp_annulation_encaissement(integer, integer, date, character varying, integer, character varying);

CREATE OR REPLACE PROCEDURE public.sp_annulation_encaissement(
	IN id_encaissement integer,
	IN id_utilisateur integer,
	IN date_annulation date,
	IN motif_annulation character varying,
	INOUT id_nouvel_encaissement integer,
	INOUT out_message character varying)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
	ligne_encaissement RECORD;
	nom_annulation character varying(50);
	date_saisie_annulation timestamp with time zone;
	ancien_indice_acompte integer;
	----Gestion des erreurs
	v_state   TEXT;
    v_msg     TEXT;
    v_detail  TEXT;
    v_hint    TEXT;
    v_context TEXT;
BEGIN

	id_nouvel_encaissement := COALESCE(id_nouvel_encaissement, 0);
	IF EXISTS (SELECT 1 
			   FROM StdDetailReversement
			   WHERE IdDetailEncaissement IN (SELECT IdDetailEncaissement
											  FROM StdDetailEncaissement
											  WHERE IdEncaissement = id_encaissement)
			  ) THEN
		out_message := 'Encaissement déjà reversé. Annulation impossible.';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	motif_annulation := TRIM(COALESCE(motif_annulation, ''));
	IF motif_annulation = '' THEN
		out_message := 'Motif d''annulation non précisé. Annulation impossible.';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	IF EXISTS (SELECT 1 FROM StdEncaissement WHERE IdEncaissement = id_encaissement AND Piece_Annulee AND DateAnnulation IS NOT NULL) THEN
		out_message := 'Encaissement déjà annulé. Nouvelle annulation impossible.';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	SELECT name
	INTO nom_annulation
	FROM public.account_uranususer
	WHERE id = id_utilisateur;
	
	date_annulation := COALESCE(date_annulation, CURRENT_DATE);
	date_saisie_annulation := CURRENT_TIMESTAMP;
	
	INSERT INTO public.StdEncaissement(NumeroPiece, DateEncaissement, MontantEncaissement, MontantEnAttente, MontantDeduit, NumeroCheque, Compte_Compensation,
									   IdUtilisateur, DateSaisie, Piece_Annulee, DateAnnulation, NomAnnulation, MotifAnnulation, DateSaisieAnnulation, NomtireurCheque,
									   IdBanque, IdModePaiement)
	SELECT NumeroPiece, date_annulation AS DateEncaissement, -MontantEncaissement, -MontantEnAttente, -MontantDeduit, NumeroCheque, Compte_Compensation,
		id_utilisateur, date_saisie_annulation AS DateSaisie, True AS Piece_Annulee, date_annulation AS DateAnnulation, nom_annulation, motif_annulation AS MotifAnnulation,
		date_saisie_annulation AS DateSaisieAnnulation, NomTireurCheque, IdBanque, IdModePaiement
	FROM public.StdEncaissement
	WHERE IdEncaissement = id_encaissement
	RETURNING IdEncaissement INTO id_nouvel_encaissement;

	UPDATE public.StdEncaissement
	SET DateAnnulation = date_annulation, DateSaisieAnnulation = date_saisie_annulation, Piece_Annulee = True, NomAnnulation = nom_annulation, MotifAnnulation = motif_annulation 
	WHERE IdEncaissement = id_encaissement;
	
	FOR ligne_encaissement IN (SELECT IdDetailEncaissement AS IdDetailEnc, Montant_Encaissement AS MontantEnc, NumeroQuittance AS NumQuittance
							   FROM StdDetailEncaissement
							   WHERE IdEncaissement = id_encaissement
							  )
	LOOP
		SELECT MAX(IndiceAcompte) 
		INTO ancien_indice_acompte
		FROM StdDetailEncaissement
		WHERE NumeroQuittance = ligne_encaissement.NumQuittance;
		ancien_indice_acompte := COALESCE(ancien_indice_acompte, 0);
		
		INSERT INTO public.stddetailencaissement(indiceacompte, soldeinitial, montantreglement, montantecart, ecart, code_ecart, montant_encaissement, dedcommission_intermediaire, dedcommission_gestionnaire, dedcommission_coassurance, dedaccessoireintermediaire, dedaccessoiregestionnaire, dedtaxecommission, dedtaxeaccessoire, comintermediaire, comgestionnaire, comconseiller, comcoassurance, accintermediaire, accgestionnaire, dedcoassurance, primecedee, taxe_commission_deduit, taxeaccessoire_deduit, impotdeduit, idencaissement, numeroquittance)
		SELECT ancien_indice_acompte + 1, -soldeinitial, -montantreglement, -montantecart, ecart, code_ecart, -montant_encaissement, dedcommission_intermediaire, dedcommission_gestionnaire, dedcommission_coassurance, dedaccessoireintermediaire, dedaccessoiregestionnaire, dedtaxecommission, dedtaxeaccessoire, -comintermediaire, -comgestionnaire, -comconseiller, -comcoassurance, -accintermediaire, -accgestionnaire, dedcoassurance, -primecedee, -taxe_commission_deduit, -taxeaccessoire_deduit, -impotdeduit, id_nouvel_encaissement, numeroquittance
		FROM public.stddetailencaissement
		WHERE IdDetailEncaissement = ligne_encaissement.IdDetailEnc;
		
		UPDATE public.StdQuittance
		SET Mt_Encaisse = COALESCE(Mt_Encaisse, 0) - ligne_encaissement.MontantEnc,
			Encaissee = False,
			Reglee = False
		WHERE NumeroQuittance = ligne_encaissement.NumQuittance;
		
		UPDATE public.StdClient AS SCli
		SET Solde = COALESCE(Solde, 0) + ligne_encaissement.MontantEnc
		FROM public.StdQuittance AS SQ
		WHERE (SQ.NumeroQuittance = ligne_encaissement.NumQuittance) AND (SQ.IdClient = SCli.IdClient);
		
	END LOOP;
	
	IF id_nouvel_encaissement <> 0 THEN
		out_message := 'Encaissement annulé avec succès.';
	END IF;
															   
	EXCEPTION WHEN others THEN
		get stacked diagnostics
        	v_state   = returned_sqlstate,
        	v_msg     = message_text,
        	v_detail  = pg_exception_detail,
        	v_hint    = pg_exception_hint,
        	v_context = pg_exception_context;
			
		id_nouvel_encaissement := 0;
		out_message := v_msg; -- || ' : ' || v_context; -- 'Problème rencontré lors de l'enregistrement de l'encaissement;
    		
		RAISE EXCEPTION E'%
        	state  : %
        	detail : %
        	hint   : %
        	context: %
        	SQLSTATE: % 
        	SQLERRM: %', v_msg, v_state, v_detail, v_hint, v_context, SQLSTATE, SQLERRM;

END;
$BODY$;
ALTER PROCEDURE public.sp_annulation_encaissement(integer, integer, date, character varying, integer, character varying)
    OWNER TO uranususer;

