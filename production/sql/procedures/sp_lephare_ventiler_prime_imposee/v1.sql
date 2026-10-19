CREATE OR REPLACE PROCEDURE public.sp_lephare_ventiler_prime_imposee(IN p_id_devis integer)
 LANGUAGE plpgsql
AS $procedure$
-- Prime imposée (demande du 2026-10-19 : « quand on impose une prime, faire apparaître cette prime sur les fiches ») :
-- sp_maj_manuelle_primes n'écrit que l'en-tête du devis (et du contrat, de la quittance) ; les garanties gardaient les
-- primes du barème, et les documents qui les additionnent (conditions particulières, liste des véhicules d'une flotte)
-- imprimaient la prime du système au lieu de la prime imposée.
-- Ici, les garanties acquises du devis — et du contrat qui en est issu — sont ramenées à la prime nette imposée, au
-- prorata de leurs primes calculées (plus forts restes : la somme tombe juste au franc) ; la taxe de chaque garantie
-- est recalculée à son taux (stdtauxtaxegarantieproduit, comme sp_correction_devis), sa prime annuelle suit le même
-- rapport ; les totaux par véhicule / assuré / maison (stddevisdetail, stdcontratdetail) suivent l'écart.
-- Hors ventilation : FGA (2, composante de prime) et CEDEAO (3, montant légal fixe). Cible : prime nette hors FGA et
-- CEDEAO (fn_lephare_prime_ht). Rien n'est fait si les garanties retombent déjà sur la prime imposée.
DECLARE
	v_produit integer;
	v_date date;
	v_cible numeric;
	v_id_contrat integer;
BEGIN
	SELECT d.idproduit, d.dateeffet::date,
	       ROUND(public.fn_lephare_prime_ht(d.primenette, d.accessoire, d.taxe, d.fga, d.cedeao, d.primettc, d.primeimposee))
	INTO v_produit, v_date, v_cible
	FROM public.stddevis d
	WHERE d.iddevis = p_id_devis;
	IF NOT FOUND OR v_cible IS NULL OR v_cible <= 0 THEN
		RETURN;
	END IF;

	-- ---------------------------------------------------------------- garanties du devis
	CREATE TEMPORARY TABLE IF NOT EXISTS tmp_lephare_ventilation (id integer, iddetail integer, ancienne numeric, nouvelle numeric) ON COMMIT DROP;
	TRUNCATE tmp_lephare_ventilation;
	INSERT INTO tmp_lephare_ventilation (id, iddetail, ancienne)
	SELECT g.iddevisdetgarantie, g.iddevisdet, COALESCE(g.primenette, 0)
	FROM public.stddevisdetgarantie g
	JOIN public.stddevisdetail dd ON dd.iddevisdetail = g.iddevisdet
	WHERE dd.iddevis = p_id_devis AND COALESCE(g.acquise, FALSE) AND g.idgarantie NOT IN (2, 3);

	IF (SELECT COALESCE(SUM(ancienne), 0) FROM tmp_lephare_ventilation) > 0
	   AND ABS((SELECT SUM(ancienne) FROM tmp_lephare_ventilation) - v_cible) > 1 THEN
		-- Prorata, parts entières, reliquat aux plus forts restes
		WITH total AS (SELECT SUM(ancienne) AS s FROM tmp_lephare_ventilation),
		     brut AS (SELECT t.id, v_cible * t.ancienne / total.s AS b FROM tmp_lephare_ventilation t, total),
		     rang AS (SELECT id, FLOOR(b) AS base, ROW_NUMBER() OVER (ORDER BY b - FLOOR(b) DESC, b DESC, id) AS r FROM brut),
		     reste AS (SELECT v_cible - SUM(base) AS k FROM rang)
		UPDATE tmp_lephare_ventilation t
		SET nouvelle = rang.base + CASE WHEN rang.r <= reste.k THEN 1 ELSE 0 END
		FROM rang, reste
		WHERE rang.id = t.id;

		UPDATE public.stddevisdetgarantie g
		SET primenette = t.nouvelle,
		    primeannuelle = CASE WHEN t.ancienne > 0 THEN ROUND(COALESCE(g.primeannuelle, 0) * t.nouvelle / t.ancienne) ELSE g.primeannuelle END,
		    taxe = COALESCE(
		        (SELECT ROUND(t.nouvelle * tt.tauxtaxe / 100) FROM public.stdtauxtaxegarantieproduit tt
		         WHERE tt.idgarantie = g.idgarantie AND tt.idproduit = v_produit AND v_date BETWEEN tt.debutvalidite AND tt.finvalidite
		         LIMIT 1),
		        CASE WHEN t.ancienne > 0 THEN ROUND(COALESCE(g.taxe, 0) * t.nouvelle / t.ancienne) ELSE g.taxe END)
		FROM tmp_lephare_ventilation t
		WHERE g.iddevisdetgarantie = t.id;

		-- Totaux de chaque véhicule / assuré / maison : l'écart de ses garanties
		UPDATE public.stddevisdetail dd
		SET primenette = COALESCE(dd.primenette, 0) + e.ecart
		FROM (SELECT iddetail, SUM(nouvelle - ancienne) AS ecart FROM tmp_lephare_ventilation GROUP BY iddetail) e
		WHERE dd.iddevisdetail = e.iddetail;
		UPDATE public.stddevisdetail dd
		SET taxeenregistrement = s.taxe
		FROM (SELECT g.iddevisdet, SUM(COALESCE(g.taxe, 0)) AS taxe FROM public.stddevisdetgarantie g
		      WHERE g.iddevisdet IN (SELECT DISTINCT iddetail FROM tmp_lephare_ventilation) AND g.idgarantie <> 2
		      GROUP BY g.iddevisdet) s
		WHERE dd.iddevisdetail = s.iddevisdet;
	END IF;

	-- ---------------------------------------------------------------- contrat issu du devis (imposition après confirmation)
	SELECT c.idcontrat,
	       ROUND(public.fn_lephare_prime_ht(c.primenette, c.accessoire, c.taxe, c.fga, c.cedeao, c.primettc, c.primeimposee))
	INTO v_id_contrat, v_cible
	FROM public.stdcontrat c
	WHERE c.iddevis = p_id_devis
	ORDER BY c.idcontrat DESC
	LIMIT 1;
	IF v_id_contrat IS NULL OR v_cible IS NULL OR v_cible <= 0 THEN
		RETURN;
	END IF;
	TRUNCATE tmp_lephare_ventilation;
	INSERT INTO tmp_lephare_ventilation (id, iddetail, ancienne)
	SELECT g.idcontratdetgarantie, g.idcontratdetail, COALESCE(g.primenette, 0)
	FROM public.stdcontratdetgarantie g
	JOIN public.stdcontratdetail cd ON cd.idcontratdetail = g.idcontratdetail
	WHERE cd.idcontrat = v_id_contrat AND COALESCE(g.acquise, FALSE) AND g.idgarantie NOT IN (2, 3);

	IF (SELECT COALESCE(SUM(ancienne), 0) FROM tmp_lephare_ventilation) > 0
	   AND ABS((SELECT SUM(ancienne) FROM tmp_lephare_ventilation) - v_cible) > 1 THEN
		WITH total AS (SELECT SUM(ancienne) AS s FROM tmp_lephare_ventilation),
		     brut AS (SELECT t.id, v_cible * t.ancienne / total.s AS b FROM tmp_lephare_ventilation t, total),
		     rang AS (SELECT id, FLOOR(b) AS base, ROW_NUMBER() OVER (ORDER BY b - FLOOR(b) DESC, b DESC, id) AS r FROM brut),
		     reste AS (SELECT v_cible - SUM(base) AS k FROM rang)
		UPDATE tmp_lephare_ventilation t
		SET nouvelle = rang.base + CASE WHEN rang.r <= reste.k THEN 1 ELSE 0 END
		FROM rang, reste
		WHERE rang.id = t.id;

		UPDATE public.stdcontratdetgarantie g
		SET primenette = t.nouvelle,
		    primeannuelle = CASE WHEN t.ancienne > 0 THEN ROUND(COALESCE(g.primeannuelle, 0) * t.nouvelle / t.ancienne) ELSE g.primeannuelle END,
		    taxe = COALESCE(
		        (SELECT ROUND(t.nouvelle * tt.tauxtaxe / 100) FROM public.stdtauxtaxegarantieproduit tt
		         WHERE tt.idgarantie = g.idgarantie AND tt.idproduit = v_produit AND v_date BETWEEN tt.debutvalidite AND tt.finvalidite
		         LIMIT 1),
		        CASE WHEN t.ancienne > 0 THEN ROUND(COALESCE(g.taxe, 0) * t.nouvelle / t.ancienne) ELSE g.taxe END)
		FROM tmp_lephare_ventilation t
		WHERE g.idcontratdetgarantie = t.id;

		UPDATE public.stdcontratdetail cd
		SET primenette = COALESCE(cd.primenette, 0) + e.ecart
		FROM (SELECT iddetail, SUM(nouvelle - ancienne) AS ecart FROM tmp_lephare_ventilation GROUP BY iddetail) e
		WHERE cd.idcontratdetail = e.iddetail;
		UPDATE public.stdcontratdetail cd
		SET taxeenregistrement = s.taxe
		FROM (SELECT g.idcontratdetail, SUM(COALESCE(g.taxe, 0)) AS taxe FROM public.stdcontratdetgarantie g
		      WHERE g.idcontratdetail IN (SELECT DISTINCT iddetail FROM tmp_lephare_ventilation) AND g.idgarantie <> 2
		      GROUP BY g.idcontratdetail) s
		WHERE cd.idcontratdetail = s.idcontratdetail;
	END IF;
END;
$procedure$;
