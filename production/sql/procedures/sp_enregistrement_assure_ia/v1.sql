CREATE OR REPLACE PROCEDURE public.sp_enregistrement_assure_ia(IN id_compagnie integer, IN id_produit integer, IN id_offre integer, IN id_assure integer, IN id_profession integer, IN date_effet date, IN date_expiration date, IN id_tarif integer, IN capital_deces numeric, IN capital_ipp numeric, IN frais_traitement numeric, IN taux_reduction numeric, IN code_activite character varying, IN date_naissance date, IN adresse_geographique character varying, IN id_devis integer, IN prime_nette numeric, IN montant_accessoire numeric, IN prime_ttc numeric, INOUT id_devis_detail integer, INOUT out_message character varying)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
	nom_conducteur character varying(80); adresse_conducteur character varying(60); date_mec date;
	num_moteur character varying(20); num_chassis character varying(20); type_vehicule varchar(50); id_marque integer;
	matricule_assure character varying(50); num_permis_conduire character varying(30); code_usage character varying(3); id_usage integer;
	id_carrosserie integer; code_carburant integer; puissance integer; nombre_place integer; charge_utile integer;
    id_old_hist integer;
	/*
	age integer;
	prime_deces numeric; prime_ipp numeric; prime_frais_traitement numeric; prime_rec RECORD;
	*/
	v_id_tarif integer;
	code_categorie character varying(3); 
	id_devis_detail_initial integer;
	v_prime_imposee bool;
	----Gestion des erreurs
	v_state TEXT; v_msg TEXT; v_detail TEXT; v_hint TEXT; v_context TEXT;
	

BEGIN
	CREATE TEMPORARY TABLE IF NOT EXISTS temp_garantie (idsousgarantie integer, libellesousgarantie character varying(60), garcapitalval numeric,
						    garplaceval integer, garfranchiseval numeric, taux numeric, acquise boolean,
						    primeannuelle numeric, primenette numeric);
	
	TRUNCATE TABLE temp_garantie;
	
	id_carrosserie := 0; code_carburant := 0; id_marque := 0; code_usage := '000'; id_usage := 0;
	num_permis_conduire := ''; nom_conducteur := ''; adresse_conducteur := '';
	date_mec := date_naissance; num_moteur := ''; num_chassis := ''; type_vehicule := '';
	num_permis_conduire := ''; puissance := 0; nombre_place := 0; charge_utile := 0;
	matricule_assure := LPAD(CAST(id_assure AS character varying), 20, '0')::character varying;
	id_devis_detail := COALESCE(id_devis_detail, 0);
	id_devis_detail_initial := id_devis_detail;
	adresse_geographique := TRIM(COALESCE(adresse_geographique, ''));
    matricule_assure := TRIM(COALESCE(matricule_assure, ''));
	prime_nette := COALESCE(prime_nette, 0);
	montant_accessoire := COALESCE(montant_accessoire, 0);
	id_old_hist := 0;
	
	-- Déterminer le montant de l'accessoire pour l'IA SPECIFIQUE (PARTICULIER OU GROUPE) car l'accessoire peut être forfaitaire
	IF id_offre IN (173, 174) AND prime_nette <> 0 AND prime_ttc <> 0 THEN
		montant_accessoire := ROUND(prime_ttc / (1 + (public.fn_get_taux_taxe(id_compagnie, id_produit, id_offre, date_effet) / 100)) - prime_nette, 0);
	END IF;
	charge_utile := montant_accessoire; --Enregistrons l'accessoire manuel dans ce champ pour le retourner au front-end en mode Edition

	SELECT primeimposee
	INTO v_prime_imposee
	FROM public.stddevis
	WHERE iddevis = id_devis;
	v_prime_imposee := COALESCE(v_prime_imposee, false);
	
	SELECT idtarif
	INTO v_id_tarif
	FROM public.stdoffre
	WHERE idoffre = id_offre;
	v_id_tarif := COALESCE(v_id_tarif, 0);
	IF v_id_tarif <> id_tarif THEN
		id_tarif := v_id_tarif;
	END IF;
	
	IF id_devis_detail <> 0 THEN
		SELECT idoldhist INTO id_old_hist
		FROM stddevisdetail
		WHERE iddevisdetail =  id_devis_detail;
		id_old_hist := COALESCE(id_old_hist, 0);
	END IF;

	IF id_offre = 66 THEN
		UPDATE StdClient
		SET Adresse2 = adresse_geographique
		WHERE IdClient = id_assure;
	END IF;
	IF id_produit <> 2 THEN
		out_message := 'Erreur logicielle. Cette procédure ne peut être utilisée qu''en IA';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	IF EXTRACT(YEAR FROM AGE(CURRENT_DATE, date_naissance)) = 0 THEN
		out_message := 'Date de naissance incorrecte.';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
	UPDATE StdClient
	SET DateNaissance = date_naissance
	WHERE IdClient = id_assure AND DateNaissance IS NULL;
	
	SELECT CodeCategorie
	INTO code_categorie
	FROM StdTarif
	WHERE IdTarif = id_tarif;
	
	IF (id_devis_detail = 0) THEN

        IF EXISTS (SELECT * FROM public.stddevisdetail WHERE iddevis = id_devis AND matricule = matricule_assure) THEN
			out_message := 'Cet assuré est déjà enregistré dans ce devis!';
			RAISE EXCEPTION '%', out_message;
		END IF;

		INSERT INTO StdDevisDetail(IdDevis, IdOffre, IdTarif, Vehicule, idusage, CodeUsage, Reference, IdCarrosserie, PuissanceFiscale, NombrePlace,
					ChargeUtile, ValeurNeuve, ValeurVenale, ValeurAccessoire, REMORQUE, IdProfession, Conducteur, AdresseCnd, DateMec,
					DateMutation, NumMoteur, NumChassis, TypeVehicule, IdMarque, Matricule, CarteVerte, Essence, NumPCCnd, TauxReduction, PrimeImposee)
		VALUES (id_devis, id_offre, id_tarif, 0, id_usage, code_usage, code_usage, id_carrosserie, puissance, nombre_place, charge_utile, capital_ipp,
			capital_deces, frais_traitement, False, id_profession, nom_conducteur, adresse_conducteur, date_mec, date_mec, num_moteur, num_chassis,
			type_vehicule, id_marque, matricule_assure, CASE WHEN code_categorie='205' THEN True ELSE FAlse END, code_carburant, num_permis_conduire, taux_reduction, v_prime_imposee)
		RETURNING IdDevisDetail INTO id_devis_detail;
	ELSE
		IF EXISTS (SELECT * FROM public.stddevisdetail WHERE iddevis = id_devis AND matricule = matricule_assure AND iddevisdetail <> id_devis_detail) THEN
			out_message := 'Cet assuré est déjà enregistré dans ce devis!';
			RAISE EXCEPTION '%', out_message;
		END IF;
        
        UPDATE StdDevisDetail
		SET IdDevis = id_devis, IdOffre = id_offre, IdTarif = id_tarif, Vehicule = 0, idusage = id_usage, CodeUsage = code_usage, Reference = code_usage,
			IdCarrosserie = id_carrosserie, PuissanceFiscale = puissance, NombrePlace = nombre_place, ChargeUtile = charge_utile, ValeurNeuve = capital_ipp,
			ValeurVenale = capital_deces, ValeurAccessoire = frais_traitement, REMORQUE = False, IdProfession = id_profession, Conducteur = nom_conducteur, AdresseCnd = adresse_conducteur,
			DateMec = date_mec, DateMutation = date_mec, NumMoteur = num_moteur, NumChassis = num_chassis, TypeVehicule = type_vehicule, IdMarque = id_marque,
			Matricule = matricule_assure, CarteVerte = CASE WHEN code_categorie='205' THEN True ELSE FAlse END, Essence = code_carburant, NumPCCnd = num_permis_conduire,
			TauxReduction = taux_reduction, PrimeImposee = v_prime_imposee
		WHERE IdDevisDetail = id_devis_detail;
	END IF;
		
	SELECT codeclasseassure
	INTO code_activite
	FROM StdProfessionIa
	WHERE Id = id_profession;
	
	INSERT INTO temp_garantie(idsousgarantie, libellesousgarantie, garcapitalval, garplaceval, garfranchiseval, acquise, primeannuelle,
				primenette)
	SELECT idsousgarantie, libellesousgarantie, capital, nombreplace, 0 AS franchise, acquise, primeannuelle, primenette
	FROM fn_garantie_offre_ia(id_compagnie, id_offre, capital_deces, capital_ipp, frais_traitement, taux_reduction, date_effet,
				date_expiration, code_activite, date_naissance, prime_nette, montant_accessoire)
	WHERE idgarantie <> 0
	ORDER BY 1;
	
	DELETE FROM StdDevisDetGarantie
	WHERE IdDevisDet = id_devis_detail;
	
	INSERT INTO StdDevisDetGarantie(IdDevisDet, IdGarantie, Acquise, taxe, Capital, minfranchise, maxfranchise, primeannuelle, PrimeNette,
				    old_acquise, old_primenette)
	SELECT id_devis_detail, idsousgarantie, acquise, 0 AS taxe, garcapitalval, 0, 0, primeannuelle, primenette, 0, 0
	FROM temp_garantie;
	
	UPDATE StdDevisDetGarantie AS DD
	SET Taxe=G.Taxe
	FROM (SELECT IdSousGarantie, ROUND((PrimeNette * TT.TauxTaxe)/100,4) AS Taxe
		      FROM temp_garantie AS TP
		      INNER JOIN StdTauxTaxeGarantieProduit AS TT ON(TT.IdGarantie = TP.Idsousgarantie)
		      WHERE (TT.IdProduit = id_produit) AND (date_effet BETWEEN TT.DebutValidite AND TT.FinValidite)
		     ) AS G
	WHERE (G.IdSousGarantie = DD.IdGarantie) AND (DD.IdDevisDet = id_devis_detail);
	
	UPDATE StdDevisDetail AS DD
	SET PrimeAnnuelle = M.PrimeAnnuelle, PrimeNette = M.PrimeNette, TaxeEnregistrement = ROUND(Taxe, 0)
	FROM (SELECT IdDevisDet, SUM(PrimeAnnuelle) AS PrimeAnnuelle, SUM(PrimeNette) AS PrimeNette, SUM(Taxe) AS Taxe
		      FROM StdDevisDetGarantie
		      WHERE IdDevisDet = id_devis_detail
		      GROUP BY IdDevisDet) AS M 
	WHERE (M.IdDevisDet = DD.IdDevisDetail) AND (IdDevisDet = id_devis_detail);
	
	DROP TABLE IF EXISTS temp_garantie;
	
	out_message := 'Assuré enregistré avec succès.';
	
	EXCEPTION WHEN others THEN
			get stacked diagnostics
        		v_state   = returned_sqlstate,
        		v_msg     = message_text,
        		v_detail  = pg_exception_detail,
        		v_hint    = pg_exception_hint,
        		v_context = pg_exception_context;
				
			IF (id_devis_detail_initial = 0) THEN
				id_devis_detail := 0;
			END IF;
			out_message := v_msg;
			RAISE EXCEPTION '%', out_message; 
		
END;
$procedure$
