-- Part du cabinet dans les accessoires d'une compagnie (%), réglée sur sa fiche : Administration > Compagnies
-- partenaires > Reversements (lephare_compagnie_document.reversement ->> 'PartAccessoiresCourtier'). NULL quand elle n'est
-- pas réglée : accessoires de la compagnie à son barème, part du cabinet à son propre barème (Accessoires du cabinet).
-- Lue par fn_get_accessoire, fn_garantie_offre_dommages et sp_creation_devis_voyage (devis) comme par le déclencheur
-- trg_fn_lephare_commission_courtier (contrats), et pour l'IA par sp_creation_devis_ia, sp_finalisation_devis et
-- fn_garantie_offre_ia (production 0224). NSIA et SUNU : 50 ; AMSA : 0, elle ne partage pas (configuration_api 0111).
CREATE OR REPLACE FUNCTION public.fn_lephare_part_accessoires_cabinet(p_id_compagnie integer)
 RETURNS numeric
 LANGUAGE sql
 STABLE
AS $function$
	SELECT CASE WHEN COALESCE(d.reversement ->> 'PartAccessoiresCourtier', '') ~ '^[0-9]+([.][0-9]+)?$'
	             AND (d.reversement ->> 'PartAccessoiresCourtier')::numeric <= 100
	            THEN (d.reversement ->> 'PartAccessoiresCourtier')::numeric END
	FROM public.lephare_compagnie_document AS d
	WHERE d.idcompagnie = p_id_compagnie
$function$;
