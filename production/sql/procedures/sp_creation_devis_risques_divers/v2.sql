CREATE OR REPLACE PROCEDURE public.sp_creation_devis_risques_divers(IN id_intermediaire integer, IN id_compagnie integer, IN id_produit integer, IN id_offre integer, IN id_avenant integer, IN id_client integer, IN id_assure integer, IN flotte_rc boolean, IN en_coassurance boolean, IN date_effet date, IN date_expiration date, IN date_emission date, IN id_tarif integer, IN assiette_prime numeric, IN id_domaine_activite integer, IN activite character varying, IN localisation_assure character varying, IN date_debut date, IN nombre_participants integer, IN taux_prime numeric, IN taux_reduction numeric, IN capital_dommage_corporel numeric, IN capital_intoxication_alimentaire numeric, IN capital_dommage_materiel numeric, IN id_duree integer, IN numero_telephone_assure character varying, IN adresse_geographique character varying, IN numero_police_connexe character varying, IN numero_police_compagnie character varying, IN user_id integer, IN p_prime_nette numeric, IN p_accessoire numeric, IN p_taxe numeric, IN p_prime_ttc numeric, IN p_liste_garantie jsonb, INOUT id_devis integer, INOUT out_message character varying)
 LANGUAGE plpgsql
AS $procedure$
DECLARE

	etat_traitement character varying(1); numero_avenant character varying(8); clef_avenant integer; numero_devis character varying(16);
	code_categorie character varying(3); local_message character varying(500); id_devis_detail integer;
	periode_contrat character varying(1); prime_nette numeric; taux_commission numeric;
	nom_conducteur character varying(80); adresse_conducteur character varying(60); code_alarme integer; bns numeric; date_mec date;
	num_moteur character varying(20); num_chassis character varying(20); type_vehicule varchar(50); id_marque integer;
	matricule_assure character varying(20); essence integer; num_permis_conduire character varying(30); code_usage character varying(3); id_usage integer;
	id_carrosserie integer; code_carburant integer; puissance integer; nombre_place integer; charge_utile integer; age integer;
	prime_deces numeric; prime_ipp numeric; prime_frais_traitement numeric; prime_rec RECORD;
	id_devis_initial integer;
	--Pour le calcul des taxes relatives aux accessoires
	v_accessoire_compagnie numeric;
	v_accessoire_intermediaire numeric;
	v_taxe_accessoire numeric;
	v_taxe_garanties numeric;
	v_prime_imposee bool;
	v_res_repartir_prime bool;
	v_taxe_calculee numeric;
	v_accessoire_calcule numeric;
	v_id_activite integer;
	v_nombre_adherents_minene int; --Pour un devis MINENE, le nombre d'adhérents dans la police Santé MINENE
	v_id_devis_minene int; 

	----Gestion des erreurs
	v_state TEXT; v_msg TEXT; v_detail TEXT; v_hint TEXT; v_context TEXT;

BEGIN

	CREATE TEMPORARY TABLE IF NOT EXISTS temp_gar(idgarantie integer, libellegarantie character varying(60), idsousgarantie integer,
					libellesousgarantie character varying(60), acquise boolean, capital numeric, primeannuelle numeric,
					primenette numeric, tauxfranchise numeric, franchiseminimum numeric, franchisemaximum numeric, montantfranchise numeric, franchisetexte character varying);
	DELETE FROM temp_gar;
	
	id_intermediaire := COALESCE(id_intermediaire,0);
	id_compagnie := COALESCE(id_compagnie,1);
	id_produit := COALESCE(id_produit,0);
	id_client := COALESCE(id_client,0);
	id_assure := COALESCE(id_assure,0);
	id_avenant := COALESCE(id_avenant,0);
	flotte_rc := COALESCE(flotte_rc,False);
	en_coassurance := COALESCE(en_coassurance,False);
	id_duree :=  COALESCE(id_duree, 0);
	id_devis :=  COALESCE(id_devis, 0);
	numero_telephone_assure :=  TRIM(COALESCE(numero_telephone_assure, ''));
	id_devis_initial := id_devis;
	id_duree := COALESCE(id_duree, 1);
	p_prime_nette := COALESCE(p_prime_nette, 0);
	p_accessoire := COALESCE(p_accessoire, 0);
	p_taxe := COALESCE(p_taxe, 0);
	p_prime_ttc := COALESCE(p_prime_ttc, 0);
	adresse_geographique := TRIM(COALESCE(adresse_geographique, ''));
	numero_police_connexe := TRIM(COALESCE(numero_police_connexe, ''));
	v_id_activite := 0;
	v_nombre_adherents_minene := 0;
	v_id_devis_minene := 0;
	activite := LEFT(activite, 50);
	IF numero_police_compagnie IS NOT NULL THEN
		numero_police_compagnie := NULLIF(TRIM(numero_police_compagnie),'');
	END IF;

	IF COALESCE(p_prime_nette, 0) = 0 OR id_offre = 67 THEN
		v_prime_imposee := false;
	ELSE
		v_prime_imposee := true;
	END IF;

	IF id_offre = 67 AND numero_police_connexe = '' THEN
		out_message := 'Le numéro de police MINENE n''a pas été renseigné!';
		RAISE EXCEPTION '%', out_message;
	END IF;

	IF id_offre = 67 AND NOT EXISTS (SELECT 1 FROM StdContrat WHERE IdProduit = 5 AND NumeroPolice = numero_police_connexe) THEN
		out_message := 'Le numéro de police MINENE n''existe pas!';
		RAISE EXCEPTION '%', out_message;
	END IF;

	IF id_devis <> 0 AND NOT EXISTS (SELECT 1 FROM StdDevis WHERE IdDevis = id_devis AND IdProduit = id_produit) THEN
		out_message := 'Devis RC inexistant!';
		RAISE EXCEPTION '%', out_message;
	END IF;

	IF id_offre = 67 THEN
		UPDATE StdClient
		SET Adresse2 = adresse_geographique
		WHERE IdClient = id_assure;
	END IF;
	
	IF id_duree = 1 THEN
		id_duree := fn_calcul_id_duree_contrat(date_expiration - date_effet);
	END IF;
	
	id_carrosserie := 0; code_carburant := 0; id_marque := 0; code_usage := '000'; id_usage := 0; code_alarme := 0; num_permis_conduire := '';
	matricule_assure := ''; nom_conducteur := ''; adresse_conducteur := ''; bns := 0; date_mec := '1900-01-01'::date; num_moteur := '';
	num_chassis := ''; type_vehicule := ''; matricule_assure := ''; essence := 0; num_permis_conduire := ''; puissance := 0; nombre_place := 0;
	charge_utile := 0;
	
	SELECT EtatTraitement
	INTO etat_traitement
	FROM StdAvenant
	WHERE IdAvenant = id_avenant;
	
	periode_contrat := fn_calcul_periode_contrat(date_expiration - date_effet);
	
	taux_commission := fn_get_taux_commission(id_produit, id_compagnie, date_emission);
	IF id_offre = 67 THEN -- RC CHEF DE FAMILLE MINENE
		-- Police Santé MINENE désignée par le paramètre : à la création, le devis RC n'existe pas encore
		-- (l'ancienne lecture par le devis donnait 0 adhérent, donc des primes à 0)
		SELECT iddevis 
		INTO v_id_devis_minene
		FROM public.stdcontrat
		WHERE idproduit = 5 AND numeropolice = numero_police_connexe
		ORDER BY dateeffet DESC
		LIMIT 1;
		SELECT COUNT(*)
		INTO v_nombre_adherents_minene
		FROM public.stdadherent
		WHERE iddevis = v_id_devis_minene;
		v_nombre_adherents_minene := GREATEST(COALESCE(v_nombre_adherents_minene, 0), 1);
	END IF;
	
	SELECT CodeCategorie
	INTO code_categorie
	FROM StdTarif
	WHERE IdTarif = id_tarif;
	
	IF (id_devis = 0) THEN
		CALL sp_numeroter_avenant(id_avenant, id_intermediaire, clef_avenant, numero_avenant);

		CALL sp_generer_numero_devis(id_intermediaire, id_compagnie, code_categorie, numero_devis, local_message);

		INSERT INTO StdDevis (IdOperateur, IdOffre, IdIntermediaire, IdCompagnie, IdProduit, IdClient, IdAssure, IdAvenant, NumeroAvenant, NumeroDevis, Flotte,
					IdAperiteur, Coassurance, Periode, DateEmission, DateEffet, DateExpiration, Confirme, AccessoireCompagnie, IdDuree, NumeroPoliceConnexe, PrimeImposee)
		VALUES (user_id, id_offre, id_intermediaire, id_compagnie, id_produit, id_client, id_assure, id_avenant, numero_avenant, numero_devis, flotte_rc, id_compagnie, 
			en_coassurance, periode_contrat, date_emission, date_effet, date_expiration, False, 0, id_duree, numero_police_connexe, v_prime_imposee) RETURNING IdDevis INTO id_devis;

		INSERT INTO StdDevisDetail(IdDevis, IdOffre, IdTarif, Vehicule, idusage, CodeUsage, Reference, IdCarrosserie, PuissanceFiscale, NombrePlace,
					ChargeUtile, ValeurNeuve, ValeurVenale, ValeurAccessoire, REMORQUE, Conducteur, AdresseCnd, DateMec,
					DateMutation, NumMoteur, NumChassis, TypeVehicule, IdMarque, Matricule, CarteVerte, Essence, NumPCCnd, TauxReduction, PrimeImposee, Observation)
		VALUES (id_devis, id_offre, id_tarif, 1, id_usage, code_usage, code_usage, id_carrosserie, puissance, nombre_place, charge_utile, capital_dommage_corporel,
			capital_intoxication_alimentaire, capital_dommage_materiel, False, nom_conducteur, adresse_conducteur, date_mec, date_mec, num_moteur, num_chassis,
			type_vehicule, id_marque, matricule_assure, CASE WHEN code_categorie='205' THEN True ELSE False END, code_carburant, num_permis_conduire, taux_reduction, v_prime_imposee, activite)
		RETURNING IdDevisDetail INTO id_devis_detail;

		IF id_produit = 8 THEN
			INSERT INTO StdComplementDevisDetailRC(TauxPrime, AssiettePrime, NombreParticipants, IdDomaineActivite, IdActivite, Localisation, DateDebut, IdDevisDetail)
			VALUES (taux_prime, assiette_prime, nombre_participants, id_domaine_activite, v_id_activite, localisation_assure, date_debut, id_devis_detail);
		END IF;
		
	ELSE
		IF EXISTS (SELECT * FROM StdDevis WHERE IdDevis = id_devis AND Confirme) THEN
			out_message := 'Devis déjà confirmé. Opération impossible!';
			RAISE EXCEPTION '%', out_message;
		END IF;
		SELECT NumeroDevis
		INTO numero_devis
		FROM StdDevis
		WHERE IdDevis = id_devis;
		numero_devis := COALESCE(numero_devis, '');
		UPDATE StdDevis
		SET IdOperateur = user_id, IdOffre = id_offre, IdIntermediaire = id_intermediaire, IdCompagnie = id_compagnie, IdProduit = id_produit, IdClient = id_client, IdAssure = id_assure, IdAvenant = id_avenant, Flotte = flotte_rc,
			IdAperiteur = id_compagnie, Coassurance = en_coassurance, Periode = periode_contrat, DateEmission = date_emission, DateEffet = date_effet, DateExpiration = date_expiration, AccessoireCompagnie = 0, IdDuree = id_duree,
			NumeroPoliceConnexe = numero_police_connexe, PrimeImposee = v_prime_imposee
		WHERE IdDevis = id_devis;
		
		IF EXISTS (SELECT COUNT(IdDevisDetail) FROM StdDevisDetail WHERE IdDevis = id_devis HAVING COUNT(IdDevisDetail) > 1) THEN
			out_message := 'Données incohérentes: détails du devis redondants. Opération impossible!';
			RAISE EXCEPTION '%', out_message;
		END IF;
		SELECT IdDevisDetail
		INTO id_devis_detail
		FROM StdDevisDetail
		WHERE IdDevis = id_devis;
		id_devis_detail := COALESCE(id_devis_detail, 0);
		IF (id_devis_detail <> 0) THEN
			UPDATE StdDevisDetail
			SET IdOffre = id_offre, IdTarif = id_tarif, Vehicule = 1, idusage = id_usage, CodeUsage = code_usage, Reference = code_usage, IdCarrosserie = id_carrosserie, PuissanceFiscale = puissance, NombrePlace = nombre_place,
					ChargeUtile = charge_utile, ValeurNeuve = capital_dommage_corporel, ValeurVenale = capital_intoxication_alimentaire, ValeurAccessoire = capital_dommage_materiel, Remorque = False, Conducteur = nom_conducteur, AdresseCnd = adresse_conducteur, DateMec = date_mec,
					DateMutation = date_mec, NumMoteur = num_moteur, NumChassis = num_chassis, TypeVehicule = type_vehicule, IdMarque = id_marque, Matricule = matricule_assure, CarteVerte = CASE WHEN code_categorie='205' THEN True ELSE False END, Essence = code_carburant,
					NumPCCnd = num_permis_conduire, TauxReduction = taux_reduction, PrimeImposee = v_prime_imposee, Observation = activite
			WHERE IdDevisDetail = id_devis_detail; 

			IF id_produit = 8 THEN
				UPDATE StdComplementDevisDetailRC
				SET TauxPrime = taux_prime, AssiettePrime = assiette_prime, NombreParticipants = nombre_participants,
					IdDomaineActivite = id_domaine_activite, IdActivite = v_id_activite, Localisation = localisation_assure, DateDebut = date_debut
				WHERE IdDevisDetail = id_devis_detail;
			END IF;
		ELSE
			out_message := 'Données incohérentes: détails du devis inexistants. Opération impossible!';
			RAISE EXCEPTION '%', out_message;
		END IF;

	END IF;
	
	IF numero_telephone_assure <> '' THEN
		UPDATE StdClient
		SET Telephone = CASE WHEN TRIM(COALESCE(Telephone,'')) IN ('', 'TELP') THEN numero_telephone_assure ELSE Telephone END,
			Mobile = CASE WHEN TRIM(COALESCE(Mobile,'')) IN ('', 'MOBILE') THEN numero_telephone_assure ELSE Mobile END
		WHERE IdClient = id_assure;
	END IF;

	IF p_liste_garantie IS NULL OR p_liste_garantie = '[]'::jsonb OR id_offre = 67 THEN -- pas de garanties imposées
		DELETE FROM StdDevisDetGarantie WHERE IdDevisDet = id_devis_detail;
		
		INSERT INTO temp_gar(idgarantie, libellegarantie, idsousgarantie, libellesousgarantie, acquise, capital, primeannuelle, primenette, tauxfranchise, franchiseminimum, franchisemaximum, montantfranchise, franchisetexte)
		SELECT idgarantie, libellegarantie, idsousgarantie, libellesousgarantie, acquise, capital, primeannuelle, primenette, tauxfranchise, franchiseminimum, franchisemaximum, montantfranchise, franchisetexte
		FROM fn_garantie_offre_risques_divers(id_compagnie, id_offre, taux_prime, capital_dommage_corporel, capital_intoxication_alimentaire, capital_dommage_materiel, assiette_prime, taux_reduction, date_effet, date_expiration, id_produit, id_devis)
		WHERE idgarantie <> 0
		ORDER BY 1;
	
		INSERT INTO StdDevisDetGarantie(IdDevisDet, IdGarantie, Acquise, taxe, capital, tauxfranchise, minfranchise, maxfranchise, primeannuelle, PrimeNette,
					    old_acquise, old_primenette, Franchise, TexteFranchise)
		SELECT id_devis_detail, TGAR.idsousgarantie, TGAR.acquise, 0 AS taxe, TGAR.capital, TGAR.tauxfranchise, TGAR.franchiseminimum, TGAR.franchisemaximum, TGAR.primeannuelle, TGAR.primenette,
				0, 0, TGAR.montantfranchise, TGAR.franchisetexte
		FROM temp_gar AS TGAR;
	ELSE
		CALL sp_inserer_garanties_devis_rc(id_devis, p_liste_garantie);
	END IF;
		
	UPDATE StdDevisDetGarantie AS DD
	SET Taxe=ROUND((PrimeNette * TT.TauxTaxe)/100, 4)
	FROM StdTauxTaxeGarantieProduit AS TT
	WHERE (DD.IdDevisDet = id_devis_detail) AND (DD.IdGarantie = TT.IdGarantie)
		AND (TT.IdProduit = id_produit) AND (date_effet BETWEEN TT.DebutValidite AND TT.FinValidite);
	
	UPDATE StdDevisDetail AS DD
	SET PrimeAnnuelle = M.PrimeAnnuelle, PrimeNette = M.PrimeNette, TaxeEnregistrement = ROUND(Taxe, 0)
	FROM (SELECT IdDevisDet, SUM(PrimeAnnuelle) AS PrimeAnnuelle, SUM(PrimeNette) AS PrimeNette, SUM(Taxe) AS Taxe
	      FROM StdDevisDetGarantie
	      WHERE IdDevisDet = id_devis_detail
	      GROUP BY IdDevisDet) AS M 
	WHERE (M.IdDevisDet = DD.IdDevisDetail) AND (IdDevisDet = id_devis_detail);

	UPDATE StdDevis AS DD
	SET PrimeAnnuelle = M.PrimeAnnuelle, PrimeNette = M.PrimeNette, Taxe = TaxeEnregistrement,
	    CommissionIntermediaire = ROUND((M.PrimeNette * COALESCE(taux_commission,0))/100,0)
	FROM (SELECT IdDevis, SUM(PrimeAnnuelle) AS PrimeAnnuelle, SUM(PrimeNette) AS PrimeNette, SUM(TaxeEnregistrement) AS TaxeEnregistrement
	      FROM StdDevisDetail
	      WHERE IdDevis = id_devis
	      GROUP BY IdDevis) AS M 
	WHERE (M.IdDevis = DD.IdDevis) AND (DD.IdDevis = id_devis) AND (NumeroDevis = numero_devis);
	
	SELECT PrimeNette
	INTO prime_nette
	FROM StdDevis
	WHERE IdDevis = id_devis;
	prime_nette := COALESCE(prime_nette, 0);
	SELECT * 
	INTO v_accessoire_compagnie, v_accessoire_intermediaire, v_taxe_accessoire
	FROM fn_get_accessoire(prime_nette, id_produit, id_offre, id_compagnie, date_effet);

	UPDATE StdDevis
	SET AccessoireCompagnie = v_accessoire_compagnie, AccessoireIntermediaire = v_accessoire_intermediaire,
		AccessoireGestionnaire = CASE WHEN id_offre = 67 THEN public.fn_get_frais_gestion_minene() ELSE 0 END,
		Accessoire = v_accessoire_compagnie + v_accessoire_intermediaire, taxe = taxe + v_taxe_accessoire
	WHERE IdDevis = id_devis;

	IF v_prime_imposee THEN
		CALL sp_calcul_devis_prime_imposee(id_devis, p_prime_nette, p_accessoire, p_taxe, id_offre);
	END IF;

	IF id_offre = 67 THEN
		-- Commission (23 % de la prime HT, barème OREOLE) sur la prime de tous les adhérents
		UPDATE StdDevis
		SET CommissionIntermediaire = ROUND((primenette * v_nombre_adherents_minene * COALESCE(taux_commission, 0)) / 100, 0),
			primenette = primenette * v_nombre_adherents_minene, accessoirecompagnie = accessoirecompagnie * v_nombre_adherents_minene,
			accessoireintermediaire = accessoireintermediaire * v_nombre_adherents_minene, accessoire = accessoire * v_nombre_adherents_minene, taxe = 2976 * v_nombre_adherents_minene,
			accessoiregestionnaire = accessoiregestionnaire * v_nombre_adherents_minene
		WHERE IdDevis = id_devis;
	END IF; 

	UPDATE StdDevis
	SET primettc = ROUND((primenette+accessoire+taxe+accessoiregestionnaire), 0)
	WHERE iddevis=id_devis;

	IF id_devis <> 0 THEN
			out_message := 'Devis enregistré avec succès.';
	END IF;
	
	DROP TABLE IF EXISTS temp_gar;
		
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
			out_message := v_msg; -- || ' : ' || v_context; -- 'Problème rencontré lors de la création du devis';
			DROP TABLE IF EXISTS temp_gar;
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
