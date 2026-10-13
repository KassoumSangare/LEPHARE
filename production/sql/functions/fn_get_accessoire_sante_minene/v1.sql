CREATE OR REPLACE FUNCTION public.fn_get_accessoire_sante_minene(id_offre integer, prime_nette_sante numeric, montant_accessoire_manuel numeric, nombre_adherent integer)
 RETURNS TABLE(accessoire_compagnie numeric, accessoire_intermediaire numeric, taxe_sur_accessoire numeric)
 LANGUAGE plpgsql
AS $function$
DECLARE
	tx_taxe_acc numeric;
	acc_compagnie numeric; 
	acc_intermediaire numeric;
	acc_sante numeric;
	taxe_sur_acc numeric;
	
BEGIN

		acc_intermediaire := 0;
		acc_compagnie := 0;
		acc_sante := 0;
		
		IF(COALESCE(montant_accessoire_manuel,0) = 0) THEN
			acc_sante := fn_get_accessoire_compagnie(prime_nette_sante, 5, 1);
		ELSE
			acc_sante := montant_accessoire_manuel;
		END IF;
		
		IF id_offre IN (17, 18, 19, 175, 176, 181) THEN
			acc_compagnie := acc_sante;
			taxe_sur_acc := ROUND((acc_sante * 8.0)/100,0);
		ELSIF id_offre IN (20, 21, 22) THEN
			acc_compagnie := acc_sante;
			taxe_sur_acc := ROUND((acc_sante * 8.0)/100,0);
		END IF;
		
		acc_compagnie := acc_compagnie * nombre_adherent;
		taxe_sur_acc := taxe_sur_acc * nombre_adherent;
		
		RETURN QUERY
			SELECT acc_compagnie AS accessoire_compagnie, acc_intermediaire AS accessoire_intermediaire,
				   taxe_sur_acc AS taxe_sur_accessoire;
	
END;
$function$;
