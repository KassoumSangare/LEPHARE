CREATE OR REPLACE FUNCTION public.fn_liste_garanties_souscrites(id_entite integer, entite character DEFAULT 'DEV'::bpchar)
 RETURNS TABLE(idsousgar integer, libellesousgar character varying, cap numeric, primeann numeric, primene numeric, txtfranchise character varying, decs numeric, infirmitepp numeric, fraistrt numeric, libelleopt character varying, garsouscrite boolean, textegarantiexclu text, textecapital text, texteprimeannuelle text, texteprimenette text, reductioncommerciale numeric, reductionbns numeric)
 LANGUAGE plpgsql
AS $function$
DECLARE
	libelle_option character varying;
	id_entite_detail integer;
	id_compagnie integer;
	reduction_commerciale numeric;
	reduction_bns numeric;
	capital_deces numeric;
	capital_ipp numeric;
	capital_ft numeric;
	prime_annuelle_fga numeric;
	prime_nette_fga numeric;
	
BEGIN
		CREATE TEMPORARY TABLE IF NOT EXISTS temp_sous_garantie_inter(codeentete character (5), idsousgarantie integer, libellesousgarantie character varying, capital numeric, primeannuelle numeric, primenette numeric, textefranchise character varying, deces numeric, ipp numeric, ft numeric, libelleoption character varying, souscrite boolean);
		--CREATE TEMPORARY TABLE IF NOT EXISTS temp_sous_garantie_res(idsousgarantie integer, libellesousgarantie character varying, capital numeric, primeannuelle numeric, primenette numeric, textefranchise character varying, deces numeric, ipp numeric, ft numeric, libelleoption character varying);
		TRUNCATE TABLE temp_sous_garantie_inter;
		--TRUNCATE TABLE temp_sous_garantie_res;
		entite := UPPER(COALESCE(entite,''));
		libelle_option := '';
		id_entite_detail := 0;
		IF entite = 'DEV' THEN
			SELECT IdCompagnie
			INTO id_compagnie
			FROM StdDevis
			WHERE IdDevis = id_entite AND IdProduit = 1;
			id_compagnie := COALESCE(id_compagnie, 0);
			IF EXISTS (SELECT 1 FROM StdDevis WHERE IdDevis = id_entite AND IdProduit = 1 AND NOT Flotte) THEN
				SELECT IdDevisDetail, TauxReduction
				INTO id_entite_detail, reduction_commerciale
				FROM StdDevisDetail
				WHERE IdDevis = id_entite
				LIMIT 1;

				id_entite_detail := COALESCE(id_entite_detail, 0);
				SELECT SAA.LibelleOption, SCA.bns
				INTO libelle_option, reduction_bns
				FROM StdComplementDevisDetailAuto AS SCA
				INNER JOIN StdAssistanceAutomobile AS SAA ON (SCA.IdOptionAssistance = SAA.IdOption)
				WHERE SCA.IdDevisDetail = id_entite_detail AND SCA.IdOptionAssistance <> 0;
				libelle_option := COALESCE(libelle_option, '');
			END IF;
			--RETURN QUERY
			INSERT INTO temp_sous_garantie_inter(codeentete, idsousgarantie, libellesousgarantie, capital, primeannuelle, primenette, textefranchise, deces, ipp, ft, libelleoption, souscrite)
			SELECT SSG.CodeEntete, COALESCE(GS.idsousgarantie, SSG.idsousgarantie), SSG.libellesousgarantie, COALESCE(GS.capital, 0.0000), COALESCE(GS.primeannuelle, 0.0000), COALESCE(GS.primenette, 0.0000),
					-- CASE WHEN (COALESCE(GS.tauxfranchise, 0.00) > 0) AND (id_compagnie IN (1, 14)) THEN fn_franchise_texte(COALESCE(GS.tauxfranchise, 0.00), COALESCE(GS.minfranchise, 0.0000), COALESCE(GS.maxfranchise, 0.0000))::character varying
					-- 	 WHEN (COALESCE(GS.tauxfranchise, 0.00) > 0) AND (id_compagnie NOT IN (1, 14)) THEN 'VOIR ANNEXES'::character varying
					-- 	 ELSE 'NEANT'::character varying END AS textefranchise,
					CASE WHEN (id_compagnie IN (1, 14)) THEN fn_franchise_texte(COALESCE(GS.tauxfranchise, 0.00), COALESCE(GS.minfranchise, 0.0000), COALESCE(GS.maxfranchise, 0.0000))::character varying
					ELSE 'NEANT'::character varying END AS textefranchise,
					COALESCE(GS.deces, 0.0000), COALESCE(GS.ipp, 0.0000), COALESCE(GS.ft, 0.0000), COALESCE(libelle_option, ''), GS.idsousgarantie IS NOT NULL
			FROM (SELECT SDG.IdGarantie AS idsousgarantie, MAX(SDG.Franchise) AS tauxfranchise, MAX(SDG.Capital) AS capital, SUM(SDG.PrimeAnnuelle) AS primeannuelle, SUM(SDG.PrimeNette) AS primenette, MAX(SDG.deces) AS deces, MAX(SDG.ipp) AS ipp, MAX(SDG.fraismed) AS ft,
							MAX(MinFranchise) AS minfranchise, MAX(MaxFranchise) AS maxfranchise
					FROM StdDevisDetGarantie AS SDG
					WHERE /* SDG.IdGarantie <> 2 AND */ SDG.IdDevisDet IN (SELECT IdDevisDetail FROM StdDevisDetail WHERE IdDevis = id_entite)
					GROUP BY IdGarantie
				  ) AS GS
			RIGHT JOIN (SELECT SG.IdSousGarantie, COALESCE(RSG.CodeEntete, '00000') AS CodeEntete, COALESCE(ESG.LibelleEntete, SG.LibelleSousGarantie) AS LibelleSousGarantie
						FROM StdSousGarantie AS SG
						LEFT JOIN StdRegroupementSousGarantie AS RSG ON (SG.idsousgarantie = RSG.idsousgarantie)
						LEFT JOIN StdEnteteSousGarantie AS ESG ON (RSG.CodeEntete = ESG.CodeEntete AND ESG.IdCompagnie = id_compagnie)
						) AS SSG ON (GS.IdSousGarantie = SSG.IdSousGarantie);
			--ORDER BY SSG.CodeEntete;
		ELSIF entite = 'CNT' THEN
			SELECT IdCompagnie
			INTO id_compagnie
			FROM StdContrat
			WHERE IdContrat = id_entite AND IdProduit = 1;
			id_compagnie := COALESCE(id_compagnie, 0);
			IF EXISTS (SELECT 1 FROM StdContrat WHERE IdContrat = id_entite AND IdProduit = 1 AND NOT Flotte) THEN
				SELECT IdContratDetail, TauxReduction
				INTO id_entite_detail, reduction_commerciale
				FROM StdContratDetail
				WHERE IdContrat = id_entite
				LIMIT 1;
				id_entite_detail := COALESCE(id_entite_detail, 0);
				SELECT SAA.LibelleOption, SCA.bns
				INTO libelle_option, reduction_bns
				FROM StdComplementContratDetailAuto AS SCA
				INNER JOIN StdAssistanceAutomobile AS SAA ON (SCA.IdOptionAssistance = SAA.IdOption)
				WHERE SCA.IdContratDetail = id_entite_detail AND SCA.IdOptionAssistance <> 0;
				libelle_option := COALESCE(libelle_option, '');
			END IF;
			--RETURN QUERY
			INSERT INTO temp_sous_garantie_inter(codeentete, idsousgarantie, libellesousgarantie, capital, primeannuelle, primenette, textefranchise, deces, ipp, ft, libelleoption, souscrite)
			SELECT SSG.CodeEntete, COALESCE(GS.idsousgarantie, SSG.idsousgarantie), SSG.libellesousgarantie, COALESCE(GS.capital, 0.0000), COALESCE(GS.primeannuelle, 0.0000), COALESCE(GS.primenette, 0.0000),
					-- CASE WHEN (COALESCE(GS.tauxfranchise, 0.00) > 0) AND (id_compagnie IN (1, 14)) THEN fn_franchise_texte(COALESCE(GS.tauxfranchise, 0.00), COALESCE(GS.minfranchise, 0.0000), COALESCE(GS.maxfranchise, 0.0000))::character varying
					-- 	 WHEN (COALESCE(GS.tauxfranchise, 0.00) > 0) AND (id_compagnie NOT IN (1, 14)) THEN 'VOIR ANNEXES'::character varying
					-- 	 ELSE 'NEANT'::character varying END AS textefranchise,
					CASE WHEN (id_compagnie IN (1, 14)) THEN fn_franchise_texte(COALESCE(GS.tauxfranchise, 0.00), COALESCE(GS.minfranchise, 0.0000), COALESCE(GS.maxfranchise, 0.0000))::character varying
					ELSE 'NEANT'::character varying END AS textefranchise,
					COALESCE(GS.deces, 0.0000), COALESCE(GS.ipp, 0.0000), COALESCE(GS.ft, 0.0000), COALESCE(libelle_option, ''), GS.idsousgarantie IS NOT NULL
			FROM (SELECT SDG.IdGarantie AS idsousgarantie, MAX(SDG.Franchise) AS tauxfranchise, MAX(SDG.Capital) AS capital, SUM(SDG.PrimeAnnuelle) AS primeannuelle, SUM(SDG.PrimeNette) AS primenette, MAX(SDG.deces) AS deces, MAX(SDG.ipp) AS ipp, MAX(SDG.fraismed) AS ft,
						  MAX(MinFranchise) AS minfranchise, MAX(MaxFranchise) AS maxfranchise
					FROM StdContratDetGarantie AS SDG
					WHERE /* SDG.IdGarantie <> 2 AND */ SDG.IdContratDetail IN (SELECT IdContratDetail FROM StdContratDetail WHERE IdContrat = id_entite)
					GROUP BY IdGarantie
				  ) AS GS
			RIGHT JOIN (SELECT SG.IdSousGarantie, COALESCE(RSG.CodeEntete, '00000') AS CodeEntete, COALESCE(ESG.LibelleEntete, SG.LibelleSousGarantie) AS LibelleSousGarantie
						FROM StdSousGarantie AS SG
						LEFT JOIN StdRegroupementSousGarantie AS RSG ON (SG.idsousgarantie = RSG.idsousgarantie)
						LEFT JOIN StdEnteteSousGarantie AS ESG ON (RSG.CodeEntete = ESG.CodeEntete AND ESG.IdCompagnie = id_compagnie)
						) AS SSG ON (GS.IdSousGarantie = SSG.IdSousGarantie);
			--ORDER BY SSG.CodeEntete;
		END IF;
		
		-- Ne pas afficher le FGA lorsque la compagnie est différentte de la NSIA
		IF id_compagnie <> 1 THEN
			DELETE FROM temp_sous_garantie_inter WHERE idsousgarantie = 2;
		ELSE -- Ajouter le FGA lorsqu'il s'agit de la NSIA
			-- IF NOT EXISTS (SELECT 1 FROM temp_sous_garantie_inter WHERE idsousgarantie = 2) THEN
				SELECT ROUND(TSGIN.primeannuelle * 2 / 100, 0), ROUND(TSGIN.primenette * 2 / 100, 0)
				INTO prime_annuelle_fga, prime_nette_fga
				FROM temp_sous_garantie_inter AS TSGIN
				WHERE TSGIN.idsousgarantie = 1;
				prime_annuelle_fga := COALESCE(prime_annuelle_fga, 0.0);
				prime_nette_fga := COALESCE(prime_nette_fga, 0.0);
				INSERT INTO temp_sous_garantie_inter(codeentete, idsousgarantie, libellesousgarantie, capital, primeannuelle, primenette, textefranchise, deces, ipp, ft, libelleoption, souscrite)
				VALUES ('00100', 2, 'FGA', 0.0, prime_annuelle_fga, prime_nette_fga, '', 0.0, 0.0, 0.0, '', True);
			-- END IF;
		END IF;
     /*
--Incendie: 30, 10
--Cedeao : 3
--Sécurité routière: 169
--Dommages: 7
--Vol: 12
--Vol à mains armées: 13
--Vol accessoires: 15

	 */
		IF id_compagnie <> 14 THEN
			UPDATE temp_sous_garantie_inter
			SET CodeEntete = CASE idsousgarantie WHEN 1 THEN '00000'
												 WHEN 164 THEN '00010'
												 WHEN 5 THEN '00015'
												 WHEN 12 THEN '00020'
												 WHEN 13 THEN '00025'
												 WHEN 14 THEN '00030'
												 WHEN 15 THEN '00035'
												 WHEN 3 THEN '00040'
												 WHEN 10 THEN '00045'
												 WHEN 9 THEN '00050'
												 WHEN 172 THEN '00055'
												 WHEN 175 THEN '00060'
												 WHEN 7 THEN '00065'
												 WHEN 174 THEN '00070'
												 WHEN 173 THEN '00075'
												 WHEN 176 THEN '00080'
												 WHEN 177 THEN '00085'
												 WHEN 178 THEN '00090'
												 WHEN 179 THEN '00095'
												 WHEN 2 THEN '00100'
												 WHEN 169 THEN '00105'
												 WHEN 123 THEN '00110'
			                                     WHEN 4 THEN '00115'
												 WHEN 6 THEN '00120'
												 WHEN 8 THEN '00125'
												 ELSE '00200' END;
			IF (id_compagnie = 1) AND EXISTS (SELECT 1 FROM temp_sous_garantie_inter WHERE idsousgarantie = 169) THEN
				
				SELECT TSGIN.deces, TSGIN.ipp, TSGIN.ft
				INTO capital_deces, capital_ipp, capital_ft
				FROM temp_sous_garantie_inter AS TSGIN
				WHERE TSGIN.idsousgarantie = 169;
				
				INSERT INTO temp_sous_garantie_inter(codeentete, idsousgarantie, libellesousgarantie, capital, primeannuelle, primenette, textefranchise, deces, ipp, ft, libelleoption, souscrite)
				VALUES ('00106', 19, '*** Capital Décès', capital_deces, 0.0, 0.0, '', 0.0, 0.0, 0.0, '', True),
						('00107', 17, '*** Incapacité', capital_ipp, 0.0, 0.0, '', 0.0, 0.0, 0.0, '', True),
						('00108', 20, '*** Frais Médicaux', capital_ft, 0.0, 0.0, '', 0.0, 0.0, 0.0, '', True);
						
				UPDATE temp_sous_garantie_inter
				SET capital = 0.0
				WHERE idsousgarantie = 169;
				
			END IF;
			
			RETURN QUERY
			SELECT idsousgarantie, libellesousgarantie, capital, primeannuelle, primenette, textefranchise, deces, ipp, ft, libelleoption, souscrite,
	               '' AS textegarantiexclusunu, '' AS textecapitalsunu, '' AS texteprimeannuellesunu, '' AS texteprimenettesunu,
				   CASE WHEN id_compagnie = 1 AND fn_sous_garantie_reductible_commerciale(idsousgarantie) THEN reduction_commerciale ELSE 0.0 END AS reductioncommerciale,
				   CASE WHEN id_compagnie = 1 AND fn_sous_garantie_reductible_bns(idsousgarantie) THEN reduction_bns ELSE 0.0 END AS reductionbns
				   
			FROM temp_sous_garantie_inter
			WHERE souscrite
			ORDER BY CodeEntete;
		ELSE
			UPDATE temp_sous_garantie_inter AS TGI
			SET primeannuelle = PC.primeannuelle, primenette = PC.primenette
			FROM (SELECT CodeEntete, SUM(primeannuelle) AS primeannuelle, SUM(primenette) AS primenette
				  FROM temp_sous_garantie_inter
				  GROUP BY CodeEntete) AS PC
			WHERE TGI.CodeEntete = PC.CodeEntete AND TGI.IdSousGarantie IN (1, 165, 4, 7, 8, 10, 12, 14, 9, 5, 17, 22, 168);
			
			RETURN QUERY
			SELECT idsousgarantie, libellesousgarantie, capital, primeannuelle, primenette, textefranchise, deces, ipp, ft, libelleoption, souscrite,
				   CASE souscrite WHEN True THEN 'Garanti' ELSE 'Exclu' END AS textegarantiexclusunu, fn_texte_capital_auto_sunu(idsousgarantie, capital) AS textecapitalsunu,
				   fn_texte_prime_auto_sunu(idsousgarantie, primeannuelle, souscrite) AS texteprimeannuellesunu, fn_texte_prime_auto_sunu(idsousgarantie, primenette, souscrite) AS texteprimenettesunu,
				    0.0 AS reductioncommerciale,
				    0.0 AS reductionbns
			FROM temp_sous_garantie_inter
			WHERE idsousgarantie IN (1, 165, 4, 7, 8, 10, 12, 14, 9, 5, 17, 22, 168)
			ORDER BY CodeEntete;
		END IF;
END;
$function$
