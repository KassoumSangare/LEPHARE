-- FUNCTION: public.fn_liste_vehicule_flotte(integer, boolean)

DROP FUNCTION IF EXISTS public.fn_liste_vehicule_flotte(integer, boolean);

CREATE OR REPLACE FUNCTION public.fn_liste_vehicule_flotte(
	id_entite integer,
	contrat boolean DEFAULT true)
    RETURNS TABLE(idcontrat integer, libelletarif character varying, libellecategorie character varying, idmarque integer, libellemarque character varying, idtypevehicule integer, libelletypevehicule character varying, chargeutile numeric, puissance smallint, immatriculation character varying, datemec date, codeenergie character varying, libelleenergie character varying, valeurneuve numeric, valeurvenale numeric, nombreplace smallint, rc numeric, fga numeric, cedeao numeric, recours numeric, recoursanticipe numeric, recoursexpress numeric, dommages numeric, collision numeric, brisdeglaces numeric, incendie numeric, explosion numeric, volsimple numeric, volmainsarmees numeric, vandalisme numeric, volaccessoires numeric, individuellechauffeur numeric, infirmitepermanente numeric, incapacitetemporaire numeric, deces numeric, fraistraitement numeric, immobilisation numeric, nsiaassistcar numeric, personnestransportees numeric, recourstiersincendie numeric, securiteroutiere numeric, primehorstaxes numeric, reduction numeric, montantprimenette numeric) 
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    ROWS 1000

AS $BODY$

BEGIN
	IF contrat THEN
		RETURN QUERY
				SELECT id_entite AS idcontrat, ST.Libelle AS libelletarif, SCat.LibelleCategorie AS libellecategorie,
					SCD.IdMarque AS idmarque, SM.LibelleMarque AS libellemarque,
					   SCD.IdTypeVehicule AS idtypevehicule, STV.LibelleType AS libelletypevehicule, SCD.ChargeUtile AS chargeutile,
					   SCD.PuissanceFiscale AS puissance, SCD.Matricule AS immatriculation, SCD.DateMec::date AS datemec, SCD.CodeCarburant AS codeenergie,
					   SE.Libelle AS libelleenergie, SCD.ValeurNeuve AS valeurneuve, SCD.ValeurVenale AS valeurvenale,
					   SCD.NombrePlace AS nombreplace, montant_rc, montant_fga, montant_cedeao, montant_recours, montant_recoursanticipe,
					   montant_recoursexpress, montant_dommages, montant_collision, montant_brisdeglaces, montant_incendie, montant_explosion,
					   montant_volsimple, montant_volmainsarmees, montant_vandalisme, montant_volaccessoires, montant_individuellechauffeur,
					   montant_infirmitepermanente, montant_incapacitetemporaire, montant_deces, montant_fraistraitement, montant_immobilisation,
					   montant_nsiaassistcar, montant_personnestransportees, montant_recourstiersincendie, montant_securiteroutiere, montant_primehorstaxes,
					   montant_reduction, montant_primenette
				FROM StdContratDetail AS SCD
				INNER JOIN StdTarif AS ST ON (SCD.IdTarif = ST.IdTarif)
				INNER JOIN StdCategorie AS SCat ON (ST.IdCategorie = SCat.IdCategorie)
				INNER JOIN StdMarque AS SM ON (SCD.IdMarque = SM.IdMarque)
				INNER JOIN StdTypeVehicule AS STV ON (SCD.IdTypeVehicule = STV.id)
				INNER JOIN StdEnergie AS SE ON (SCD.CodeCarburant = SE.CodeEnergie)
				INNER JOIN (SELECT IdContratDetail, SUM(CASE WHEN IdGarantie = 1 THEN PrimeNette ELSE 0 END) AS montant_rc,
						SUM(CASE WHEN IdGarantie = 1 THEN ROUND(PrimeNette * 0.02, 0) ELSE 0 END) AS montant_fga,
						SUM(CASE WHEN IdGarantie = 3 THEN PrimeNette ELSE 0 END) AS montant_cedeao,
						SUM(CASE WHEN IdGarantie = 4 THEN PrimeNette ELSE 0 END) AS montant_recours,
						SUM(CASE WHEN IdGarantie = 5 THEN PrimeNette ELSE 0 END) AS montant_recoursanticipe,
						SUM(CASE WHEN IdGarantie = 6 THEN PrimeNette ELSE 0 END) AS montant_recoursexpress,
						SUM(CASE WHEN IdGarantie = 7 THEN PrimeNette ELSE 0 END) AS montant_dommages,
						SUM(CASE WHEN IdGarantie = 8 THEN PrimeNette ELSE 0 END) AS montant_collision,
						SUM(CASE WHEN IdGarantie = 9 THEN PrimeNette ELSE 0 END) AS montant_brisdeglaces,
						SUM(CASE WHEN IdGarantie = 10 THEN PrimeNette ELSE 0 END) AS montant_incendie,
						SUM(CASE WHEN IdGarantie = 11 THEN PrimeNette ELSE 0 END) AS montant_explosion,
						SUM(CASE WHEN IdGarantie = 12 THEN PrimeNette ELSE 0 END) AS montant_volsimple,
						SUM(CASE WHEN IdGarantie = 13 THEN PrimeNette ELSE 0 END) AS montant_volmainsarmees,
						SUM(CASE WHEN IdGarantie = 14 THEN PrimeNette ELSE 0 END) AS montant_vandalisme,
						SUM(CASE WHEN IdGarantie = 15 THEN PrimeNette ELSE 0 END) AS montant_volaccessoires,
						SUM(CASE WHEN IdGarantie = 16 THEN PrimeNette ELSE 0 END) AS montant_individuellechauffeur,
						SUM(CASE WHEN IdGarantie = 17 THEN PrimeNette ELSE 0 END) AS montant_infirmitepermanente,
						SUM(CASE WHEN IdGarantie = 18 THEN PrimeNette ELSE 0 END) AS montant_incapacitetemporaire,
						SUM(CASE WHEN IdGarantie = 19 THEN PrimeNette ELSE 0 END) AS montant_deces,
						SUM(CASE WHEN IdGarantie = 20 THEN PrimeNette ELSE 0 END) AS montant_fraistraitement,
						SUM(CASE WHEN IdGarantie = 21 THEN PrimeNette ELSE 0 END) AS montant_immobilisation,
						SUM(CASE WHEN IdGarantie = 22 THEN PrimeNette ELSE 0 END) AS montant_nsiaassistcar,
						SUM(CASE WHEN IdGarantie = 163 THEN PrimeNette ELSE 0 END) AS montant_personnestransportees,
						SUM(CASE WHEN IdGarantie = 164 THEN PrimeNette ELSE 0 END) AS montant_recourstiersincendie,
						SUM(CASE WHEN IdGarantie = 169 THEN PrimeNette ELSE 0 END) AS montant_securiteroutiere,
						SUM(PrimeNette) AS montant_primehorstaxes,
						SUM(PrimeNette) AS montant_reduction,
						SUM(PrimeNette) AS montant_primenette
				FROM StdContratDetGarantie
				GROUP BY IdContratDetail) AS PG ON (SCD.IdContratDetail = PG.IdContratDetail)
				WHERE SCD.IdContrat = id_entite
				ORDER BY libelletarif, libellecategorie;
		ELSE
			RETURN QUERY
				SELECT id_entite AS iddevis, ST.Libelle AS libelletarif, SCat.LibelleCategorie AS libellecategorie,
					SCD.IdMarque AS idmarque, SM.LibelleMarque AS libellemarque,
					   SCD.IdTypeVehicule AS idtypevehicule, STV.LibelleType AS libelletypevehicule, SCD.ChargeUtile AS chargeutile,
					   SCD.PuissanceFiscale AS puissance, SCD.Matricule AS immatriculation, SCD.DateMec::date AS datemec, SE.CodeEnergie,
					   SE.Libelle AS libelleenergie, SCD.ValeurNeuve AS valeurneuve, SCD.ValeurVenale AS valeurvenale,
					   SCD.NombrePlace AS nombreplace, montant_rc, montant_fga, montant_cedeao, montant_recours, montant_recoursanticipe,
					   montant_recoursexpress, montant_dommages, montant_collision, montant_brisdeglaces, montant_incendie, montant_explosion,
					   montant_volsimple, montant_volmainsarmees, montant_vandalisme, montant_volaccessoires, montant_individuellechauffeur,
					   montant_infirmitepermanente, montant_incapacitetemporaire, montant_deces, montant_fraistraitement, montant_immobilisation,
					   montant_nsiaassistcar, montant_personnestransportees, montant_recourstiersincendie, montant_securiteroutiere, montant_primehorstaxes,
					   montant_reduction, montant_primenette
				FROM StdDevisDetail AS SCD
				INNER JOIN StdTarif AS ST ON (SCD.IdTarif = ST.IdTarif)
				INNER JOIN StdCategorie AS SCat ON (ST.IdCategorie = SCat.IdCategorie)
				INNER JOIN StdMarque AS SM ON (SCD.IdMarque = SM.IdMarque)
				INNER JOIN StdTypeVehicule AS STV ON (SCD.IdTypeVehicule = STV.id)
				INNER JOIN StdEnergie AS SE ON (SCD.Essence = SE.IdEnergie)
				INNER JOIN (SELECT IdDevisDet, SUM(CASE WHEN IdGarantie = 1 THEN PrimeNette ELSE 0 END) AS montant_rc,
						SUM(CASE WHEN IdGarantie = 1 THEN ROUND(PrimeNette * 0.02, 0) ELSE 0 END) AS montant_fga,
						SUM(CASE WHEN IdGarantie = 3 THEN PrimeNette ELSE 0 END) AS montant_cedeao,
						SUM(CASE WHEN IdGarantie = 4 THEN PrimeNette ELSE 0 END) AS montant_recours,
						SUM(CASE WHEN IdGarantie = 5 THEN PrimeNette ELSE 0 END) AS montant_recoursanticipe,
						SUM(CASE WHEN IdGarantie = 6 THEN PrimeNette ELSE 0 END) AS montant_recoursexpress,
						SUM(CASE WHEN IdGarantie = 7 THEN PrimeNette ELSE 0 END) AS montant_dommages,
						SUM(CASE WHEN IdGarantie = 8 THEN PrimeNette ELSE 0 END) AS montant_collision,
						SUM(CASE WHEN IdGarantie = 9 THEN PrimeNette ELSE 0 END) AS montant_brisdeglaces,
						SUM(CASE WHEN IdGarantie = 10 THEN PrimeNette ELSE 0 END) AS montant_incendie,
						SUM(CASE WHEN IdGarantie = 11 THEN PrimeNette ELSE 0 END) AS montant_explosion,
						SUM(CASE WHEN IdGarantie = 12 THEN PrimeNette ELSE 0 END) AS montant_volsimple,
						SUM(CASE WHEN IdGarantie = 13 THEN PrimeNette ELSE 0 END) AS montant_volmainsarmees,
						SUM(CASE WHEN IdGarantie = 14 THEN PrimeNette ELSE 0 END) AS montant_vandalisme,
						SUM(CASE WHEN IdGarantie = 15 THEN PrimeNette ELSE 0 END) AS montant_volaccessoires,
						SUM(CASE WHEN IdGarantie = 16 THEN PrimeNette ELSE 0 END) AS montant_individuellechauffeur,
						SUM(CASE WHEN IdGarantie = 17 THEN PrimeNette ELSE 0 END) AS montant_infirmitepermanente,
						SUM(CASE WHEN IdGarantie = 18 THEN PrimeNette ELSE 0 END) AS montant_incapacitetemporaire,
						SUM(CASE WHEN IdGarantie = 19 THEN PrimeNette ELSE 0 END) AS montant_deces,
						SUM(CASE WHEN IdGarantie = 20 THEN PrimeNette ELSE 0 END) AS montant_fraistraitement,
						SUM(CASE WHEN IdGarantie = 21 THEN PrimeNette ELSE 0 END) AS montant_immobilisation,
						SUM(CASE WHEN IdGarantie = 22 THEN PrimeNette ELSE 0 END) AS montant_nsiaassistcar,
						SUM(CASE WHEN IdGarantie = 163 THEN PrimeNette ELSE 0 END) AS montant_personnestransportees,
						SUM(CASE WHEN IdGarantie = 164 THEN PrimeNette ELSE 0 END) AS montant_recourstiersincendie,
						SUM(CASE WHEN IdGarantie = 169 THEN PrimeNette ELSE 0 END) AS montant_securiteroutiere,
						SUM(PrimeNette) AS montant_primehorstaxes,
						SUM(PrimeNette) AS montant_reduction,
						SUM(PrimeNette) AS montant_primenette
				FROM StdDevisDetGarantie
				GROUP BY IdDevisDet) AS PG ON (SCD.IdDevisDetail = PG.IdDevisDet)
				WHERE SCD.IdDevis = id_entite
				ORDER BY libelletarif, libellecategorie;
		END IF;

			
END; 
$BODY$;

ALTER FUNCTION public.fn_liste_vehicule_flotte(integer, boolean)
    OWNER TO uranususer;
