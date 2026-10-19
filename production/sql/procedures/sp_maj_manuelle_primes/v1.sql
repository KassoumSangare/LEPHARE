-- Procédure d'URANUS telle qu'en base au 2026-10-19 (version d'origine, retour de la migration production 0167)
CREATE OR REPLACE PROCEDURE public.sp_maj_manuelle_primes(IN p_numero_devis character varying, IN p_prime_annuelle numeric, IN p_prime_nette numeric, IN p_accessoire numeric, IN p_taxe_enregistrement numeric, IN p_fga numeric, IN p_cedeao numeric, IN p_prime_ttc numeric)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
	v_id_devis INTEGER;
	v_id_quittance INTEGER;
	v_numero_police CHARACTER VARYING;
	v_id_produit INTEGER;
BEGIN

	 p_prime_annuelle := COALESCE(p_prime_annuelle, 0);
	 p_prime_nette := COALESCE(p_prime_nette, 0);
	 p_accessoire := COALESCE(p_accessoire, 0);
	 p_taxe_enregistrement := COALESCE(p_taxe_enregistrement, 0);
	 p_fga := COALESCE(p_fga, 0);
	 p_cedeao := COALESCE(p_cedeao, 0);
	 p_prime_ttc := COALESCE(p_prime_ttc, 0);
	 
	 SELECT iddevis, idproduit
	 INTO v_id_devis, v_id_produit
	 FROM public.stddevis
	 WHERE numerodevis = p_numero_devis AND NOT archive;
	 v_id_devis := COALESCE(v_id_devis, 0);
	 v_id_produit := COALESCE(v_id_produit, 0);

	 IF v_id_produit <> 1 THEN
	 	p_fga := 0;
	 	p_cedeao := 0;
	 END IF; 
	 
	 IF v_id_devis != 0 THEN
	 	UPDATE public.stddevis
		SET primeimposee = true, primeannuelle = p_prime_annuelle, primenette = p_prime_nette + p_fga, accessoire = p_accessoire, taxe = p_taxe_enregistrement, fga = p_fga, cedeao = p_cedeao, primettc = p_prime_ttc
		WHERE iddevis = v_id_devis;
		
		SELECT numeropolice, idquittance
		INTO v_numero_police, v_id_quittance
		FROM public.stdcontrat
		WHERE iddevis = v_id_devis;
		v_numero_police := TRIM(COALESCE(v_numero_police, ''));
		v_id_quittance := COALESCE(v_id_quittance, 0);
		
		UPDATE public.stdcontrat
		SET primeimposee = true, primeannuelle = p_prime_annuelle, primenette = p_prime_nette + p_fga, accessoire = p_accessoire, taxe = p_taxe_enregistrement, fga = p_fga, cedeao = p_cedeao, primettc = p_prime_ttc
		WHERE iddevis = v_id_devis;

		IF (v_numero_police != '') AND (v_id_quittance != 0) THEN
			UPDATE public.stdquittance
			SET primenette = p_prime_nette + p_fga, accessoire = p_accessoire, taxe = p_taxe_enregistrement, primettc = p_prime_ttc
			WHERE idquittance = v_id_quittance AND numeropolice = v_numero_police;
		END IF;
		
	 END IF;
END;
$procedure$;
