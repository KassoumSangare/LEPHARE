

CREATE OR REPLACE FUNCTION public.set_numero_facture_before_insert()
    RETURNS TRIGGER
    LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
    v_annee INTEGER;
    v_mois INTEGER;
    v_nouveau_numero INTEGER;
    v_numero_facture VARCHAR;
	v_code_intermediaire VARCHAR;
	v_contrat BOOL;
BEGIN
    -- 0. Déterminer la table à partir de laquelle nous sommes appelés
	IF TG_TABLE_SCHEMA = 'public' AND TG_TABLE_NAME = 'stdcontrat' THEN
        v_contrat := true;
    ELSIF TG_TABLE_SCHEMA = 'public' AND TG_TABLE_NAME = 'stddevis' THEN
        v_contrat := false;
	ELSE --Je ne suis pas prêt à accepter qu'on m'appelle d'une autre table
		RETURN NEW;
    END IF;
	
	-- 1. Déterminer l'année et le mois actuels
    v_annee := EXTRACT(YEAR FROM NOW());
    v_mois := EXTRACT(MONTH FROM NOW());

    -- 2. Démarrer la logique critique en Verrouillant la ligne pour le mois/année
    
    -- Tenter d'insérer l'enregistrement de séquence s'il n'existe pas.
    -- Si le mois/année existe, ne rien faire.
    INSERT INTO public.stdsequencefacture (annee, mois, derniernumerodevis, derniernumerocontrat)
    VALUES (v_annee, v_mois, 0, 0)
    ON CONFLICT (annee, mois) DO NOTHING;

    -- Récupérer et VERROUILLER la ligne de séquence.
    -- La clause FOR UPDATE bloque toute autre transaction jusqu'à la fin de la transaction courante.
	IF v_contrat THEN
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
	IF v_contrat THEN
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
	WHERE idcompagnie = NEW.idcompagnie AND idintermediaire = NEW.idintermediaire;
	v_code_intermediaire := COALESCE(v_code_intermediaire, '0000');

    -- 6. Construire le numéro de facture final 
	-- Le devis et le contrat n'ont pas la même nomenclature
    IF v_contrat THEN -- (Nomenclature : Séquence/Code Intermediaire/MM-AAAA)
		NEW.numerofacture := LPAD(v_nouveau_numero::TEXT, 5, '0') || '/' ||
							v_code_intermediaire || '/' ||
                      		TO_CHAR(v_mois, 'FM00') || '-' || v_annee;
	ELSE -- (Nomenclature : Code Intermediaire/MM-AAAA/Séquence)
		NEW.numerofacture := v_code_intermediaire || '/' ||
                      TO_CHAR(v_mois, 'FM00') || '-' ||
                      v_annee || '/' || LPAD(v_nouveau_numero::TEXT, 5, '0');
	END IF;
	
    RETURN NEW;

END;
$BODY$;

ALTER FUNCTION public.set_numero_facture_before_insert()
    OWNER TO uranususer;

