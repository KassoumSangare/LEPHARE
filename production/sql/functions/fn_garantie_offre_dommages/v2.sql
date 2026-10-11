-- v2 (2026-10-11) : résultats identiques à URANUS (fn_garantie_offre_tousrisquesinfo), vérifiés sur des
-- saisies identiques : primes des garanties non arrondies avant la taxe (taxe arrondie par garantie,
-- TTC arrondie sur le total) ; réduction appliquée seulement aux primes calculées au taux (une prime
-- saisie est reprise telle quelle, comme dans URANUS).
-- Garanties et prime d'un devis Dommages (produit 9), toutes catégories (tarifs 4xx) :
-- Tous Risques Informatiques, Caution, Globale de Banque, Tous Risques Chantiers, Bris de Machines…
--
-- Même principe que fn_garantie_offre_tousrisquesinfo d'URANUS (prime = capital x taux, ou montant de
-- prime saisi ; réduction ; taxe d'enregistrement de la garantie ; accessoire du barème), mais les
-- garanties ne sont plus codées en dur (101, 62, 102, 243) : ce sont celles de l'offre de la catégorie
-- pour la compagnie (stdoffregarantie, réglées dans l'admin), chacune avec son capital et son taux.
--
-- p_liste_garantie : [{"id_garantie": <sous-garantie>, "acquise": true, "capital": 0, "taux": 0,
--                      "prime": 0, "taux_franchise": null, "franchise_minimum": null, "franchise_maximum": null}]
--   taux > 0 : prime annuelle = capital x taux / 100 ; sinon prime annuelle = prime saisie.
--   Franchise absente : celle de l'offre.
-- p_prorata : prime au prorata de la durée (jours / 365) quand le contrat n'est pas annuel ; URANUS
--   n'en applique pas (réglage de la catégorie, désactivé par défaut).
-- p_accessoire : NULL = barème de la compagnie (fn_get_accessoire) ; sinon accessoire imposé, partagé
--   compagnie / cabinet comme le barème, avec sa taxe.
--
-- Une ligne par garantie de l'offre (ou saisie), puis une ligne de cumul (idgarantie = idsousgarantie = 0)
-- qui porte aussi l'accessoire, sa taxe, la prime TTC et le coefficient de prorata appliqué.
CREATE OR REPLACE FUNCTION public.fn_garantie_offre_dommages(
	p_id_compagnie integer,
	p_id_offre integer,
	p_liste_garantie jsonb,
	p_taux_reduction numeric,
	p_date_effet date,
	p_date_expiration date,
	p_prorata boolean DEFAULT false,
	p_accessoire numeric DEFAULT NULL)
RETURNS TABLE(idgarantie integer, libellegarantie character varying, idsousgarantie integer, libellesousgarantie character varying,
	acquise boolean, capital numeric, tauxprime numeric, primeannuelle numeric, primenette numeric, tauxtaxe numeric, taxe numeric,
	tauxfranchise numeric, franchiseminimum numeric, franchisemaximum numeric, textefranchise character varying, ordre integer,
	accessoirecompagnie numeric, accessoireintermediaire numeric, taxeaccessoire numeric, primettc numeric, coefficientprorata numeric)
LANGUAGE plpgsql
AS $function$
#variable_conflict use_column
DECLARE
	v_reduction numeric;
	v_coef numeric := 1;
	v_pa_totale numeric;
	v_pn_totale numeric;
	v_taxe_totale numeric;
	v_acc_cie numeric := 0;
	v_acc_int numeric := 0;
	v_taxe_acc numeric := 0;
	v_taux_taxe_acc numeric;
BEGIN
	v_reduction := LEAST(GREATEST(COALESCE(p_taux_reduction, 0), 0), 100);

	IF COALESCE(p_prorata, FALSE) AND p_date_effet IS NOT NULL AND p_date_expiration IS NOT NULL
	   AND p_date_expiration >= p_date_effet
	   AND fn_calcul_id_duree_contrat(p_date_effet, p_date_expiration) <> 4 THEN
		v_coef := ROUND(((p_date_expiration - p_date_effet) + 1)::numeric / 365, 6);
	END IF;

	IF to_regclass('pg_temp.tmp_garantie_dommages') IS NULL THEN
		CREATE TEMPORARY TABLE tmp_garantie_dommages (
			t_idgar integer, t_libgar character varying, t_idsg integer, t_libsg character varying, t_acq boolean,
			t_cap numeric, t_taux numeric, t_pa numeric, t_pn numeric, t_tx numeric, t_taxe numeric,
			t_tf numeric, t_fmin numeric, t_fmax numeric, t_ordre integer);
	END IF;
	DELETE FROM tmp_garantie_dommages;

	INSERT INTO tmp_garantie_dommages
	WITH saisie AS (
		SELECT DISTINCT ON ((g->>'id_garantie')::integer)
			(g->>'id_garantie')::integer AS id_sg,
			COALESCE((g->>'acquise')::boolean, FALSE) AS acq,
			GREATEST(COALESCE(NULLIF(g->>'capital', '')::numeric, 0), 0) AS cap,
			GREATEST(COALESCE(NULLIF(g->>'taux', '')::numeric, 0), 0) AS taux,
			GREATEST(COALESCE(NULLIF(g->>'prime', '')::numeric, 0), 0) AS prime,
			NULLIF(g->>'taux_franchise', '')::numeric AS tf,
			NULLIF(g->>'franchise_minimum', '')::numeric AS fmin,
			NULLIF(g->>'franchise_maximum', '')::numeric AS fmax
		FROM jsonb_array_elements(COALESCE(p_liste_garantie, '[]'::jsonb)) AS g
		WHERE COALESCE(g->>'id_garantie', '') ~ '^[0-9]+$'
	),
	offre AS (
		SELECT DISTINCT ON (og.idsousgarantie)
			og.idsousgarantie AS id_sg, og.tauxfranchise AS tf, og.franchiseminimum AS fmin,
			og.franchisemaximum AS fmax, og.ordreaffichage AS ord
		FROM stdoffregarantie AS og
		WHERE og.idoffre = p_id_offre AND og.idcompagnie = p_id_compagnie AND og.idsousgarantie IS NOT NULL
		ORDER BY og.idsousgarantie, og.idoffregarantie
	),
	base AS (
		SELECT o.id_sg, o.tf, o.fmin, o.fmax, o.ord FROM offre AS o
		UNION ALL
		-- Garantie saisie hors de l'offre (offre modifiée depuis l'enregistrement du devis) : gardée
		SELECT s.id_sg, 0, 0, 0, 999 FROM saisie AS s WHERE s.id_sg NOT IN (SELECT o.id_sg FROM offre AS o)
	),
	lignes AS (
		SELECT ssg.idgarantie AS id_g, sg.libellegarantie AS lib_g, b.id_sg, ssg.libellesousgarantie AS lib_sg,
			COALESCE(s.acq, FALSE) AS acq,
			CASE WHEN COALESCE(s.acq, FALSE) THEN COALESCE(s.cap, 0) ELSE 0 END AS cap,
			CASE WHEN COALESCE(s.acq, FALSE) THEN COALESCE(s.taux, 0) ELSE 0 END AS taux,
			CASE
				WHEN NOT COALESCE(s.acq, FALSE) THEN 0
				WHEN COALESCE(s.taux, 0) > 0 THEN s.cap * s.taux / 100
				ELSE COALESCE(s.prime, 0)
			END AS pa,
			COALESCE(s.tf, b.tf, 0) AS tf, COALESCE(s.fmin, b.fmin, 0) AS fmin, COALESCE(s.fmax, b.fmax, 0) AS fmax,
			COALESCE((SELECT tt.tauxtaxe FROM stdtauxtaxegarantieproduit AS tt
			          WHERE tt.idgarantie = b.id_sg AND tt.idproduit = 9
			            AND COALESCE(p_date_effet, CURRENT_DATE) BETWEEN tt.debutvalidite AND tt.finvalidite
			          ORDER BY tt.debutvalidite DESC LIMIT 1), 0) AS tx,
			b.ord
		FROM base AS b
		JOIN stdsousgarantie AS ssg ON ssg.idsousgarantie = b.id_sg
		LEFT JOIN stdgarantie AS sg ON sg.idgarantie = ssg.idgarantie
		LEFT JOIN saisie AS s ON s.id_sg = b.id_sg
	)
	SELECT l.id_g, l.lib_g, l.id_sg, l.lib_sg, l.acq, l.cap, l.taux, l.pa,
		l.pa * (1 - (CASE WHEN l.taux > 0 THEN v_reduction ELSE 0 END) / 100) * v_coef AS pn,
		l.tx,
		ROUND(l.pa * (1 - (CASE WHEN l.taux > 0 THEN v_reduction ELSE 0 END) / 100) * v_coef * l.tx / 100, 0) AS taxe,
		l.tf, l.fmin, l.fmax, l.ord
	FROM lignes AS l;

	SELECT COALESCE(SUM(t.t_pa), 0), COALESCE(SUM(t.t_pn), 0), COALESCE(SUM(t.t_taxe), 0)
	INTO v_pa_totale, v_pn_totale, v_taxe_totale
	FROM tmp_garantie_dommages AS t
	WHERE t.t_acq;

	IF p_accessoire IS NULL THEN
		-- Barème de la compagnie pour le produit 9 (StdAccessoire), moitié compagnie / moitié cabinet
		-- pour NSIA, SUNU et AMSA, taxe au taux des garanties de l'offre
		SELECT a.accessoire_compagnie, a.accessoire_intermediaire, a.taxe_sur_accessoire
		INTO v_acc_cie, v_acc_int, v_taxe_acc
		FROM fn_get_accessoire(v_pn_totale, 9, p_id_offre, p_id_compagnie, COALESCE(p_date_effet, CURRENT_DATE)) AS a;
	ELSE
		-- Accessoire imposé : même partage et même taxe que le barème
		IF p_id_compagnie IN (1, 14, 21) THEN
			v_acc_cie := ROUND(GREATEST(p_accessoire, 0) / 2, 0);
			v_acc_int := ROUND(GREATEST(p_accessoire, 0), 0) - v_acc_cie;
		ELSE
			v_acc_cie := ROUND(GREATEST(p_accessoire, 0), 0);
			v_acc_int := 0;
		END IF;
		v_taux_taxe_acc := fn_get_taux_taxe(p_id_compagnie, 9, p_id_offre, COALESCE(p_date_effet, CURRENT_DATE));
		v_taxe_acc := ROUND((v_acc_cie + v_acc_int) * COALESCE(v_taux_taxe_acc, 0) / 100, 0);
	END IF;
	v_acc_cie := COALESCE(v_acc_cie, 0);
	v_acc_int := COALESCE(v_acc_int, 0);
	v_taxe_acc := COALESCE(v_taxe_acc, 0);

	RETURN QUERY
		SELECT t.t_idgar, t.t_libgar, t.t_idsg, t.t_libsg, t.t_acq, t.t_cap, t.t_taux, t.t_pa, t.t_pn, t.t_tx, t.t_taxe,
			t.t_tf, t.t_fmin, t.t_fmax, fn_franchise_texte(t.t_tf, t.t_fmin, t.t_fmax), t.t_ordre,
			0::numeric, 0::numeric, 0::numeric, 0::numeric, v_coef
		FROM tmp_garantie_dommages AS t
		ORDER BY t.t_ordre, t.t_idsg;

	RETURN QUERY
		SELECT 0, 'CUMUL DES MONTANTS DES GARANTIES'::character varying, 0, 'CUMUL DES MONTANTS DES S/GARANTIES'::character varying,
			TRUE, 0::numeric, 0::numeric, v_pa_totale, v_pn_totale, 0::numeric, v_taxe_totale + v_taxe_acc,
			0::numeric, 0::numeric, 0::numeric, ''::character varying, 9999,
			v_acc_cie, v_acc_int, v_taxe_acc, ROUND(v_pn_totale + v_acc_cie + v_acc_int + v_taxe_totale + v_taxe_acc, 0), v_coef;
END;
$function$;
