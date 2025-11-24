-- FUNCTION: public.fn_quittance_proposition(integer)

-- DROP FUNCTION IF EXISTS public.fn_quittance_proposition(integer);

CREATE OR REPLACE FUNCTION public.fn_quittance_proposition(
	id_devis integer)
    RETURNS TABLE(iddevis integer, raisonsociale character varying, libelleintermediaire character varying, idclient integer, numerodevis character varying, numeroavenant character varying, nomclient character varying, adresseclient character varying, dateeffet date, dateexpiration date, dateemission date, duree integer, primenette numeric, primenettehorsfga numeric, fga numeric, accessoire numeric, accessoirecompagnie numeric, accessoireintermediaire numeric, taxeenregistrement numeric, primettc numeric, confirme boolean, libelleproduit character varying, libellecategorie character varying, commissionintermediaire numeric, commissiongestionnaire numeric, commissionaperition numeric, titreclient character varying, professionclient character varying, typeassure character varying, typesouscripteur character varying, telephoneclient character varying, mobileclient character varying, adressegeographique character varying, emailclient character varying, cedeao numeric, libellemouvement character varying, nomassure character varying, adresseassure character varying, offre character varying, libellebareme character varying, codecategorie character varying, fraisgestion numeric, numeropoliceconnexe character varying, codeintermediaire character varying, datenaissanceclient date, datenaissanceassure date) 
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

	SELECT SUM(DD.PrimeNette) AS prime_cedeao
	INTO montant_cedeao
	FROM StdDevisDetGarantie AS DD
	INNER JOIN StdDevisDetail AS SD ON(SD.iddevisdetail=DD.IdDevisDet)
	WHERE SD.iddevis=id_devis and DD.IdGarantie = 3;
	
	IF EXISTS (SELECT 1 FROM public.stddevis AS SD WHERE SD.iddevis = id_devis AND NOT SD.primeimposee ) THEN
		SELECT SUM(CASE WHEN DD.idgarantie = 1 THEN ROUND(DD.primenette * 0.02, 0) ELSE 0 END) AS prime_fga
		INTO montant_fga
		FROM StdDevisDetGarantie AS DD
		INNER JOIN StdDevisDetail AS SD ON(SD.iddevisdetail=DD.IdDevisDet)
		WHERE SD.iddevis=id_devis and DD.IdGarantie IN (1, 3);
	ELSE
		SELECT SD.fga
		INTO montant_fga
		FROM public.stddevis AS SD
		WHERE SD.iddevis = id_devis;
	END IF;
	
	montant_fga := COALESCE(montant_fga, 0.0);
	montant_cedeao := COALESCE(montant_cedeao, 0.0);
	
	SELECT SD.IdProduit, SA.TexteMouvement, fn_get_libelle_bareme_contrat(COALESCE(SD.IdDuree,1))
	INTO id_produit, libelle_mouvement, libelle_bareme
	FROM StdDevis AS SD
	INNER JOIN StdAvenant AS SA ON (SD.idavenant = SA.IdAvenant)
	WHERE SD.iddevis = id_devis;
	
	SELECT idtarif, idoffre
	INTO id_tarif, id_offre
	FROM StdDevisDetail AS DD
	WHERE DD.iddevis = id_devis
	LIMIT 1;
	
	SELECT SC.LibelleCategorie, ST.CodeCategorie
	INTO libelle_categorie, code_categorie
	FROM StdTarif AS ST
	INNER JOIN StdCategorie AS SC ON (ST.IdCategorie = SC.IdCategorie)
	WHERE IdTarif = id_tarif;
	
	libelle_categorie := COALESCE(libelle_categorie, '');
	code_categorie := COALESCE(code_categorie, '000');

	libelle_offre := '';
	IF (id_produit = 5 AND id_offre IN (17, 18, 19, 20, 21, 22)) OR (id_produit = 1) THEN
		SELECT LibelleOffre
		INTO libelle_offre
		FROM StdOffre
		WHERE IdOffre = id_offre;
		libelle_offre := COALESCE(libelle_offre, '');
	END IF;
	
	RETURN QUERY
			SELECT SD.iddevis, CO.RaisonSociale, SC.LibelleIntermediaire, SD.idclient, SD.numerodevis, SD.numeroavenant, (TRIM((Cl.Nom || ' ' || COALESCE(Cl.Prenoms, ''))))::character varying AS nomclient,
					Cl.Adresse1 AS adresseclient, SD.dateeffet::date, SD.dateexpiration::date, SD.dateemission::date, (SD.dateexpiration::date - SD.dateeffet::date ) + 1 AS duree,
					SD.primenette, (SD.primenette-montant_fga) AS primenettehorsfga, montant_fga AS fga,
					SD.accessoire, SD.accessoirecompagnie, SD.AccessoireIntermediaire, SD.taxe AS taxeenregistrement, SD.primettc, COALESCE(SD.confirme, False) AS confirme, SP.libelleproduit,
					libelle_categorie AS libellecategorie, SD.CommissionIntermediaire, SD.CommissionGestionnaire, SD.CommissionAperiteur, Cl.titre_client, Cl.profession_client, Cl.type_assure,
					Cl.type_souscripteur, Cl.Telephone AS telephone_client, Cl.Mobile AS mobile_client, Cl.Adresse2 AS adresse_geographique, Cl.Email AS email_client,  CASE WHEN id_produit = 1 AND montant_cedeao = 0 THEN SD.cedeao ELSE montant_cedeao END AS cedeao,
					libelle_mouvement AS libellemouvement, (TRIM((Ass.Nom || ' ' || COALESCE(Ass.Prenoms, ''))))::character varying AS nomassure, Ass.Adresse1 AS adresseassure,
					(CASE WHEN SD.idproduit = 1 AND SD.flotte THEN 'FLOTTE AUTOMOBILE' ELSE libelle_offre END)::character varying AS offre, libelle_bareme AS libellebareme, CASE WHEN SD.IdProduit=5 THEN code_categorie ELSE '' END AS codecategorie,
					SD.primettc - (SD.primenette + SD.accessoire + SD.taxe) AS fraisgestion, COALESCE(SD.NumeroPoliceConnexe, '') AS numeropoliceconnexe, TRIM(SC.CodeIntermediaire)::character varying AS codeintermediaire,
					Cl.DateNaissance AS DateNaissanceClient, Ass.DateNaissance AS DateNaissanceAssure
			FROM StdDevis AS  SD
			INNER JOIN vue_client AS Cl ON(SD.idclient = Cl.IdClient)
			INNER JOIN vue_client AS Ass ON (SD.idassure = Ass.IdClient)
			INNER JOIN StdIntermediaire AS SC ON (SC.IdIntermediaire=SD.idintermediaire)
			INNER JOIN StdCompagnie AS CO ON(CO.IdCompagnie=SD.idcompagnie)
			INNER JOIN StdProduit AS SP ON (SD.idproduit = SP.idproduit)
			WHERE SD.iddevis = id_devis AND NOT SD.Archive ;
	
END; 
$BODY$;

ALTER FUNCTION public.fn_quittance_proposition(integer)
    OWNER TO uranususer;

