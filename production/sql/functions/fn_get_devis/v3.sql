-- RE-CRÉATION DE LA FONCTION fn_get_devis AVEC PAGINATION ET COMPTAGE

DROP FUNCTION IF EXISTS public.fn_get_devis;

CREATE OR REPLACE FUNCTION public.fn_get_devis(
    p_id_devis integer,
    p_numero_police character varying DEFAULT ''::character varying,
    p_nom_client character varying DEFAULT ''::character varying,
    p_date_debut date DEFAULT NULL::date,
    p_date_fin date DEFAULT NULL::date,
    p_id_produit integer DEFAULT 1,
    p_limit integer DEFAULT 50,    -- NOUVEAU : Taille de la page
    p_offset integer DEFAULT 0)   -- NOUVEAU : Point de départ
    RETURNS TABLE(
        -- Colonnes de la vue (doivent correspondre aux champs Python)
        iddevis integer, id_produit integer, flotte boolean, coassurance boolean, numerodevis character varying, 
        referenceagent character varying, renouvelable boolean, echeance character varying, periode character varying, 
        numeroavenant character varying, dateeffet timestamp with time zone, heuredebut timestamp with time zone, 
        dateexpiration timestamp with time zone, confirme boolean, dateemission timestamp with time zone, transfere boolean, 
        nbreche smallint, anticipation boolean, observation character varying, idoldhist integer, oldnumerodevis character varying, 
        auteur boolean, primeannuelle numeric, primenette numeric, accessoire numeric, taxe numeric, primettc numeric, 
        idoperateur integer, bonus_malus numeric, idenergie smallint, idhisto integer, accessoirecompagnie numeric, 
        accessoiregestionnaire numeric, accessoireintermediaire numeric, commissionaperiteur numeric, commissiongestionnaire numeric, 
        commissionintermediaire numeric, nomassure character varying, libelle_aperiteur character varying, libelle_avenant character varying, 
        nomclient text, adressepostaleclient character varying, adressegeoclient character varying, emailclient character varying, 
        telephoneclient character varying, libelle_compagnie character varying, libelle_intermediaire character varying, 
        libelle_offre character varying, libelle_produit character varying, libelle_categorie character varying, 
        id_contrat integer,
        -- Colonne de comptage pour la pagination côté client
        total_rows bigint   -- NOUVEAU : Pour le comptage total
    )
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000
AS $BODY$
DECLARE
    v_approx_rows bigint;
	v_numeros_devis_array CHARACTER VARYING[];
BEGIN

    -- Initialisation des paramètres de filtre
	v_numeros_devis_array := '{}';
    IF p_id_devis = 0 THEN p_id_devis := NULL; END IF;
    p_nom_client := TRIM(COALESCE(p_nom_client,''));
    p_numero_police := TRIM(COALESCE(p_numero_police,''));
    IF p_date_fin IS NULL THEN p_date_fin := CURRENT_DATE; END IF;
    IF p_date_debut IS NULL THEN p_date_debut := p_date_fin - INTERVAL '3 years'; END IF; -- Utilisé 3 ans pour correspondre à votre test

    -- OPTIMISATION : Suppression du coûteux COUNT(*).
    -- Nous affectons une valeur statique ou faisons une estimation légère.
    -- Ici, nous utilisons une estimation simple basée sur les statistiques de la table vue_devis, si elle est présente.
    -- (Sinon, mettre une valeur fixe comme 100000 pour éviter le blocage.)
    SELECT reltuples INTO v_approx_rows 
    FROM pg_class 
    WHERE relname = 'vue_devis';
    
    IF v_approx_rows IS NULL OR v_approx_rows = 0 THEN
        v_approx_rows := 100000; -- Valeur de secours si l'estimation échoue
    END IF;

	-- 2. Recherche des devis correspondants au numéro de police
	IF p_numero_police <> '' THEN
		SELECT ARRAY_AGG(T1.numerodevis) INTO v_numeros_devis_array
        FROM public.stddevis AS T1
        INNER JOIN public.stdcontrat AS T2
            ON T1.iddevis = T2.iddevis
        WHERE T2.numeropolice = v_numero_police_trim;
        
        -- Si la requête ne trouve rien, v_numeros_devis_array est NULL, nous devons le gérer
        IF v_numeros_devis_array IS NULL THEN
            v_numeros_devis_array := '{}'; -- S'assurer que ce n'est pas NULL
        END IF;
	END IF;
	
    -- 3. Retourne la requête paginée avec le comptage total
    RETURN QUERY
        SELECT 
            SDev.iddevis, SDev.idproduit, SDev.flotte, SDev.coassurance, COALESCE(SCont.NumeroPoliceCompagnie, SCont.Numeropolice, SDev.numerodevis), SDev.referenceagent, SDev.renouvelable, SDev.echeance, SDev.periode,
            SDev.numeroavenant, SDev.dateeffet, SDev.heuredebut, SDev.dateexpiration, SDev.confirme, SDev.dateemission, SDev.transfere,
            SDev.nbreche, SDev.anticipation, SDev.observation, SDev.idoldhist, SDev.oldnumerodevis, SDev.auteur, SDev.primeannuelle, SDev.primenette,
            SDev.accessoire, SDev.taxe, SDev.primettc, SDev.idoperateur, SDev.bonus_malus, SDev.idenergie, SDev.idhisto,
            SDev.accessoirecompagnie, SDev.AccessoireGestionnaire AS accessoiregestionnaire, SDev.AccessoireIntermediaire AS accessoireintermediaire,
            SDev.CommissionAperiteur AS commissionaperiteur, SDev.CommissionGestionnaire AS commissiongestionnaire,
            SDev.CommissionIntermediaire AS commissionintermediaire, SDev.nomassure, SAper.RaisonSociale AS libelle_aperiteur,
            SAven.LibelleAvenant AS libelle_avenant, TRIM(SCli.Nom) || ' ' || TRIM(COALESCE(SCli.Prenoms,'')) AS nomclient,
            COALESCE(SCli.Adresse1,'') AS adressepostaleclient, COALESCE(SCli.Adresse2,'') AS adressegeoclient,
            COALESCE(SCli.Email,'') AS emailclient, COALESCE(SCli.Telephone,'') AS telephoneclient,                                                                        
            SComp.RaisonSociale AS libelle_compagnie, SInt.LibelleIntermediaire AS libelle_intermediaire,
            SOff.LibelleOffre AS libelle_offre, SProd.libelleproduit AS libelle_produit, COALESCE(SCat.LibelleCategorie,'NON SPECIFIEE') AS libelle_categorie, IdContrat AS id_contrat,
            -- Ajout de la colonne de comptage total (même valeur pour toutes les lignes de la page)
            v_approx_rows AS total_rows

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
                   WHERE SDet.iddevis = COALESCE(p_id_devis,SDet.iddevis) 
                   GROUP BY SDet.iddevis
                   ) AS MaxDet ON (SDev.iddevis = MaxDet.iddevis)
        LEFT JOIN public.StdDevisDetail AS SDevDet ON (MaxDet.iddevis = SDevDet.iddevis AND MaxDet.iddevisdetail = SDevDet.iddevisdetail)
        LEFT JOIN public.StdTarif AS STar ON (SDevDet.idtarif = STar.IdTarif)
        LEFT JOIN public.StdCategorie AS SCat ON (STar.IdCategorie = SCat.IdCategorie)
        LEFT JOIN public.StdContrat AS SCont ON (SDev.iddevis = SCont.IdDevis)
        
        -- Clauses WHERE optimisées pour utiliser les paramètres de la PS
        WHERE SDev.IdProduit = p_id_produit 
            AND (SDev.iddevis = COALESCE(p_id_devis, SDev.iddevis))
            AND NOT SDev.Archive
            AND (TRIM(SCli.Nom) LIKE (p_nom_client || '%'))
            AND (-- Condition de non-filtrage : si le tableau est vide
                v_numeros_devis_array = '{}' 
                -- Condition de filtrage par police :
                OR SDev.numerodevis = ANY(v_numeros_devis_array))
            AND (SDev.DateEmission::date BETWEEN p_date_debut AND p_date_fin)
            
        ORDER BY SDev.DateEmission DESC
        LIMIT p_limit 
        OFFSET p_offset; -- Le cœur de la pagination

END;
$BODY$;
ALTER FUNCTION public.fn_get_devis OWNER TO uranususer;