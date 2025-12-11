-- #######################################################################
-- # 1. CRÉATION DES INDEX (Amélioration de la performance du SELECT de la fonction public.fn_get_devis)
-- #######################################################################

-- 1.1 Index Composite Ciblé : Accélère la sous-requête GROUP BY/MIN sur les détails.
-- (Ceci est le suspect n°1 après la complexité du COUNT)
-- Table : public.StdDevisDetail
CREATE INDEX IF NOT EXISTS idx_stddevisdetail_iddevis_iddevisdetail 
ON public.stddevisdetail (iddevis, iddevisdetail);


-- 1.2 Index pour le Filtre sur l'ID Produit.
-- Colonne : SDev.IdProduit (dans la vue/table sous-jacente)
-- Table : public.vue_devis ou la table source de IdProduit
CREATE INDEX IF NOT EXISTS idx_devis_idproduit 
ON public.stddevis (idproduit);


-- 1.3 Index pour le Filtre de Date (DateEmission).
-- Améliore le filtre BETWEEN.
-- Table : public.vue_devis ou la table source de DateEmission
CREATE INDEX IF NOT EXISTS idx_devis_dateemission 
ON public.stddevis (dateemission DESC); -- DESC est bon pour l'ORDER BY final


-- 1.4 Index pour le Filtre du Numéro de Devis (LIKE 'prefix%').
-- Table : public.vue_devis ou la table source de NumeroDevis
CREATE INDEX IF NOT EXISTS idx_devis_numerodevis 
ON public.stddevis (numerodevis);


-- 1.5 Index pour le Filtre du Nom Client (LIKE 'prefix%').
-- Table : public.StdClient (la table jointe)
CREATE INDEX IF NOT EXISTS idx_client_nom
ON public.stdclient (nom);

-- Note sur la réindexation : Les index sont créés de manière non bloquante si la table est vide.
-- En production, utilisez REINDEX TABLE CONCURRENTLY si vous soupçonnez une fragmentation.