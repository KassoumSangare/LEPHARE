CREATE OR REPLACE FUNCTION public.fn_liste_offre_voyage(id_compagnie integer, id_tarif integer, id_zone integer)
 RETURNS TABLE(id_offre integer, libelle_offre character varying)
 LANGUAGE plpgsql
AS $function$
-- Offres actives de la formule proposées dans la zone de destination (stdoffrevoyagezone,
-- modifiable dans l'admin, Grilles Voyage). La zone appartient à une seule compagnie.
BEGIN
	RETURN QUERY
		SELECT o.idoffre, o.libelleoffre
		FROM public.stdoffre AS o
		WHERE o.idoffre <> 0
			AND o.ppr = 'V'
			AND o.actif
			AND o.idtarif = fn_liste_offre_voyage.id_tarif
			AND EXISTS (SELECT 1 FROM public.stdoffrevoyagezone AS oz
						WHERE oz.id_offre = o.idoffre AND oz.id_zone = fn_liste_offre_voyage.id_zone)
		ORDER BY o.idoffre;
END;
$function$;
