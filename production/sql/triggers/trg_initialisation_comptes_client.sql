-- Création du trigger attaché à la table StdClient
CREATE OR REPLACE TRIGGER trg_initialisation_comptes_client
BEFORE INSERT ON public.stdclient
FOR EACH ROW
EXECUTE FUNCTION public.fn_init_client_comptes();