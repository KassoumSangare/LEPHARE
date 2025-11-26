-- PROCEDURE: public.sp_avenant_creation_devis_initial(integer, integer, integer, date, date, date, character varying, integer, character varying)

-- DROP PROCEDURE IF EXISTS public.sp_avenant_creation_devis_initial(integer, integer, integer, date, date, date, character varying, integer, character varying);

CREATE OR REPLACE PROCEDURE public.sp_avenant_creation_devis_initial(
	IN user_id integer,
	IN id_contrat integer,
	IN id_avenant integer,
	IN date_emission date,
	IN date_effet date,
	IN date_expiration date,
	IN motif_annulation character varying,
	INOUT id_devis integer,
	INOUT out_message character varying)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
	numero_avenant varchar(8);
	cle_avenant int;
	numero_devis varchar(16);
	code_categorie char(3);
	local_message varchar(250);
	duree_contrat int;
	periode_contrat char(1);
	id_contrat_base int;
	id_devis_base int;
	id_devis_ancien int;
	id_avenant_ancien int;
	date_expiration_ancienne date;
	date_effet_ancienne date;
	code_avenant char(3);
	id_intermediaire integer;
	id_tarif integer;
	id_duree integer;
	id_histo integer; --id du devis actuel
	id_old_hist integer; --contrat de base pour le contrat courant (ou encore contrat précédent)
	numero_police character varying (50);
	contrat_flotte boolean;
	id_produit integer;
    id_compagnie integer;
	matricule_enregistre character varying;
	var_contrat_detail RECORD;
	var_devis_detail RECORD;
	id_devis_detail integer;
	id_devis_detail_ancien integer;
	id_contrat_ancien integer;
	id_contrat_detail_ancien integer;
	v_prime_imposee bool;
	
	----Gestion des erreurs
	v_state   TEXT;
    v_msg     TEXT;
    v_detail  TEXT;
    v_hint    TEXT;
    v_context TEXT;
	
BEGIN
	
        id_devis := 0;
        out_message := '';

		SELECT codeavenant
		INTO code_avenant
		FROM public.stdavenant
		WHERE idavenant = id_avenant;
		

		IF code_avenant IN ('ANL', 'ANP') THEN

			IF UPPER(TRIM(COALESCE(motif_annulation, ''))) IN ('', 'RAS', 'R.A.S') THEN
				out_message := 'Motif d''annulation non indiqué!';
				RAISE EXCEPTION '%', out_message;
			END IF;

			SELECT iddevis
			INTO id_old_hist
			FROM public.stdcontrat  
			WHERE idcontrat = id_contrat;
			IF id_old_hist IS NULL THEN
				out_message := 'Erreur sur les données. Ce contrat ne correspond à aucun devis!';
				RAISE EXCEPTION '%', out_message;
			END IF; 
		ELSE
			SELECT numeropolice
			INTO numero_police
			FROM public.stdcontrat
			WHERE idcontrat = id_contrat;

			SELECT iddevis
			INTO id_old_hist
			FROM public.stdcontrat AS SC
			JOIN public.stdavenant AS SA ON (SC.idavenant = SA.idavenant)
			WHERE numeropolice = numero_police
				AND SA.codeavenant IN ('AFN', 'REN', 'RPP', 'TRP')
				AND COALESCE(idcontratannulation, 0)=0
			ORDER BY dateeffet DESC
			LIMIT 1;
			IF COALESCE(id_old_hist, 0) = 0 THEN
				out_message := 'Mauvaise configuration logicielle détectée lors de la création du devis pour cet avenant!.';
				RAISE EXCEPTION '%', out_message;
			END IF;
		END IF;

		SELECT IdProduit, Flotte, DateEffet, DateExpiration, IdDevis, IdAvenant, IdIntermediaire, IdCompagnie, NumeroPolice
		INTO id_produit, contrat_flotte, date_effet_ancienne, date_expiration_ancienne, id_devis_ancien, id_avenant_ancien, id_intermediaire, id_compagnie, numero_police
		FROM public.stdcontrat
		WHERE iddevis = id_old_hist;
		
		IF date_effet_ancienne - date_effet > 0 THEN
			out_message := 'Mauvais choix de date d''effet.';
			RAISE EXCEPTION '%', out_message;
		END IF;
		
		SELECT IdTarif
		INTO id_tarif
		FROM StdDevisDetail
		WHERE IdDevis = id_devis_ancien
		ORDER BY IdDevisDetail
		LIMIT 1;
		
		SELECT CodeCategorie
		INTO code_categorie
		FROM StdTarif
		WHERE IdTarif = id_tarif;
		
		-- IF (code_avenant = 'ANL') THEN
		-- 	date_expiration := date_expiration_ancienne; 	
		-- ELSE
		-- 	date_expiration := date_effet + (date_expiration_ancienne - date_effet_ancienne)::integer * INTERVAL '1 day';
		-- END IF;
		
		duree_contrat := date_expiration - date_effet + 1;
		periode_contrat := fn_calcul_periode_contrat(duree_contrat);
		id_duree := fn_calcul_id_duree_contrat(date_effet, date_expiration);

	 	CALL sp_numeroter_avenant(id_avenant, id_intermediaire, cle_avenant, numero_avenant);
		
		CALL sp_generer_numero_devis (id_intermediaire, id_compagnie, code_categorie, numero_devis, local_message);

		INSERT INTO public.stddevis(flotte, coassurance, numerodevis, referenceagent, renouvelable, echeance, periode, numeroavenant, dateeffet, heuredebut, dateexpiration, confirme, dateemission, transfere, nbreche, anticipation, observation, idoldhist, oldnumerodevis, auteur, primeannuelle, primenette, accessoire, taxe, primettc, idoperateur, bonus_malus, idenergie, idassure, accessoirecompagnie, accessoiregestionnaire, accessoireintermediaire, commissionaperiteur, commissiongestionnaire, commissionintermediaire, idaperiteur, idavenant, idclient, idcompagnie, idintermediaire, idoffre, idproduit, nomassure, fga, idduree, idterme, idpolicepegas, numeropolicecompagnie, primeimposee)
		SELECT flotte, coassurance, numero_devis, referenceagent, renouvelable, echeance, periode_contrat, numero_avenant, date_effet, heuredebut, date_expiration, False AS confirme, CURRENT_DATE, transfere, nbreche, anticipation, observation, id_old_hist, numerodevis, auteur, primeannuelle, primenette, accessoire, taxe, primettc, user_id, bonus_malus, idenergie, idassure, accessoirecompagnie, accessoiregestionnaire, accessoireintermediaire, commissionaperiteur, commissiongestionnaire, commissionintermediaire, idaperiteur, id_avenant, idclient, idcompagnie, idintermediaire, idoffre, idproduit, nomassure, CASE WHEN id_produit = 1 THEN fga ELSE 0 END AS fga, id_duree, idterme, idpolicepegas, numeropolicecompagnie, primeimposee
		FROM public.stddevis
		WHERE iddevis = id_devis_ancien
		RETURNING iddevis INTO id_devis;

		UPDATE public.stddevis
		SET idhisto = id_devis
		WHERE iddevis = id_devis;

		IF (code_avenant IN ('ANL', 'ANP')) THEN

			UPDATE public.stddevis
			SET primeannuelle = -primeannuelle, primenette = -primenette, accessoire = -accessoire, taxe = -taxe, primettc = -primettc, accessoirecompagnie = -accessoirecompagnie, accessoiregestionnaire = -accessoiregestionnaire, accessoireintermediaire = -accessoireintermediaire, commissionaperiteur = -commissionaperiteur, commissiongestionnaire = -commissiongestionnaire, commissionintermediaire = -commissionintermediaire, fga = CASE WHEN id_produit = 1 THEN -fga ELSE 0 END, motifannulation= motif_annulation
			WHERE iddevis = id_devis;

			FOR var_devis_detail IN (SELECT iddevisdetail FROM StdDevisDetail WHERE iddevis=id_devis_ancien)
			LOOP
				id_devis_detail_ancien := var_devis_detail.iddevisdetail;
				INSERT INTO public.stddevisdetail(iddevis, idtarif, vehicule, codeusage, reference, idcarrosserie, puissancefiscale, nombreplace, chargeutile, valeurneuve, valeurvenale, valeuraccessoire, remorque, matrem1, matrem2, extincteur, idprofession, conducteur, adressecnd, villecnd, sexe, datemec, datemutation, nummoteur, numchassis, nbreextinteur, typevehicule, idmarque, matricule, typeimmat, attestation, provisoire, permis, datedelipc, datenaicnd, iddelegation, agrement, villeagrement, observation, idoldhist, oldpolice, oldattestation, oldmarque, oldtype, oldmatricule, carteverte, numcarteverte, primeannuelle, primenette, mt_delegation, essence, attestationprov, cg_control, numpccnd, pctype, idoffre, taxeenregistrement, pc_control, idgenrevehicule, idtypevehicule, modelevehicule, idusage, codealarme, auteur, fga, tauxreduction)
				SELECT id_devis, idtarif, vehicule, codeusage, reference, idcarrosserie, puissancefiscale, nombreplace, chargeutile, valeurneuve, valeurvenale, valeuraccessoire, remorque, matrem1, matrem2, extincteur, idprofession, conducteur, adressecnd, villecnd, sexe, datemec, datemutation, nummoteur, numchassis, nbreextinteur, typevehicule, idmarque, matricule, typeimmat, attestation, provisoire, permis, datedelipc, datenaicnd, iddelegation, agrement, villeagrement, observation, id_devis_ancien, numero_police, attestation, idmarque, oldtype, matricule, carteverte, numcarteverte, -primeannuelle, -primenette, mt_delegation, essence, attestationprov, cg_control, numpccnd, pctype, idoffre, -taxeenregistrement, pc_control, idgenrevehicule, idtypevehicule, modelevehicule, idusage, codealarme, auteur, CASE WHEN id_produit = 1 THEN -fga ELSE 0 END as fga, tauxreduction
				FROM public.stddevisdetail
				WHERE IdDevis = id_devis_ancien AND IdDevisDetail = id_devis_detail_ancien
				RETURNING IdDevisDetail INTO id_devis_detail;
				
			
				INSERT INTO public.stddevisdetgarantie(iddevisdet, idgarantie, acquise, capital, franchise, formule, primenette, old_acquise, old_capital, old_franchise, old_formule, old_places, old_primenette, deces, ipp, fraismed, hosp, minfranchise, maxfranchise, primeannuelle, taxe, textefranchise)
				SELECT id_devis_detail, idgarantie, acquise, capital, franchise, formule, -primenette, CASE WHEN acquise THEN '1' ELSE '0' END, capital, franchise, formule, old_places, primenette, deces, ipp, fraismed, hosp, minfranchise, maxfranchise, -primeannuelle, -taxe, textefranchise
				FROM public.stddevisdetgarantie
				WHERE IdDevisDet = id_devis_detail_ancien;

			END LOOP;

		ELSIF (code_avenant IN ('REN', 'INC')) THEN
			SELECT COALESCE(primeimposee, False)
			INTO v_prime_imposee
			FROM public.stddevis
			WHERE iddevis = id_devis;
			v_prime_imposee := COALESCE(v_prime_imposee, False);
			IF NOT v_prime_imposee THEN
				UPDATE public.stddevis
				SET primeannuelle = 0, primenette = 0, accessoire = 0, taxe = 0, primettc = 0, accessoirecompagnie = 0, accessoiregestionnaire = 0, accessoireintermediaire = 0, commissionaperiteur = 0, commissiongestionnaire = 0, commissionintermediaire = 0, fga = 0
				WHERE iddevis = id_devis;
			END IF;

			IF (code_avenant = 'REN') THEN
				FOR var_contrat_detail IN (SELECT idcontrat, idcontratdetail, matricule FROM fn_liste_objets_assures(numero_police))
				LOOP
					id_contrat_detail_ancien := var_contrat_detail.idcontratdetail;
					id_contrat_ancien := var_contrat_detail.idcontrat;
					matricule_enregistre := var_contrat_detail.matricule;

					SELECT iddevis INTO id_devis_ancien
					FROM public.stdcontrat
					WHERE idcontrat = id_contrat_ancien;

					SELECT iddevisdetail INTO id_devis_detail_ancien
					FROM public.stddevisdetail AS SDD
					INNER JOIN public.stddevis AS SD ON (SDD.iddevis = SD.iddevis)
					WHERE SD.iddevis = id_devis_ancien AND TRIM(SDD.matricule) = matricule_enregistre;

					INSERT INTO public.stddevisdetail(iddevis, idtarif, vehicule, codeusage, reference, idcarrosserie, puissancefiscale, nombreplace, chargeutile, valeurneuve, valeurvenale, valeuraccessoire, remorque, matrem1, matrem2, extincteur, idprofession, conducteur, adressecnd, villecnd, sexe, datemec, datemutation, nummoteur, numchassis, nbreextinteur, typevehicule, idmarque, matricule, typeimmat, attestation, provisoire, permis, datedelipc, datenaicnd, iddelegation, agrement, villeagrement, observation, idoldhist, oldpolice, oldattestation, oldmarque, oldtype, oldmatricule, carteverte, numcarteverte, primeannuelle, primenette, mt_delegation, essence, attestationprov, cg_control, numpccnd, pctype, idoffre, taxeenregistrement, pc_control, idgenrevehicule, idtypevehicule, modelevehicule, idusage, codealarme, auteur, fga, tauxreduction)
					SELECT id_devis, idtarif, vehicule, codeusage, reference, idcarrosserie, puissancefiscale, nombreplace, chargeutile, valeurneuve, valeurvenale, valeuraccessoire, remorque, matrem1, matrem2, extincteur, idprofession, conducteur, adressecnd, villecnd, sexe, datemec, datemutation, nummoteur, numchassis, nbreextinteur, typevehicule, idmarque, matricule, typeimmat, '' AS attestation, provisoire, permis, datedelipc, datenaicnd, iddelegation, agrement, villeagrement, observation, id_devis_ancien, numero_police, attestation, idmarque, oldtype, matricule, carteverte, '' AS numcarteverte, primeannuelle, primenette, mt_delegation, essence, attestationprov, cg_control, numpccnd, pctype, idoffre, taxeenregistrement, pc_control, idgenrevehicule, idtypevehicule, modelevehicule, idusage, codealarme, auteur, CASE WHEN id_produit = 1 THEN fga ELSE 0 END as fga, tauxreduction
					FROM public.stddevisdetail
					WHERE IdDevis = id_devis_ancien AND IdDevisDetail = id_devis_detail_ancien
					RETURNING IdDevisDetail INTO id_devis_detail;

					IF id_produit = 1 THEN --Production Automobile
						INSERT INTO StdComplementDevisDetailAuto(bns, carburantautrematiere, transporteleves, transportemployes, transportpassagersupplementaire, iddevisdetail, idformulesecuriteroutiere, idoptionassistance)
						SELECT bns, carburantautrematiere, transporteleves, transportemployes, transportpassagersupplementaire, id_devis_detail, idformulesecuriteroutiere, idoptionassistance
						FROM StdComplementDevisDetailAuto
						WHERE iddevisdetail = id_devis_detail_ancien;
					END IF;

					IF id_produit = 3 THEN --Production Voyage
						INSERT INTO StdComplementDevisDetailVoyage(IdDevisDetail, NumeroAttestation, NumeroPasseport, IdPaysDestination, IdPaysVoyageur, ReferenceContrat, VisaSchengen)
						SELECT id_devis_detail, NumeroAttestation, NumeroPasseport, IdPaysDestination, IdPaysVoyageur, ReferenceContrat, VisaSchengen
						FROM StdComplementDevisDetailVoyage
						WHERE IdDevisDetail = id_devis_detail_ancien;	
					END IF;

					IF id_produit = 5 THEN --Production Santé
						INSERT INTO StdComplementDevisDetailSante(PrimeFamille, PrimeAffilie, PrimeGlobale, MontantSurprime, MontantAccessoireManuel, TauxReductionCommerciale, IdTypeContrat, GestionnaireSante, IdContratDetail)
						SELECT PrimeFamille, PrimeAffilie, PrimeGlobale, MontantSurprime, MontantAccessoireManuel, TauxReductionCommerciale, IdTypeContrat, GestionnaireSante, id_contrat_detail
						FROM StdComplementDevisDetailSante
						WHERE IdDevisDetail = id_devis_detail_ancien;
					END IF;

					IF id_produit = 8 THEN --Production RC
						INSERT INTO StdComplementDevisDetailRC(TauxPrime, AssiettePrime, NombreParticipants, IdDomaineActivite, IdActivite, Localisation, DateDebut, IdContratDetail)
						SELECT TauxPrime, AssiettePrime, NombreParticipants, IdDomaineActivite, IdActivite, Localisation, DateDebut, id_contrat_detail
						FROM StdComplementDevisDetailRC
						WHERE IdDevisDetail = id_devis_detail_ancien;
					END IF;

					IF id_produit = 9 THEN --Production Dommages (TRI, Globale de banque)
						INSERT INTO StdComplementDevisDetailDommage(TauxPrime, MontantPrime, IdDevisDetail)
						SELECT TauxPrime, MontantPrime, id_devis_detail
						FROM StdComplementDevisDetailDommage
						WHERE IdDevisDetail = id_devis_detail_ancien;
					END IF;

					INSERT INTO public.stddevisdetgarantie(iddevisdet, idgarantie, acquise, capital, franchise, formule, primenette, old_acquise, old_capital, old_franchise, old_formule, old_places, old_primenette, deces, ipp, fraismed, hosp, minfranchise, maxfranchise, primeannuelle, taxe, textefranchise)
					SELECT id_devis_detail, idgarantie, acquise, capital, franchise, formule, primenette, CASE WHEN acquise THEN '1' ELSE '0' END, capital, franchise, formule, old_places, primenette, deces, ipp, fraismed, hosp, minfranchise, maxfranchise, primeannuelle, taxe, textefranchise
					FROM public.stddevisdetgarantie
					WHERE IdDevisDet = id_devis_detail_ancien;

				END LOOP;

			END IF;

		END IF;
		
		IF id_devis <> 0 THEN
			out_message := 'Devis initialisé avec succès.';
		END IF;
		EXCEPTION WHEN others THEN
			get stacked diagnostics
        		v_state   = returned_sqlstate,
        		v_msg     = message_text,
        		v_detail  = pg_exception_detail,
        		v_hint    = pg_exception_hint,
        		v_context = pg_exception_context;

			id_devis := 0;
			out_message := v_msg; -- || ' : ' || v_context; -- 'Problème rencontré lors de l'annulation du contrat;
    		/* RAISE EXCEPTION E'Got exception:
        	state  : %
        	message: %
        	detail : %
        	hint   : %
        	context: %
        	SQLSTATE: % 
        	SQLERRM: %', v_state, v_msg, v_detail, v_hint, v_context, SQLSTATE, SQLERRM;
			*/
			RAISE EXCEPTION '%', out_message;

END; 
$BODY$;
ALTER PROCEDURE public.sp_avenant_creation_devis_initial(integer, integer, integer, date, date, date, character varying, integer, character varying)
    OWNER TO uranususer;

