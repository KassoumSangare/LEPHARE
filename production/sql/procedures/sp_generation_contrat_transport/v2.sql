-- PROCEDURE: public.sp_generation_contrat_transport(integer, character varying, character varying)

-- DROP PROCEDURE IF EXISTS public.sp_generation_contrat_transport(integer, character varying, character varying);

CREATE OR REPLACE PROCEDURE public.sp_generation_contrat_transport(
	IN id_devis integer,
	IN numero_police character varying,
	INOUT out_message character varying)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
	local_message varchar(500);
	commit_var int;
	police_locale varchar(50);
	vehicule_ int;
	id_avenant int;
	date_effet date;
	date_emission date;
	code_avenant character varying(5);
	id_intermediaire int; 
	old_date_effet date;
	flotte_ boolean;
	numero_police_local varchar(16);
	taux_commission numeric(5,2);
	matricule_ varchar(10);
	id_devis_detail int;
	id_contrat_detail int;
	id_contrat_det_garantie int;
	id_tarif int;
	id_produit int;
	id_compagnie int;
	id_assure int;
	id_offre int;
	code_categorie char(3);
	var_devis RECORD;
	var_devis_detail RECORD;
	id_quittance int;
	liste_matricules character varying;
	motif_annulation character varying;
	devis_archive boolean;
	taxe_devis numeric :=0;
	id_contrat integer;
	----Gestion des erreurs
	v_state   TEXT;
    v_msg     TEXT;
    v_detail  TEXT;
    v_hint    TEXT;
    v_context TEXT;
	
BEGIN
	id_contrat := 0;
	out_message := '';
	local_message := '';
	id_quittance := 0;
  	SELECT numerodevis,
         dateeffet,
         idavenant,		 
         idintermediaire,
         flotte,
         idoldhist,
		 idproduit,
		 idassure,
		 idcompagnie,
		 dateemission,
		 motifannulation,
		 COALESCE(archive, False) AS archive
	INTO var_devis
    FROM public.StdDevis      
    WHERE iddevis = id_devis;    
   
   	police_locale := var_devis.numerodevis;
    date_effet := var_devis.dateeffet;
	date_emission := var_devis.dateemission;
    id_avenant  := var_devis.idavenant;		 
    id_intermediaire := var_devis.idintermediaire;
	id_compagnie := var_devis.idcompagnie;
    flotte_     := var_devis.flotte;
	id_produit  := COALESCE(var_devis.idproduit,0);
	id_assure := var_devis.idassure;

	   
	IF devis_archive THEN
		out_message := 'Devis archivé. Confirmation impossible!';
		RAISE EXCEPTION '%', out_message;
	END IF;
	
  	SELECT CodeAvenant
	INTO code_avenant
    FROM public.StdAvenant
    WHERE IdAvenant = id_avenant;
	
	UPDATE public.StdDevis 
	SET confirme=True
	WHERE iddevis=id_devis;

    SELECT idcontrat
    INTO id_contrat
    FROM public.StdContrat
    WHERE iddevis = id_devis;
    id_contrat := COALESCE(id_contrat, 0);

    IF (id_contrat = 0) THEN
	
        INSERT INTO public.StdContrat (IdDevis, IdOldHist, IdIntermediaire, IdProduit, IdCompagnie, IdClient, IdAssure, IdAvenant,
                                Flotte, Coassurance, IdAperiteur, NumeroPolice, Renouvelable, Echeance,
                                Periode, NumeroAvenant, DateEffet, HeureDebut, DateExpiration,
                                DateEmission, Transfere, NbrEche, Anticipation, Observation, OldNumeroDevis, Auteur,
                                IdOperateur, Bonus_Malus, Assure, IdDuree, IdTerme, MotifAnnulation, NumeroPoliceConnexe, primeimposee)

        SELECT iddevis, idoldhist, idintermediaire, idproduit, idcompagnie, idclient, idassure, idavenant,
            flotte, coassurance, idaperiteur, numero_police, renouvelable, echeance,
            periode, numeroavenant, dateeffet, heuredebut, dateexpiration, dateemission, transfere,
            nbreche, anticipation, observation, oldnumerodevis, auteur, idoperateur, bonus_malus, nomassure, idduree, idterme, motifannulation,
            numeropoliceconnexe, primeimposee
        FROM public.StdDevis
        WHERE iddevis = id_devis
        RETURNING IdContrat INTO id_contrat;
    ELSE
        UPDATE public.StdContrat AS SC
        SET IdOldHist = SD.idoldhist, IdIntermediaire = SD.idintermediaire, IdProduit = SD.idproduit, IdCompagnie = SD.idcompagnie, IdClient = SD.idclient,
            IdAssure = SD.idassure, IdAvenant = SD.idavenant, Flotte = SD.flotte, Coassurance = SD.coassurance, IdAperiteur = SD.idaperiteur, NumeroPolice = SD.numero_police,
            Renouvelable = SD.renouvelable, Echeance = SD.echeance, Periode = SD.periode, NumeroAvenant = SD.numeroavenant, DateEffet = SD.dateeffet, HeureDebut = SD.heuredebut, DateExpiration = SD.dateexpiration,
            DateEmission = SD.dateemission, Transfere = SD.transfere, NbrEche = SD.nbreche, Anticipation = SD.anticipation, Observation = SD.observation, OldNumeroDevis = SD.oldnumerodevis, Auteur = SD.auteur,
            IdOperateur = SD.idoperateur, Bonus_Malus = SD.bonus_malus, Assure = SD.nomassure, IdDuree = SD.idduree, IdTerme = SD.idterme, MotifAnnulation = SD.motifannulation, NumeroPoliceConnexe = SD.numeropoliceconnexe
        FROM public.stddevis AS SD
        WHERE SC.iddevis = SD.iddevis AND SD.iddevis = id_devis;

        DELETE FROM public.StdContratDetail WHERE idcontrat = id_contrat;
    END IF;

    FOR var_devis_detail IN (SELECT iddevisdetail FROM public.StdDevisDetail WHERE iddevis=id_devis)
    LOOP
        id_devis_detail := var_devis_detail.iddevisdetail;
        INSERT INTO public.StdContratDetail (IdContrat, modelevehicule, CarteVerte, NumCarteVerte, IdAssure, IdTarif, IdProduit, IdOffre, Mt_Delegation, idusage, CodeUsage, Reference, IdCarrosserie, Matricule,
                                        PuissanceFiscale, NombrePlace, ChargeUtile, ValeurNeuve, ValeurVenale, ValeurAccessoire, Remorque, CodeCarburant,
                                        Matrem1, Matrem2, Extincteur, Conducteur, Assure, AdresseCnd, Sexe, DateMec, NumMoteur, NumChassis, NbreExtinteur, IdMarque,
                                        idtypevehicule, idgenrevehicule, Attestation, TypePermis, Permis, PrimeAnnuelle, PrimeNette, IdOldContratDet, OldNumeroPolice, OldTypeVehicule, taxeenregistrement, fga, idprofession, tauxreduction, codealarme)
        SELECT id_contrat, modelevehicule, carteverte, numcarteverte, id_assure, idtarif, id_produit, idoffre, 0 AS mt_delegation, idusage, codeusage, reference, idcarrosserie, matricule, puissancefiscale, nombreplace, chargeutile,
            valeurneuve, valeurvenale, valeuraccessoire, remorque, COALESCE(SEner.CodeEnergie,'0000'), matrem1, matrem2, False as extincteur, conducteur,'' AS assure, adressecnd,
            sexe, datemec, nummoteur, numchassis, 0 AS nombreextincteur, idmarque, idtypevehicule, idgenrevehicule, attestation,pctype,permis,primeannuelle, primenette, 0, '000', '', taxeenregistrement, fga, idprofession, tauxreduction, codealarme
        FROM public.StdDevisDetail AS SDevDet
        LEFT JOIN public.StdEnergie AS SEner ON (SDevDet.essence = SEner.IdEnergie)
        WHERE (iddevis = id_devis) AND (iddevisdetail = id_devis_detail);
        --RETURNING IdContratDetail INTO id_contrat_detail;
    END LOOP;
	
	UPDATE public.StdContrat AS SC
	SET AccessoireCompagnie = SD.AccessoireCompagnie, AccessoireIntermediaire = SD.AccessoireIntermediaire,
		Accessoire = SD.Accessoire, Taxe = SD.Taxe, PrimeNette = SD.PrimeNette, PrimeAnnuelle = SD.PrimeAnnuelle,
		PrimeTTC = SD.PrimeTTC, Fga = SD.fga
	FROM public.StdDevis AS SD
	WHERE SC.IdContrat = id_contrat AND SC.IdDevis = SD.IdDevis AND SD.IdDevis = id_devis;

	CALL public.sp_generation_quittance_transport (id_contrat, id_quittance, out_message);

	IF (id_contrat <> 0) AND (id_quittance <> 0) THEN
		out_message := 'Contrat enregistré avec succès.';
	END IF;

	EXCEPTION WHEN others THEN
	
		get stacked diagnostics
        	v_state   = returned_sqlstate,
        	v_msg     = message_text,
        	v_detail  = pg_exception_detail,
        	v_hint    = pg_exception_hint,
        	v_context = pg_exception_context;
			
		id_contrat := 0;
		out_message := v_msg; -- || ' : ' || v_context; -- 'Problème rencontré lors de la création du devis';
		
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
$BODY$;
ALTER PROCEDURE public.sp_generation_contrat_transport(integer, character varying, character varying)
    OWNER TO uranususer;

