-- FUNCTION: public.fn_get_devis(integer, character varying, character varying, date, date, integer)

DROP FUNCTION IF EXISTS public.fn_get_devis;

CREATE OR REPLACE FUNCTION public.fn_get_devis(
	id_devis integer,
	numero_devis character varying DEFAULT ''::character varying,
	nom_client character varying DEFAULT ''::character varying,
	date_debut date DEFAULT NULL::date,
	date_fin date DEFAULT NULL::date,
	id_produit integer DEFAULT 1)
    RETURNS TABLE(iddevis_ integer, idproduit_ integer, flotte_ boolean, coassurance_ boolean, numerodevis_ character varying, referenceagent_ character varying, renouvelable_ boolean, echeance_ character varying, periode_ character varying, numeroavenant_ character varying, dateeffet_ timestamp with time zone, heuredebut_ timestamp with time zone, dateexpiration_ timestamp with time zone, confirme_ boolean, dateemission_ timestamp with time zone, transfere_ boolean, nbrech_ smallint, anticipation_ boolean, observation_ character varying, idoldhist_ integer, oldnumerodevis_ character varying, auteur_ boolean, primeannuelle_ numeric, primenette_ numeric, accessoire_ numeric, taxe_ numeric, primettc_ numeric, idoperateur_ integer, bonus_malus_ numeric, idenergie_ smallint, idhisto_ integer, accessoirecompagnie_ numeric, accessoiregestionnaire_ numeric, accessoireintermediaire_ numeric, commissionaperiteur_ numeric, commissiongestionnaire_ numeric, commissionintermediaire_ numeric, nomassure_ character varying, libelle_aperiteur_ character varying, libelle_avenant_ character varying, nomclient_ text, adressepostaleclient_ character varying, adressegeoclient_ character varying, emailclient_ character varying, telephoneclient_ character varying, libelle_compagnie_ character varying, libelle_intermediaire_ character varying, libelle_offre_ character varying, libelle_produit_ character varying, libelle_categorie_ character varying, id_contrat_ integer) 
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
BEGIN

	IF id_devis = 0 THEN
		id_devis := NULL;
	END IF;
	nom_client := TRIM(COALESCE(nom_client,''));
	numero_devis := TRIM(COALESCE(numero_devis,''));
	IF date_fin IS NULL THEN
		date_fin := CURRENT_DATE;
	END IF;
	IF date_debut IS NULL THEN
		date_debut := date_fin - INTERVAL '15 years';
	END IF;

	RETURN QUERY
		SELECT SDev.iddevis, SDev.idproduit, SDev.flotte, SDev.coassurance, COALESCE(SCont.NumeroPoliceCompagnie, SCont.Numeropolice, SDev.numerodevis), SDev.referenceagent, SDev.renouvelable, SDev.echeance, SDev.periode,
				SDev.numeroavenant, SDev.dateeffet, SDev.heuredebut, SDev.dateexpiration, SDev.confirme, SDev.dateemission, SDev.transfere,
				SDev.nbreche, SDev.anticipation, SDev.observation, SDev.idoldhist, SDev.oldnumerodevis, SDev.auteur, SDev.primeannuelle, SDev.primenette,
				SDev.accessoire, SDev.taxe, SDev.primettc, SDev.idoperateur, SDev.bonus_malus, SDev.idenergie, SDev.idhisto,
				SDev.accessoirecompagnie, SDev.AccessoireGestionnaire AS accessoiregestionnaire, SDev.AccessoireIntermediaire AS accessoireintermediaire,
				SDev.CommissionAperiteur AS commissionaperiteur, SDev.CommissionGestionnaire AS commissiongestionnaire,
				SDev.CommissionIntermediaire AS commissionintermediaire, nomassure, SAper.RaisonSociale AS aperiteur,
				SAven.LibelleAvenant AS avenant, TRIM(SCli.Nom) || ' ' || TRIM(COALESCE(SCli.Prenoms,'')) AS nomclient,
				COALESCE(SCli.Adresse1,'') AS adressepostaleclient, COALESCE(SCli.Adresse2,'') AS adressegeoclient,
				COALESCE(SCli.Email,'') AS emailclient, COALESCE(SCli.Telephone,'') AS telephoneclient, 																
				SComp.RaisonSociale AS compagnie, SInt.LibelleIntermediaire AS intermediaire,
				SOff.LibelleOffre AS offre, SProd.libelleproduit AS produit, COALESCE(SCat.LibelleCategorie,'NON SPECIFIEE') AS categorie, IdContrat AS idcontrat

		FROM public.vue_devis AS SDev
		INNER JOIN public.StdCompagnie AS SAper ON (SDev.idaperiteur = SAper.IdCompagnie)
		INNER JOIN public.StdAvenant AS SAven ON (SDev.idavenant = SAven.IdAvenant)
		INNER JOIN public.StdClient AS SCli ON (SDev.idclient = SCli.IdClient)
		INNER JOIN public.StdCompagnie AS SComp ON (SDev.idcompagnie = SComp.IdCompagnie)
		INNER JOIN public.StdIntermediaire AS SInt ON (SDev.idintermediaire = SInt.IdIntermediaire)
		INNER JOIN public.StdOffre AS SOff ON (SDev.idoffre = SOff.IdOffre)
		INNER JOIN public.StdProduit AS SProd ON (SDev.idproduit = SProd.idproduit)
		LEFT JOIN (SELECT SDet.iddevis, MIN(iddevisdetail) AS iddevisdetail
					FROM public.StdDevisDetail AS SDet
					WHERE SDet.iddevis = COALESCE(id_devis,SDet.iddevis)
					GROUP BY SDet.iddevis
					) AS MaxDet ON (SDev.iddevis = MaxDet.iddevis)
		LEFT JOIN public.StdDevisDetail AS SDevDet ON (MaxDet.iddevis = SDevDet.iddevis AND MaxDet.iddevisdetail = SDevDet.iddevisdetail)
		LEFT JOIN public.StdTarif AS STar ON (SDevDet.idtarif = STar.IdTarif)
		LEFT JOIN public.StdCategorie AS SCat ON (STar.IdCategorie = SCat.IdCategorie)
		LEFT JOIN public.StdContrat AS SCont ON (SDev.iddevis = SCont.IdDevis)
		WHERE SDev.IdProduit = id_produit AND (SDev.iddevis = COALESCE(id_devis, SDev.iddevis))
			AND NOT SDev.Archive
			AND (TRIM(SCli.Nom) LIKE (nom_client || '%'))
			AND (SDev.NumeroDevis LIKE (numero_devis || '%'))
			AND (SDev.DateEmission::date BETWEEN date_debut AND date_fin)
		ORDER BY SDev.DateEmission DESC
		LIMIT 500;

END;
$BODY$;

ALTER FUNCTION public.fn_get_devis
    OWNER TO uranususer;

