-- PROCEDURE: public.sp_avenant_renouvellement(integer, integer, integer, date, date, integer, character varying)

-- DROP PROCEDURE IF EXISTS public.sp_avenant_renouvellement(integer, integer, integer, date, date, integer, character varying);

CREATE OR REPLACE PROCEDURE public.sp_avenant_renouvellement(
	IN user_id integer,
	IN id_contrat integer,
	IN id_avenant integer,
	IN date_emission date,
	IN date_effet date,
	INOUT id_devis integer,
	INOUT out_message character varying)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE

	code_avenant char(3);
	code_avenant_ancien char(3); --code de l'avenant de base
	-- date_effet_avenant_ancien date; --date d'effet de l'avenant de base
	date_expiration_avenant_ancien date; --date d'expiration de l'avenant de base
	date_effet_probable date;
	numero_police character varying;
	motif_annulation character varying;
	date_effet_avenant_ancien date;
	id_duree_avenant_ancien integer;
	date_expiration date;
	
	----Gestion des erreurs
	v_state   TEXT;
    v_msg     TEXT;
    v_detail  TEXT;
    v_hint    TEXT;
    v_context TEXT;
	
BEGIN
   	
		id_devis := COALESCE(id_devis,0);
		out_message := '';
		motif_annulation := '';

		SELECT codeavenant
		INTO code_avenant
		FROM public.stdavenant
		WHERE idavenant = id_avenant;
		code_avenant := COALESCE(code_avenant, 'XXX');
		IF code_avenant <> 'REN' THEN
			out_message := 'Erreur logicielle. Mauvais code avenant!';
			RAISE EXCEPTION '%', out_message;
		END IF;

		SELECT SA.codeavenant, SC.idduree, SC.dateeffet, SC.dateexpiration, SC.numeropolice
		INTO code_avenant_ancien, id_duree_avenant_ancien, date_effet_avenant_ancien, date_expiration_avenant_ancien, numero_police
		FROM public.stdcontrat AS SC
		INNER JOIN public.stdavenant AS SA ON (SC.idavenant = SA.idavenant)
		WHERE idcontrat = id_contrat;
		
		IF code_avenant_ancien NOT IN ('AFN', 'REN', 'RPP', 'TRP') THEN
			out_message := 'Renouvellement impossible sur cet avenant.';
			RAISE EXCEPTION '%', out_message;
		END IF;

		date_emission := COALESCE(date_emission, CURRENT_DATE);
		IF date_effet IS NULL THEN
			SELECT NPC.date_effet, NPC.date_expiration
			INTO date_effet, date_expiration
			FROM public.fn_get_nouvelle_periode_couverture(id_duree_avenant_ancien, date_effet_avenant_ancien, date_expiration_avenant_ancien) AS NPC;
		ELSIF date_expiration IS NULL THEN
			date_expiration := public.fn_get_date_expiration(date_effet, id_duree_avenant_ancien);
		END IF;	
		
		IF date_effet <= date_expiration_avenant_ancien THEN
			out_message := 'La date d''expiration doit être postérieure à celle du contrat à renouveler.';
			RAISE EXCEPTION '%', out_message;
		END IF;
	
		CALL sp_avenant_creation_devis_initial(user_id, id_contrat, id_avenant, date_emission, date_effet, date_expiration, motif_annulation, id_devis, out_message);
		
		IF id_devis <> 0 THEN
			out_message := 'Devis de renouvellement enregistré avec succès.';
		END IF;
		EXCEPTION WHEN others THEN
			get stacked diagnostics
        		v_state   = returned_sqlstate,
        		v_msg     = message_text,
        		v_detail  = pg_exception_detail,
        		v_hint    = pg_exception_hint,
        		v_context = pg_exception_context;

			id_devis := 0;
			out_message := v_msg; -- || ' : ' || v_context; -- 'Problème rencontré lors de l'annulation du contrat;
    		/* RAISE EXCEPTION E'Got exception:
        	state  : %
        	message: %
        	detail : %
        	hint   : %
        	context: %
        	SQLSTATE: % 
        	SQLERRM: %', v_state, v_msg, v_detail, v_hint, v_context, SQLSTATE, SQLERRM;
			*/
			RAISE EXCEPTION '%', out_message;

END; 
$BODY$;
ALTER PROCEDURE public.sp_avenant_renouvellement(integer, integer, integer, date, date, integer, character varying)
    OWNER TO uranususer;

