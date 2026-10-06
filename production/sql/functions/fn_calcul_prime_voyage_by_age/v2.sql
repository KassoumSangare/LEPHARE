CREATE OR REPLACE FUNCTION public.fn_calcul_prime_voyage_by_age(age integer, duree_voyage integer, id_zone_voyage integer, id_tarif integer, id_offre integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
-- Prime nette de la grille Voyage (fn_grille_voyage), 0 hors grille.
DECLARE
	prime_voyage numeric;
BEGIN
	SELECT g.prime_nette
	INTO prime_voyage
	FROM public.fn_grille_voyage(id_tarif, id_offre, id_zone_voyage, age, duree_voyage) AS g;
	RETURN COALESCE(prime_voyage, 0);
END;
$function$;
