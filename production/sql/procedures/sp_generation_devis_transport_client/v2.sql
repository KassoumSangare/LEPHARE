-- PROCEDURE: public.sp_generation_devis_transport_client(integer, integer, date, date, integer, character varying)

-- DROP PROCEDURE IF EXISTS public.sp_generation_devis_transport_client(integer, integer, date, date, integer, character varying);

CREATE OR REPLACE PROCEDURE public.sp_generation_devis_transport_client(
	IN user_id integer,
	IN id_client integer,
	IN date_debut_periode date,
	IN date_fin_periode date,
	INOUT id_devis integer,
	INOUT out_message character varying)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
    id_intermediaire integer;
	id_compagnie integer;
	id_produit integer;
	id_offre integer;
	id_avenant integer;
	id_assure integer;
	flotte_transport boolean;
	en_coassurance boolean;
	date_effet date;
	date_expiration date;
	date_emission date;
	id_tarif integer;
	date_debut date;
	taux_prime numeric;
	taux_reduction numeric;
	montant_accessoire_client numeric;
	id_duree integer;
	numero_telephone_assure character varying;
	adresse_geographique character varying;
    out_message_local character varying;
	id_historique_importation integer;
	numero_police_guce character varying;
	numero_police_uranus character varying;
	police_guce_rec RECORD;
	raison_sociale_assureur character varying;
    etat_traitement character varying(1); numero_avenant character varying(8); clef_avenant integer; numero_devis character varying(16);
	code_categorie character varying(3); local_message character varying(500); id_devis_detail integer;
	periode_contrat character varying(1); prime_nette numeric; montant_accessoire numeric; montant_taxe numeric; prime_ttc numeric; taux_commission numeric;
	nom_conducteur character varying(80); adresse_conducteur character varying(60); code_alarme integer; bns numeric; date_mec date;
	num_moteur character varying(20); num_chassis character varying(20); type_vehicule varchar(50); id_marque integer;
	matricule_assure character varying(20); essence integer; num_permis_conduire character varying(30); code_usage character varying(3); id_usage integer;
	id_carrosserie integer; code_carburant integer; puissance integer; nombre_place integer; charge_utile integer; age integer;
	prime_deces numeric; prime_ipp numeric; prime_frais_traitement numeric; prime_rec RECORD;
	id_devis_initial integer;
	nombre_assure integer;
	
BEGIN
    id_intermediaire := 1;
	id_compagnie := COALESCE(id_compagnie,1);
	id_produit := 6;
	id_client := COALESCE(id_client, 0);
	id_assure := id_client;
	id_avenant := COALESCE(id_avenant,0);
	flotte_transport := COALESCE(flotte_transport,False);
	en_coassurance := COALESCE(en_coassurance,False);
	id_duree :=  COALESCE(id_duree, 0);
	id_devis :=  0;
	id_tarif := 101;
	id_offre := 109; --Police à l'abonnement
	id_avenant := 18;  --Emission de certificat de transport
	numero_telephone_assure :=  TRIM(COALESCE(numero_telephone_assure, ''));
	id_devis_initial := id_devis;
	id_duree := COALESCE(id_duree, 1);
	adresse_geographique := TRIM(COALESCE(adresse_geographique, ''));
	id_historique_importation := 0;
	date_emission := CURRENT_DATE;
	date_expiration := date_fin_periode;
	date_effet := date_debut_periode;
	id_duree := fn_calcul_id_duree_contrat(date_expiration - date_effet);
	
	
	id_carrosserie := 0; code_carburant := 0; id_marque := 0; code_usage := '000'; id_usage := 0; code_alarme := 0; num_permis_conduire := '';
	matricule_assure := ''; nom_conducteur := ''; adresse_conducteur := ''; bns := 0; date_mec := '1900-01-01'::date; num_moteur := '';
	num_chassis := ''; type_vehicule := ''; matricule_assure := ''; essence := 0; num_permis_conduire := ''; puissance := 0; nombre_place := 0;
	charge_utile := 0;
	
	SELECT EtatTraitement
	INTO etat_traitement
	FROM StdAvenant
	WHERE IdAvenant = id_avenant;
	
	periode_contrat := fn_calcul_periode_contrat(date_expiration - date_effet);
	
	SELECT CodeCategorie
	INTO code_categorie
	FROM StdTarif
	WHERE IdTarif = id_tarif;

	IF id_client = 0 THEN
		out_message := 'Client introuvable! A-t-il été vraiment créé?';
		RAISE EXCEPTION '%', out_message;
	END IF;

	---Récupérer l'id de l'historique d'importation pour cette période (date_debut_periode date, date_fin_periode)
	SELECT idimportation
	INTO id_historique_importation
	FROM public.stdhistoriqueimportationcertificat
	WHERE datedebutperiode = date_debut_periode AND datefinperiode = date_fin_periode;
	id_historique_importation := COALESCE(id_historique_importation, 0);
	IF id_historique_importation = 0 THEN
		out_message := 'Historique d''importation introuvable! La première étape de l''importation s''est-elle bien passée?';
		RAISE EXCEPTION '%', out_message;
	END IF;
	---Générer des devis et des contrats pour les différentes polices GUCE du client sur la période
	FOR police_guce_rec IN (SELECT DISTINCT numeropolice, assureur
							FROM public.stdcertificattransport
							WHERE (idclienturanus = id_client)
							AND (datedebutperiode = date_debut_periode)
							AND (datefinperiode = date_fin_periode)
							)
	LOOP 
		prime_nette := 0; montant_accessoire := 0; montant_taxe := 0; prime_ttc :=0; montant_accessoire_client := 0;
		nombre_assure := 0;
		flotte_transport := False;
		numero_police_uranus := '';
		numero_police_guce := TRIM(COALESCE(police_guce_rec.numeropolice, ''));
		IF numero_police_guce = '' THEN
			CONTINUE;
		END IF;
		raison_sociale_assureur := TRIM(COALESCE(police_guce_rec.assureur, ''));
		SELECT idcompagnie
		INTO id_compagnie
		FROM public.stdcompagnie
		WHERE SUBSTRING(raison_sociale_assureur FROM 1 FOR LENGTH(TRIM(raisonsociale))) = TRIM(raisonsociale);
		id_compagnie := COALESCE(id_compagnie, 0);

		--Recupérons les composantes de primes et le nombre d'assurés
		SELECT SUM(primenette), SUM(accessoire), SUM(taxe), SUM(primettc), COUNT(DISTINCT assure), SUM(CASE WHEN accessoire < ABS(COALESCE(accessoireafsci, 0)) THEN 0 ELSE ABS(COALESCE(accessoireafsci, 0)) END)
		INTO prime_nette, montant_accessoire, montant_taxe, prime_ttc, nombre_assure, montant_accessoire_client
		FROM public.stdcertificattransport
		WHERE (idclienturanus = id_client)
			AND (datedebutperiode = date_debut_periode)
			AND (datefinperiode = date_fin_periode)
			AND (numeropolice = numero_police_guce);
		prime_nette := COALESCE(prime_nette, 0);
		montant_accessoire := COALESCE(montant_accessoire, 0);
		montant_accessoire_client := COALESCE(montant_accessoire_client, 0);
		montant_taxe := COALESCE(montant_taxe, 0);
		prime_ttc := COALESCE(prime_ttc, 0);
		nombre_assure := COALESCE(nombre_assure, 0);
		flotte_transport := (nombre_assure > 1);

		---Existe-t-il un devis déjà créé pour le client sur cette période (date_debut_periode date, date_fin_periode)?
		SELECT ICD.iddevis
		INTO id_devis
		FROM public.stdimportationcertificatdevis AS ICD
		INNER JOIN public.stddevis AS SD ON (ICD.iddevis = SD.iddevis)
		WHERE (ICD.idhistoriqueimportation = id_historique_importation)
			AND (SD.idclient = id_client)
			AND (SD.idproduit = id_produit)
			AND (COALESCE(SD.numeropoliceconnexe, '') = numero_police_guce)
		LIMIT 1;
		id_devis := COALESCE(id_devis, 0);

		taux_commission := public.fn_get_taux_commission(id_produit, id_compagnie, date_emission);
		IF (id_devis = 0) THEN --Pas de dévis existant pour cette période pour cette police du client

			--Voir s'il y a déjà au moins un devis Uranus pour cette police, même si ce devis n'est pas sur la période courante
			SELECT numerodevis
			INTO numero_devis
			FROM public.stddevis
			WHERE idclient = id_client
				AND idproduit = id_produit
				AND (COALESCE(numeropoliceconnexe, '') = numero_police_guce)
			LIMIT 1;
			numero_devis := COALESCE(numero_devis, '');
			CALL public.sp_numeroter_avenant(id_avenant, id_intermediaire, clef_avenant, numero_avenant);

			IF numero_devis = '' THEN
				CALL public.sp_generer_numero_devis(id_intermediaire, id_compagnie, code_categorie, numero_devis, local_message);
			END IF;

			---Générer la ligne de devis correspondant à cette police pour cette période
			INSERT INTO public.StdDevis (IdOperateur, IdOffre, IdIntermediaire, IdCompagnie, IdProduit, IdClient, IdAssure, IdAvenant, NumeroAvenant, NumeroDevis, Flotte,
					IdAperiteur, Coassurance, Periode, DateEmission, DateEffet, DateExpiration, Confirme, AccessoireIntermediaire, AccessoireCompagnie, IdDuree, NumeroPoliceConnexe, PrimeNette,
					Accessoire, Taxe, PrimeTTC, primeimposee)
			VALUES (user_id, id_offre, id_intermediaire, id_compagnie, id_produit, id_client, id_assure, id_avenant, numero_avenant, numero_devis, flotte_transport, id_compagnie, 
					en_coassurance, periode_contrat, date_emission, date_effet, date_expiration, False, montant_accessoire - montant_accessoire_client, 0, id_duree, numero_police_guce, prime_nette,
					montant_accessoire - montant_accessoire_client, montant_taxe, prime_ttc - montant_accessoire_client, false) RETURNING IdDevis INTO id_devis;
			
			---Marquer que le groupe de certificats de cette période a été généré en devis
            INSERT INTO public.stdimportationcertificatdevis(idhistoriqueimportation, iddevis)
            VALUES (id_historique_importation, id_devis);

			---Enregistrer les certificats émis sur cette période pour ce client et cette police
			INSERT INTO public.StdDevisDetail(IdDevis, IdOffre, IdTarif, Vehicule, idusage, CodeUsage, Reference, IdCarrosserie, PuissanceFiscale, NombrePlace,
					ChargeUtile, ValeurNeuve, ValeurVenale, ValeurAccessoire, REMORQUE, Conducteur, AdresseCnd, DateMec,
					DateMutation, NumMoteur, NumChassis, TypeVehicule, IdMarque, Matricule, CarteVerte, Essence, NumPCCnd, TauxReduction, primenette, taxeenregistrement, primeimposee)
			SELECT id_devis, id_offre, id_tarif, 1, id_usage, code_usage, code_usage, id_carrosserie, puissance, nombre_place, charge_utile,
					valeurassurance, 0, 0, False, assure, adresse_conducteur, datecertificat, datecertificat, num_moteur, numerorequete,
					type_vehicule, id_marque, referencecertificat, CASE WHEN code_categorie='205' THEN True ELSE False END, code_carburant, COALESCE(numerodocumenttransport,''), taux_reduction,
					primenette, taxe, false
			FROM public.stdcertificattransport
			WHERE (idclienturanus = id_client)
				AND (datedebutperiode = date_debut_periode)
				AND (datefinperiode = date_fin_periode)
				AND (numeropolice = numero_police_guce);
		ELSE
			IF EXISTS (SELECT * FROM public.StdDevis WHERE IdDevis = id_devis AND Confirme) THEN
				out_message := 'Devis déjà confirmé. Opération impossible!';
				RAISE EXCEPTION '%', out_message;
			END IF;

			UPDATE public.StdDevis
			SET IdOperateur = user_id, IdOffre = id_offre, IdIntermediaire = id_intermediaire, IdCompagnie = id_compagnie, IdProduit = id_produit, IdClient = id_client, IdAssure = id_assure, IdAvenant = id_avenant, Flotte = flotte_transport,
				IdAperiteur = id_compagnie, Coassurance = en_coassurance, Periode = periode_contrat, DateEmission = date_emission, DateEffet = date_effet, DateExpiration = date_expiration, AccessoireCompagnie = 0, IdDuree = id_duree,
				NumeroPoliceConnexe = numero_police_guce, PrimeNette = prime_nette, AccessoireIntermediaire = montant_accessoire - montant_accessoire_client, AccessoireCompagnie = 0, Accessoire = montant_accessoire - montant_accessoire_client, Taxe = montant_taxe, PrimeTTC = prime_ttc - montant_accessoire_client
			WHERE IdDevis = id_devis;
			
			UPDATE public.StdDevisDetail AS SDD
			SET IdOffre = id_offre, IdTarif = id_tarif, Vehicule = 1, idusage = id_usage, CodeUsage = code_usage, Reference = code_usage, IdCarrosserie = id_carrosserie, PuissanceFiscale = puissance, NombrePlace = nombre_place,
						ChargeUtile = charge_utile, ValeurNeuve = SCT.valeurassurance, ValeurVenale = 0, ValeurAccessoire = 0, Remorque = False, Conducteur = assure, AdresseCnd = adresse_conducteur, DateMec = SCT.datecertificat,
						DateMutation = SCT.datecertificat, NumMoteur = num_moteur, NumChassis = SCT.numerorequete, TypeVehicule = type_vehicule, IdMarque = id_marque, Matricule = SCT.referencecertificat,
						CarteVerte = CASE WHEN code_categorie='205' THEN True ELSE False END, Essence = code_carburant,
						NumPCCnd = SCT.numerodocumenttransport, TauxReduction = taux_reduction, primenette = SCT.primenette, taxeenregistrement = SCT.taxe
			FROM public.stdcertificattransport AS SCT
			WHERE SDD.iddevis = id_devis 
				AND (SCT.idclienturanus = id_client)
				AND (SCT.datedebutperiode = date_debut_periode)
				AND (SCT.datefinperiode = date_fin_periode)
				AND (SCT.numeropolice = numero_police_guce)
				AND (SDD.matricule = SCT.referencecertificat)
				AND (SDD.numchassis = SCT.numerorequete);
		END IF;

		SELECT numeropolice
		INTO numero_police_uranus
		FROM public.stdcontrat
		WHERE iddevis = id_devis
		LIMIT 1;
		numero_police_uranus := COALESCE(numero_police_uranus, '');
		IF numero_police_uranus = '' THEN  ---Contrat non encore généré pour ce devis
			SELECT numeropolice
			INTO numero_police_uranus
			FROM public.stdcontrat AS SC
			INNER JOIN public.stddevis AS SD ON (SC.iddevis = SD.iddevis)
			WHERE SD.idproduit = 6 AND SD.idclient = id_client AND SD.numeropoliceconnexe = numero_police_guce
			LIMIT 1;
			numero_police_uranus := COALESCE(numero_police_uranus, '');
			IF (numero_police_uranus = '') THEN
				CALL public.sp_generer_numero_police(id_intermediaire, id_compagnie, code_categorie, numero_police_uranus, local_message);
			END IF;
		END IF;
		CALL public.sp_generation_contrat_transport(id_devis, numero_police_uranus, local_message);

	END LOOP;

END;
$BODY$;
ALTER PROCEDURE public.sp_generation_devis_transport_client(integer, integer, date, date, integer, character varying)
    OWNER TO uranususer;

