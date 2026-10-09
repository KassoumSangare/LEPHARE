-- Création ou modification (id_devis <> 0) d'un devis Dommages (produit 9), toutes catégories.
--
-- Reprend le déroulé de sp_creation_devis_tousrisquesinfo d'URANUS (numérotation de l'avenant et du
-- devis, en-tête, ligne unique, complément « dommage », garanties, taxes, accessoire, commission,
-- TTC), avec les primes de fn_garantie_offre_dommages : garanties de l'offre de la catégorie pour la
-- compagnie, capital et taux (ou prime saisie) par garantie.
-- Différences voulues avec la procédure d'URANUS :
--   - toutes les catégories 4xx (l'offre est celle du tarif), pas seulement TRI et Caution ;
--   - le numéro de police compagnie est enregistré (URANUS le recevait sans l'écrire) ;
--   - un devis repris sans ligne de détail reçoit sa ligne au lieu d'être refusé ;
--   - seules les garanties acquises sont enregistrées ;
--   - p_saisie (jsonb) garde ce qui n'a pas de colonne : description du risque, taux et primes saisis.
CREATE OR REPLACE PROCEDURE public.sp_creation_devis_dommages(
	IN p_id_intermediaire integer,
	IN p_id_compagnie integer,
	IN p_id_avenant integer,
	IN p_id_client integer,
	IN p_id_assure integer,
	IN p_date_effet date,
	IN p_date_expiration date,
	IN p_date_emission date,
	IN p_id_tarif integer,
	IN p_taux_reduction numeric,
	IN p_liste_garantie jsonb,
	IN p_prorata boolean,
	IN p_accessoire numeric,
	IN p_id_duree integer,
	IN p_numero_telephone_assure character varying,
	IN p_numero_police_compagnie character varying,
	IN p_saisie jsonb,
	IN p_user_id integer,
	INOUT id_devis integer,
	INOUT out_message character varying)
LANGUAGE plpgsql
AS $procedure$
DECLARE
	v_id_produit CONSTANT integer := 9;
	v_id_offre integer;
	v_code_categorie character varying(3);
	v_numero_avenant character varying(8);
	v_clef_avenant integer;
	v_numero_devis character varying(16);
	v_local_message character varying(500);
	v_id_devis_detail integer;
	v_id_devis_initial integer;
	v_periode character varying(1);
	v_id_duree integer;
	v_taux_commission numeric;
	v_capital_total numeric;
	v_taux_unique numeric;
	v_prime_saisie numeric;
	v_prime_imposee boolean;
	v_cumul RECORD;
	v_telephone character varying;
	v_police character varying;
	v_reduction numeric;
	v_msg TEXT;
BEGIN
	id_devis := COALESCE(id_devis, 0);
	v_id_devis_initial := id_devis;
	p_id_intermediaire := COALESCE(p_id_intermediaire, 0);
	p_id_avenant := COALESCE(NULLIF(p_id_avenant, 0), 1);
	p_id_assure := COALESCE(NULLIF(p_id_assure, 0), p_id_client);
	v_reduction := LEAST(GREATEST(COALESCE(p_taux_reduction, 0), 0), 100);
	v_telephone := TRIM(COALESCE(p_numero_telephone_assure, ''));
	v_police := NULLIF(TRIM(COALESCE(p_numero_police_compagnie, '')), '');

	IF p_date_effet IS NULL OR p_date_expiration IS NULL OR p_date_expiration < p_date_effet THEN
		out_message := 'Dates du contrat incorrectes : la date d''expiration doit suivre la date d''effet.';
		RAISE EXCEPTION '%', out_message;
	END IF;

	SELECT t.codecategorie INTO v_code_categorie FROM stdtarif AS t WHERE t.idtarif = p_id_tarif;
	IF v_code_categorie IS NULL OR v_code_categorie NOT LIKE '4%' THEN
		out_message := 'Catégorie hors de la branche Dommages. Opération impossible!';
		RAISE EXCEPTION '%', out_message;
	END IF;

	SELECT o.idoffre INTO v_id_offre
	FROM stdoffre AS o
	WHERE o.idtarif = p_id_tarif
	ORDER BY o.actif DESC, o.idoffre
	LIMIT 1;
	IF COALESCE(v_id_offre, 0) = 0 THEN
		out_message := 'Offre non paramétrée. Opération impossible!';
		RAISE EXCEPTION '%', out_message;
	END IF;

	v_id_duree := COALESCE(p_id_duree, 0);
	IF v_id_duree IN (0, 1) THEN
		v_id_duree := fn_calcul_id_duree_contrat(p_date_expiration - p_date_effet);
	END IF;
	v_periode := fn_calcul_periode_contrat(p_date_expiration - p_date_effet);
	v_taux_commission := COALESCE(fn_get_taux_commission(v_id_produit, p_id_compagnie, p_date_emission), 0);

	-- Primes de la saisie (mêmes montants que l'aperçu de l'écran)
	DROP TABLE IF EXISTS tmp_devis_dommages;
	CREATE TEMPORARY TABLE tmp_devis_dommages AS
		SELECT * FROM fn_garantie_offre_dommages(p_id_compagnie, v_id_offre, p_liste_garantie, v_reduction,
			p_date_effet, p_date_expiration, p_prorata, p_accessoire);

	IF NOT EXISTS (SELECT 1 FROM tmp_devis_dommages AS g WHERE g.idsousgarantie <> 0 AND g.acquise) THEN
		out_message := 'Aucune garantie retenue : cochez au moins une garantie.';
		RAISE EXCEPTION '%', out_message;
	END IF;

	SELECT * INTO v_cumul FROM tmp_devis_dommages AS g WHERE g.idsousgarantie = 0 LIMIT 1;
	SELECT COALESCE(SUM(g.capital), 0) INTO v_capital_total FROM tmp_devis_dommages AS g WHERE g.idsousgarantie <> 0 AND g.acquise;
	-- Complément « dommage » d'URANUS : taux commun à toutes les garanties, montant des primes saisies
	SELECT CASE WHEN COUNT(DISTINCT g.tauxprime) = 1 AND MIN(g.tauxprime) > 0 THEN MIN(g.tauxprime) ELSE 0 END,
		COALESCE(SUM(CASE WHEN g.tauxprime > 0 THEN 0 ELSE g.primeannuelle END), 0)
	INTO v_taux_unique, v_prime_saisie
	FROM tmp_devis_dommages AS g WHERE g.idsousgarantie <> 0 AND g.acquise;
	v_prime_imposee := (v_prime_saisie > 0) OR (p_accessoire IS NOT NULL);

	IF id_devis = 0 THEN
		CALL sp_numeroter_avenant(p_id_avenant, p_id_intermediaire, v_clef_avenant, v_numero_avenant);
		CALL sp_generer_numero_devis(p_id_intermediaire, p_id_compagnie, v_code_categorie, v_numero_devis, v_local_message);

		INSERT INTO stddevis (idoperateur, idoffre, idintermediaire, idcompagnie, idproduit, idclient, idassure, idavenant,
			numeroavenant, numerodevis, flotte, idaperiteur, coassurance, periode, dateemission, dateeffet, dateexpiration,
			confirme, accessoirecompagnie, idduree, numeropolicecompagnie, primeimposee)
		VALUES (p_user_id, v_id_offre, p_id_intermediaire, p_id_compagnie, v_id_produit, p_id_client, p_id_assure, p_id_avenant,
			v_numero_avenant, v_numero_devis, FALSE, p_id_compagnie, FALSE, v_periode, p_date_emission, p_date_effet, p_date_expiration,
			FALSE, 0, v_id_duree, v_police, v_prime_imposee)
		RETURNING stddevis.iddevis INTO id_devis;
		v_id_devis_detail := 0;
	ELSE
		IF NOT EXISTS (SELECT 1 FROM stddevis AS d WHERE d.iddevis = id_devis AND d.idproduit = v_id_produit) THEN
			out_message := 'Devis Dommages inexistant. Opération impossible!';
			RAISE EXCEPTION '%', out_message;
		END IF;
		IF EXISTS (SELECT 1 FROM stddevis AS d WHERE d.iddevis = id_devis AND d.confirme) THEN
			out_message := 'Devis déjà confirmé. Opération impossible!';
			RAISE EXCEPTION '%', out_message;
		END IF;
		IF EXISTS (SELECT 1 FROM stddevisdetail AS dd WHERE dd.iddevis = id_devis HAVING COUNT(*) > 1) THEN
			out_message := 'Données incohérentes: détails du devis redondants. Opération impossible!';
			RAISE EXCEPTION '%', out_message;
		END IF;

		UPDATE stddevis AS d
		SET idoperateur = p_user_id, idoffre = v_id_offre, idintermediaire = p_id_intermediaire, idcompagnie = p_id_compagnie,
			idclient = p_id_client, idassure = p_id_assure, idavenant = p_id_avenant, flotte = FALSE, idaperiteur = p_id_compagnie,
			coassurance = FALSE, periode = v_periode, dateemission = p_date_emission, dateeffet = p_date_effet,
			dateexpiration = p_date_expiration, accessoirecompagnie = 0, idduree = v_id_duree,
			numeropolicecompagnie = v_police, primeimposee = v_prime_imposee
		WHERE d.iddevis = id_devis;

		SELECT dd.iddevisdetail INTO v_id_devis_detail FROM stddevisdetail AS dd WHERE dd.iddevis = id_devis LIMIT 1;
		v_id_devis_detail := COALESCE(v_id_devis_detail, 0);
	END IF;

	IF v_id_devis_detail = 0 THEN
		-- Nouveau devis, ou devis repris d'URANUS sans ligne de détail
		INSERT INTO stddevisdetail (iddevis, idoffre, idtarif, vehicule, idusage, codeusage, reference, idcarrosserie, puissancefiscale,
			nombreplace, chargeutile, valeurneuve, valeurvenale, valeuraccessoire, remorque, conducteur, adressecnd, datemec,
			datemutation, nummoteur, numchassis, typevehicule, idmarque, matricule, carteverte, essence, numpccnd, tauxreduction,
			primeimposee)
		VALUES (id_devis, v_id_offre, p_id_tarif, 1, 0, '000', '000', 0, 0, 0, 0, v_capital_total, 0, 0, FALSE, '', '',
			'1900-01-01'::date, '1900-01-01'::date, '', '', '', 0, '', FALSE, 0, '', v_reduction, v_prime_imposee)
		RETURNING stddevisdetail.iddevisdetail INTO v_id_devis_detail;
	ELSE
		UPDATE stddevisdetail AS dd
		SET idoffre = v_id_offre, idtarif = p_id_tarif, vehicule = 1, valeurneuve = v_capital_total, valeurvenale = 0,
			valeuraccessoire = 0, tauxreduction = v_reduction, primeimposee = v_prime_imposee
		WHERE dd.iddevisdetail = v_id_devis_detail;
	END IF;

	IF EXISTS (SELECT 1 FROM stdcomplementdevisdetaildommage AS c WHERE c.iddevisdetail = v_id_devis_detail) THEN
		UPDATE stdcomplementdevisdetaildommage AS c
		SET tauxprime = v_taux_unique, montantprime = v_prime_saisie, saisie = p_saisie
		WHERE c.iddevisdetail = v_id_devis_detail;
	ELSE
		INSERT INTO stdcomplementdevisdetaildommage (tauxprime, montantprime, iddevisdetail, saisie)
		VALUES (v_taux_unique, v_prime_saisie, v_id_devis_detail, p_saisie);
	END IF;

	IF v_telephone <> '' THEN
		UPDATE stdclient AS c
		SET telephone = CASE WHEN TRIM(COALESCE(c.telephone, '')) IN ('', 'TELP') THEN v_telephone ELSE c.telephone END,
			mobile = CASE WHEN TRIM(COALESCE(c.mobile, '')) IN ('', 'MOBILE') THEN v_telephone ELSE c.mobile END
		WHERE c.idclient = p_id_assure;
	END IF;

	DELETE FROM stddevisdetgarantie AS g WHERE g.iddevisdet = v_id_devis_detail;
	INSERT INTO stddevisdetgarantie (iddevisdet, idgarantie, acquise, taxe, capital, tauxfranchise, minfranchise, maxfranchise,
		franchise, textefranchise, primeannuelle, primenette, old_acquise, old_primenette)
	SELECT v_id_devis_detail, g.idsousgarantie, TRUE, g.taxe, g.capital, g.tauxfranchise, g.franchiseminimum, g.franchisemaximum,
		0, g.textefranchise, g.primeannuelle, g.primenette, '1', g.primenette
	FROM tmp_devis_dommages AS g
	WHERE g.idsousgarantie <> 0 AND g.acquise;

	UPDATE stddevisdetail AS dd
	SET primeannuelle = v_cumul.primeannuelle, primenette = v_cumul.primenette,
		taxeenregistrement = v_cumul.taxe - v_cumul.taxeaccessoire
	WHERE dd.iddevisdetail = v_id_devis_detail;

	UPDATE stddevis AS d
	SET primeannuelle = v_cumul.primeannuelle, primenette = v_cumul.primenette,
		accessoirecompagnie = v_cumul.accessoirecompagnie, accessoireintermediaire = v_cumul.accessoireintermediaire,
		accessoire = v_cumul.accessoirecompagnie + v_cumul.accessoireintermediaire,
		taxe = v_cumul.taxe, fga = 0, cedeao = 0, primettc = v_cumul.primettc,
		commissionintermediaire = ROUND(v_cumul.primenette * v_taux_commission / 100, 0)
	WHERE d.iddevis = id_devis;

	out_message := 'Devis enregistré avec succès.';
	DROP TABLE IF EXISTS tmp_devis_dommages;

EXCEPTION WHEN others THEN
	GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
	IF v_id_devis_initial = 0 THEN
		id_devis := 0;
	END IF;
	out_message := v_msg;
	DROP TABLE IF EXISTS tmp_devis_dommages;
	RAISE EXCEPTION '%', out_message;
END;
$procedure$;
