CREATE OR REPLACE PROCEDURE public.sp_enregistrement_encaissement(
    IN id_utilisateur integer,
    IN id_mode_encaissement integer,
    IN date_encaissement date,
    IN id_banque integer,
    IN montant_total numeric,
    IN numero_cheque character varying,
    IN reference_encaissement character varying,
    IN reference_compensation character varying,
    IN nom_emetteur character varying,
    IN liste_quittance character varying,
    IN liste_montant character varying,
    INOUT id_encaissement integer,
    INOUT out_message character varying)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
    montant_total_calcule numeric;
    numero_piece character varying;
    code_intermediaire character varying (4);
    date_emission date;
    reference_transaction uuid;
    v_msg TEXT;
BEGIN
    -- 1. INITIALISATION & VALIDATION
    out_message := '';
    id_encaissement := 0;
    id_banque := COALESCE(id_banque, 1);
    montant_total := COALESCE(montant_total, 0);

    -- 2. TABLE TEMPORAIRE
    CREATE TEMPORARY TABLE IF NOT EXISTS temp_data_encaissement(numeroquittance character varying(16), montantencaissement numeric);
    TRUNCATE TABLE temp_data_encaissement;
    
    INSERT INTO temp_data_encaissement(numeroquittance, montantencaissement)
    VALUES (CAST(UNNEST(STRING_TO_ARRAY(liste_quittance, ';')) AS character varying), 
            CAST(UNNEST(STRING_TO_ARRAY(liste_montant,';')) AS numeric));

    -- Validation montant total
    SELECT SUM(montantencaissement) INTO montant_total_calcule FROM temp_data_encaissement;
    IF COALESCE(montant_total_calcule,0) <> montant_total THEN
        RAISE EXCEPTION 'Incohérence : Somme des lignes (%) != Montant total (%)', montant_total_calcule, montant_total;
    END IF;

    -- 3. GÉNÉRATION DU NUMÉRO DE PIÈCE (via votre procédure interne)
    SELECT SQ.DateEmission, TRIM(COALESCE(SI.CodeIntermediaire,'0')) 
    INTO date_emission, code_intermediaire
    FROM temp_data_encaissement AS TDE
    INNER JOIN StdQuittance AS SQ ON TDE.NumeroQuittance = SQ.NumeroQuittance
    INNER JOIN StdContrat AS SC ON SQ.idquittance = SC.idquittance
    INNER JOIN StdIntermediaireCompagnie AS SI ON (SC.IdIntermediaire = SI.IdIntermediaire AND SC.IdCompagnie = SI.IdCompagnie)
    LIMIT 1;

    CALL sp_generation_numero_piece (code_intermediaire, date_emission, numero_piece);

    -- 4. INSERTION ENTÊTE ENCAISSEMENT
    INSERT INTO StdEncaissement(numeropiece, dateencaissement, montantencaissement, idutilisateur, nomtireurcheque, idbanque, idmodepaiement, datesaisie)
    VALUES (numero_piece, date_encaissement, montant_total, id_utilisateur, nom_emetteur, id_banque, id_mode_encaissement, CURRENT_DATE)
    RETURNING idencaissement INTO id_encaissement;

    -- 5. UPDATE STDCLIENT (AVANT StdQuittance pour utiliser les anciennes valeurs de Mt_Encaisse)
    -- On utilise LEAST et GREATEST pour une logique mathématique infaillible
    UPDATE StdClient AS SCli
    SET 
        Solde = COALESCE(SCli.Solde, 0) - sub.montant_imputable,
        Avoir = COALESCE(SCli.Avoir, 0) + sub.montant_surplus
    FROM (
        SELECT 
            SQ.IdClient,
            -- Reste à payer avant cet encaissement
            SUM(LEAST(TDE.MontantEncaissement, (SQ.PrimeTTC - COALESCE(SQ.Mt_Encaisse, 0)))) as montant_imputable,
            -- Excédent (si versement > reste à payer)
            SUM(GREATEST(0, TDE.MontantEncaissement - (SQ.PrimeTTC - COALESCE(SQ.Mt_Encaisse, 0)))) as montant_surplus
        FROM temp_data_encaissement TDE
        INNER JOIN StdQuittance SQ ON TDE.NumeroQuittance = SQ.NumeroQuittance
        GROUP BY SQ.IdClient
    ) AS sub
    WHERE SCli.IdClient = sub.IdClient;

    -- 6. UPDATE STDQUITTANCE (Après avoir calculé les avoirs client)
    UPDATE StdQuittance AS SQ
    SET 
        Mt_Encaisse = CASE 
            WHEN (COALESCE(SQ.Mt_Encaisse, 0) + TDE.MontantEncaissement) > SQ.PrimeTTC THEN SQ.PrimeTTC 
            ELSE (COALESCE(SQ.Mt_Encaisse, 0) + TDE.MontantEncaissement) 
        END,
        Encaissee = CASE 
            WHEN (COALESCE(SQ.Mt_Encaisse, 0) + TDE.MontantEncaissement) >= SQ.PrimeTTC THEN True 
            ELSE False 
        END
    FROM temp_data_encaissement AS TDE
    WHERE SQ.NumeroQuittance = TDE.NumeroQuittance;

    -- 7. INSERTION DÉTAILS
    INSERT INTO StdDetailEncaissement(idencaissement, numeroquittance, soldeinitial, montant_encaissement, indiceacompte)
    SELECT id_encaissement, TDE.NumeroQuittance, (SQ.PrimeTTC - (COALESCE(SQ.Mt_Encaisse,0) - TDE.MontantEncaissement)), TDE.MontantEncaissement, 1
    FROM temp_data_encaissement TDE
    INNER JOIN StdQuittance SQ ON TDE.NumeroQuittance = SQ.NumeroQuittance;

    out_message := 'Encaissement enregistré avec succès.';

EXCEPTION WHEN others THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
    id_encaissement := 0;
    out_message := 'Erreur : ' || v_msg;
END;
$BODY$;