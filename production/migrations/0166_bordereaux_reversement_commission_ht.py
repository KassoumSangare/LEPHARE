# Reversements aux compagnies au modèle d'OREOLE (dossier FInance_LEPHARE, demande du 2026-10-19) :
#   - stdencaissement.ordrereglement / datecheque : chèque ou virement à l'ordre du cabinet ou de la compagnie (le
#     titre du bordereau en dépend) et date du chèque (reprise par les courriers) ; les encaissements du mode URANUS
#     « A la compagnie » (28) sont à l'ordre de la compagnie ;
#   - stdcontrat.numeroavenantcompagnie : colonne « Avt » des bordereaux ;
#   - lephare_bordereau_reversement : numéro (suite d'OREOLE), nature, date du courrier, date de décharge ;
#   - commission du courtier sur la prime HT hors FGA et CEDEAO, accessoires du cabinet à la part réglée par compagnie
#     (NSIA et SUNU : 50/50) : déclencheur sur stdcontrat (fn_lephare_commission_courtier v1), appliqué aux contrats
#     émis depuis le 01/12/2025 (encaissements LE PHARE) ; les contrats plus anciens, reversés hors LE PHARE, ne
#     changent pas.
# Retour : python manage.py migrate production 0165 (commissions et accessoires corrigés laissés tels quels)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

from uranus.utils.migrations import load_sql_version

DECLENCHEUR = (
    "DROP TRIGGER IF EXISTS trg_lephare_commission_courtier ON public.stdcontrat;"
    " CREATE TRIGGER trg_lephare_commission_courtier BEFORE INSERT OR UPDATE OF primenette, fga, cedeao, accessoire, taxe,"
    " primettc, taux_commission, commissionintermediaire, accessoireintermediaire, idcompagnie ON public.stdcontrat"
    " FOR EACH ROW EXECUTE FUNCTION public.trg_fn_lephare_commission_courtier();"
)
CORRECTION = (
    "UPDATE public.stdcontrat SET commissionintermediaire = commissionintermediaire WHERE dateemission >= DATE '2025-12-01';"
    " UPDATE public.stdencaissement SET ordrereglement = 'COMPAGNIE' WHERE idmodepaiement = 28;"
)
RETRAIT = (
    "DROP TRIGGER IF EXISTS trg_lephare_commission_courtier ON public.stdcontrat;"
    " DROP FUNCTION IF EXISTS public.trg_fn_lephare_commission_courtier();"
    " DROP FUNCTION IF EXISTS public.fn_lephare_prime_ht(numeric, numeric, numeric, numeric, numeric, numeric, boolean);"
)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('production', '0165_tarif_annote_nsia_relu'),
        ('configuration_api', '0095_reversements_courriers'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrat',
            name='numero_avenant_compagnie',
            field=models.CharField(blank=True, db_column='numeroavenantcompagnie', max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='encaissement',
            name='date_cheque',
            field=models.DateField(blank=True, db_column='datecheque', null=True),
        ),
        migrations.AddField(
            model_name='encaissement',
            name='ordre_reglement',
            field=models.CharField(choices=[('CABINET', "À l'ordre du cabinet"), ('COMPAGNIE', "À l'ordre de la compagnie")], db_column='ordrereglement', default='CABINET', max_length=10),
        ),
        migrations.CreateModel(
            name='BordereauReversement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_reversement', models.IntegerField(db_column='idreversement', unique=True)),
                ('numero', models.PositiveIntegerField(db_column='numero')),
                ('nature', models.CharField(choices=[('REVERSEMENT', 'Bordereau de reversement de prime'), ('RECLAMATION', 'Bordereau de réclamation de commission')], db_column='nature', max_length=12)),
                ('date_bordereau', models.DateField(db_column='datebordereau')),
                ('date_decharge', models.DateField(blank=True, db_column='datedecharge', null=True)),
                ('annule', models.BooleanField(db_column='annule', default=False)),
                ('motif_annulation', models.CharField(blank=True, db_column='motifannulation', default='', max_length=255)),
                ('date_annulation', models.DateTimeField(blank=True, db_column='dateannulation', null=True)),
                ('cree_le', models.DateTimeField(auto_now_add=True, db_column='creele')),
                ('cree_par', models.ForeignKey(blank=True, db_column='creepar', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='bordereaux_reversement', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Bordereau de reversement',
                'verbose_name_plural': 'Bordereaux de reversement',
                'db_table': 'lephare_bordereau_reversement',
            },
        ),
        migrations.AddConstraint(
            model_name='bordereaureversement',
            constraint=models.UniqueConstraint(condition=models.Q(('annule', False)), fields=('numero',), name='lephare_bordereau_numero_actif'),
        ),
            migrations.RunSQL(load_sql_version(__file__, "functions/fn_lephare_commission_courtier", 1) + "\n" + DECLENCHEUR, RETRAIT),
        migrations.RunSQL(CORRECTION, migrations.RunSQL.noop),
    ]
