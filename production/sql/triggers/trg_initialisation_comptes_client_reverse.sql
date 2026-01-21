-- Suppression du trigger attaché à la table StdClient
DROP TRIGGER IF EXISTS trg_initialisation_comptes_client ON public.stdclient;