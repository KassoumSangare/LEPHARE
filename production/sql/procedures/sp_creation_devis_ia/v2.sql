CREATE OR REPLACE PROCEDURE public.sp_creation_devis(IN id_intermediaire integer, IN id_compagnie integer, IN id_produit integer, IN id_offre integer, IN id_avenant integer, IN id_client integer, IN id_assure integer, IN flotte_auto boolean, IN en_coassurance boolean, IN date_effet date, IN date_expiration date, IN date_emission date, IN id_tarif integer, IN code_usage integer, IN id_carroserie integer, IN code_carburant integer, IN puissance integer, IN nombre_place integer, IN charge integer, IN valeur_neuve numeric, IN valeur_venale numeric, IN valeur_accessoire numeric, IN taux_reduction numeric, IN code_alarme integer, IN bns numeric, IN nom_conducteur character varying, IN adresse_conducteur character varying, IN date_mec date, IN num_moteur character varying, IN num_chassis character varying, IN id_type_vehicule integer, IN id_marque integer, IN numero_immmatriculation character varying, IN numero_permis_conduire character varying, IN id_genre_vehicule integer, IN numero_carte_brune_physique character varying, IN modele_vehicule character varying, IN remorque_attelee boolean, IN libelle_formule_securite_routiere character varying, IN id_option_assistance integer, IN carburant_autre_matiere boolean, IN transport_eleves boolean, IN transport_employes boolean, IN transport_passager_supplementaire boolean, IN nsia_auto_plus boolean, IN numero_police_compagnie character varying, IN id_duree integer, IN id_terme integer, INOUT id_devis integer, INOUT id_devis_detail integer, INOUT out_message character varying)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
	numero_avenant varchar(8);
	cle_avenant int;
	numero_devis varchar(16);
	code_categorie char(3);
	local_message varchar(250);
	duree_contrat int;
	periode_contrat char(1);
	id_devis_initial int;
	code_avenant char(3);
	flotte_auto_ancien boolean;
	id_old_hist int;
	date_expiration_ancienne date;
	
	----Gestion des erreurs
	v_state   TEXT;
    v_msg     TEXT;
    v_detail  TEXT;
    v_hint    TEXT;
    v_context TEXT;
	age_vehicule INTEGER;
	
BEGIN
   
		id_devis := COALESCE(id_devis,0);
		id_devis_initial := id_devis;
		id_devis_detail := COALESCE(id_devis_detail,0);
		out_message := '';
		
		id_intermediaire := COALESCE(id_intermediaire,0);
		id_compagnie := COALESCE(id_compagnie,1);
		id_produit := COALESCE(id_produit,0);
		id_offre := COALESCE(id_offre,0);
		id_client := COALESCE(id_client,0);
		id_assure := COALESCE(id_assure,0);
		id_avenant := COALESCE(id_avenant,0);
		flotte_auto := COALESCE(flotte_auto,False);
		en_coassurance := COALESCE(en_coassurance, False);
		id_carroserie := COALESCE(id_carroserie,0);
		code_carburant := COALESCE(code_carburant,0);
		code_usage := COALESCE(code_usage,0);
		code_alarme := COALESCE(code_alarme,0);
		id_genre_vehicule := COALESCE(id_genre_vehicule,0);
		id_type_vehicule := COALESCE(id_type_vehicule,0);
		carburant_autre_matiere := COALESCE(carburant_autre_matiere, False);
		transport_eleves := COALESCE(transport_eleves, False);
		transport_employes := COALESCE(transport_employes, False);
		transport_passager_supplementaire := COALESCE(transport_passager_supplementaire, False);
		numero_carte_brune_physique := COALESCE(numero_carte_brune_physique,'');
		id_duree := COALESCE(id_duree, 0);
		id_terme := COALESCE(id_terme, 1);
		id_option_assistance := COALESCE(id_option_assistance, 0);
		nsia_auto_plus := COALESCE(nsia_auto_plus, False);

		IF numero_police_compagnie IS NOT NULL THEN
			numero_police_compagnie := NULLIF(TRIM(numero_police_compagnie),'');
		END IF;
		
		IF id_duree = 0 THEN
			id_duree := fn_calcul_id_duree_contrat(date_effet, date_expiration);
		ELSIF NOT public.fn_valide_id_duree_contrat(id_duree, date_effet, date_expiration) THEN
		  	date_expiration := public.fn_ajuster_date_expiration(id_duree, date_effet, date_expiration);
			IF date_expiration IS NULL THEN
				out_message := 'Incohérence entre période de couverture et durée du contrat!';
				RAISE EXCEPTION '%', out_message;
			END IF;
		END IF;
		
		SELECT codeavenant
		INTO code_avenant  
		FROM public.stdavenant
		WHERE idavenant = id_avenant;
		IF code_avenant IS NULL THEN
			out_message := 'Erreur logicielle: avenant mal ou non paramétré!';
			RAISE EXCEPTION '%', out_message;
		END IF;

		duree_contrat := date_expiration - date_effet;
		periode_contrat := fn_calcul_periode_contrat(duree_contrat);

		IF (id_devis = 0) THEN
	 		CALL sp_numeroter_avenant(id_avenant, id_intermediaire, cle_avenant, numero_avenant);
	 	END IF;
		
		SELECT codecategorie INTO code_categorie
		FROM public.stdtarif
		WHERE idtarif = id_tarif;

		--- Les offres EBENE PREMIUM PROMENADE & AFFAIRES et EBENE PREMIUM TPC (202) de la NSIA ne sont valables que pour les véhicules dont
		--- l'âge est inférieur ou égal à 5 ans 
		IF id_compagnie = 1 AND id_offre IN (93, 99) THEN
			age_vehicule := EXTRACT ('year' FROM AGE(CURRENT_DATE, date_mec))::integer;
			-- IF (age_vehicule <= 4) OR (age_vehicule >= 11) THEN
			-- 	out_message := 'L''âge du véhicule n''est pas compatible avec l''offre choisie!';
			-- 	RAISE EXCEPTION '%', out_message;
			-- END IF;
			IF (age_vehicule > 5) THEN
				out_message := 'L''âge du véhicule n''est pas compatible avec l''offre choisie!';
				RAISE EXCEPTION '%', out_message;
			END IF;
		END IF;
		
		IF (id_devis = 0) THEN

			IF (code_avenant NOT IN ('AFN', 'RPP', 'TRP')) THEN
				out_message := 'Erreur logicielle: création de nouveau devis impossible pour cet avenant!';
				RAISE EXCEPTION '%', out_message;
			END IF;
			CALL sp_generer_numero_devis (id_intermediaire, id_compagnie, code_categorie, numero_devis, local_message);

			INSERT INTO public.stddevis (idintermediaire, idcompagnie, idproduit, idoffre, idclient, idassure, idavenant, numeroavenant, numerodevis, flotte, idaperiteur, coassurance,
									periode, dateemission, dateeffet, dateexpiration, confirme, accessoirecompagnie, idduree, idterme, numeropolicecompagnie)
			VALUES (id_intermediaire, id_compagnie, id_produit, id_offre, id_client, id_assure, id_avenant, numero_avenant, numero_devis, flotte_auto, id_compagnie, en_coassurance,
					periode_contrat, date_emission, date_effet, date_expiration, False, 0, id_duree, id_terme, numero_police_compagnie)
			RETURNING iddevis INTO id_devis;
		ELSE
			IF EXISTS (SELECT * FROM public.stddevis WHERE iddevis = id_devis AND confirme) THEN
				out_message = 'Devis déjà confirmé. Impossible de faire une modification!';
				RAISE EXCEPTION '%', out_message;
			END IF;

			IF (code_avenant = 'INC') THEN

				IF NOT flotte_auto THEN
					out_message := 'Erreur logicielle: ce devis doit être une flotte!';
					RAISE EXCEPTION '%', out_message;	
				END IF;

				SELECT idoldhist
				INTO id_old_hist
				FROM public.stddevis
				WHERE iddevis = id_devis;

				IF id_old_hist IS NULL THEN
					out_message := 'Erreur logicielle: devis mal initialisé!';
					RAISE EXCEPTION '%', out_message;
				END IF;

				SELECT flotte, dateexpiration
				INTO flotte_auto_ancien, date_expiration_ancienne
				FROM public.stddevis
				WHERE iddevis = id_old_hist;

				IF NOT flotte_auto_ancien THEN
					out_message := 'Impossible de faire une incorporation dans une police mono!';
					RAISE EXCEPTION '%', out_message;
				END IF;

				IF date_expiration != date_expiration_ancienne THEN --L'incorporation et l'avenant de base doivent expirer à la même date
					out_message := 'Date d''expiration incorrecte!';
					RAISE EXCEPTION '%', out_message;
				END IF;  

			END IF;
			
			IF (code_avenant IN ('AFN', 'RPP')) THEN
				UPDATE public.stddevis AS SD
				SET idintermediaire = id_intermediaire, idcompagnie = id_compagnie, idproduit = id_produit, idoffre = id_offre, idclient = id_client, idassure = id_assure, flotte = flotte_auto, idaperiteur = id_compagnie, coassurance = en_coassurance, periode = periode_contrat, dateemission = date_emission,
					dateeffet = date_effet, dateexpiration = date_expiration, confirme = False, accessoirecompagnie = 0, idduree = id_duree, idterme = id_terme, numeropolicecompagnie = numero_police_compagnie
				WHERE iddevis = id_devis AND NOT confirme;	
			ELSE
				UPDATE public.stddevis AS SD
				SET idcompagnie = CASE WHEN code_avenant = 'TRP' THEN id_compagnie ELSE idcompagnie END, idoffre = id_offre, idassure = id_assure, flotte = flotte_auto, coassurance = en_coassurance, periode = periode_contrat, dateemission = date_emission,
					dateeffet = date_effet, dateexpiration = date_expiration, confirme = False, accessoirecompagnie = 0, idduree = id_duree, idterme = id_terme,
					numeropolicecompagnie = CASE WHEN TRIM(COALESCE(numeropolicecompagnie,'')) = '' THEN numero_police_compagnie ELSE numeropolicecompagnie END
				WHERE iddevis = id_devis AND NOT confirme;
			END IF;

		END IF;
			
		CALL sp_enregistrement_vehicule(id_compagnie, id_produit, id_offre, date_effet, date_expiration, date_emission, id_tarif, code_usage, id_carroserie, code_carburant,
										puissance, nombre_place, charge, valeur_neuve, valeur_venale, valeur_accessoire, taux_reduction, code_alarme, bns, nom_conducteur,
										adresse_conducteur, date_mec, num_moteur, num_chassis, id_type_vehicule, id_marque, numero_immmatriculation, numero_permis_conduire,
										id_genre_vehicule, numero_carte_brune_physique, modele_vehicule, remorque_attelee, libelle_formule_securite_routiere, id_option_assistance, carburant_autre_matiere,
										transport_eleves, transport_employes, transport_passager_supplementaire, nsia_auto_plus, id_devis, id_devis_detail, out_message);
										
        IF NOT flotte_auto THEN
			CALL sp_finalisation_devis(id_devis, id_client, id_assure, flotte_auto, out_message);
		END IF;
		
		EXCEPTION WHEN others THEN
			get stacked diagnostics
        		v_state   = returned_sqlstate,
        		v_msg     = message_text,
        		v_detail  = pg_exception_detail,
        		v_hint    = pg_exception_hint,
        		v_context = pg_exception_context;
			IF id_devis_initial = 0 THEN
				id_devis := 0;
			END IF;
			out_message := v_msg || ' : ' || v_context; -- 'Problème rencontré lors de la création du devis';
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
$procedure$
