CREATE OR REPLACE PROCEDURE public.sp_avenant_incorporation(IN user_id integer, IN id_contrat integer, IN id_avenant integer, IN date_emission date, IN date_effet date, INOUT id_devis integer, INOUT out_message character varying)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
	code_avenant char(3);
	code_avenant_ancien char(3);
    flotte_avenant_ancien boolean; 
	date_effet_avenant_ancien date;
	date_expiration_avenant_ancien date;
	id_duree_avenant_ancien integer;
	motif_annulation character varying;
	date_expiration date;
	
	----Gestion des erreurs
	v_state   TEXT;
    v_msg     TEXT;
    v_detail  TEXT;
    v_hint    TEXT;
    v_context TEXT;

BEGIN

		motif_annulation := '';

		SELECT SA.CodeAvenant, SC.idduree, SC.flotte, SC.date_effet, SC.date_expiration
		INTO code_avenant_ancien, id_duree_avenant_ancien, flotte_avenant_ancien, date_effet_avenant_ancien, date_expiration_avenant_ancien
		FROM StdContrat AS SC
		INNER JOIN StdAvenant AS SA ON (SC.IdAvenant = SA.IdAvenant)
		WHERE IdContrat = id_contrat;
		
		IF code_avenant_ancien IN ('RET', 'SUS', 'RES', 'ANP', 'ANL', 'INC', 'MOD', 'PRG', 'CHI', 'CHV') THEN
			out_message := 'Incorporation impossible sur cet avenant!';
			RAISE EXCEPTION '%', out_message;
		END IF;
		
		SELECT CodeAvenant
		INTO code_avenant
		FROM StdAvenant
		WHERE IdAvenant = id_avenant;
		code_avenant := COALESCE(code_avenant, 'XXX');
		IF code_avenant <> 'INC' THEN
			out_message := 'Erreur logicielle. Mauvais code avenant!';
			RAISE EXCEPTION '%', out_message;
		END IF;

        IF NOT flotte_avenant_ancien THEN
            out_message := 'Avenant impossible pour une police mono!';
			RAISE EXCEPTION '%', out_message;
        END IF;

		date_emission := COALESCE(date_emission, CURRENT_DATE);
		IF date_effet IS NULL OR date_expiration IS NULL THEN
			SELECT NPC.date_effet, NPC.date_expiration
			INTO date_effet, date_expiration
			FROM public.fn_get_nouvelle_periode_couverture(id_duree_avenant_ancien, date_effet_avenant_ancien, date_expiration_avenant_ancien) AS NPC;
		END IF;
	
		CALL sp_avenant_creation_devis_initial(user_id, id_contrat, id_avenant, date_emission, date_effet, date_expiration, motif_annulation, id_devis, out_message);
		
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
$procedure$
