-- PROCEDURE: public.sp_enregistrement_reversement(integer, integer, integer[], numeric[], integer, date, integer, numeric, character varying, character varying, character varying, character varying, integer, character varying)

-- DROP PROCEDURE IF EXISTS public.sp_enregistrement_reversement(integer, integer, integer[], numeric[], integer, date, integer, numeric, character varying, character varying, character varying, character varying, integer, character varying);

CREATE OR REPLACE PROCEDURE public.sp_enregistrement_reversement(
    IN id_utilisateur integer,
    IN id_compagnie integer,
    IN liste_encaissement integer[],
    IN liste_montant numeric[],
    IN id_mode_reversement integer DEFAULT NULL::integer,
    IN date_reversement date DEFAULT CURRENT_DATE,
    IN id_banque integer DEFAULT 1,
    IN montant_total numeric DEFAULT '-1'::integer,
    IN numero_cheque character varying DEFAULT ''::character varying,
    IN nom_emetteur character varying DEFAULT ''::character varying,
    IN reference_reversement character varying DEFAULT ''::character varying,
    IN reference_compensation character varying DEFAULT ''::character varying,
    INOUT id_reversement integer DEFAULT 0,
    INOUT out_message character varying DEFAULT ''::character varying)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
    montant_total_calcule    numeric := 0;
    numero_reversement       varchar;
    code_intermediaire       varchar(4);
    libelle_banque           varchar(50);
    encaissement_trop_reverse text := '';
    n_soumis                 integer := 0;
    n_reel                   integer := 0;
BEGIN
    -- Normalisation
    out_message            := '';
    id_reversement         := 0;
    id_banque              := COALESCE(id_banque, 0);
    montant_total          := COALESCE(montant_total, 0);
    numero_cheque          := TRIM(COALESCE(numero_cheque, ''));
    reference_reversement  := TRIM(COALESCE(reference_reversement, ''));
    reference_compensation := TRIM(COALESCE(reference_compensation, ''));
    nom_emetteur           := TRIM(COALESCE(nom_emetteur, ''));
	date_reversement       := COALESCE(date_reversement, CURRENT_DATE);

    -- Vérification du montant à reverser
    IF montant_total <= 0 THEN
        RAISE EXCEPTION USING MESSAGE = 'Montant du reversement incorrect.';
    END IF;

    -- Vérification des listes
    IF liste_encaissement IS NULL OR array_length(liste_encaissement, 1) = 0 THEN
        RAISE EXCEPTION USING MESSAGE = 'Aucun encaissement soumis.';
    END IF;
    IF array_length(liste_encaissement, 1) <> array_length(liste_montant, 1) THEN
        RAISE EXCEPTION USING MESSAGE = 'Incohérence: nombre d''encaissements différent du nombre de montants.';
    END IF;

    -- Calcul et validations sur les montants
    SELECT SUM(m) INTO montant_total_calcule
    FROM UNNEST(liste_montant) AS m;

    montant_total_calcule := COALESCE(montant_total_calcule, 0);
    IF montant_total_calcule <> montant_total THEN
        RAISE EXCEPTION USING MESSAGE = 'Incohérence: la somme des montants ne correspond pas au montant total.';
    END IF;

    -- Montants positifs
    IF EXISTS (
        SELECT 1
        FROM UNNEST(liste_montant) AS m
        WHERE m < 0
    ) THEN
        RAISE EXCEPTION USING MESSAGE = 'Un montant de reversement ne peut pas être négatif.';
    END IF;

    -- Vérifier existence et sur-reversement
    -- Aligner id et montant via WITH ORDINALITY (en sous-requête inline)
    SELECT COUNT(*)
    INTO n_soumis
    FROM (
        SELECT id_enc, mt
        FROM UNNEST(liste_encaissement, liste_montant) WITH ORDINALITY AS u(id_enc, mt, ord)
    ) AS p;

    SELECT COUNT(p.id_enc)
    INTO n_reel
    FROM (
        SELECT id_enc, mt
        FROM UNNEST(liste_encaissement, liste_montant) WITH ORDINALITY AS u(id_enc, mt, ord)
    ) AS p
    JOIN StdDetailEncaissement sde ON sde.IdDetailEncaissement = p.id_enc;

    IF n_reel <> n_soumis THEN
        RAISE EXCEPTION USING MESSAGE = 'Incohérence: certains encaissements n''existent pas.';
    END IF;

    -- Encaissements trop reversés
    SELECT STRING_AGG(p.id_enc::text, ';')
    INTO encaissement_trop_reverse
    FROM (
        SELECT id_enc, mt
        FROM UNNEST(liste_encaissement, liste_montant) WITH ORDINALITY AS u(id_enc, mt, ord)
    ) AS p
    JOIN StdDetailEncaissement sde ON sde.IdDetailEncaissement = p.id_enc
    WHERE (COALESCE(sde.Montant_Encaissement, 0) - COALESCE(sde.MontantReglement, 0) - p.mt) < 0;

    IF COALESCE(encaissement_trop_reverse, '') <> '' THEN
        RAISE EXCEPTION USING MESSAGE = 'Encaissements trop reversés:' || E'\n' || encaissement_trop_reverse;
    END IF;

    -- Récup code intermédiaire (en se basant sur la première quittance par date)
    SELECT TRIM(COALESCE(SI.CodeIntermediaire, '0'))
    INTO code_intermediaire
    FROM UNNEST(liste_encaissement) AS id_enc
    JOIN StdDetailEncaissement AS SDE ON SDE.IdDetailEncaissement = id_enc
    JOIN StdQuittance AS SQ ON SQ.NumeroQuittance = SDE.NumeroQuittance
    JOIN StdIntermediaireCompagnie AS SI
         ON SQ.IdIntermediaire = SI.IdIntermediaire AND SI.IdCompagnie = id_compagnie
    ORDER BY SQ.DateEmission
    LIMIT 1;

    -- Génération du numéro
    CALL sp_generation_numero_reversement(code_intermediaire, date_reversement, numero_reversement);

    -- Insertion du reversement
    INSERT INTO StdReversementCompagnie(
        NumeroReversement, DateReversement, MontantReversement, MontantEnAttente, MontantDeduit,
        NumeroCheque, CompteCompensation, DateSaisie, PieceAnnulee, DateAnnulation, NomAnnulation,
        MotifAnnulation, DateSaisieAnnulation, NomTireurCheque, IdBanque, IdCompagnie,
        IdModeReversement, IdUtilisateur, Valide
    )
    VALUES (
        numero_reversement, date_reversement, montant_total, 0, 0,
        numero_cheque, reference_compensation, CURRENT_TIMESTAMP, False, NULL, '',
        '', NULL, nom_emetteur, id_banque, id_compagnie,
        id_mode_reversement, id_utilisateur, False
    )
    RETURNING IdReversement INTO id_reversement;

    -- Appliquer les reversements (remplacement du WITH pairs par sous-requête inline)
    UPDATE StdDetailEncaissement sde
    SET MontantReglement = COALESCE(sde.MontantReglement, 0) + p.mt
    FROM (
        SELECT id_enc, mt
        FROM UNNEST(liste_encaissement, liste_montant) WITH ORDINALITY AS u(id_enc, mt, ord)
    ) AS p
    WHERE sde.IdDetailEncaissement = p.id_enc;

    UPDATE StdQuittance sq
    SET Mt_Regle = COALESCE(sq.Mt_Regle, 0) + p.mt,
        Reglee   = CASE WHEN (COALESCE(sq.Mt_Regle, 0) + p.mt) = COALESCE(sq.Mt_Encaisse, 0) THEN True ELSE False END
    FROM StdDetailEncaissement sde
    JOIN (
        SELECT id_enc, SUM(mt) AS mt
        FROM UNNEST(liste_encaissement, liste_montant) WITH ORDINALITY AS u(id_enc, mt, ord)
        GROUP BY id_enc
    ) p ON p.id_enc = sde.IdDetailEncaissement
    WHERE sq.NumeroQuittance = sde.NumeroQuittance;

    INSERT INTO StdDetailReversement(
        soldeinitial, montantreverse, dedcommission_intermediaire, dedcommission_gestionnaire,
        dedcommission_coassurance, dedaccessoireintermediaire, dedaccessoiregestionnaire,
        dedtaxecommission, dedtaxeaccessoire, comintermediaire, comgestionnaire, comconseiller,
        comcoassurance, accintermediaire, accgestionnaire, dedcoassurance, primecedee,
        taxe_commission_deduit, taxeaccessoire_deduit, iddetailencaissement, idreversement
    )
    SELECT sde.soldeinitial, p.mt AS montantreverse, sde.dedcommission_intermediaire, sde.dedcommission_gestionnaire,
           sde.dedcommission_coassurance, sde.dedaccessoireintermediaire, sde.dedaccessoiregestionnaire,
           sde.dedtaxecommission, sde.dedtaxeaccessoire, sde.comintermediaire, sde.comgestionnaire, sde.comconseiller,
           sde.comcoassurance, sde.accintermediaire, sde.accgestionnaire, sde.dedcoassurance, sde.primecedee,
           sde.taxe_commission_deduit, sde.taxeaccessoire_deduit, sde.IdDetailEncaissement, id_reversement
    FROM StdDetailEncaissement sde
    JOIN (
        SELECT id_enc, mt
        FROM UNNEST(liste_encaissement, liste_montant) WITH ORDINALITY AS u(id_enc, mt, ord)
    ) p ON p.id_enc = sde.IdDetailEncaissement;

    IF id_reversement <> 0 THEN
        out_message := 'Reversement enregistré avec succès.';
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        -- Renvoie un message métier et laisse l’exception à l’appelant (ou supprime RAISE pour un retour “soft”)
        id_reversement := 0;
        out_message := SQLERRM;
        RAISE;
END;
$BODY$;

ALTER PROCEDURE public.sp_enregistrement_reversement(integer, integer, integer[], numeric[], integer, date, integer, numeric, character varying, character varying, character varying, character varying, integer, character varying)
    OWNER TO uranususer;
