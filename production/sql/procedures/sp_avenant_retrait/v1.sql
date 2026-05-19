-- Version originale (bugguée) : appel à sp_avenant_creation_devis_initial avec 7 params
-- alors que la signature en attend 9 (date_expiration et motif_annulation manquants)
CREATE OR REPLACE PROCEDURE public.sp_avenant_retrait(IN user_id integer, IN id_contrat integer, IN id_avenant integer, IN date_emission date, IN date_effet date, INOUT id_devis integer, INOUT out_message character varying)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
	code_avenant char(3);
	code_avenant_ancien char(3);
    contrat_flotte boolean;

	----Gestion des erreurs
	v_state   TEXT;
    v_msg     TEXT;
    v_detail  TEXT;
    v_hint    TEXT;
    v_context TEXT;

BEGIN

		SELECT SA.CodeAvenant, SC.flotte
		INTO code_avenant_ancien, contrat_flotte
		FROM StdContrat AS SC
		INNER JOIN StdAvenant AS SA ON (SC.IdAvenant = SA.IdAvenant)
		WHERE IdContrat = id_contrat;
        contrat_flotte := COALESCE(contrat_flotte, False);

		IF code_avenant_ancien IN ('RET', 'SUS', 'RES', 'ANP', 'ANL') THEN
			out_message := 'Retrait impossible sur cet avenant.';
			RAISE EXCEPTION '%', out_message;
		END IF;

        IF NOT contrat_flotte THEN
            out_message := 'Retrait impossible dans un contrat mono.';
			RAISE EXCEPTION '%', out_message;
        END IF;

		SELECT CodeAvenant
		INTO code_avenant
		FROM StdAvenant
		WHERE IdAvenant = id_avenant;
		code_avenant := COALESCE(code_avenant, 'XXX');
		IF code_avenant <> 'RET' THEN
			out_message := 'Erreur logicielle. Mauvais code avenant!';
			RAISE EXCEPTION '%', out_message;
		END IF;

		CALL sp_avenant_creation_devis_initial(user_id, id_contrat, id_avenant, date_emission, date_effet, id_devis, out_message);

		EXCEPTION WHEN others THEN
			get stacked diagnostics
        		v_state   = returned_sqlstate,
        		v_msg     = message_text,
        		v_detail  = pg_exception_detail,
        		v_hint    = pg_exception_hint,
        		v_context = pg_exception_context;

			id_devis := 0;
			out_message := v_msg;
			RAISE EXCEPTION '%', out_message;

END;
$procedure$
