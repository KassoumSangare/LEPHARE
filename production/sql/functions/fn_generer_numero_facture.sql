-- FUNCTION: public.fn_generer_numero_facture(boolean, integer, integer, date)

-- DROP FUNCTION IF EXISTS public.fn_generer_numero_facture(boolean, integer, integer, date);

CREATE OR REPLACE FUNCTION public.fn_generer_numero_facture(
	p_contrat boolean,
	p_id_compagnie integer,
	p_id_intermediaire integer,
	p_date_saisie date DEFAULT CURRENT_DATE)
    RETURNS character varying
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    v_annee INTEGER;
    v_mois INTEGER;
    v_nouveau_numero INTEGER;
    v_numero_facture VARCHAR;
	v_code_intermediaire VARCHAR;
BEGIN
    -- 1. Déterminer l'année et le mois actuels
	p_date_saisie := COALESCE(p_date_saisie, CURRENT_DATE);
    v_annee := EXTRACT(YEAR FROM p_date_saisie);
    v_mois := EXTRACT(MONTH FROM p_date_saisie);

    -- 2. Démarrer la logique critique en Verrouillant la ligne pour le mois/année
    
    -- Tenter d'insérer l'enregistrement de séquence s'il n'existe pas.
    -- Si le mois/année existe, ne rien faire.
    INSERT INTO public.stdsequencefacture (annee, mois, derniernumerodevis, derniernumerocontrat)
    VALUES (v_annee, v_mois, 0, 0)
    ON CONFLICT (annee, mois) DO NOTHING;

    -- Récupérer et VERROUILLER la ligne de séquence.
    -- La clause FOR UPDATE bloque toute autre transaction jusqu'à la fin de la transaction courante.
	IF p_contrat THEN
		    SELECT derniernumerocontrat
		    INTO v_nouveau_numero
		    FROM public.stdsequencefacture
		    WHERE annee = v_annee
		      AND mois = v_mois
		    FOR UPDATE; -- Verrouillage exclusif sur la ligne (année, mois) !
	ELSE
			SELECT derniernumerodevis
		    INTO v_nouveau_numero
		    FROM public.stdsequencefacture
		    WHERE annee = v_annee
		      AND mois = v_mois
		    FOR UPDATE; 
	END IF;

    -- 3. Incrémenter le numéro séquentiel
    v_nouveau_numero := v_nouveau_numero + 1;

    -- 4. Mettre à jour la table de séquence avec le nouveau numéro
	IF p_contrat THEN
	    UPDATE public.stdsequencefacture
	    SET derniernumerocontrat = v_nouveau_numero
	    WHERE annee = v_annee
	      AND mois = v_mois;
	ELSE
		UPDATE public.stdsequencefacture
	    SET derniernumerodevis = v_nouveau_numero
	    WHERE annee = v_annee
	      AND mois = v_mois;
	END IF;
	
	-- 5. Obtenir le code intermédiaire chez la compagnie
	SELECT codeintermediaire INTO v_code_intermediaire
	FROM public.stdintermediairecompagnie
	WHERE idcompagnie = p_id_compagnie AND idintermediaire = p_id_intermediaire;
	v_code_intermediaire := COALESCE(v_code_intermediaire, '0000');

    -- 6. Construire le numéro de facture final 
	-- Le devis et le contrat n'ont pas la même nomenclature
    IF p_contrat THEN -- (Nomenclature : Séquence/Code Intermediaire/MM-AAAA)
		v_numero_facture := LPAD(v_nouveau_numero::TEXT, 5, '0') || '/' ||
							v_code_intermediaire || '/' ||
                      		TO_CHAR(v_mois, 'FM00') || '-' || v_annee;
	ELSE -- (Nomenclature : Code Intermediaire/MM-AAAA/Séquence)
		v_numero_facture := v_code_intermediaire || '/' ||
                      TO_CHAR(v_mois, 'FM00') || '-' ||
                      v_annee || '/' || LPAD(v_nouveau_numero::TEXT, 5, '0');
	END IF;
	
    RETURN v_numero_facture;

END;
$BODY$;

ALTER FUNCTION public.fn_generer_numero_facture(boolean, integer, integer, date)
    OWNER TO uranususer;

