CREATE OR REPLACE PROCEDURE public.sp_saisie_affilie_sante(IN nom_affilie character varying, IN prenom_affilie character varying, IN date_naissance date, IN sexe_affilie character, IN mobile1_affilie character varying, IN mobile2_affilie character varying, IN cni_affilie character varying, IN lien_affilie character, IN date_effet date, IN certificat_joint boolean, IN matricule_affilie character varying, IN observations_ character varying, IN affilie_handicape boolean, IN debut_consommation date, IN surprime_appliquee boolean, IN montant_surprime numeric, IN nombre_pathologie integer, IN numero_cmu character varying, IN groupe_sanguin character varying, IN user_id integer, INOUT id_affilie integer, INOUT adherent integer, INOUT devis integer, INOUT out_message character varying)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
	initial_id_affilie integer;
	age_affilie integer;
	date_controle date;
	nombre_affilie integer; --Pour contrôler le nombre de personnes dans chaque famille dans le cas des polices MINENE
	id_offre integer;
	----Gestion des erreurs
	v_state   TEXT;
    v_msg     TEXT;
    v_detail  TEXT;
    v_hint    TEXT;
    v_context TEXT;
	
BEGIN
	
	id_affilie := COALESCE(id_affilie,0);
	devis := COALESCE(devis,0);
	nombre_pathologie := COALESCE(nombre_pathologie, 0);
	numero_cmu := TRIM(COALESCE(numero_cmu,''));
	mobile1_affilie := COALESCE(mobile1_affilie, '');
	mobile2_affilie := COALESCE(mobile2_affilie, '');
	initial_id_affilie := id_affilie;
	age_affilie := EXTRACT('year' FROM AGE(CURRENT_DATE, date_naissance));
	matricule_affilie := TRIM(COALESCE(matricule_affilie,''));
	nom_affilie := TRIM(COALESCE(nom_affilie,''));
	prenom_affilie := TRIM(COALESCE(prenom_affilie,''));
	out_message := '';
	id_offre := 0;
	
	IF UPPER(numero_cmu) IN ('NA', 'N/A', 'N-A') THEN
		numero_cmu := '';
	END IF;
	
	IF devis = 0 THEN
		out_message := 'Le numéro n''a pas été initialisé.';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	IF devis <> 0 AND NOT EXISTS (SELECT * FROM StdNumeroSaisieSante
								  WHERE IdOperateur=user_id AND SaisieEnCours AND IdDevis=devis) THEN
		out_message := 'Saisie non initialisée pour cet utilisateur.';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	
	IF (adherent = 0) OR NOT EXISTS(SELECT * FROM StdAdherent WHERE idadherent = adherent and iddevis=devis) THEN
		out_message := 'Adhérent inexistant.';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	IF nom_affilie = '' THEN
		out_message := 'Nom de l''affilie non renseigné.';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	age_affilie := EXTRACT('year' FROM AGE(CURRENT_DATE, date_naissance));
   	IF lien_affilie = 'E' AND age_affilie > 25 THEN
		out_message := 'Enfant de plus de 25 ans rejeté.';
		RAISE EXCEPTION '%', out_message;
	ELSIF lien_affilie ='E' AND age_affilie >= 21 AND NOT certificat_joint THEN
		out_message := 'Certificat de scolarité non fourni. Enfant rejeté.';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	IF groupe_sanguin NOT IN ('O-','O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+', 'NA', 'N/A', 'N-A', 'NS', '') THEN
		out_message := 'Groupe sanguin incorrect!';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	IF nombre_pathologie < 0 OR nombre_pathologie > 3 THEN
		out_message = 'Le nombre de pathologies doit être compris entre 0 et 3 compris.';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	--IF matricule_affilie = '' THEN
	--	out_message := 'Matricule obligatoire pour l''affilié!';
	--	RAISE EXCEPTION '%', out_message;
	--END IF;
	
	IF numero_cmu <> '' AND EXISTS (SELECT * FROM StdAffilie WHERE NumeroCmu = numero_cmu AND IdAffilie <> id_affilie) THEN
		out_message := 'Numéro CMU déjà enregistré pour un autre affilié!';
		RAISE EXCEPTION '%', out_message;	
	END IF;
	
-- 	IF nombre_pathologie < 0 THEN
-- 		out_message := 'Nombre de pathologies erroné!';
-- 		RAISE EXCEPTION '%', out_message;
-- 	END IF;
	
	SELECT COUNT(IdAffilie)
	INTO nombre_affilie
	FROM StdAffilie
	WHERE IdDevis = devis AND IdAdherent = adherent AND IdOperateur = user_id;
	nombre_affilie := COALESCE(nombre_affilie, 0) + CASE WHEN id_affilie = 0 THEN 1 ELSE 0 END; --Augmenter le nombre d'affiliés d'une unité si l'enregistrement en cours concerne un nouvel affilié
	--Vérifier le nombre maximal d'affiliés n'est pas dépassé
	SELECT SF.IdOffreSante
	INTO id_offre
	FROM StdAdherent AS SA 
	INNER JOIN StdFiliale AS SF ON (SA.IdFiliale = SF.IdFiliale AND SA.IdDevis=SF.IdDevis)
	WHERE SA.IdDevis = devis AND IdAdherent = adherent AND SA.IdOperateur = user_id;
	id_offre := COALESCE(id_offre, 0);
	
	IF id_offre = 0 THEN
		out_message := 'Aucune offre choisie pour cette famille!';
		RAISE EXCEPTION '%', out_message;	
	END IF;
	
	IF (id_offre IN (17, 20) AND nombre_affilie > 1) OR (id_offre IN (18, 21) AND nombre_affilie > 3) OR (id_offre IN (19, 22) AND nombre_affilie > 6) THEN--OFFRES SOLO
		out_message := 'Nombre maximum de personnes dépassé!';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	IF groupe_sanguin IN ('NA', 'N/A', 'N-A', '') THEN
		groupe_sanguin := 'NS';
	END IF;
	
	IF id_offre IN (17, 18, 19, 20, 21, 22) THEN
		IF lien_affilie IN ('A', 'C') AND age_affilie >= 70 THEN
			out_message := 'Âge limite dépassé. Assuré rejeté.';
			RAISE EXCEPTION '%', out_message;	
		END IF;
	END IF;
	
   	IF id_affilie = 0 THEN
		IF lien_affilie = 'A' THEN
			IF EXISTS (SELECT * FROM StdAffilie WHERE idadherent = adherent AND iddevis = devis AND idoperateur = user_id AND lien = 'A') THEN
				out_message := 'Adhérent déjà saisi en tant qu''affilié.';
				RAISE EXCEPTION '%',out_message;
			END IF;
		END IF;
		IF lien_affilie = 'E' AND age_affilie >= 21 AND certificat_joint THEN
			date_controle := CURRENT_DATE;
		END IF;
		INSERT INTO stdaffilie(groupesanguin, lien, nom, prenom, nombrepathologie, numerocmu, cni, datenaissance, mobile1, mobile2, dateadhesion, datesortie, certificat, datectrl, matricule, carte_vigueur, ancien_matricule, date_dernier_demande, observations, handicape, sexe, actif, primeannuelle, datemaj, iddevis, datedebutconsommation, surprimeappliquee, montantsurprime, idadherent, idoperateur)
		VALUES (groupe_sanguin, lien_affilie, nom_affilie, prenom_affilie, nombre_pathologie, numero_cmu, cni_affilie, date_naissance, mobile1_affilie, mobile2_affilie, date_effet, NULL, certificat_joint, date_controle, matricule_affilie, False, '', NULL, observations_, affilie_handicape, sexe_affilie, True, 0, CURRENT_TIMESTAMP, devis, debut_consommation, surprime_appliquee, montant_surprime, adherent, user_id)
		RETURNING idaffilie INTO id_affilie;
		
	ELSE
		IF EXISTS (SELECT * FROM StdAffilie WHERE idadherent = adherent AND iddevis = devis AND idoperateur = user_id AND lien ='A' AND idaffilie <> id_affilie) THEN
			out_message := 'Un autre affilié est déjà adhérent dans cette famille.';
			RAISE EXCEPTION '%', out_message;
		END IF;
		UPDATE stdaffilie
		SET groupesanguin = groupe_sanguin, lien = lien_affilie, nom = nom_affilie, prenom = prenom_affilie, cni = cni_affilie, datenaissance = date_naissance, dateadhesion = date_effet, certificat = certificat_joint,
		    datectrl = date_controle, matricule = matricule_affilie, observations = observations_, handicape = affilie_handicape, sexe = sexe_affilie, datemaj = CURRENT_TIMESTAMP,
			iddevis = devis, datedebutconsommation = debut_consommation, idadherent = adherent, surprimeappliquee = surprime_appliquee, montantsurprime = montant_surprime,
			mobile1 = mobile1_affilie, mobile2 = mobile2_affilie, nombrepathologie = nombre_pathologie, numerocmu = numero_cmu
		WHERE idaffilie = id_affilie;
	END IF;
   	
	IF (initial_id_affilie = 0) AND (id_affilie <>0) THEN
		out_message := 'Affilié enregistré avec succès.';
	ELSE
		out_message := 'Mise à jour d''affilié réussie.';
	END IF;
	
	EXCEPTION WHEN others THEN
	
		get stacked diagnostics
        	v_state   = returned_sqlstate,
        	v_msg     = message_text,
        	v_detail  = pg_exception_detail,
        	v_hint    = pg_exception_hint,
        	v_context = pg_exception_context;
			
		out_message := v_msg; -- || ' : ' || v_context; -- 'Problème rencontré lors de l''enregistrement de l'affilié;
		
    	RAISE EXCEPTION E'%
        	state  : %
        	detail : %
        	hint   : %
        	context: %
        	SQLSTATE: % 
        	SQLERRM: %', v_msg, v_state, v_detail, v_hint, v_context, SQLSTATE, SQLERRM;

END; 
$procedure$
