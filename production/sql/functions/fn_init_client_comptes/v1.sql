-- 1. Création de la fonction du trigger
CREATE OR REPLACE FUNCTION public.fn_init_client_comptes()
RETURNS TRIGGER AS $$
BEGIN
    NEW.solde := COALESCE(NEW.solde, 0);
    NEW.avoir := COALESCE(NEW.avoir, 0);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
ALTER FUNCTION public.fn_init_client_comptes() OWNER TO uranususer;
