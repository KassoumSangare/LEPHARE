-- FUNCTION: public.fn_quittance_contrat(integer)

-- DROP FUNCTION IF EXISTS public.fn_quittance_contrat(integer);

CREATE OR REPLACE FUNCTION public.fn_quittance_contrat(
	id_contrat integer)
    RETURNS TABLE(idcontrat integer, raisonsociale character varying, libelleintermediaire character varying, idclient integer, numeropolice character varying, numeroavenant character varying, nomclient character varying, adresseclient character varying, dateeffet date, dateexpiration date, dateemission date, duree integer, primenette numeric, primenettehorsfga numeric, fga numeric, accessoire numeric, accessoirecompagnie numeric, accessoireintermediaire numeric, taxeenregistrement numeric, primettc numeric, confirme boolean, libelleproduit character varying, libellecategorie character varying, commissionintermediaire numeric, commissiongestionnaire numeric, commissionaperition numeric, titreclient character varying, professionclient character varying, typeassure character varying, typesouscripteur character varying, telephoneclient character varying, mobileclient character varying, adressegeographique character varying, emailclient character varying, cedeao numeric, libellemouvement character varying, nomassure character varying, adresseassure character varying, numeroquittance character varying, offre character varying, libellebareme character varying, iddevis integer, codecategorie character varying, fraisgestion numeric, numeropoliceconnexe character varying, codeintermediaire character varying, datenaissanceclient date, datenaissanceassure date) 
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
DECLARE
    montant_fga numeric;
    montant_cedeao numeric;
    libelle_mouvement character varying(50);
	id_tarif integer;
	libelle_categorie character varying (100);
	libelle_bareme character varying (11);
	code_categorie character varying(3);
	id_offre integer;
	libelle_offre character varying(120);
	id_produit integer;
	
BEGIN

	SELECT SUM(CASE WHEN DD.idgarantie = 3 THEN DD.primenette ELSE 0 END)
	INTO montant_cedeao
	FROM stdcontratdetgarantie AS DD
	INNER JOIN StdContratDetail AS SD ON(SD.IdContratDetail=DD.idcontratdetail)
	WHERE SD.IdContrat=id_contrat and DD.idgarantie = 3;

	IF EXISTS (SELECT 1 FROM public.stdcontrat AS SD WHERE SD.idcontrat = id_contrat AND NOT SD.primeimposee ) THEN
		SELECT SUM(CASE WHEN DD.idgarantie = 1 THEN ROUND(DD.primenette * 0.02, 0) ELSE 0 END)
		INTO montant_fga
		FROM stdcontratdetgarantie AS DD
		INNER JOIN StdContratDetail AS SD ON(SD.IdContratDetail=DD.idcontratdetail)
		WHERE SD.IdContrat=id_contrat and DD.idgarantie = 1;
	ELSE
		SELECT SD.fga
		INTO montant_fga
		FROM public.stdcontrat AS SD
		WHERE SD.idcontrat = id_contrat;
	END IF; 
	
	montant_fga := COALESCE(montant_fga, 0.0);
	montant_cedeao := COALESCE(montant_cedeao, 0.0);
	
	SELECT SC.IdProduit, SA.TexteMouvement, fn_get_libelle_bareme_contrat(COALESCE(SC.IdDuree,1))
	INTO id_produit, libelle_mouvement, libelle_bareme
	FROM StdContrat AS SC
	INNER JOIN StdAvenant AS SA ON (SC.IdAvenant = SA.IdAvenant)
	WHERE SC.IdContrat = id_contrat;
	
	SELECT IdTarif, IdOffre
	INTO id_tarif, id_offre
	FROM StdContratDetail AS DD
	WHERE DD.IdContrat = id_contrat
	LIMIT 1;
	
	SELECT SC.LibelleCategorie, ST.CodeCategorie
	INTO libelle_categorie, code_categorie
	FROM StdTarif AS ST
	INNER JOIN StdCategorie AS SC ON (ST.IdCategorie = SC.IdCategorie)
	WHERE IdTarif = id_tarif;
	
	libelle_categorie := COALESCE(libelle_categorie, '');
	code_categorie := COALESCE(code_categorie, '000');

	libelle_offre := '';
	IF (id_produit = 5 AND id_offre IN (17, 18, 19, 20, 21, 22)) OR (id_produit = 1) THEN --(id_produit = 5 AND id_offre IN (17, 18, 19, 20, 21, 22)) OR (id_produit = 1)
		SELECT LibelleOffre
		INTO libelle_offre
		FROM StdOffre
		WHERE IdOffre = id_offre;
		libelle_offre := COALESCE(libelle_offre, '');
	END IF;

	RETURN QUERY
			SELECT SD.IdContrat,CO.RaisonSociale, SC.LibelleIntermediaire, SD.IdClient, COALESCE(SD.IdPolicePegas, SD.NumeroPolice) AS NumeroPolice, SD.NumeroAvenant, (TRIM((Cl.Nom || ' ' || COALESCE(Cl.Prenoms, ''))))::character varying AS nomclient,
					Cl.Adresse1 AS adresseclient, SD.DateEffet::date, SD.DateExpiration::date, SD.DateEmission::date, (SD.DateExpiration::date - SD.DateEffet::date) + 1 AS duree,
					SD.PrimeNette, (SD.PrimeNette-montant_fga) AS primenettehorsfga, montant_fga AS fga,
					SD.Accessoire, SD.AccessoireCompagnie, SD.AccessoireIntermediaire, SD.Taxe AS taxeenregistrement, SD.PrimeTtc, True AS confirme, SP.libelleproduit,
					libelle_categorie AS libellecategorie, SD.CommissionIntermediaire, SD.CommissionGestionnaire, SD.CommissionAperiteur, Cl.titre_client, Cl.profession_client, Cl.type_assure,
					Cl.type_souscripteur, Cl.Telephone AS telephone_client, Cl.Mobile AS mobile_client, Cl.Adresse2 AS adresse_geographique, Cl.Email AS email_client, montant_cedeao AS cedeao,
					libelle_mouvement AS libellemouvement, (TRIM((Ass.Nom || ' ' || COALESCE(Ass.Prenoms, ''))))::character varying AS nomassure, Ass.Adresse1 AS adresseassure,
					COALESCE(SQ.numeroquittance, '') AS numeroquittance, (CASE WHEN SD.IdProduit = 1 AND SD.Flotte THEN 'FLOTTE AUTOMOBILE' ELSE libelle_offre END)::character varying AS offre, libelle_bareme AS libellebareme, SD.IdDevis, CASE WHEN SD.IdProduit=5 THEN code_categorie ELSE '' END AS codecategorie,
					SD.PrimeTTC - (SD.PrimeNette + SD.Accessoire + SD.Taxe) AS fraisgestion, COALESCE(SD.NumeroPoliceConnexe, '') AS numeropoliceconnexe, TRIM(SC.CodeIntermediaire)::character varying AS codeintermediaire,
					Cl.DateNaissance AS DateNaissanceClient, Ass.DateNaissance AS DateNaissanceAssure
			FROM StdContrat AS  SD
			INNER JOIN vue_client AS Cl ON(SD.IdClient = Cl.IdClient)
			INNER JOIN vue_client AS Ass ON (SD.IdAssure = Ass.IdClient)
			INNER JOIN StdIntermediaire AS SC ON (SC.IdIntermediaire=SD.IdIntermediaire)
			INNER JOIN StdCompagnie AS CO ON(CO.IdCompagnie=SD.IdCompagnie)
			INNER JOIN stdproduit AS SP ON (SD.IdProduit = SP.idproduit)
			LEFT JOIN stdquittance AS SQ ON (SD.NumeroPolice = SQ.numeropolice AND SD.idquittance = SQ.idquittance)
			WHERE SD.IdContrat=id_contrat;
	
END; 
$BODY$;

ALTER FUNCTION public.fn_quittance_contrat(integer)
    OWNER TO uranususer;

