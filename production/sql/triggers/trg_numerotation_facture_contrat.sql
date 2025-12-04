CREATE TRIGGER trg_numerotation_facture_contrat
BEFORE INSERT ON public.stdcontrat
FOR EACH ROW
EXECUTE FUNCTION public.set_numero_facture_before_insert();