CREATE OR REPLACE PROCEDURE public.sp_consolidation_devis(
    IN p_id_user integer,
    IN p_devis_ids integer[],
    INOUT p_devis_principal_id integer)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
    v_id_client INTEGER;
    v_id_assure INTEGER;
    v_out_message CHARACTER VARYING;
BEGIN
    -- 1. Validation basics
    IF array_length(p_devis_ids, 1) < 2 THEN
        RAISE EXCEPTION 'Au moins 2 devis sont requis.';
    END IF;

    p_devis_principal_id := p_devis_ids[1];

    -- 2. Get Master Info & Verify Existence
    SELECT idclient, idassure INTO v_id_client, v_id_assure
    FROM public.stddevis WHERE iddevis = p_devis_principal_id;

    IF NOT FOUND OR v_id_client IS NULL OR v_id_assure IS NULL THEN
        RAISE EXCEPTION 'Devis principal invalide ou client/assuré manquant.';
    END IF;

    -- 3. RECORD ORIGINAL RELATIONSHIP & MOVE DETAILS
    -- We update all lines belonging to source quotes (excluding the principal)
    UPDATE public.stddevisdetail
    SET 
        iddevis_origine = iddevis,           -- Keep the "Backlink"
        iddevis = p_devis_principal_id       -- Move to Principal
    WHERE iddevis = ANY(p_devis_ids[2:array_length(p_devis_ids, 1)]);

    -- 4. Update Source Quotes Status
    UPDATE public.stddevis
    SET statut = 'ARCHIVE',
        archive = true,
        iddevisconsolide = p_devis_principal_id,
        dateconsolidation = CURRENT_TIMESTAMP
    WHERE iddevis = ANY(p_devis_ids[2:array_length(p_devis_ids, 1)]);

    -- 5. Update Principal Quote Status
    UPDATE public.stddevis
    SET statut = 'CONSOLIDE',
        flotte = true,
        datemodification = CURRENT_TIMESTAMP
    WHERE iddevis = p_devis_principal_id;

    -- 6. History & Finalization
    INSERT INTO public.stdhistoriqueconsolidation (iddevisconsolide, iddevissource, dateconsolidation, idutilisateur)
    VALUES (p_devis_principal_id, p_devis_ids, CURRENT_TIMESTAMP, p_id_user);

    CALL public.sp_finalisation_devis(p_devis_principal_id, v_id_client, v_id_assure, true, v_out_message);

EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Erreur consolidation: %', SQLERRM;
END;
$BODY$;
ALTER PROCEDURE public.sp_consolidation_devis(integer, integer[], integer)
    OWNER TO uranususer;

COMMENT ON PROCEDURE public.sp_consolidation_devis(integer, integer[], integer)
    IS 'Consolide plusieurs devis en rattachant les lignes des devis suivants au premier devis de la liste. Retourne l''ID du devis principal (consolidé).';
