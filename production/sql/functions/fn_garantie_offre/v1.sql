CREATE OR REPLACE FUNCTION public.fn_garantie_offre(idcompagnie_ integer, idoffre_ integer, idtarif_ integer, valneuve_ numeric, valvenale_ numeric, valaccessoire_ numeric, puissance_ integer, codecarburant_ integer, tonnage_ integer, tauxreduc_ numeric, codealarme_ integer, dateeffet_ date, dateexpiration_ date, bns_ numeric, datemec_ date, remorqueattelee_ boolean, formulesecuriteroutiere_ character varying, idoptionassistance_ integer, nombreplace_ integer, codeusage_ integer DEFAULT NULL::integer, carburantautrematiere_ boolean DEFAULT NULL::boolean, transporteleves_ boolean DEFAULT NULL::boolean, transportemployes_ boolean DEFAULT NULL::boolean, transportpassagersupplementaire_ boolean DEFAULT NULL::boolean, nsiaautoplus_ boolean DEFAULT NULL::boolean)
 RETURNS TABLE(idgarantie integer, libellegarantie character varying, idsousgarantie integer, libellesousgarantie character varying, acquise boolean, capital numeric, nombreplace smallint, primeannuelle numeric, primenette numeric, taxe numeric, montantaccessoire numeric, tauxfranchise numeric, franchiseminimum numeric, franchisemaximum numeric, franchisetexte character varying, idformule integer, capitaldeces numeric, capitalipp numeric, capitalft numeric)
 LANGUAGE plpgsql
AS $function$
DECLARE
	code_categorie character varying(3);
BEGIN

	SELECT CodeCategorie
	INTO code_categorie
	FROM StdTarif
	WHERE IdTarif = idtarif_;
	code_categorie := COALESCE(code_categorie, '000');
	
	IF code_categorie IN ('201','212') THEN  ---PROMENADE ET AFFAIRES, ENGINS MOBILES DE CHANTIER
		IF idcompagnie_ = 1 THEN --- NSIA
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat1_nsia(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_, nsiaautoplus_, idoptionassistance_);
		ELSIF idcompagnie_ = 21 THEN --AMSA
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat1_amsa(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_);

		ELSIF idcompagnie_ = 14 THEN --SUNU
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat1_sunu(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, idoptionassistance_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_);
		END IF;
	ELSIF code_categorie = '202' THEN
		IF idcompagnie_ = 1 THEN --- NSIA
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat2_nsia(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_, nsiaautoplus_, idoptionassistance_);
		ELSIF idcompagnie_ = 21 THEN --AMSA
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat2_amsa(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_);

		ELSIF idcompagnie_ = 14 THEN --SUNU
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat2_sunu(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, idoptionassistance_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_);
		END IF;
		
	ELSIF code_categorie IN ('209', '203') THEN
		IF idcompagnie_ = 1 THEN --- NSIA
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat3_nsia(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_, nsiaautoplus_, idoptionassistance_);
		ELSIF idcompagnie_ = 21 THEN --AMSA
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat3_amsa(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_);

		ELSIF idcompagnie_ = 14 THEN --SUNU
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat3_sunu(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, idoptionassistance_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_);
		END IF;
	
	ELSIF code_categorie = '205' THEN
		IF idcompagnie_ = 1 THEN --- NSIA
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat5_nsia(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_, nsiaautoplus_, idoptionassistance_);
		ELSIF idcompagnie_ = 21 THEN --AMSA
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat5_amsa(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_);

		ELSIF idcompagnie_ = 14 THEN --SUNU
			RETURN QUERY
				SELECT *
				FROM fn_garantie_offre_cat5_sunu(idcompagnie_, idoffre_, idtarif_, valneuve_, valvenale_, valaccessoire_, puissance_, codecarburant_, tonnage_, tauxreduc_,
												codealarme_, dateeffet_, dateexpiration_, bns_, datemec_, remorqueattelee_, formulesecuriteroutiere_, nombreplace_, codeusage_,
												carburantautrematiere_, transporteleves_, transportemployes_, transportpassagersupplementaire_);
		END IF;
	END IF;
	
END; 
$function$;
