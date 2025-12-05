DO
$$
DECLARE
	v_nouveau_numero VARCHAR(20);
	v_devis_rec RECORD;
	v_contrat_rec RECORD;
	v_date_debut date;
	v_date_fin date;
BEGIN
	v_date_debut := EXTRACT(YEAR FROM CURRENT_DATE) - 5;
	v_date_fin := v_date_debut + 10;
	FOR v_devis_rec IN (SELECT iddevis, idcompagnie, idintermediaire, dateemission
						 FROM public.stddevis
						 WHERE NOT archive
						 		AND TRIM(COALESCE(numerofacture, '')) = ''
						 		AND DATE_PART('year', dateeffet) BETWEEN v_date_debut AND v_date_fin
						 ORDER BY dateemission)
	LOOP
		SELECT public.fn_generer_numero_facture(false, v_devis_rec.idcompagnie, v_devis_rec.idintermediaire, v_devis_rec.dateemission::DATE) INTO v_nouveau_numero;
		UPDATE public.stddevis
		SET numerofacture = v_nouveau_numero
		WHERE iddevis = v_devis_rec.iddevis;
	END LOOP;

	FOR v_contrat_rec IN (SELECT idcontrat, idcompagnie, idintermediaire, dateemission
						 FROM public.stdcontrat
						 WHERE TRIM(COALESCE(numerofacture, '')) = ''
						 		AND DATE_PART('year', dateeffet) BETWEEN v_date_debut AND v_date_fin
						 ORDER BY dateemission)
	LOOP
		SELECT public.fn_generer_numero_facture(true, v_contrat_rec.idcompagnie, v_contrat_rec.idintermediaire, v_contrat_rec.dateemission::DATE) INTO v_nouveau_numero;
		UPDATE public.stdcontrat
		SET numerofacture = v_nouveau_numero
		WHERE idcontrat = v_contrat_rec.idcontrat;
	END LOOP;
	

END;
$$ LANGUAGE 'plpgsql';