CREATE OR REPLACE FUNCTION public.fn_garantie_offre_voyage(id_compagnie integer, id_tarif integer, id_offre integer, id_zone_voyage integer, taux_reduction numeric, date_effet date, date_expiration date, date_naissance date)
 RETURNS TABLE(idgarantie integer, libellegarantie character varying, idsousgarantie integer, libellesousgarantie character varying, acquise boolean, capital numeric, nombreplace integer, primeannuelle numeric, primenette numeric, taxe numeric, montantaccessoire numeric)
 LANGUAGE plpgsql
AS $function$
DECLARE

	duree_contrat integer;
	--duree_totale integer;
	age integer;
	garantie_rec RECORD;
	prime_voyage numeric;

	----Pour le calcul des totaux des composantes de prime
	taux_taxe numeric;
	prime_annuelle_totale numeric;
	prime_nette_totale numeric;
	v_accessoire numeric;
	v_accessoire_intermediaire numeric;
	--taux_taxe_accessoire numeric;
	taxe_accessoire numeric;
	taxe_totale numeric;
	v_id_tarif integer;

BEGIN

	--duree_totale := CAST ((CAST (EXTRACT('year' FROM CURRENT_DATE) AS char(4)) || '-12-31') AS DATE) - CAST ((CAST (EXTRACT('year' FROM CURRENT_DATE) AS char(4)) || '-01-01') AS DATE) + 1;
	age := EXTRACT('year' FROM AGE(CURRENT_DATE, date_naissance));
	duree_contrat := date_expiration - date_effet;

	SELECT idtarif INTO v_id_tarif FROM public.stdoffre WHERE idoffre = id_offre;
	IF id_tarif <> v_id_tarif THEN
		id_tarif := v_id_tarif;
	END IF;

	prime_voyage := fn_calcul_prime_voyage_by_age(age,duree_contrat,id_zone_voyage,id_tarif,id_offre);

	---Initialisation des cumuls
	prime_annuelle_totale := 0;
	prime_nette_totale := 0;
	v_accessoire := 0;
	v_accessoire_intermediaire := 0;
	taxe_totale := 0;

	FOR garantie_rec IN (SELECT sg.IdGarantie as id_garantie, G.LibelleGarantie AS libelle_garantie, og.IdSousGarantie as id_sous_garantie, sg.LibelleSousGarantie AS libelle_sous_garantie, True AS garantie_acquise, 0 AS capital_garanti, 0 AS nombre_place, 0 AS prime_annuelle, 0 AS prime_nette, 0 AS taxe_enregistrement, 0 AS montant_accessoire
							FROM StdOffreGarantie AS og
							INNER JOIN StdSousGarantie AS sg ON(sg.IdSousGarantie=og.IdSousGarantie)
							INNER JOIN StdGarantie AS G ON(G.IdGarantie=sg.IdGarantie)
							WHERE IdOffre = id_offre AND IdCompagnie = id_compagnie
							ORDER BY 1
						)
	LOOP
		idgarantie := garantie_rec.id_garantie;
		libellegarantie := garantie_rec.libelle_garantie;
		idsousgarantie := garantie_rec.id_sous_garantie;
		libellesousgarantie := garantie_rec.libelle_sous_garantie;
		acquise := garantie_rec.garantie_acquise;
		capital := garantie_rec.capital_garanti;
		nombreplace := garantie_rec.nombre_place;
		primeannuelle := COALESCE(garantie_rec.prime_annuelle, 0.0);
		primenette := COALESCE(garantie_rec.prime_nette, 0.0);
		taxe := COALESCE(garantie_rec.taxe_enregistrement, 0.0);
		montantaccessoire := COALESCE(garantie_rec.montant_accessoire, 0.0);

		IF (garantie_rec.id_sous_garantie = 23) THEN
			primeannuelle := prime_voyage;
			primenette := prime_voyage - (prime_voyage * taux_reduction)/100;
			--Détermination de la prime de la période de couverture
			--primenette := ROUND((primenette * duree_contrat)/duree_totale,0);
		END IF;

		---Calcul de la taxe
		SELECT tauxtaxe
		INTO taux_taxe
		FROM stdtauxtaxegarantieproduit AS tt
		WHERE (idproduit = 3) AND (tt.idgarantie = garantie_rec.id_sous_garantie);
		taux_taxe := COALESCE(taux_taxe, 0);
		taxe := ROUND((primenette * taux_taxe)/100,0);

		---Faire le cumul des 2 composantes de prime (prime nette et taxe)
		prime_annuelle_totale := prime_annuelle_totale + primeannuelle;
		prime_nette_totale := prime_nette_totale + primenette;
		taxe_totale := taxe_totale + taxe;


		RETURN NEXT;

	END LOOP;

	--Calcul de l'accessoire
-- 	SELECT accessoires
-- 	INTO v_accessoire
-- 	FROM stdaccessoire
-- 	WHERE prime_nette_totale between primemin and primemax and idproduit = 3;

-- 	v_accessoire := COALESCE(v_accessoire, 0.0);
-- 	taux_taxe_accessoire := fn_get_taux_taxe(3, id_offre, date_effet);
-- 	taxe_accessoire := (v_accessoire * taux_taxe_accessoire)/100;
	SELECT *
	INTO v_accessoire, v_accessoire_intermediaire, taxe_accessoire
	FROM fn_get_accessoire(prime_nette_totale, 3, id_offre, id_compagnie, date_effet);
	--- Retourner la ligne des cumuls
	idgarantie := 0;
	libellegarantie := 'CUMUL DES MONTANTS DES GARANTIES';
	idsousgarantie := 0;
	libellesousgarantie := 'CUMUL DES MONTANTS DES S/GARANTIES';
	acquise := True;
	capital := 0.0;
	nombreplace := 0.0;
    primeannuelle := prime_annuelle_totale;
	primenette := prime_nette_totale;
	taxe := taxe_totale + taxe_accessoire;
	montantaccessoire := v_accessoire + v_accessoire_intermediaire;
	RETURN NEXT;

END;
$function$;
