
CREATE OR REPLACE PROCEDURE public.sp_annulation_consolidation_devis(
    IN p_id_user integer,
    IN p_devis_principal_id integer)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
    v_id_client INTEGER;
    v_id_assure INTEGER;
    v_out_message CHARACTER VARYING;
    v_source_record RECORD;
BEGIN
    -- 1. Verify the quote status
    IF NOT EXISTS (SELECT 1 FROM public.stddevis WHERE iddevis = p_devis_principal_id AND statut = 'CONSOLIDE') THEN
        RAISE EXCEPTION 'Le devis % n''est pas consolidé ou n''existe pas.', p_devis_principal_id;
    END IF;

    -- 2. Restore Detail Lines
    UPDATE public.stddevisdetail
    SET 
        iddevis = iddevis_origine,
        iddevis_origine = NULL
    WHERE iddevis = p_devis_principal_id 
    AND iddevis_origine IS NOT NULL;

    -- 3. Restore Source Quotes and Loop for Finalization
    -- We use a cursor/loop to ensure each restored quote gets its totals updated
    FOR v_source_record IN 
        UPDATE public.stddevis
        SET statut = 'ACTIF',
            archive = false,
            iddevisconsolide = NULL,
            dateconsolidation = NULL
        WHERE iddevisconsolide = p_devis_principal_id
        RETURNING iddevis, idclient, idassure
    LOOP
        -- Recalculate each source quote
        CALL public.sp_finalisation_devis(
            v_source_record.iddevis, 
            v_source_record.idclient, 
            v_source_record.idassure, 
            true, 
            v_out_message
        );
    END LOOP;

    -- 4. Reset and Recalculate Principal Quote
    UPDATE public.stddevis
    SET statut = 'ACTIF',
        flotte = false,
        datemodification = CURRENT_TIMESTAMP
    WHERE iddevis = p_devis_principal_id;

    SELECT idclient, idassure INTO v_id_client, v_id_assure
    FROM public.stddevis WHERE iddevis = p_devis_principal_id;

    CALL public.sp_finalisation_devis(p_devis_principal_id, v_id_client, v_id_assure, true, v_out_message);

    RAISE NOTICE 'Annulation terminée. Tous les devis ont été recalculés.';

EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Erreur lors de l''annulation: %', SQLERRM;
END;
$BODY$;

ALTER PROCEDURE public.sp_annulation_consolidation_devis(integer, integer)
    OWNER TO uranususer;

COMMENT ON PROCEDURE public.sp_annulation_consolidation_devis(integer, integer)
    IS 'Annule la consolidation de devis en restaurant tous les devis préalablement consolidés et archivés.';