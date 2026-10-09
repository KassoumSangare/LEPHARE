-- Déclencheurs différés : le contrôle a lieu à la validation de la transaction, une fois l'en-tête
-- et les lignes du devis enregistrés, ce qui évite de consommer deux numéros quand la compagnie et
-- la catégorie changent dans la même modification.
CREATE CONSTRAINT TRIGGER trg_aligner_numero_devis_entete
AFTER UPDATE OF idcompagnie, idintermediaire ON public.stddevis
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
WHEN (OLD.idcompagnie IS DISTINCT FROM NEW.idcompagnie OR OLD.idintermediaire IS DISTINCT FROM NEW.idintermediaire)
EXECUTE FUNCTION public.trg_fn_aligner_numero_devis();

CREATE CONSTRAINT TRIGGER trg_aligner_numero_devis_ligne
AFTER INSERT OR DELETE ON public.stddevisdetail
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION public.trg_fn_aligner_numero_devis();

CREATE CONSTRAINT TRIGGER trg_aligner_numero_devis_ligne_tarif
AFTER UPDATE OF idtarif ON public.stddevisdetail
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
WHEN (OLD.idtarif IS DISTINCT FROM NEW.idtarif)
EXECUTE FUNCTION public.trg_fn_aligner_numero_devis();
