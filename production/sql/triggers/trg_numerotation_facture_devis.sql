CREATE TRIGGER trg_numerotation_facture_devis
BEFORE INSERT ON public.stddevis
FOR EACH ROW
EXECUTE FUNCTION public.set_numero_facture_before_insert();