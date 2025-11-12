-- FUNCTION: public.fn_liste_contrat_encaissement(character varying, character varying)

-- DROP FUNCTION IF EXISTS public.fn_liste_contrat_encaissement(character varying, character varying);

CREATE OR REPLACE FUNCTION public.fn_liste_contrat_encaissement(
	reference_client character varying,
	reference_contrat character varying)
    RETURNS TABLE(idcontrat integer, idclient integer, libellecategorie character varying, numeropolice character varying, numeroavenant character varying, numeroquittance character varying, nomclient character varying, dateeffet date, dateexpiration date, dateemission date, duree integer, primenette numeric, taxeenregistrement numeric, commission numeric, accessoire numeric, primettc numeric, montantencaisse numeric, solde numeric) 
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$
DECLARE
    date_emission date;
BEGIN

	reference_client := TRIM(COALESCE(reference_client,''));
	reference_contrat := TRIM(COALESCE(reference_contrat, ''));
	
	IF (reference_contrat <> '') THEN
		date_emission := fn_try_cast_date(reference_contrat);
	END IF;
	
	IF (reference_client <> '') AND (reference_contrat <> '') THEN
		RETURN QUERY
			SELECT SD.IdContrat, SD.IdClient, CASE WHEN SD.Flotte THEN 'FLOTTE' ELSE SC.LibelleCategorie END AS libellecategorie,
			SD.NumeroPolice, SD.NumeroAvenant, COALESCE(SQ.NumeroQuittance, '') AS numeroquittance,
			 (TRIM((Cl.Nom || ' ' || COALESCE(Cl.Prenoms, ''))))::character varying AS nomclient, SD.DateEffet::date,
			 SD.DateExpiration::date, SD.DateEmission::date, (SD.DateExpiration::date - SD.DateEffet::date )::integer +1 AS duree,
			 SQ.PrimeNette, SQ.Taxe AS taxeenregistrement, SQ.Commission, SQ.Accessoire, SQ.PrimeTtc, COALESCE(SQ.Mt_Encaisse,0) AS montantencaisse, (SQ.PrimeTTC - COALESCE(SQ.Mt_Encaisse,0)) AS Solde
			FROM StdContrat AS  SD
			INNER JOIN (SELECT D.IdContrat, MIN (IdTarif) AS IdTarif
					    FROM StdContratDetail AS D
					    GROUP BY D.IdContrat) AS SCD ON (SD.IdContrat = SCD.IdContrat)
			INNER JOIN StdTarif AS ST ON (SCD.IdTarif = ST.IdTarif)
			INNER JOIN StdCategorie AS SC ON (ST.IdCategorie=SC.IdCategorie)
			INNER JOIN vue_client AS Cl ON(SD.IdClient = Cl.IdClient)
			INNER JOIN stdquittance AS SQ ON (SD.idquittance = SQ.idquittance AND SD.NumeroPolice = SQ.numeropolice)
			WHERE (COALESCE(SD.IdContratAnnulation,0) = 0) AND (SQ.PrimeTTC - COALESCE(SQ.Mt_Encaisse,0) > 0)
			      AND (TRIM(Cl.Nom) LIKE reference_client||'%' OR TRIM(Cl.Email) LIKE reference_client||'%'
			           OR TRIM(Cl.Telephone) LIKE reference_client||'%')
				  AND ((SD.DateEmission::date = (CASE WHEN date_emission IS NOT NULL THEN date_emission ELSE '1900-01-01'::date END))
					    OR (SD.NumeroPolice LIKE reference_contrat||'%')
						OR (SD.IdPolicePegas LIKE reference_contrat||'%')
					    OR (TRIM(SQ.NumeroQuittance) LIKE reference_contrat||'%')
					  );
	ELSIF (reference_contrat <> '') THEN
		RETURN QUERY
			SELECT SD.IdContrat, SD.IdClient, CASE WHEN SD.Flotte THEN 'FLOTTE' ELSE SC.LibelleCategorie END AS libellecategorie,
			SD.NumeroPolice, SD.NumeroAvenant, COALESCE(SQ.NumeroQuittance, '') AS numeroquittance,
			 (TRIM((Cl.Nom || ' ' || COALESCE(Cl.Prenoms, ''))))::character varying AS nomclient, SD.DateEffet::date,
			 SD.DateExpiration::date, SD.DateEmission::date, (SD.DateExpiration::date - SD.DateEffet::date )::integer +1 AS duree,
			 SQ.PrimeNette, SQ.Taxe AS taxeenregistrement, SQ.Commission, SQ.Accessoire, SQ.PrimeTtc, COALESCE(SQ.Mt_Encaisse,0) AS montantencaisse, (SQ.PrimeTTC - COALESCE(SQ.Mt_Encaisse,0)) AS Solde
			FROM StdContrat AS  SD
			INNER JOIN (SELECT D.IdContrat, MIN (IdTarif) AS IdTarif
					    FROM StdContratDetail AS D
					    GROUP BY D.IdContrat) AS SCD ON (SD.IdContrat = SCD.IdContrat)
			INNER JOIN StdTarif AS ST ON (SCD.IdTarif = ST.IdTarif)
			INNER JOIN StdCategorie AS SC ON (ST.IdCategorie=SC.IdCategorie)
			INNER JOIN vue_client AS Cl ON(SD.IdClient = Cl.IdClient)
			INNER JOIN stdquittance AS SQ ON (SD.idquittance = SQ.idquittance AND SD.NumeroPolice = SQ.numeropolice)
			WHERE (COALESCE(SD.IdContratAnnulation,0) = 0) AND (SQ.PrimeTTC - COALESCE(SQ.Mt_Encaisse,0) > 0)
				  AND ((SD.DateEmission::date = (CASE WHEN date_emission IS NOT NULL THEN date_emission ELSE '1900-01-01'::date END))
					    OR (SD.NumeroPolice LIKE reference_contrat||'%')
						OR (SD.IdPolicePegas LIKE reference_contrat||'%')
					    OR (TRIM(SQ.NumeroQuittance) LIKE reference_contrat||'%')
					  );
	ELSIF (reference_client <> '') THEN
		RETURN QUERY
			SELECT SD.IdContrat, SD.IdClient, CASE WHEN SD.Flotte THEN 'FLOTTE' ELSE SC.LibelleCategorie END AS LibelleCategorie,
			SD.NumeroPolice, SD.NumeroAvenant, COALESCE(SQ.numeroquittance, '') AS numeroquittance,
			 (TRIM((Cl.Nom || ' ' || COALESCE(Cl.Prenoms, ''))))::character varying AS nomclient, SD.DateEffet::date,
			 SD.DateExpiration::date, SD.DateEmission::date, (SD.DateExpiration::date - SD.DateEffet::date )::integer +1 AS duree,
			 SQ.PrimeNette, SQ.Taxe AS taxeenregistrement, SQ.Commission, SQ.Accessoire, SQ.PrimeTtc, COALESCE(SQ.Mt_Encaisse,0) AS montantencaisse, (SQ.PrimeTTC - COALESCE(SQ.Mt_Encaisse,0)) AS Solde
			FROM StdContrat AS  SD
			INNER JOIN (SELECT D.IdContrat, MIN (IdTarif) AS IdTarif
					    FROM StdContratDetail AS D
					    GROUP BY D.IdContrat) AS SCD ON (SD.IdContrat = SCD.IdContrat)
			INNER JOIN StdTarif AS ST ON (SCD.IdTarif = ST.IdTarif)
			INNER JOIN StdCategorie AS SC ON (ST.IdCategorie=SC.IdCategorie)
			INNER JOIN vue_client AS Cl ON(SD.IdClient = Cl.IdClient)
			INNER JOIN stdquittance AS SQ ON (SD.idquittance = SQ.idquittance AND SD.NumeroPolice = SQ.numeropolice )
			WHERE (COALESCE(SD.IdContratAnnulation,0) = 0) AND (SQ.PrimeTTC - COALESCE(SQ.Mt_Encaisse,0) > 0)
			      AND (TRIM(Cl.Nom) LIKE reference_client||'%' OR TRIM(Cl.Email) LIKE reference_client||'%'
			           OR TRIM(Cl.Telephone) LIKE reference_client||'%');
	ELSE
		RETURN QUERY
			SELECT SD.IdContrat, SD.IdClient, CASE WHEN SD.Flotte THEN 'FLOTTE' ELSE SC.LibelleCategorie END AS LibelleCategorie,
			SD.NumeroPolice, SD.NumeroAvenant, COALESCE(SQ.numeroquittance, '') AS numeroquittance,
			 (TRIM((Cl.Nom || ' ' || COALESCE(Cl.Prenoms, ''))))::character varying AS nomclient, SD.DateEffet::date,
			 SD.DateExpiration::date, SD.DateEmission::date, (SD.DateExpiration::date - SD.DateEffet::date )::integer +1 AS duree,
			 SQ.PrimeNette, SQ.Taxe AS taxeenregistrement, SQ.Commission, SQ.Accessoire, SQ.PrimeTtc, COALESCE(SQ.Mt_Encaisse,0) AS montantencaisse, (SQ.PrimeTTC - COALESCE(SQ.Mt_Encaisse,0)) AS Solde
			FROM StdContrat AS  SD
			INNER JOIN (SELECT D.IdContrat, MIN (IdTarif) AS IdTarif
					    FROM StdContratDetail AS D
					    GROUP BY D.IdContrat) AS SCD ON (SD.IdContrat = SCD.IdContrat)
			INNER JOIN StdTarif AS ST ON (SCD.IdTarif = ST.IdTarif)
			INNER JOIN StdCategorie AS SC ON (ST.IdCategorie=SC.IdCategorie)
			INNER JOIN vue_client AS Cl ON(SD.IdClient = Cl.IdClient)
			INNER JOIN stdquittance AS SQ ON (SD.idquittance = SQ.idquittance AND SD.NumeroPolice = SQ.numeropolice)
			WHERE (COALESCE(SD.IdContratAnnulation,0) = 0) AND (SQ.PrimeTTC - COALESCE(SQ.Mt_Encaisse,0) > 0);
	END IF;
		
END; 
$BODY$;

ALTER FUNCTION public.fn_liste_contrat_encaissement(character varying, character varying)
    OWNER TO uranususer;
