CREATE FUNCTION public.fn_garantie_offre_voyage(id_compagnie integer, id_tarif integer, id_offre integer, id_zone_voyage integer, taux_reduction numeric, date_effet date, date_expiration date, date_naissance date) RETURNS TABLE(idgarantie integer, libellegarantie character varying, idsousgarantie integer, libellesousgarantie character varying, acquise boolean, capital numeric, nombreplace integer, primeannuelle numeric, primenette numeric, taxe numeric, montantaccessoire numeric)
    LANGUAGE plpgsql
    AS $$
DECLARE
	
	duree_contrat integer;
	--duree_totale integer;
	age integer;
	garantie_rec RECORD;
	prime_voyage numeric;
	
	----Pour le calcul des totaux des composantes de prime
	taux_taxe numeric;
	prime_annuelle_totale numeric;
	prime_nette_totale numeric;
	v_accessoire numeric;
	v_accessoire_intermediaire numeric;
	--taux_taxe_accessoire numeric;
	taxe_accessoire numeric;
	taxe_totale numeric;
	v_id_tarif integer;

BEGIN

	--duree_totale := CAST ((CAST (EXTRACT('year' FROM CURRENT_DATE) AS char(4)) || '-12-31') AS DATE) - CAST ((CAST (EXTRACT('year' FROM CURRENT_DATE) AS char(4)) || '-01-01') AS DATE) + 1;
	age := EXTRACT('year' FROM AGE(CURRENT_DATE, date_naissance));
	duree_contrat := date_expiration - date_effet;

	SELECT idtarif INTO v_id_tarif FROM public.stdoffre WHERE idoffre = id_offre;
	IF id_tarif <> v_id_tarif THEN
		id_tarif := v_id_tarif;
	END IF;
	
	prime_voyage := fn_calcul_prime_voyage_by_age(age,duree_contrat,id_zone_voyage,id_tarif,id_offre);
	
	---Initialisation des cumuls
	prime_annuelle_totale := 0;
	prime_nette_totale := 0;
	v_accessoire := 0;
	v_accessoire_intermediaire := 0;
	taxe_totale := 0;

	FOR garantie_rec IN (SELECT sg.IdGarantie as id_garantie, G.LibelleGarantie AS libelle_garantie, og.IdSousGarantie as id_sous_garantie, sg.LibelleSousGarantie AS libelle_sous_garantie, True AS garantie_acquise, 0 AS capital_garanti, 0 AS nombre_place, 0 AS prime_annuelle, 0 AS prime_nette, 0 AS taxe_enregistrement, 0 AS montant_accessoire 
							FROM StdOffreGarantie AS og
							INNER JOIN StdSousGarantie AS sg ON(sg.IdSousGarantie=og.IdSousGarantie)
							INNER JOIN StdGarantie AS G ON(G.IdGarantie=sg.IdGarantie)
							WHERE IdOffre = id_offre AND IdCompagnie = id_compagnie
							ORDER BY 1
						)
	LOOP
		idgarantie := garantie_rec.id_garantie;
		libellegarantie := garantie_rec.libelle_garantie;
		idsousgarantie := garantie_rec.id_sous_garantie;
		libellesousgarantie := garantie_rec.libelle_sous_garantie;
		acquise := garantie_rec.garantie_acquise;
		capital := garantie_rec.capital_garanti;
		nombreplace := garantie_rec.nombre_place;
		primeannuelle := COALESCE(garantie_rec.prime_annuelle, 0.0);
		primenette := COALESCE(garantie_rec.prime_nette, 0.0);
		taxe := COALESCE(garantie_rec.taxe_enregistrement, 0.0);
		montantaccessoire := COALESCE(garantie_rec.montant_accessoire, 0.0);
		
		IF (garantie_rec.id_sous_garantie = 23) THEN
			primeannuelle := prime_voyage;
			primenette := prime_voyage - (prime_voyage * taux_reduction)/100;
			--Détermination de la prime de la période de couverture
			--primenette := ROUND((primenette * duree_contrat)/duree_totale,0);
		END IF;
		
		---Calcul de la taxe
		SELECT tauxtaxe
		INTO taux_taxe
		FROM stdtauxtaxegarantieproduit AS tt
		WHERE (idproduit = 3) AND (tt.idgarantie = garantie_rec.id_sous_garantie);
		taux_taxe := COALESCE(taux_taxe, 0);
		taxe := ROUND((primenette * taux_taxe)/100,0);
		
		---Faire le cumul des 2 composantes de prime (prime nette et taxe)
		prime_annuelle_totale := prime_annuelle_totale + primeannuelle;
		prime_nette_totale := prime_nette_totale + primenette;
		taxe_totale := taxe_totale + taxe;

		
		RETURN NEXT;
		
	END LOOP;
	
	--Calcul de l'accessoire
-- 	SELECT accessoires
-- 	INTO v_accessoire
-- 	FROM stdaccessoire
-- 	WHERE prime_nette_totale between primemin and primemax and idproduit = 3;
	
-- 	v_accessoire := COALESCE(v_accessoire, 0.0);
-- 	taux_taxe_accessoire := fn_get_taux_taxe(3, id_offre, date_effet);
-- 	taxe_accessoire := (v_accessoire * taux_taxe_accessoire)/100;
	SELECT * 
	INTO v_accessoire, v_accessoire_intermediaire, taxe_accessoire
	FROM fn_get_accessoire(prime_nette_totale, 3, id_offre, id_compagnie, date_effet);
	--- Retourner la ligne des cumuls
	idgarantie := 0;
	libellegarantie := 'CUMUL DES MONTANTS DES GARANTIES';
	idsousgarantie := 0;
	libellesousgarantie := 'CUMUL DES MONTANTS DES S/GARANTIES';
	acquise := True;
	capital := 0.0;
	nombreplace := 0.0;
    primeannuelle := prime_annuelle_totale;
	primenette := prime_nette_totale;
	taxe := taxe_totale + taxe_accessoire;
	montantaccessoire := v_accessoire + v_accessoire_intermediaire;
	RETURN NEXT;

END;
$$;



CREATE FUNCTION public.fn_liste_pays_voyage(id_compagnie_ integer) RETURNS TABLE(idpays integer, libellepays character varying, nationalite character varying, idzone integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
	
	RETURN QUERY
		SELECT SP.id_pays, SP.libelle_pays, SP.nationalite, SVP.id_zone
		FROM StdPays AS SP
		INNER JOIN StdZoneVoyagePays AS SVP ON (SP.id_pays = SVP.id_pays)
		INNER JOIN StdZoneVoyage AS SV ON (SVP.id_zone = SV.id_zone)
		WHERE SV.id_compagnie = id_compagnie_
		ORDER BY SP.libelle_pays;
		
END; 
$$;



CREATE PROCEDURE public.sp_creation_devis_voyage(IN id_intermediaire integer, IN id_compagnie_p integer, IN id_produit integer, IN id_offre integer, IN id_avenant integer, IN id_client integer, IN id_assure integer, IN flotte_voyage boolean, IN en_coassurance boolean, IN date_effet date, IN date_expiration date, IN date_emission date, IN id_tarif integer, IN id_pays_destination integer, IN id_pays_voyageur integer, IN reference_contrat character varying, IN numero_attestation character varying, IN visa_schengen boolean, IN numero_passport character varying, IN taux_reduction numeric, IN date_naissance date, IN numero_police_compagnie character varying, INOUT id_devis integer, INOUT out_message character varying)
    LANGUAGE plpgsql
    AS $$
DECLARE
	etat_traitement character varying(1); numero_avenant character varying(8); clef_avenant integer; numero_devis varchar(16);code_categorie character varying(3);
	local_message varchar(500); id_devis_detail integer; id_garantie integer; duree_contrat integer; periode_contrat character varying(1);
	prime_nette numeric; taux_commission numeric; nom_conducteur varchar(80); adresse_conducteur varchar(60); code_alarme integer;
	bns numeric; date_mec date; num_moteur varchar(20); num_chassis varchar(20); type_vehicule varchar(50); id_marque integer;
	matricule_assure varchar(20); essence integer; num_permis_conduire varchar(30); code_usage character varying(3); id_usage integer; id_carrosserie integer;
	code_carburant integer; puissance integer; nombre_place integer; charge_utile integer; 
	age integer; prime_deces numeric; prime_ip numeric; prime_frais_traitement numeric; capital_deces numeric; capital_ipp numeric;
	frais_traitement numeric; code_activite character varying(2); prime_voyage numeric;
	id_devis_initial integer; id_zone_voyage integer;
	--Pour le calcul des taxes relatives aux accessoires
	v_accessoire numeric;
	v_accessoire_intermediaire numeric;
	taxe_accessoire numeric;
	v_prime_imposee bool;
	----Gestion des erreurs
	v_state TEXT; v_msg TEXT; v_detail TEXT; v_hint TEXT; v_context TEXT;

BEGIN

	CREATE TEMPORARY TABLE IF NOT EXISTS temp_garantie (idsousgarantie integer, libellesousgarantie varchar(60), garcapitalval numeric, garplaceval integer,
						garfranchiseval Money, taux numeric, acquise boolean, primeannuelle numeric, primenette numeric);
	
	DELETE FROM temp_garantie;
	
	id_devis := COALESCE(id_devis,0);
	id_devis_initial := id_devis;
	out_message := '';
	
	id_intermediaire := COALESCE(id_intermediaire,0);
	id_compagnie_p := COALESCE(id_compagnie_p,1);
	id_produit := COALESCE(id_produit,0);
	id_offre := COALESCE(id_offre,0);
	id_client := COALESCE(id_client,0);
	id_assure := COALESCE(id_assure,0);
	id_avenant := COALESCE(id_avenant,0);
	flotte_voyage := COALESCE(flotte_voyage, False);
	en_coassurance := COALESCE(en_coassurance,False);
	v_prime_imposee := false;
	IF numero_police_compagnie IS NOT NULL THEN
		numero_police_compagnie := NULLIF(TRIM(numero_police_compagnie),'');
	END IF;
	
	id_carrosserie:=0;code_carburant:=0;id_marque:=0;code_usage:='000';id_usage:=0;code_alarme:=0;
	num_permis_conduire:='';matricule_assure:='';nom_conducteur:='';
	adresse_conducteur := ''; bns := 0; date_mec := date_naissance; num_moteur :='';num_chassis :='';type_vehicule :='';
	essence :=0;num_permis_conduire :='';puissance :=0;nombre_place :=0;charge_utile :=0;
	capital_deces := 0;capital_ipp := 0; frais_traitement := 0;
	
	SELECT SVP.id_zone
	INTO id_zone_voyage
	FROM StdPays AS SP
	INNER JOIN StdZoneVoyagePays AS SVP ON (SP.id_pays = SVP.id_pays)
	INNER JOIN StdZoneVoyage AS SV ON (SVP.id_zone = SV.id_zone)
	WHERE SV.id_compagnie = id_compagnie_p AND SP.id_pays = id_pays_destination;
	id_zone_voyage := COALESCE(id_zone_voyage, 0);
	
	SELECT EtatTraitement
	INTO etat_traitement
	FROM StdAvenant
	WHERE IdAvenant = id_avenant;
	
	duree_contrat := date_expiration - date_effet;
	IF duree_contrat < 1 THEN
		IF id_devis <> 0 THEN
			out_message := 'La durée du voyage est incorrecte. Modification du devis impossible!';
		ELSE
			out_message := 'La durée du voyage est incorrecte. Création du devis impossible!';
		END IF;
	END IF;
	periode_contrat := fn_calcul_periode_contrat(duree_contrat);
	age := EXTRACT('year' FROM AGE(CURRENT_DATE, date_naissance));
	
	taux_commission := fn_get_taux_commission(id_produit, id_compagnie_p, date_emission);
	
	SELECT CodeCategorie
	INTO code_categorie
	FROM StdTarif
	WHERE IdTarif = id_tarif;
		
	IF id_devis = 0 THEN
		CALL sp_numeroter_avenant(id_avenant, id_intermediaire, clef_avenant, numero_avenant);
	
		CALL sp_generer_numero_devis (id_intermediaire, id_compagnie_p, code_categorie, numero_devis, local_message);
	
		INSERT INTO StdDevis (IdIntermediaire,IdCompagnie,IdProduit,IdClient,IdAssure,IdAvenant,NumeroAvenant,NumeroDevis,Flotte,
					IdAperiteur,Coassurance,Periode,DateEmission,DateEffet,DateExpiration,Confirme,AccessoireCompagnie)
		VALUES (id_intermediaire,id_compagnie_p,id_produit,id_client,id_assure,id_avenant,numero_avenant,numero_devis,flotte_voyage,
			id_compagnie_p,en_coassurance, periode_contrat,date_emission,date_effet,date_expiration,False,0) RETURNING IdDevis INTO id_devis;
	 
		INSERT INTO StdDevisDetail (IdDevis,IdOffre,IdTarif,Vehicule,idusage,CodeUsage,Reference,IdCarrosserie,PuissanceFiscale,NombrePlace,ChargeUtile,
	 					ValeurNeuve,ValeurVenale,ValeurAccessoire,Remorque,Conducteur, AdresseCnd,DateMec, DateMutation,
	 					NumMoteur,NumChassis,TypeVehicule,IdMarque,Matricule,CarteVerte,Essence,NumPCCnd,TauxReduction, Attestation, PrimeImposee)
		VALUES (id_devis,id_offre,id_tarif,1,id_usage,code_usage,code_usage,id_carrosserie,puissance,nombre_place,charge_utile,
	 		capital_ipp,capital_deces,frais_traitement,False,nom_conducteur,adresse_conducteur,date_mec,date_mec,num_moteur,num_chassis,
	 		type_vehicule,id_marque,matricule_assure,CASE WHEN code_categorie='205' THEN True ELSE False END,code_carburant,num_permis_conduire,taux_reduction, numero_attestation, v_prime_imposee)
		RETURNING iddevisdetail INTO id_devis_detail;
		
		INSERT INTO StdComplementDevisDetailVoyage(IdDevisDetail, NumeroAttestation, NumeroPasseport, IdPaysDestination, IdPaysVoyageur, ReferenceContrat, VisaSchengen)
		VALUES (id_devis_detail, numero_attestation, numero_passport, id_pays_destination, id_pays_voyageur, reference_contrat, visa_schengen);
	ELSE
		IF EXISTS (SELECT 1 FROM StdDevis WHERE IdDevis = id_devis AND Confirme) THEN
			out_message := 'Devis déjà confirmé. Modification impossible.';
			RAISE EXCEPTION '%', out_message;
		END IF;
		
		SELECT NumeroDevis
		INTO numero_devis
		FROM StdDevis
		WHERE IdDevis = id_devis;
		
		SELECT IdDevisDetail
		INTO id_devis_detail
		FROM StdDevisDetail
		WHERE IdDevis = id_devis
		LIMIT 1;
		id_devis_detail := COALESCE(id_devis_detail, 0);
		
		UPDATE StdDevis
		SET IdIntermediaire = id_intermediaire,IdCompagnie = id_compagnie_p, IdProduit = id_produit,IdClient = id_client,IdAssure = id_assure,IdAvenant = id_avenant,Flotte = flotte_voyage,
					IdAperiteur = id_compagnie_p,Coassurance = en_coassurance,Periode = periode_contrat,DateEmission = date_emission,DateEffet = date_effet,DateExpiration = date_expiration,AccessoireCompagnie = 0
		WHERE IdDevis = id_devis AND NOT Confirme;
		IF id_devis_detail <> 0 THEN
			UPDATE StdDevisDetail 
			SET IdOffre = id_offre,IdTarif = id_tarif,idusage = id_usage,CodeUsage = code_usage,Reference = code_usage,IdCarrosserie = id_carrosserie,PuissanceFiscale = puissance,NombrePlace = nombre_place,ChargeUtile = charge_utile,
	 			ValeurNeuve = capital_ipp,ValeurVenale = capital_deces,ValeurAccessoire = frais_traitement,Remorque = False,Conducteur = nom_conducteur, AdresseCnd = adresse_conducteur,DateMec = date_mec, DateMutation = date_mec,
	 			NumMoteur = num_moteur,NumChassis = num_chassis,TypeVehicule = type_vehicule,IdMarque = id_marque,Matricule = matricule_assure, CarteVerte = CASE WHEN code_categorie='205' THEN True ELSE False END,Essence = code_carburant,NumPCCnd = num_permis_conduire,TauxReduction = taux_reduction,
				Attestation = numero_attestation, PrimeImposee = v_prime_imposee
			WHERE IdDevis = id_devis AND IdDevisDetail = id_devis_detail;
			IF EXISTS (SELECT COUNT(IdComplement) FROM StdComplementDevisDetailVoyage WHERE IdDevisDetail = id_devis_detail HAVING COUNT(IdComplement) > 1) THEN
				out_message := 'Données incohérentes: doublons détectés dans les détails du devis. Modification impossible.';
				RAISE EXCEPTION '%', out_message;
			END IF;
			UPDATE StdComplementDevisDetailVoyage
			SET NumeroAttestation = numero_attestation, NumeroPasseport = numero_passport, IdPaysDestination = id_pays_destination, IdPaysVoyageur = id_pays_voyageur, ReferenceContrat = reference_contrat, VisaSchengen = visa_schengen
			WHERE IdDevisDetail = id_devis_detail;
		ELSE
			out_message := 'Données incohérentes: détails du devis non enregistrés. Modification impossible.';
			RAISE EXCEPTION '%', out_message;
		END IF;
		
		DELETE FROM  StdDevisDetGarantie WHERE IdDevisDet = id_devis_detail;
		
	END IF;
	INSERT INTO temp_garantie(IdSousGarantie, LibelleSousGarantie, garcapitalval, garplaceval, garfranchiseval, Acquise,
				primeannuelle, primenette)
	SELECT idsousgarantie, libellesousgarantie, capital, nombreplace, 0 AS franchise, acquise, primeannuelle, primenette 
	FROM fn_garantie_offre_voyage(id_compagnie_p, id_tarif, id_offre, id_zone_voyage, taux_reduction, date_effet, date_expiration, date_naissance)
	WHERE idgarantie <> 0
	ORDER BY 1;

	prime_voyage := fn_calcul_prime_voyage_by_age(age, duree_contrat, id_zone_voyage, id_tarif, id_offre);
	
	UPDATE temp_garantie
	SET garcapitalval = (CASE WHEN id_zone_voyage = 1 THEN 19679000 ELSE 32798000 END), garfranchiseval = 32800, primeannuelle = prime_voyage,
		primenette = prime_voyage - (prime_voyage * taux_reduction)/100
	WHERE idsousgarantie=29;
	
	UPDATE temp_garantie
	SET garcapitalval = 105000, garfranchiseval = 32800
	WHERE IdSousGarantie = 28;
	
	UPDATE temp_garantie
	SET garcapitalval = 1562000, primeannuelle = 0, primenette = 0
	WHERE IdSousGarantie=23;

	INSERT INTO StdDevisDetGarantie(IdDevisDet,IdGarantie,Acquise,Taxe,Capital,MinFranchise,MaxFranchise,PrimeAnnuelle,PrimeNette,
	Old_Acquise,Old_PrimeNette)
	SELECT id_devis_detail, idsousgarantie, acquise, 0 AS taxe, garcapitalval, 0, garfranchiseval, primeannuelle, primenette, 0, 0
	FROM temp_garantie;
	
	UPDATE StdDevisDetGarantie AS DD
	SET Taxe=G.Taxe
	FROM (SELECT IdSousGarantie, round((PrimeNette* TT.TauxTaxe)/100,0) AS Taxe
		FROM temp_garantie AS TP
		JOIN StdTauxTaxeGarantieProduit AS TT ON (TT.IdGarantie=TP.IdSousGarantie)
		WHERE (IdProduit = id_produit) AND (date_effet BETWEEN TT.DebutValidite AND TT.FinValidite)) AS G
	WHERE (G.IdSousGarantie = DD.IdGarantie) AND (DD.IdDevisDet = id_devis_detail);

	UPDATE StdDevisDetail AS DD
	SET PrimeAnnuelle=M.PrimeAnnuelle,PrimeNette=M.PrimeNette,TaxeEnregistrement=Taxe
	FROM (SELECT IdDevisDet, SUM(PrimeAnnuelle) AS PrimeAnnuelle, SUM(PrimeNette) AS PrimeNette, SUM(Taxe) AS Taxe
		FROM StdDevisDetGarantie
		WHERE IdDevisDet = id_devis_detail
		GROUP BY IdDevisDet) AS M
	WHERE (M.IdDevisDet = DD.IdDevisDetail) AND (IdDevisDet = id_devis_detail);

	UPDATE StdDevis AS DD
	SET PrimeAnnuelle = M.PrimeAnnuelle, PrimeNette = M.PrimeNette, Taxe = TaxeEnregistrement,
		CommissionIntermediaire = ROUND((M.PrimeNette*COALESCE(taux_commission,0))/100,0)
	FROM (SELECT IdDevis, SUM(PrimeAnnuelle) AS PrimeAnnuelle, SUM(PrimeNette) AS PrimeNette, SUM(TaxeEnregistrement) AS TaxeEnregistrement
		FROM StdDevisDetail
		WHERE IdDevis = id_devis
		GROUP BY IdDevis) AS M
	WHERE (M.IdDevis = DD.IdDevis) AND (DD.IdDevis = id_devis) AND (NumeroDevis = numero_devis);
	
	SELECT PrimeNette
	INTO prime_nette
	FROM StdDevis
	WHERE IdDevis=id_devis;
	
	SELECT *
	INTO v_accessoire, v_accessoire_intermediaire, taxe_accessoire
	FROM fn_get_accessoire(prime_nette, id_produit, id_offre, id_compagnie_p, date_effet);
	
	UPDATE StdDevis
	SET AccessoireCompagnie = v_accessoire, AccessoireIntermediaire = v_accessoire_intermediaire,
		Accessoire = v_accessoire + v_accessoire_intermediaire, Taxe = Taxe + taxe_accessoire
	WHERE IdDevis = id_devis;
	
	UPDATE StdDevis
	SET primettc = ROUND((primenette+accessoire+taxe), 0)
	WHERE iddevis = id_devis;

	
	DROP TABLE IF EXISTS temp_garantie;
	IF id_devis <> 0 THEN
		out_message := 'Devis enregistré avec succès.';
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
		out_message := v_msg; --|| ' : ' || v_context; -- 'Problème rencontré lors de la création du devis';
		DROP TABLE IF EXISTS temp_garantie;
    	/*RAISE EXCEPTION E'Got exception:
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
$$;



