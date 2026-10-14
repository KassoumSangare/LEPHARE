CREATE OR REPLACE FUNCTION public.fn_lephare_arrondi_montant(p_montant numeric, p_id_produit integer DEFAULT NULL)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Arrondi des primes TTC : la plus petite pièce en Côte d'Ivoire est de 5 F. Le montant est ramené au multiple de
-- « pas » inférieur si son reste ne dépasse pas le seuil (2 F), porté au multiple supérieur au-delà :
-- 13 452 -> 13 450, 13 453 -> 13 455. Réglages : Administration > Paramètres du cabinet > Règles de gestion >
-- Arrondi des montants (pas 0 ou 1 : montant inchangé) ; produit exclu : Administration > Produits.
DECLARE
	v_pas numeric;
	v_seuil numeric;
	v_entier numeric;
	v_reste numeric;
BEGIN
	IF p_montant IS NULL THEN
		RETURN NULL;
	END IF;

	IF p_id_produit IS NOT NULL AND EXISTS (SELECT 1 FROM public.lephare_produit_parametre
											WHERE idproduit = p_id_produit AND NOT arrondittc) THEN
		RETURN p_montant;
	END IF;

	v_pas := COALESCE(public.fn_lephare_parametre_nombre('montants.arrondi_pas', 5), 0);
	IF v_pas <= 1 THEN
		RETURN p_montant;
	END IF;
	v_seuil := COALESCE(public.fn_lephare_parametre_nombre('montants.arrondi_seuil', 2), 0);

	v_entier := ROUND(ABS(p_montant), 0);
	v_reste := MOD(v_entier, v_pas);
	IF v_reste > 0 THEN
		v_entier := CASE WHEN v_reste <= v_seuil THEN v_entier - v_reste ELSE v_entier - v_reste + v_pas END;
	END IF;
	RETURN SIGN(p_montant) * v_entier;
END;
$function$;

CREATE OR REPLACE FUNCTION public.trg_fn_lephare_arrondi_primettc()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Prime TTC d'un devis, d'un contrat ou d'une quittance arrondie à son enregistrement (fn_lephare_arrondi_montant) :
-- toutes les branches et tous les documents, qui lisent la TTC enregistrée. Les composantes (prime nette,
-- accessoire, taxe) restent celles du calcul ; l'écart (2 F au plus) est celui de l'arrondi.
BEGIN
	IF NEW.primettc IS NOT NULL THEN
		NEW.primettc := public.fn_lephare_arrondi_montant(NEW.primettc, NEW.idproduit);
	END IF;
	RETURN NEW;
END;
$function$;
