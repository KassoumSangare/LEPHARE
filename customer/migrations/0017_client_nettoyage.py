from django.db import migrations, models

# Un contrat émis pour une fiche archivée par le nettoyage (statut « A ») la remet dans le
# répertoire. La mise à jour passe par trg_clients_cle_unique, qui recalcule la clé anti-doublon
# des fiches qui n'en ont pas : si cette clé est déjà prise (doublon resté en base), la fiche
# reçoit une clé propre à son identifiant plutôt que de faire échouer l'émission du contrat.
REACTIVATION = """
CREATE OR REPLACE FUNCTION public.fn_reactiver_client_archive() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        UPDATE public.stdclient SET statut = 'V'
         WHERE statut = 'A' AND idclient IN (NEW.idclient, NEW.idassure);
    EXCEPTION WHEN unique_violation THEN
        UPDATE public.stdclient SET statut = 'V', cle_unique = 'CLIENT-' || idclient
         WHERE statut = 'A' AND idclient IN (NEW.idclient, NEW.idassure);
    END;
    RETURN NULL;
END;
$$;
DROP TRIGGER IF EXISTS trg_reactiver_client_archive ON public.stdcontrat;
CREATE TRIGGER trg_reactiver_client_archive
    AFTER INSERT OR UPDATE OF idclient, idassure ON public.stdcontrat
    FOR EACH ROW EXECUTE FUNCTION public.fn_reactiver_client_archive();
"""

SUPPRESSION = """
DROP TRIGGER IF EXISTS trg_reactiver_client_archive ON public.stdcontrat;
DROP FUNCTION IF EXISTS public.fn_reactiver_client_archive();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("customer", "0016_client_idstatutjuridique"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientNettoyage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("idclient", models.IntegerField(db_column="idclient", unique=True)),
                ("idclient_reference", models.IntegerField(blank=True, db_column="idclient_reference", null=True)),
                ("decision", models.CharField(choices=[
                    ("conserve", "Conservé"),
                    ("regroupe", "Regroupé sur la fiche de référence"),
                    ("exclu", "Exclu : aucun contrat"),
                    ("a_verifier", "À vérifier"),
                ], max_length=12)),
                ("motif", models.TextField(blank=True, default="")),
                ("nom_origine", models.CharField(blank=True, default="", max_length=310)),
                ("statut_avant", models.CharField(blank=True, default="", max_length=1)),
                ("donnees_avant", models.JSONField(blank=True, default=dict)),
                ("lot", models.CharField(max_length=120)),
                ("date_application", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "lephare_client_nettoyage"},
        ),
        migrations.RunSQL(sql=REACTIVATION, reverse_sql=SUPPRESSION),
    ]
