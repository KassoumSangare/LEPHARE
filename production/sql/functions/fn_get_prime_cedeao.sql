CREATE OR REPLACE FUNCTION public.fn_get_prime_cedeao(IN p_idtarif INTEGER, IN p_puissance INTEGER, IN p_tonnage INTEGER)
RETURNS NUMERIC(19, 4)
LANGUAGE 'plpgsql'
AS
$$
DECLARE
	id_garantie_cedeao INTEGER := 3;
	prime_cedeao NUMERIC(19, 4);
BEGIN

	p_tonnage := COALESCE(p_tonnage, 0);
	p_puissance := COALESCE(p_puissance, 0);
	SELECT primegar
	INTO prime_cedeao
	FROM public.stdtarifdetail
	WHERE idtarif = p_idtarif 
	      AND idgarantie = id_garantie_cedeao
		  AND (p_puissance BETWEEN puissancemin AND puissancemax)
		  AND (p_tonnage between tonnagemin and tonnagemax);

	RETURN COALESCE(prime_cedeao, 0);
END;
$$;
ALTER FUNCTION public.fn_get_prime_cedeao(INTEGER, INTEGER, INTEGER) OWNER TO uranususer;