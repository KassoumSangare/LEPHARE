CREATE OR REPLACE FUNCTION public.fn_garantie_offre_voyage(id_compagnie integer, id_tarif integer, id_offre integer, id_zone_voyage integer, taux_reduction numeric, date_effet date, date_expiration date, date_naissance date)
 RETURNS TABLE(idgarantie integer, libellegarantie character varying, idsousgarantie integer, libellesousgarantie character varying, acquise boolean, capital numeric, nombreplace integer, primeannuelle numeric, primenette numeric, taxe numeric, montantaccessoire numeric)
 LANGUAGE plpgsql
AS $function$
-- Garanties et primes d'un devis Voyage d'après la grille de la compagnie (fn_grille_voyage) :
--   - prime de la grille sur les frais médicaux et pharmaceutiques (sous-garantie 29), diminuée
--     de la réduction et arrondie au franc ;
--   - accessoire de la ligne de grille (ligne de cumul) ;
--   - taxe au taux de la ligne sur prime nette + accessoire, arrondie au franc, comme les tarifs
--     des compagnies : la garantie porte la taxe de sa prime, la ligne de cumul la taxe totale ;
--   - âge à la date du jour (règle d'URANUS), durée en jours de couverture, date d'effet et
--     date d'expiration comprises.
-- Hors grille (âge, durée, offre non proposée dans la zone) : primes, accessoire et taxe à 0.
DECLARE
	duree_voyage integer;
	age integer;
	garantie_rec RECORD;
	prime_voyage numeric;
	v_accessoire numeric;
	v_taux_taxe numeric;
	v_id_tarif integer;
	prime_annuelle_totale numeric;
	prime_nette_totale numeric;
BEGIN
	age := EXTRACT('year' FROM AGE(CURRENT_DATE, date_naissance));
	duree_voyage := date_expiration - date_effet + 1;

	SELECT o.idtarif INTO v_id_tarif FROM public.stdoffre AS o WHERE o.idoffre = id_offre;
	id_tarif := COALESCE(v_id_tarif, id_tarif);

	SELECT g.prime_nette, g.accessoire, g.taux_taxe
	INTO prime_voyage, v_accessoire, v_taux_taxe
	FROM public.fn_grille_voyage(id_tarif, id_offre, id_zone_voyage, age, duree_voyage) AS g;
	prime_voyage := COALESCE(prime_voyage, 0);
	v_accessoire := CASE WHEN prime_voyage > 0 THEN COALESCE(v_accessoire, 0) ELSE 0 END;
	v_taux_taxe := COALESCE(v_taux_taxe, 0);

	prime_annuelle_totale := 0;
	prime_nette_totale := 0;

	FOR garantie_rec IN (SELECT sg.IdGarantie as id_garantie, G.LibelleGarantie AS libelle_garantie, og.IdSousGarantie as id_sous_garantie, sg.LibelleSousGarantie AS libelle_sous_garantie
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
		acquise := True;
		capital := 0;
		nombreplace := 0;
		primeannuelle := 0;
		primenette := 0;
		taxe := 0;
		montantaccessoire := 0;

		IF garantie_rec.id_sous_garantie = 29 THEN
			primeannuelle := prime_voyage;
			primenette := ROUND(prime_voyage - (prime_voyage * taux_reduction) / 100, 0);
			taxe := ROUND((primenette * v_taux_taxe) / 100, 0);
		END IF;

		prime_annuelle_totale := prime_annuelle_totale + primeannuelle;
		prime_nette_totale := prime_nette_totale + primenette;

		RETURN NEXT;
	END LOOP;

	--- Ligne des cumuls : taxe totale sur prime nette + accessoire
	idgarantie := 0;
	libellegarantie := 'CUMUL DES MONTANTS DES GARANTIES';
	idsousgarantie := 0;
	libellesousgarantie := 'CUMUL DES MONTANTS DES S/GARANTIES';
	acquise := True;
	capital := 0.0;
	nombreplace := 0.0;
	primeannuelle := prime_annuelle_totale;
	primenette := prime_nette_totale;
	taxe := ROUND(((prime_nette_totale + v_accessoire) * v_taux_taxe) / 100, 0);
	montantaccessoire := v_accessoire;
	RETURN NEXT;

END;
$function$;
