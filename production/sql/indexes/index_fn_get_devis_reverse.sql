-- #######################################################################
-- # 1. Suppression des index créés pour l'amélioration de la performance
-- #    du SELECT de la fonction public.fn_get_devis
-- #######################################################################
DO LANGUAGE 'plpgsql'
$$
DECLARE
	index_name TEXT;
	sql_command TEXT;
BEGIN
		-- 1.1 Index Composite Ciblé : Accélère la sous-requête GROUP BY/MIN sur les détails.
		-- Table : public.StdDevisDetail
		SELECT indexname INTO index_name
		FROM pg_indexes AS i
		WHERE i.schemaname = 'public'
			  AND i.tablename = 'stddevisdetail'
			  AND i.indexname = 'idx_stddevisdetail_iddevis_iddevisdetail'
			  AND i.indexdef LIKE '%iddevis%'
			  AND i.indexdef LIKE '%iddevisdetail%';
		IF index_name IS NOT NULL THEN
			sql_command := 'DROP INDEX public.' || quote_ident(index_name);
	        EXECUTE sql_command;
		END IF;
		
		-- 1.2 Index pour le Filtre sur l'ID Produit.
		-- Colonne : SDev.IdProduit (dans la vue/table sous-jacente)
		-- Table : public.vue_devis ou la table source de IdProduit
		SELECT indexname INTO index_name
		FROM pg_indexes AS i
		WHERE i.schemaname = 'public'
			  AND i.tablename = 'stddevis'
			  AND i.indexname = 'idx_devis_idproduit'
			  AND i.indexdef LIKE '%idproduit%';
		IF index_name IS NOT NULL THEN
			sql_command := 'DROP INDEX public.' || quote_ident(index_name);
	        EXECUTE sql_command;
		END IF;
		
		-- 1.3 Index pour le Filtre de Date (DateEmission).
		-- Améliore le filtre BETWEEN.
		-- Table : public.vue_devis ou la table source de DateEmission
		SELECT indexname INTO index_name
		FROM pg_indexes AS i
		WHERE i.schemaname = 'public'
			  AND i.tablename = 'stddevis'
			  AND i.indexname = 'idx_devis_dateemission'
			  AND i.indexdef LIKE '%dateemission%';
		IF index_name IS NOT NULL THEN
			sql_command := 'DROP INDEX public.' || quote_ident(index_name);
	        EXECUTE sql_command;
		END IF;

		-- 1.4 Index pour le Filtre du Numéro de Devis (LIKE 'prefix%').
		-- Table : public.vue_devis ou la table source de NumeroDevis
		SELECT indexname INTO index_name
		FROM pg_indexes AS i
		WHERE i.schemaname = 'public'
			  AND i.tablename = 'stddevis'
			  AND i.indexname = 'idx_devis_numerodevis'
			  AND i.indexdef LIKE '%numerodevis%';
		IF index_name IS NOT NULL THEN
			sql_command := 'DROP INDEX public.' || quote_ident(index_name);
	        EXECUTE sql_command;
		END IF;		
		
		-- 1.5 Index pour le Filtre du Nom Client (LIKE 'prefix%').
		-- Table : public.StdClient (la table jointe)
		SELECT indexname INTO index_name
		FROM pg_indexes AS i
		WHERE i.schemaname = 'public'
			  AND i.tablename = 'stdclient'
			  AND i.indexname = 'idx_client_nom'
			  AND i.indexdef LIKE '%nom%';
		IF index_name IS NOT NULL THEN
			sql_command := 'DROP INDEX public.' || quote_ident(index_name);
	        EXECUTE sql_command;
		END IF;
END;
$$