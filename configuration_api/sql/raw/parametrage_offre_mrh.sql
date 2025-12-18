DO LANGUAGE 'plpgsql'
$$
BEGIN

	UPDATE public.stdoffre
	SET libelleoffre = CASE idoffre WHEN 10 THEN 'LOCATAIRE OCCUPANT TOTAL'
									WHEN 11 THEN 'PROPRIETAIRE OCCUPANT TOTAL'
									WHEN 12 THEN 'PROPRIETAIRE NON OCCUPANT'
									WHEN 13 THEN 'PROPRIETAIRE OCCUPANT PARTIEL'
									ELSE libelleoffre
						END
	WHERE idtarif = 81 AND libelleoffre LIKE 'MULTIRISQUES HABITATION%';

	UPDATE public.stdmrh_usage_habitation
	SET idoffre = CASE code WHEN 'proprietaire_occupant_total' THEN 11
							WHEN 'proprietaire_occupant_partiel' THEN 13
							WHEN 'proprietaire_non_occupant' THEN 12
							WHEN 'proprietaire_non_occupant_meuble' THEN 152
							WHEN 'locataire_meuble' THEN 153
							WHEN 'locataire' THEN 10
							WHEN 'locataire_partiel' THEN 150
							WHEN 'logement_fonction' THEN 151
							ELSE NULL
					END;
END;
$$