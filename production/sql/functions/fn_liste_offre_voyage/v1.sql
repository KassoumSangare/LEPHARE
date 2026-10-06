CREATE OR REPLACE FUNCTION public.fn_liste_offre_voyage(id_compagnie integer, id_tarif integer, id_zone integer)
 RETURNS TABLE(id_offre integer, libelle_offre character varying)
 LANGUAGE plpgsql
AS $function$
BEGIN
	--Pour la compagnie NSIA, l'offre dépend du tarif
	IF (id_compagnie = 1)  AND (id_tarif = 105) THEN
		RETURN QUERY
			SELECT IdOffre AS id_offre, LibelleOffre AS libelle_offre
			FROM StdOffre AS STO
			INNER JOIN StdTarif AS STT ON (STO.IdTarif = STT.IdTarif)
			WHERE ((id_zone = 6 AND IdOffre IN (68, 69)) OR (id_zone = 7 AND IdOffre IN (70, 71, 72, 73))) AND (Ppr = 'V') AND STT.IdTarif = id_tarif;
	ELSE
		RETURN QUERY
			SELECT IdOffre AS id_offre, LibelleOffre AS libelle_offre
			FROM StdOffre AS STO
			INNER JOIN StdTarif AS STT ON (STO.IdTarif = STT.IdTarif)
			WHERE (IdOffre <> 0) AND (Ppr = 'V') AND STT.IdTarif = id_tarif;

	END IF;
END;
$function$;
