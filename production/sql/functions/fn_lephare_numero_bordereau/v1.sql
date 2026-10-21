-- Numérotation des bordereaux d'OREOLE (demande du 2026-10-20), calquée sur celle des polices :
--   code courtier (4) + catégorie de la CP (3) + mois (2) + exercice (2) + « B » + n° séquentiel (4)
--   ex. 1186 201 10 26 B 0001 pour le premier bordereau d'octobre 2026 d'une prime Automobile 201.
-- Encaissements, bordereaux de reversement et de réclamation de commission, récapitulatifs de réclamation et
-- paiements de commissions partagent une même suite par code courtier et par mois : elle repart à 1 chaque mois et
-- deux pièces ne portent jamais le même numéro. Code courtier et catégorie : ceux du contrat de la première prime
-- de la pièce (positions 1-4 et 5-7 de son n° de police). Le compteur est transactionnel (une saisie annulée ne
-- consomme pas de numéro) et sûr en accès simultané (verrou de ligne de l'INSERT ... ON CONFLICT).

CREATE TABLE IF NOT EXISTS public.lephare_numero_bordereau (
    code_intermediaire character varying(4) NOT NULL,
    exercice integer NOT NULL,
    mois integer NOT NULL,
    dernier integer NOT NULL DEFAULT 0,
    CONSTRAINT lephare_numero_bordereau_pk PRIMARY KEY (code_intermediaire, exercice, mois)
);

CREATE OR REPLACE FUNCTION public.fn_lephare_numero_bordereau(p_numero_quittance character varying, p_date date)
RETURNS character varying
LANGUAGE plpgsql
AS $$
DECLARE
    v_courtier character varying;
    v_police character varying;
    v_categorie character varying;
    v_date date := COALESCE(p_date, CURRENT_DATE);
    v_rang integer;
BEGIN
    SELECT TRIM(COALESCE(si.codeintermediaire, '')), COALESCE(NULLIF(TRIM(c.numeropolice), ''), TRIM(q.numeropolice))
    INTO v_courtier, v_police
    FROM stdquittance q
    LEFT JOIN LATERAL (SELECT ct.idintermediaire, ct.idcompagnie, ct.numeropolice FROM stdcontrat ct
                       WHERE ct.idquittance = q.idquittance ORDER BY ct.idcontrat LIMIT 1) c ON TRUE
    LEFT JOIN stdintermediairecompagnie si ON si.idintermediaire = c.idintermediaire AND si.idcompagnie = c.idcompagnie
    WHERE q.numeroquittance = p_numero_quittance
    LIMIT 1;

    -- Code courtier sur 4 caractères, comme sp_generer_numero_police ; à défaut, celui du n° de police
    IF COALESCE(v_courtier, '') = '' THEN
        v_courtier := SUBSTRING(COALESCE(v_police, '') FROM 1 FOR 4);
    END IF;
    v_courtier := COALESCE(NULLIF(v_courtier, ''), '0');
    v_courtier := CASE WHEN LENGTH(v_courtier) > 4 THEN RIGHT(v_courtier, 4) ELSE LPAD(v_courtier, 4, '0') END;

    -- Catégorie de la CP : positions 5 à 7 du n° de police (courtier + catégorie + année + n° + clé)
    v_categorie := SUBSTRING(COALESCE(v_police, '') FROM 5 FOR 3);
    IF v_categorie IS NULL OR v_categorie !~ '^[0-9]{3}$' THEN
        v_categorie := '000';
    END IF;

    INSERT INTO public.lephare_numero_bordereau AS n (code_intermediaire, exercice, mois, dernier)
    VALUES (v_courtier, EXTRACT(YEAR FROM v_date)::integer, EXTRACT(MONTH FROM v_date)::integer, 1)
    ON CONFLICT (code_intermediaire, exercice, mois) DO UPDATE SET dernier = n.dernier + 1
    RETURNING n.dernier INTO v_rang;

    RETURN v_courtier || v_categorie || TO_CHAR(v_date, 'MMYY') || 'B'
        || CASE WHEN v_rang > 9999 THEN v_rang::text ELSE LPAD(v_rang::text, 4, '0') END;
END;
$$;
