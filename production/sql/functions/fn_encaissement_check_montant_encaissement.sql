CREATE OR REPLACE FUNCTION public.fn_encaissement_check_montant_encaissement()
RETURNS TRIGGER AS $$
BEGIN
  IF (NEW.montant_encaissement >= 0) AND (NEW.montant_encaissement < NEW.montantreglement) THEN
    RAISE EXCEPTION 'montant_encaissement doit être supérieur à montantreglement';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
ALTER FUNCTION public.fn_encaissement_check_montant_encaissement() OWNER TO uranususer;