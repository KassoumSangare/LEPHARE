-- PROCEDURE: public.sp_consolidation_devis(integer, integer[], integer)

-- DROP PROCEDURE IF EXISTS public.sp_consolidation_devis(integer, integer[], integer);

CREATE OR REPLACE PROCEDURE public.sp_consolidation_devis(
	IN p_id_user integer,
	IN p_devis_ids integer[],
	INOUT p_devis_principal_id integer)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
    v_devis_id INTEGER;
    v_count INTEGER;
	v_out_message CHARACTER VARYING;
	v_id_client INTEGER;
	v_id_assure INTEGER;
BEGIN

	v_out_message := '';
	p_devis_principal_id := 0;
	-- Vérification que le tableau n'est pas vide
    IF array_length(p_devis_ids, 1) IS NULL OR array_length(p_devis_ids, 1) < 2 THEN
        RAISE EXCEPTION 'Au moins 2 devis sont requis pour la consolidation';
    END IF;
    
    -- Le premier devis devient le devis principal (consolidé)
    p_devis_principal_id := p_devis_ids[1];
    
    -- Vérification que le devis principal existe
    SELECT COUNT(*) INTO v_count
    FROM public.stddevis
    WHERE iddevis = p_devis_principal_id;
    
    IF v_count = 0 THEN
		v_out_message := 'Le devis principal ' || CAST(p_devis_principal_id AS VARCHAR) || ' n''existe pas.';
		p_devis_principal_id := 0;
        RAISE EXCEPTION USING MESSAGE = v_out_message;
    END IF;

	--Récupération de id_client integer, IN id_assure integer
    SELECT idclient, idassure
	INTO v_id_client, v_id_assure
	FROM public.stddevis
	WHERE iddevis = p_devis_principal_id;
	v_id_client := COALESCE(v_id_client, 0);
	v_id_assure := COALESCE(v_id_assure, 0);
	
	IF v_id_client = 0 THEN
		v_out_message := 'Le devis principal ' || CAST(p_devis_principal_id AS VARCHAR) || ' n''a pas de client.';
		p_devis_principal_id := 0;
		RAISE EXCEPTION USING MESSAGE = v_out_message;
	END IF;
	
	IF v_id_assure = 0 THEN
		v_out_message := 'Le devis principal ' || CAST(p_devis_principal_id AS VARCHAR) || ' n''a pas d''assuré.';
		p_devis_principal_id := 0;
		RAISE EXCEPTION USING MESSAGE = v_out_message;
	END IF;
	
    -- Copie des lignes de devis des autres devis vers le devis principal
    -- On parcourt tous les devis sauf le premier
    FOR i IN 2..array_length(p_devis_ids, 1) LOOP
        v_devis_id := p_devis_ids[i];
        
        -- Vérification que le devis source existe
        SELECT COUNT(*) INTO v_count
        FROM public.stddevis
        WHERE iddevis = v_devis_id;
        
        IF v_count = 0 THEN
            RAISE EXCEPTION 'Le devis source % n''existe pas', v_devis_id;
        END IF;
        
        -- Rattachement des lignes de devis du devis source au devis principal
        UPDATE public.stddevisdetail
		SET iddevis = p_devis_principal_id
        WHERE iddevis = v_devis_id;
        
        -- Log du nombre de lignes copiées
        GET DIAGNOSTICS v_count = ROW_COUNT;
        RAISE NOTICE 'Copié % lignes du devis % vers le devis %', v_count, v_devis_id, p_devis_principal_id;
        
    END LOOP;
    
    -- Mise à jour du statut du devis principal
    UPDATE public.stddevis
    SET statut = 'CONSOLIDE',
		flotte =true,
        datemodification = CURRENT_TIMESTAMP
    WHERE iddevis = p_devis_principal_id;
    
    -- Mise à jour du statut des devis sources (marqués comme consolidés/archivés)
    -- On exclut le premier devis (devis principal)
    UPDATE public.stddevis
    SET statut = 'ARCHIVE',
		archive = true,
        iddevisconsolide = p_devis_principal_id,
        dateconsolidation = CURRENT_TIMESTAMP
    WHERE iddevis = ANY(p_devis_ids[2:array_length(p_devis_ids, 1)]);
    
    -- Insertion dans la table d'historique
    INSERT INTO public.stdhistoriqueconsolidation (iddevisconsolide, iddevissource, dateconsolidation, idutilisateur)
    VALUES (p_devis_principal_id, p_devis_ids, CURRENT_TIMESTAMP, p_id_user);

	CALL public.sp_finalisation_devis(p_devis_principal_id, v_id_client, v_id_assure, true, v_out_message);
    -- Log de l'opération
    RAISE NOTICE 'Consolidation terminée. Devis principal: %', p_devis_principal_id;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Rollback automatique en cas d'erreur
        RAISE EXCEPTION 'Erreur lors de la consolidation: %', SQLERRM;
END;
$BODY$;
ALTER PROCEDURE public.sp_consolidation_devis(integer, integer[], integer)
    OWNER TO uranususer;

COMMENT ON PROCEDURE public.sp_consolidation_devis(integer, integer[], integer)
    IS 'Consolide plusieurs devis en rattachant les lignes des devis suivants au premier devis de la liste. Retourne l''ID du devis principal (consolidé).';
