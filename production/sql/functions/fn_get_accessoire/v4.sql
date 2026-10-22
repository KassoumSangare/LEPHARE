-- v4 : plus aucune compagnie ni offre écrite ici (v3 : NSIA, SUNU et AMSA à 50/50, offres IA 154-156 et 162-170 à
-- 1 000 F et 79 F).
--   - Part du cabinet : réglage de la fiche de la compagnie (fn_lephare_part_accessoires_cabinet ; NSIA, SUNU et
--     AMSA : 50 %). Le barème de la compagnie est partagé selon cette part ; sans réglage, la compagnie garde son
--     barème et le cabinet a le sien (Accessoires du cabinet, sauf Voyage).
--   - Offres IA à accessoire forfaitaire (CGA, CI-ÉNERGIES… ; Réglages par branche > Individuelle Accidents,
--     lephare_ia_accessoire_offre) : montant de l'offre partagé selon la part du cabinet.
--   - IA NSIA hors MINENE (66) : grille du tarif NSIA (fn_get_accessoire_ia_nsia) partagée selon la part du cabinet.
-- Mêmes montants que la v3 avec les réglages d'origine.
CREATE OR REPLACE FUNCTION public.fn_get_accessoire(prime_nette numeric, id_produit integer, id_offre integer, id_compagnie integer, date_effet date)
  RETURNS TABLE(accessoire_compagnie numeric, accessoire_intermediaire numeric, taxe_sur_accessoire numeric)
  LANGUAGE plpgsql
 AS $function$
 DECLARE
         tx_taxe_acc numeric;
         acc_compagnie numeric;
         acc_intermediaire numeric;
         taxe_sur_acc numeric;
         v_part numeric;
         v_montant_offre numeric;
         v_total numeric;

 BEGIN
                 v_part := public.fn_lephare_part_accessoires_cabinet(id_compagnie);
                 IF v_part IS NOT NULL AND id_produit = 2 THEN
                         SELECT a.montant INTO v_montant_offre
                         FROM public.lephare_ia_accessoire_offre AS a
                         WHERE a.idoffre = id_offre AND a.actif;
                 END IF;

                 IF v_montant_offre IS NOT NULL THEN
                         -- Offre IA à accessoire forfaitaire
                         acc_intermediaire := v_montant_offre * v_part / 100;
                         acc_compagnie := v_montant_offre - acc_intermediaire;
                 ELSIF id_compagnie = 1 AND id_produit = 2 AND id_offre <> 66 THEN
                         -- IA NSIA : grille du tarif IA NSIA. MINENE (66) garde l'accessoire de son tarif (6 000).
                         v_total := fn_get_accessoire_ia_nsia(prime_nette);
                         acc_compagnie := ROUND(v_total * (100 - COALESCE(v_part, 50)) / 100, 0);
                         acc_intermediaire := v_total - acc_compagnie;
                 ELSE
                         acc_compagnie := fn_get_accessoire_compagnie(prime_nette, id_produit, id_compagnie);
                         acc_intermediaire := 0;
                         IF v_part IS NOT NULL THEN
                                 v_total := acc_compagnie;
                                 acc_compagnie := ROUND(v_total * (100 - v_part) / 100, 0);
                                 acc_intermediaire := ROUND(v_total * v_part / 100, 0);
                         ELSIF id_produit <> 3 THEN
                                 acc_intermediaire := fn_get_accessoire_intermediaire(prime_nette, id_compagnie);
                         END IF;
                 END IF;

                 tx_taxe_acc := fn_get_taux_taxe(id_compagnie, id_produit, id_offre, date_effet);
                 taxe_sur_acc := ROUND(((acc_compagnie + acc_intermediaire) * tx_taxe_acc)/100, 0);

                 RETURN QUERY
                         SELECT acc_compagnie AS accessoire_compagnie, acc_intermediaire AS accessoire_intermediaire,
                                    taxe_sur_acc AS taxe_sur_accessoire;

 END;
 $function$;
