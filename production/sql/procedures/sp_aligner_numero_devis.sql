-- Numéro de devis OREOLE : code courtier (4) + code catégorie (3) + année (2) + 'D' + n° séquentiel + clé.
-- Les procédures de création ne numérotent qu'à la création : un devis modifié vers une autre compagnie
-- (autre code courtier) ou une autre catégorie de tarif gardait son ancien numéro. Cette procédure lui
-- attribue alors un nouveau numéro par sp_generer_numero_devis. Le numéro de police, lui, n'est attribué
-- qu'à la confirmation (sp_confirmation_devis).
CREATE OR REPLACE PROCEDURE public.sp_aligner_numero_devis(IN p_iddevis integer)
LANGUAGE plpgsql
AS $procedure$
DECLARE
	v_idintermediaire integer;
	v_idcompagnie integer;
	v_numero varchar(50);
	v_confirme boolean;
	v_archive boolean;
	v_code_courtier varchar(10);
	v_categorie_numero varchar(3);
	v_categorie_cible varchar(3);
	v_nouveau_numero varchar(16) := '';
	v_message varchar(500) := '';
BEGIN
	SELECT idintermediaire, idcompagnie, TRIM(COALESCE(numerodevis, '')), COALESCE(confirme, false), COALESCE(archive, false)
	INTO v_idintermediaire, v_idcompagnie, v_numero, v_confirme, v_archive
	FROM public.stddevis
	WHERE iddevis = p_iddevis;

	-- Devis supprimé, déjà en contrat, archivé, pas encore numéroté (brouillon Santé) ou hors format
	IF NOT FOUND OR v_confirme OR v_archive OR v_numero !~ '^[0-9]{9}D' THEN
		RETURN;
	END IF;

	-- Même mise en forme que sp_generer_numero_devis
	SELECT LPAD(RIGHT(TRIM(COALESCE(codeintermediaire, '0')), 4), 4, '0')
	INTO v_code_courtier
	FROM public.stdintermediairecompagnie
	WHERE idintermediaire = v_idintermediaire AND idcompagnie = v_idcompagnie;

	IF v_code_courtier IS NULL THEN
		RETURN;
	END IF;

	v_categorie_numero := SUBSTRING(v_numero, 5, 3);

	-- Catégorie conservée si une ligne du devis la porte (flotte : catégorie du premier véhicule),
	-- sinon catégorie de la première ligne ; sans ligne catégorisée, celle du numéro est gardée.
	IF EXISTS (SELECT 1
			   FROM public.stddevisdetail AS SDD
			   INNER JOIN public.stdtarif AS ST ON (ST.idtarif = SDD.idtarif)
			   WHERE SDD.iddevis = p_iddevis
				 AND LPAD(RIGHT(TRIM(COALESCE(ST.codecategorie, '0')), 3), 3, '0') = v_categorie_numero
				 AND v_categorie_numero <> '000') THEN
		v_categorie_cible := v_categorie_numero;
	ELSE
		SELECT LPAD(RIGHT(TRIM(ST.codecategorie), 3), 3, '0')
		INTO v_categorie_cible
		FROM public.stddevisdetail AS SDD
		INNER JOIN public.stdtarif AS ST ON (ST.idtarif = SDD.idtarif)
		WHERE SDD.iddevis = p_iddevis
		  AND LPAD(RIGHT(TRIM(COALESCE(ST.codecategorie, '0')), 3), 3, '0') <> '000'
		ORDER BY SDD.iddevisdetail
		LIMIT 1;

		v_categorie_cible := COALESCE(v_categorie_cible, v_categorie_numero);
	END IF;

	IF LEFT(v_numero, 4) = v_code_courtier AND v_categorie_cible = v_categorie_numero THEN
		RETURN;
	END IF;

	CALL public.sp_generer_numero_devis(v_idintermediaire, v_idcompagnie, v_categorie_cible, v_nouveau_numero, v_message);

	IF TRIM(COALESCE(v_nouveau_numero, '')) = '' THEN
		RAISE EXCEPTION 'Renumérotation du devis % impossible : %', p_iddevis, v_message;
	END IF;

	UPDATE public.stddevis
	SET numerodevis = v_nouveau_numero
	WHERE iddevis = p_iddevis;
END;
$procedure$;

CREATE OR REPLACE FUNCTION public.trg_fn_aligner_numero_devis()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
	IF TG_OP = 'DELETE' THEN
		CALL public.sp_aligner_numero_devis(OLD.iddevis);
	ELSE
		CALL public.sp_aligner_numero_devis(NEW.iddevis);
	END IF;
	RETURN NULL;
END;
$function$;
