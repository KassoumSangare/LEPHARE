CREATE OR REPLACE PROCEDURE public.sp_creation_devis_voyage(IN id_intermediaire integer, IN id_compagnie_p integer, IN id_produit integer, IN id_offre integer, IN id_avenant integer, IN id_client integer, IN id_assure integer, IN flotte_voyage boolean, IN en_coassurance boolean, IN date_effet date, IN date_expiration date, IN date_emission date, IN id_tarif integer, IN id_pays_destination integer, IN id_pays_voyageur integer, IN reference_contrat character varying, IN numero_attestation character varying, IN visa_schengen boolean, IN numero_passport character varying, IN taux_reduction numeric, IN date_naissance date, IN numero_police_compagnie character varying, INOUT id_devis integer, INOUT out_message character varying)
 LANGUAGE plpgsql
AS $procedure$
-- v2 (grilles Voyage OREOLE 2026) : garanties, primes, taxes et accessoire repris tels quels de
-- fn_garantie_offre_voyage (grille de la compagnie, taux de taxe de la ligne de grille) : le devis
-- enregistré a les montants affichés à l'écran. v3 : accessoire partagé selon la part du cabinet réglée sur la
-- fiche de la compagnie (fn_lephare_part_accessoires_cabinet ; NSIA, SUNU et AMSA : 50 %), sinon à la compagnie.
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
	--Accessoire et taxe totale de la ligne de cumul de fn_garantie_offre_voyage
	v_accessoire numeric;
	v_accessoire_intermediaire numeric;
	v_accessoire_total numeric;
	v_part_cabinet numeric;
	v_taxe_totale numeric;
	v_taxe_garanties numeric;
	taxe_accessoire numeric;
	v_prime_imposee bool;
	----Gestion des erreurs
	v_state TEXT; v_msg TEXT; v_detail TEXT; v_hint TEXT; v_context TEXT;

BEGIN

	DROP TABLE IF EXISTS temp_garantie_voyage;
	CREATE TEMPORARY TABLE temp_garantie_voyage (idgarantie integer, idsousgarantie integer, libellesousgarantie varchar(60), garcapitalval numeric, garplaceval integer,
						garfranchiseval Money, taux numeric, acquise boolean, primeannuelle numeric, primenette numeric, taxe numeric, montantaccessoire numeric);

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
	INSERT INTO temp_garantie_voyage(idgarantie, IdSousGarantie, LibelleSousGarantie, garcapitalval, garplaceval, garfranchiseval, Acquise,
				primeannuelle, primenette, taxe, montantaccessoire)
	SELECT idgarantie, idsousgarantie, libellesousgarantie, capital, nombreplace, 0 AS franchise, acquise, primeannuelle, primenette, taxe, montantaccessoire
	FROM fn_garantie_offre_voyage(id_compagnie_p, id_tarif, id_offre, id_zone_voyage, taux_reduction, date_effet, date_expiration, date_naissance);

	-- Ligne de cumul : accessoire et taxe totale (garanties + accessoire)
	SELECT COALESCE(montantaccessoire, 0), COALESCE(taxe, 0)
	INTO v_accessoire_total, v_taxe_totale
	FROM temp_garantie_voyage
	WHERE idgarantie = 0;
	DELETE FROM temp_garantie_voyage WHERE idgarantie = 0;

	UPDATE temp_garantie_voyage
	SET garcapitalval = (CASE WHEN id_zone_voyage = 1 THEN 19679000 ELSE 32798000 END), garfranchiseval = 32800
	WHERE idsousgarantie=29;

	UPDATE temp_garantie_voyage
	SET garcapitalval = 105000, garfranchiseval = 32800
	WHERE IdSousGarantie = 28;

	UPDATE temp_garantie_voyage
	SET garcapitalval = 1562000
	WHERE IdSousGarantie=23;

	INSERT INTO StdDevisDetGarantie(IdDevisDet,IdGarantie,Acquise,Taxe,Capital,MinFranchise,MaxFranchise,PrimeAnnuelle,PrimeNette,
	Old_Acquise,Old_PrimeNette)
	SELECT id_devis_detail, idsousgarantie, acquise, taxe, garcapitalval, 0, garfranchiseval, primeannuelle, primenette, 0, 0
	FROM temp_garantie_voyage
	ORDER BY idgarantie, idsousgarantie;

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

	SELECT COALESCE(SUM(taxe), 0) INTO v_taxe_garanties FROM temp_garantie_voyage;
	taxe_accessoire := COALESCE(v_taxe_totale, 0) - v_taxe_garanties;
	v_accessoire_total := COALESCE(v_accessoire_total, 0);
	v_part_cabinet := public.fn_lephare_part_accessoires_cabinet(id_compagnie_p);
	IF v_part_cabinet IS NOT NULL THEN
		v_accessoire := ROUND(v_accessoire_total * (100 - v_part_cabinet) / 100, 0);
		v_accessoire_intermediaire := v_accessoire_total - v_accessoire;
	ELSE
		v_accessoire := v_accessoire_total;
		v_accessoire_intermediaire := 0;
	END IF;

	UPDATE StdDevis
	SET AccessoireCompagnie = v_accessoire, AccessoireIntermediaire = v_accessoire_intermediaire,
		Accessoire = v_accessoire + v_accessoire_intermediaire, Taxe = Taxe + taxe_accessoire
	WHERE IdDevis = id_devis;

	UPDATE StdDevis
	SET primettc = ROUND((primenette+accessoire+taxe), 0)
	WHERE iddevis = id_devis;


	DROP TABLE IF EXISTS temp_garantie_voyage;
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
		DROP TABLE IF EXISTS temp_garantie_voyage;
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
$procedure$;
