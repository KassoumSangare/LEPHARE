-- Numérotation des bordereaux d'OREOLE, version 2 (demande du 2026-10-21 : catégorie retirée du numéro) :
--   code courtier (4) + mois (2) + exercice (2) + « B » + n° séquentiel (4)
--   ex. 1186 10 26 B 0018 pour le dix-huitième bordereau d'octobre 2026.
-- Encaissements, bordereaux de reversement et de réclamation de commission, récapitulatifs de réclamation et
-- paiements de commissions partagent une même suite par code courtier et par mois (compteur inchangé : les numéros
-- de la version 1, avec catégorie, restent tels quels et la suite continue sans doublon). Code courtier : celui du
-- contrat de la première prime de la pièce, à défaut les 4 premiers caractères de son n° de police. Le compteur est
-- transactionnel (une saisie annulée ne consomme pas de numéro) et sûr en accès simultané (INSERT ... ON CONFLICT).

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

    INSERT INTO public.lephare_numero_bordereau AS n (code_intermediaire, exercice, mois, dernier)
    VALUES (v_courtier, EXTRACT(YEAR FROM v_date)::integer, EXTRACT(MONTH FROM v_date)::integer, 1)
    ON CONFLICT (code_intermediaire, exercice, mois) DO UPDATE SET dernier = n.dernier + 1
    RETURNING n.dernier INTO v_rang;

    RETURN v_courtier || TO_CHAR(v_date, 'MMYY') || 'B'
        || CASE WHEN v_rang > 9999 THEN v_rang::text ELSE LPAD(v_rang::text, 4, '0') END;
END;
$$;
