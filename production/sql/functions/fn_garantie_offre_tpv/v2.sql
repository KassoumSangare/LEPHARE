-- Migration production 0165 : l'offre « assureur » de la catégorie 204 (ex. NSIA « TIERS SIMPLE + SECURITE ROUTIERE
-- (CAT 204) ») échouait (« l'enregistrement v_pool n'est pas encore affecté ») : les montants du Pool sont copiés dans
-- des variables à 0 F hors offre Pool au lieu d'être lus dans l'enregistrement.
-- Garanties d'une offre de la catégorie 204 (transport public de voyageurs) pour le moteur (fn_garantie_offre) :
--   - offre « POOL TPV » : RC et Recours au tarif du Pool (fn_pool_tpv), CEDEAO de la catégorie,
--     accessoire du Pool pour la durée dans la ligne de cumul ; aucune réduction (tarif annoté NSIA, catégorie 4 :
--     « pas de réduction flotte ») ;
--   - autre offre (assureur) : garanties de l'offre à 0 F, primes de la compagnie à imposer (URANUS n'avait
--     aucun tarif TPV : ses devis TPV étaient en primes imposées).
-- Taxe de chaque garantie (CEDEAO exceptée) et de l'accessoire au taux de la compagnie (14,5 %).
CREATE OR REPLACE FUNCTION public.fn_garantie_offre_tpv(idcompagnie_ integer, idoffre_ integer, idtarif_ integer, puissance_ integer,
														 tonnage_ integer, nombreplace_ integer, dateeffet_ date, dateexpiration_ date)
 RETURNS TABLE(idgarantie integer, libellegarantie character varying, idsousgarantie integer, libellesousgarantie character varying,
			   acquise boolean, capital numeric, nombreplace smallint, primeannuelle numeric, primenette numeric, taxe numeric,
			   montantaccessoire numeric, tauxfranchise numeric, franchiseminimum numeric, franchisemaximum numeric,
			   franchisetexte character varying, idformule integer, capitaldeces numeric, capitalipp numeric, capitalft numeric)
 LANGUAGE plpgsql
AS $function$
DECLARE
	v_pool RECORD;
	v_est_pool boolean;
	v_taux numeric;
	v_cedeao numeric;
	v_accessoire numeric := 0;
	v_rc_annuelle numeric := 0;
	v_rc numeric := 0;
	v_recours_annuelle numeric := 0;
	v_recours numeric := 0;
BEGIN
	v_est_pool := public.fn_est_offre_pool_tpv(idoffre_);
	v_taux := COALESCE(public.fn_get_taux_taxe(idcompagnie_, 1, idoffre_, dateeffet_), 14.5);
	v_cedeao := public.fn_get_prime_cedeao(idtarif_, COALESCE(puissance_, 0)::smallint, COALESCE(tonnage_, 0));
	IF v_est_pool THEN
		SELECT P.* INTO v_pool FROM public.fn_pool_tpv(nombreplace_, dateeffet_, dateexpiration_) AS P;
		IF NOT FOUND THEN
			RAISE EXCEPTION 'Tarif du Pool TPV : aucune tranche pour % place(s) (Administration > Réglages Automobile > Pool TPV).', nombreplace_;
		END IF;
		v_accessoire := v_pool.accessoire;
		v_rc_annuelle := v_pool.prime_rc_annuelle;
		v_rc := v_pool.prime_rc;
		v_recours_annuelle := v_pool.prime_recours_annuelle;
		v_recours := v_pool.prime_recours;
	END IF;

	RETURN QUERY
	WITH lignes AS (
		SELECT SG.idgarantie AS idg, G.libellegarantie::character varying AS libg, OG.idsousgarantie AS idsg,
			   SG.libellesousgarantie::character varying AS libsg, OG.ordreaffichage AS ordre,
			   OG.tauxfranchise AS txf, OG.franchiseminimum AS fmin, OG.franchisemaximum AS fmax,
			   CASE WHEN OG.idsousgarantie = 3 THEN v_cedeao
					WHEN OG.idsousgarantie = 1 THEN v_rc_annuelle
					WHEN OG.idsousgarantie = 4 THEN v_recours_annuelle
					ELSE 0 END::numeric AS pa,
			   CASE WHEN OG.idsousgarantie = 3 THEN v_cedeao
					WHEN OG.idsousgarantie = 1 THEN v_rc
					WHEN OG.idsousgarantie = 4 THEN v_recours
					ELSE 0 END::numeric AS pn
		FROM public.stdoffregarantie AS OG
		INNER JOIN public.stdsousgarantie AS SG ON (SG.idsousgarantie = OG.idsousgarantie)
		INNER JOIN public.stdgarantie AS G ON (G.idgarantie = SG.idgarantie)
		WHERE OG.idoffre = idoffre_ AND OG.idcompagnie = idcompagnie_
	), taxees AS (
		SELECT L.*, CASE WHEN L.idsg = 3 THEN 0 ELSE ROUND(L.pn * v_taux / 100, 0) END::numeric AS tx FROM lignes AS L
	)
	SELECT T.idg, T.libg, T.idsg, T.libsg, TRUE, 0::numeric, 0::smallint, T.pa, T.pn, T.tx, 0::numeric,
		   COALESCE(T.txf, 0)::numeric, COALESCE(T.fmin, 0)::numeric, COALESCE(T.fmax, 0)::numeric,
		   'NEANT'::character varying, 0, 0::numeric, 0::numeric, 0::numeric
	FROM taxees AS T
	UNION ALL
	SELECT 0, 'CUMUL DES MONTANTS DES GARANTIES'::character varying, 0, 'CUMUL DES MONTANTS DES S/GARANTIES'::character varying, TRUE,
		   0::numeric, 0::smallint, COALESCE(SUM(T.pa), 0), COALESCE(SUM(T.pn), 0),
		   COALESCE(SUM(T.tx), 0) + ROUND(v_accessoire * v_taux / 100, 0), v_accessoire,
		   0::numeric, 0::numeric, 0::numeric, ''::character varying, 0, 0::numeric, 0::numeric, 0::numeric
	FROM taxees AS T;
END;
$function$;
