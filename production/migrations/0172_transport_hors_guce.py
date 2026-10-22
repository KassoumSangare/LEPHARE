# Transport hors GUCE (documents OREOLE « TRANSPORTS.docx » et questionnaires Transport, Facultés, Facultés
# terrestres reçus le 2026-10-21) : cotation des marchandises transportées hors guichet unique, police au voyage,
# police annuelle ou police d'abonnement alimentée par les voyages déclarés et facturée par ressortie mensuelle.
#
#   - lephare_transport_affaire : type de police, mode de transport, saisie et décompte du devis ;
#   - lephare_transport_voyage : voyages déclarés sur une police d'abonnement, facturés par la ressortie du mois ;
#   - sous-garanties du tarif OREOLE absentes du référentiel : Tous risques facultés, FAP Sauf, emballage
#     (clause 53), chargement et déchargement (guerre 189, grèves 190, transbordement 182 et accidents
#     caractérisés 144 existent déjà) ;
#   - offres « POLICE ANNUELLE (F. …) » des cinq catégories Facultés, copiées des offres au voyage (URANUS n'avait
#     que l'abonnement et le voyage).
# Retour : python manage.py migrate production 0171

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

SOUS_GARANTIES = [
    # code, libellé, garantie, ordre
    ("19011", "TOUS RISQUES FACULTÉS", 19, 99),
    ("30022", "FAP SAUF (ACCIDENTS MAJEURS)", 3, 80),
    ("30023", "COUVERTURE DE L''EMBALLAGE (CLAUSE 53)", 3, 81),
    ("30024", "RISQUES DE CHARGEMENT ET DE DÉCHARGEMENT", 3, 82),
]
VALEURS = ", ".join(f"('{c}', '{l}', {g}, {o})" for c, l, g, o in SOUS_GARANTIES)
CODES = ", ".join(f"'{c}'" for c, *_ in SOUS_GARANTIES)

CREATION_REFERENTIEL = f"""
SELECT setval(pg_get_serial_sequence('stdsousgarantie', 'idsousgarantie'), (SELECT MAX(idsousgarantie) FROM stdsousgarantie));
INSERT INTO stdsousgarantie (codesousgarantie, libellesousgarantie, active, ordre, saisieauto, saisierd, saisiesante,
                             saisietransport, idgarantie)
SELECT v.code, v.libelle, TRUE, v.ordre, FALSE, FALSE, FALSE, TRUE, v.idgarantie
FROM (VALUES {VALEURS}) AS v(code, libelle, idgarantie, ordre)
WHERE NOT EXISTS (SELECT 1 FROM stdsousgarantie AS s WHERE s.codesousgarantie = v.code);

SELECT setval(pg_get_serial_sequence('stdoffre', 'idoffre'), (SELECT MAX(idoffre) FROM stdoffre));
INSERT INTO stdoffre (actif, anticipation, differe, echeance, entreprise, exoneredeaccess, exoneredetaxes, flotte, gestion,
                      jpaiement, libelleoffre, majfract, payement, ppr, renouvelable, visibilite, idtarif, idzonecouverture)
SELECT o.actif, o.anticipation, o.differe, o.echeance, o.entreprise, o.exoneredeaccess, o.exoneredetaxes, o.flotte, o.gestion,
       o.jpaiement, REPLACE(o.libelleoffre, 'POLICE AU VOYAGE', 'POLICE ANNUELLE'), o.majfract, o.payement, o.ppr,
       o.renouvelable, o.visibilite, o.idtarif, o.idzonecouverture
FROM stdoffre AS o
JOIN stdtarif AS t ON t.idtarif = o.idtarif AND t.codecategorie IN ('611', '612', '613', '614', '619')
WHERE o.libelleoffre LIKE 'POLICE AU VOYAGE%'
  AND NOT EXISTS (SELECT 1 FROM stdoffre AS x
                  WHERE x.idtarif = o.idtarif AND x.libelleoffre = REPLACE(o.libelleoffre, 'POLICE AU VOYAGE', 'POLICE ANNUELLE'))
ORDER BY o.idoffre;
"""

RETOUR_REFERENTIEL = f"""
DELETE FROM stdoffre AS o
WHERE o.libelleoffre LIKE 'POLICE ANNUELLE (F.%'
  AND NOT EXISTS (SELECT 1 FROM stddevisdetail AS d WHERE d.idoffre = o.idoffre)
  AND NOT EXISTS (SELECT 1 FROM stdcontratdetail AS c WHERE c.idoffre = o.idoffre);
DELETE FROM stdsousgarantie AS s
WHERE s.codesousgarantie IN ({CODES})
  AND NOT EXISTS (SELECT 1 FROM stddevisdetgarantie AS g WHERE g.idgarantie = s.idsousgarantie)
  AND NOT EXISTS (SELECT 1 FROM stdcontratdetgarantie AS g WHERE g.idgarantie = s.idsousgarantie);
"""


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("production", "0171_numero_bordereau_sans_categorie"),
    ]

    operations = [
        migrations.CreateModel(
            name="AffaireTransport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("id_devis", models.IntegerField(db_column="iddevis", unique=True)),
                ("type_police", models.CharField(choices=[("VOYAGE", "Police au voyage"), ("ANNUELLE", "Police annuelle"), ("ABONNEMENT", "Police d'abonnement")], db_column="typepolice", max_length=12)),
                ("mode", models.CharField(choices=[("MARITIME", "Maritime"), ("AERIEN", "Aérien"), ("TERRESTRE", "Terrestre"), ("FERROVIAIRE", "Ferroviaire"), ("FLUVIAL", "Fluvial")], db_column="mode", max_length=12)),
                ("saisie", models.JSONField(db_column="saisie", default=dict)),
                ("calcul", models.JSONField(db_column="calcul", default=dict)),
                ("cree_le", models.DateTimeField(auto_now_add=True, db_column="creele")),
                ("modifie_le", models.DateTimeField(auto_now=True, db_column="modifiele")),
                ("cree_par", models.ForeignKey(blank=True, db_column="creepar", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="affaires_transport", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Affaire Transport hors GUCE",
                "verbose_name_plural": "Affaires Transport hors GUCE",
                "db_table": "lephare_transport_affaire",
            },
        ),
        migrations.CreateModel(
            name="VoyageTransport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("id_contrat", models.IntegerField(db_column="idcontrat", db_index=True)),
                ("numero_police", models.CharField(db_column="numeropolice", max_length=50)),
                ("numero", models.PositiveIntegerField(db_column="numero")),
                ("date_depart", models.DateField(db_column="datedepart")),
                ("date_arrivee", models.DateField(blank=True, db_column="datearrivee", null=True)),
                ("marchandise", models.CharField(db_column="marchandise", max_length=255)),
                ("emballage", models.CharField(blank=True, db_column="emballage", default="", max_length=120)),
                ("conditionnement", models.CharField(blank=True, db_column="conditionnement", default="", max_length=120)),
                ("lieu_depart", models.CharField(db_column="lieudepart", max_length=120)),
                ("lieu_arrivee", models.CharField(db_column="lieuarrivee", max_length=120)),
                ("moyen_transport", models.CharField(blank=True, db_column="moyentransport", default="", max_length=120)),
                ("document_transport", models.CharField(blank=True, db_column="documenttransport", default="", max_length=80)),
                ("valeur", models.DecimalField(db_column="valeur", decimal_places=2, max_digits=18)),
                ("taux_total", models.DecimalField(db_column="tauxtotal", decimal_places=4, max_digits=9)),
                ("prime_nette", models.DecimalField(db_column="primenette", decimal_places=2, max_digits=18)),
                ("accessoire", models.DecimalField(db_column="accessoire", decimal_places=2, max_digits=18)),
                ("taxe", models.DecimalField(db_column="taxe", decimal_places=2, max_digits=18)),
                ("prime_ttc", models.DecimalField(db_column="primettc", decimal_places=2, max_digits=18)),
                ("garanties", models.JSONField(db_column="garanties", default=list)),
                ("id_devis_ressortie", models.IntegerField(blank=True, db_column="iddevisressortie", null=True)),
                ("annule", models.BooleanField(db_column="annule", default=False)),
                ("motif_annulation", models.CharField(blank=True, db_column="motifannulation", default="", max_length=255)),
                ("cree_le", models.DateTimeField(auto_now_add=True, db_column="creele")),
                ("cree_par", models.ForeignKey(blank=True, db_column="creepar", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="voyages_transport", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Voyage déclaré (Transport)",
                "verbose_name_plural": "Voyages déclarés (Transport)",
                "db_table": "lephare_transport_voyage",
                "ordering": ["id_contrat", "numero"],
            },
        ),
        migrations.AddConstraint(
            model_name="voyagetransport",
            constraint=models.UniqueConstraint(fields=("id_contrat", "numero"), name="lephare_transport_voyage_numero"),
        ),
        migrations.RunSQL(CREATION_REFERENTIEL, RETOUR_REFERENTIEL),
    ]
