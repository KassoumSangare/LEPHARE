# Journal d'audit centralisé (autorisations/journal.py) : utilisateur, module, action, objet,
# résultat, adresse IP, valeurs avant / après, motif. La table devient en ajout seul : un
# déclencheur refuse toute modification, suppression ou vidage, quel que soit l'utilisateur de
# l'application (administrateur compris).
# Retour : python manage.py migrate institutionnel 0002

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


LECTURE_SEULE = """
CREATE OR REPLACE FUNCTION fn_journal_audit_lecture_seule() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Journal d''audit en lecture seule : modification et suppression interdites.';
END;
$$;
DROP TRIGGER IF EXISTS trg_journal_audit_lecture_seule ON institutionnel_auditlogcima;
CREATE TRIGGER trg_journal_audit_lecture_seule BEFORE UPDATE OR DELETE ON institutionnel_auditlogcima
    FOR EACH ROW EXECUTE FUNCTION fn_journal_audit_lecture_seule();
DROP TRIGGER IF EXISTS trg_journal_audit_sans_vidage ON institutionnel_auditlogcima;
CREATE TRIGGER trg_journal_audit_sans_vidage BEFORE TRUNCATE ON institutionnel_auditlogcima
    FOR EACH STATEMENT EXECUTE FUNCTION fn_journal_audit_lecture_seule();
"""

LECTURE_SEULE_RETOUR = """
DROP TRIGGER IF EXISTS trg_journal_audit_sans_vidage ON institutionnel_auditlogcima;
DROP TRIGGER IF EXISTS trg_journal_audit_lecture_seule ON institutionnel_auditlogcima;
DROP FUNCTION IF EXISTS fn_journal_audit_lecture_seule();
"""


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('institutionnel', '0002_bordereaureversement_quittancecima_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlogcima',
            name='action',
            field=models.CharField(blank=True, default='', max_length=80, verbose_name='Action (droit ou évènement)'),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='adresse_ip',
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name='Adresse IP'),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='chemin',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Route appelée'),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='methode',
            field=models.CharField(blank=True, default='', max_length=8, verbose_name='Méthode HTTP'),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='module',
            field=models.CharField(blank=True, default='', max_length=40, verbose_name='Module'),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='motif',
            field=models.TextField(blank=True, default='', verbose_name='Motif saisi'),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='objet_id',
            field=models.CharField(blank=True, default='', max_length=80, verbose_name="Identifiant de l'objet"),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='objet_type',
            field=models.CharField(blank=True, default='', max_length=60, verbose_name="Type d'objet"),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='resultat',
            field=models.CharField(blank=True, default='', max_length=10, verbose_name='Résultat (SUCCES, ECHEC, REFUS)'),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='statut_http',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Code de réponse'),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='utilisateur',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='journal_audit', to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur'),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='valeur_apres',
            field=models.JSONField(blank=True, null=True, verbose_name='Valeur après'),
        ),
        migrations.AddField(
            model_name='auditlogcima',
            name='valeur_avant',
            field=models.JSONField(blank=True, null=True, verbose_name='Valeur avant'),
        ),
        migrations.AddIndex(
            model_name='auditlogcima',
            index=models.Index(fields=['date_creation'], name='audit_date_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlogcima',
            index=models.Index(fields=['utilisateur', 'date_creation'], name='audit_utilisateur_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlogcima',
            index=models.Index(fields=['module', 'action'], name='audit_module_action_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlogcima',
            index=models.Index(fields=['objet_type', 'objet_id'], name='audit_objet_idx'),
        ),
        migrations.RunSQL(LECTURE_SEULE, LECTURE_SEULE_RETOUR),
    ]
