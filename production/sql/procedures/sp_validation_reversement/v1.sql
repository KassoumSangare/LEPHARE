DROP PROCEDURE IF EXISTS public.sp_validation_reversement;

CREATE OR REPLACE PROCEDURE public.sp_validation_reversement(
    IN id_utilisateur           integer,
	IN id_reversement        integer,
    IN id_mode_reversement      integer DEFAULT NULL,
    IN date_reversement         date DEFAULT CURRENT_DATE,
    IN id_banque                integer DEFAULT 1,
    IN numero_cheque            varchar DEFAULT '',
    IN nom_emetteur             varchar DEFAULT '',
    IN reference_reversement    varchar DEFAULT '',
    IN reference_compensation   varchar DEFAULT '',
    INOUT out_message           varchar DEFAULT ''
)
LANGUAGE plpgsql
AS $$
DECLARE

    reversement_banque       boolean := false;
    reversement_compensation boolean := false;
    libelle_banque           varchar(50);
    abrege_reglement         varchar(3);
BEGIN
    -- Normalisation
    out_message            := '';
    id_banque              := COALESCE(id_banque, 0);
    numero_cheque          := TRIM(COALESCE(numero_cheque, ''));
    reference_reversement  := TRIM(COALESCE(reference_reversement, ''));
    reference_compensation := TRIM(COALESCE(reference_compensation, ''));
    nom_emetteur           := TRIM(COALESCE(nom_emetteur, ''));
	date_reversement       := COALESCE(date_reversement, CURRENT_DATE);

    -- Mode reversement
    SELECT banque, compensation, UPPER(abregereglement)
    INTO reversement_banque, reversement_compensation, abrege_reglement
    FROM StdModeEncaissement
    WHERE idmodeencaissement = id_mode_reversement;

    reversement_banque       := COALESCE(reversement_banque, false);
    reversement_compensation := COALESCE(reversement_compensation, false);
    abrege_reglement         := COALESCE(abrege_reglement, '');

    IF NOT reversement_banque THEN
        numero_cheque := '';
        id_banque := 1;
        reference_compensation := '';
    ELSE
        SELECT UPPER(TRIM(COALESCE(Libelle,'')))
        INTO libelle_banque
        FROM StdBanque
        WHERE IdBanque = id_banque;

        IF libelle_banque IN ('', 'AUCUNE', 'AUCUN', 'NEANT') THEN
            RAISE EXCEPTION USING MESSAGE = 'Une banque doit être précisée pour ce mode de reversement.';
        END IF;

        IF abrege_reglement = 'CHQ' AND numero_cheque = '' THEN
            RAISE EXCEPTION USING MESSAGE = 'Le numéro de chèque doit être précisé.';
        END IF;

        reference_compensation := '';
    END IF;

    IF reversement_compensation THEN
        IF reference_compensation = '' THEN
            RAISE EXCEPTION USING MESSAGE = 'La référence de la compensation doit être précisée.';
        END IF;
        numero_cheque := '';
        id_banque := NULL;
    END IF;

    -- Mise à jour du reversement
    UPDATE StdReversementCompagnie
    SET NumeroCheque = numero_cheque, CompteCompensation = reference_compensation, NomTireurCheque = nom_emetteur,
		IdBanque = id_banque, IdModeReversement = id_mode_reversement, Valide = True, DateValidation = CURRENT_TIMESTAMP,
		IdUtilisateurValidation = id_utilisateur, DateReversement = date_reversement
    WHERE IdReversement = id_reversement;
	
    IF id_reversement <> 0 THEN
        out_message := 'Reversement enregistré avec succès.';
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        -- Renvoie un message métier et laisse l’exception à l’appelant (ou supprime RAISE pour un retour “soft”)
        out_message := SQLERRM;
        RAISE;
END;
$$;

ALTER PROCEDURE public.sp_validation_reversement OWNER TO uranususer;
