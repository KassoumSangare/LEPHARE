-- Bareme automobile - ANNULATION de l'alignement NSIA (25/09/2026)
-- Equivalent SQL des migrations LE PHARE configuration_api 0068 et production 0141.
-- Rejouable sans risque : si ces migrations passent ensuite, elles reecrivent les memes valeurs.
-- Execution : psql -v ON_ERROR_STOP=1 -U <utilisateur> -d <base> -f annuler.sql

BEGIN;

UPDATE stdformulesecuriteroutiere SET primenette = 6000 WHERE idformule = 1 AND idcompagnie = 1 AND libelleformule = 'FORMULE I' AND nombreplace = 3;
UPDATE stdformulesecuriteroutiere SET primenette = 6000 WHERE idformule = 14 AND idcompagnie = 1 AND libelleformule = 'FORMULE I' AND nombreplace = 5;
UPDATE stdformulesecuriteroutiere SET primenette = 6000 WHERE idformule = 4 AND idcompagnie = 1 AND libelleformule = 'FORMULE I' AND nombreplace = 7;
UPDATE stdtarifdetail SET taux = 3.5 WHERE iddetail IN (1059, 1060, 1061) AND idtarif IN (121, 122, 123) AND idgarantie = 10 AND capitalmin = 10000001;

CREATE OR REPLACE FUNCTION public.fn_calcul_prime_prorata(id_sous_garantie integer, prime_nette numeric, bns numeric, duree_contrat integer, date_effet date)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
	taux_prime numeric;
BEGIN
	
	prime_nette := COALESCE(prime_nette, 0.0);
	taux_prime := fn_calcul_taux_prime_fractionnee(duree_contrat, date_effet);
  	IF id_sous_garantie NOT IN (3, 17, 18, 19, 20, 22, 163, 164, 169, 172, 173, 176, 177, 178, 179) THEN
			prime_nette := prime_nette * bns;
	END IF;

	IF (id_sous_garantie <> 3) THEN
		prime_nette := prime_nette * taux_prime;
	END IF;
	
  	RETURN ROUND(prime_nette, 0);

END;
$function$;

-- Verification (a lire dans la sortie) : 1:6000 14:6000 4:6000 / taux 3.5 / bonus bris de glace toits = false
SELECT string_agg(idformule || ':' || primenette::int, ' ' ORDER BY idformule) AS securite_routiere FROM stdformulesecuriteroutiere WHERE idformule IN (1, 14, 4);
SELECT string_agg(iddetail || ':' || taux, ' ' ORDER BY iddetail) AS incendie_tpc FROM stdtarifdetail WHERE iddetail IN (1059, 1060, 1061);
SELECT position('169, 173' IN prosrc) > 0 AS bonus_bris_glace_toits_applique FROM pg_proc WHERE proname = 'fn_calcul_prime_prorata' AND pronargs = 5 AND proargtypes::text LIKE '%1082';

COMMIT;
