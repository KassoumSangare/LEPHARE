CREATE OR REPLACE FUNCTION public.fn_lephare_prime_ht(
	p_primenette numeric, p_accessoire numeric, p_taxe numeric, p_fga numeric, p_cedeao numeric, p_primettc numeric,
	p_primeimposee boolean DEFAULT FALSE)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Prime HT d'une quittance (colonne « Prime HT » des bordereaux d'OREOLE, base de la commission du courtier) : prime
-- nette hors accessoires, taxes, FGA et CEDEAO. Le FGA est toujours compris dans la prime nette enregistrée ; la
-- CEDEAO l'est si la prime a été calculée, pas si elle a été imposée (sp_maj_manuelle_primes). Même détection que
-- cedeaoDansPrimeNette (frontend/src/utils/tarificationAuto.js) : la composition qui retombe sur la TTC enregistrée
-- (telle quelle, arrondie à la pièce, ou au multiple de 5 supérieur d'URANUS), sinon selon la prime imposée.
-- Ex. JCW 2026 : 1 844 335 - FGA 4 449 = 1 839 886 (CEDEAO 3 000 hors prime nette, TTC 2 147 325).
DECLARE
	v_fga numeric := ROUND(COALESCE(p_fga, 0));
	v_cedeao numeric := ROUND(COALESCE(p_cedeao, 0));
	v_ttc numeric := ROUND(COALESCE(p_primettc, 0));
	v_somme numeric := ROUND(COALESCE(p_primenette, 0)) + ROUND(COALESCE(p_accessoire, 0)) + ROUND(COALESCE(p_taxe, 0));
	v_cedeao_incluse boolean;
BEGIN
	IF v_fga = 0 AND v_cedeao = 0 THEN
		RETURN COALESCE(p_primenette, 0);
	END IF;
	IF v_ttc IN (v_somme, public.fn_lephare_arrondi_montant(v_somme, 1), CEIL(v_somme / 5) * 5) THEN
		v_cedeao_incluse := TRUE;
	ELSIF v_cedeao <> 0 AND v_ttc IN (v_somme + v_cedeao, public.fn_lephare_arrondi_montant(v_somme + v_cedeao, 1),
	                                  CEIL((v_somme + v_cedeao) / 5) * 5) THEN
		v_cedeao_incluse := FALSE;
	ELSE
		v_cedeao_incluse := NOT COALESCE(p_primeimposee, FALSE);
	END IF;
	RETURN COALESCE(p_primenette, 0) - COALESCE(p_fga, 0) - CASE WHEN v_cedeao_incluse THEN COALESCE(p_cedeao, 0) ELSE 0 END;
END;
$function$;

CREATE OR REPLACE FUNCTION public.trg_fn_lephare_commission_courtier()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Rémunération du cabinet sur un contrat, quelle que soit la procédure qui l'enregistre (URANUS ou LE PHARE) :
-- 1. commission = prime HT (hors FGA et CEDEAO) x taux : les procédures la calculent sur la prime nette, FGA et
--    CEDEAO compris ; corrigée seulement quand elle vaut ce calcul (une commission saisie autrement est gardée) ;
-- 2. accessoires du cabinet = part réglée pour la compagnie (Administration > Compagnies > Reversements ; NSIA et
--    SUNU : 50/50), le reste à la compagnie ; sans réglage : barème « Accessoires du cabinet » inchangé.
DECLARE
	v_taux numeric := COALESCE(NEW.taux_commission, 0);
	v_part numeric;
BEGIN
	IF v_taux > 0 AND (COALESCE(NEW.fga, 0) <> 0 OR COALESCE(NEW.cedeao, 0) <> 0)
	   AND ABS(COALESCE(NEW.commissionintermediaire, 0) - ROUND(COALESCE(NEW.primenette, 0) * v_taux / 100)) <= 1 THEN
		NEW.commissionintermediaire := ROUND(public.fn_lephare_prime_ht(NEW.primenette, NEW.accessoire, NEW.taxe, NEW.fga,
		                                                                NEW.cedeao, NEW.primettc, NEW.primeimposee) * v_taux / 100);
	END IF;

	SELECT CASE WHEN COALESCE(d.reversement ->> 'PartAccessoiresCourtier', '') ~ '^[0-9]+([.][0-9]+)?$'
	            THEN (d.reversement ->> 'PartAccessoiresCourtier')::numeric END
	INTO v_part
	FROM public.lephare_compagnie_document d
	WHERE d.idcompagnie = NEW.idcompagnie;
	IF v_part IS NOT NULL AND v_part <= 100 THEN
		NEW.accessoireintermediaire := ROUND(COALESCE(NEW.accessoire, 0) * v_part / 100);
		NEW.accessoirecompagnie := COALESCE(NEW.accessoire, 0) - NEW.accessoireintermediaire - COALESCE(NEW.accessoiregestionnaire, 0);
	END IF;
	RETURN NEW;
END;
$function$;
