# Branche Dommages (produit 9) ouverte à la saisie, avec ses réglages dans l'admin (Réglages Dommages) :
#   - lephare_dommage_categorie : catégorie (tarif 4xx) proposée ou non, ordre, description, prorata,
#     description du risque demandée à la saisie ;
#   - lephare_dommage_garantie : taux de prime proposé et garantie obligatoire, par garantie d'offre.
# Le produit 9 a désormais son onglet « Dommages » au registre des devis et sa saisie ouverte.
# Retour : python manage.py migrate configuration_api 0074

from django.db import migrations, models


def _champ(cle, libelle, type_="texte", obligatoire=False):
    return {"Cle": cle, "Libelle": libelle, "Type": type_, "Obligatoire": obligatoire}


DESIGNATION = _champ("designation", "Désignation des biens assurés", "texte_long", True)
SITUATION = _champ("situation", "Situation du risque (adresse)")
CHANTIER = [
    _champ("nature_travaux", "Nature des travaux / de l'ouvrage", "texte_long", True),
    _champ("situation", "Situation du chantier"),
    _champ("maitre_ouvrage", "Maître d'ouvrage"),
    _champ("entreprise", "Entreprise titulaire des travaux"),
    _champ("debut_travaux", "Début des travaux", "date"),
    _champ("fin_travaux", "Fin des travaux", "date"),
]

# (idtarif, ordre, description, champs du risque) : les 12 catégories Dommages de stdtarif (codes 4xx)
CATEGORIES = [
    (144, 1, "Engagement de la compagnie envers le bénéficiaire en cas de défaillance de l'assuré "
             "(soumission, bonne exécution, avance de démarrage, retenue de garantie).",
     [_champ("beneficiaire", "Bénéficiaire de la caution", "texte", True),
      _champ("nature_caution", "Nature de la caution"),
      _champ("objet_marche", "Objet du marché ou de l'engagement", "texte_long"),
      _champ("reference_marche", "Référence du marché / de l'appel d'offres")]),
    (82, 2, "Matériel informatique et électronique : dommages matériels, frais de reconstitution des médias, "
            "frais supplémentaires d'exploitation.",
     [_champ("designation", "Désignation du matériel assuré", "texte_long", True),
      _champ("situation", "Lieu d'installation du matériel")]),
    (83, 3, "Vols, détournements et détériorations des fonds, valeurs et locaux d'un établissement financier.",
     [_champ("designation", "Établissement et agences couverts", "texte_long", True), SITUATION]),
    (128, 4, "Dommages matériels à l'ouvrage pendant la durée du chantier.", CHANTIER),
    (129, 5, "Dommages aux équipements et installations pendant leur montage et leurs essais.", CHANTIER),
    (130, 6, "Dommages accidentels aux machines et équipements en exploitation.",
     [_champ("designation", "Machines assurées (désignation, marque, année)", "texte_long", True),
      _champ("situation", "Lieu d'exploitation")]),
    (131, 7, "Perte de marge brute et frais supplémentaires après un sinistre garanti.",
     [_champ("activite", "Activité de l'entreprise", "texte", True), SITUATION]),
    (132, 8, "Préfinancement de la réparation des désordres de nature décennale affectant l'ouvrage.", CHANTIER),
    (135, 9, "Biens assurés en tous lieux : déplacements, chantiers, dépôts.", [DESIGNATION, SITUATION]),
    (133, 10, "Marchandises et bijoux du commerçant, en magasin, en coffre ou en transport.",
     [_champ("designation", "Nature des marchandises assurées", "texte_long", True),
      _champ("situation", "Adresse du magasin")]),
    (134, 11, "Risques exclus des polices ordinaires, selon les conditions de la compagnie.", [DESIGNATION, SITUATION]),
    (136, 12, "Couverture combinée des dommages aux biens de l'entreprise.", [DESIGNATION, SITUATION]),
]


def initialiser(apps, schema_editor):
    DommageCategorie = apps.get_model("configuration_api", "DommageCategorie")
    ProduitParametre = apps.get_model("configuration_api", "ProduitParametre")
    tarifs = set()
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT idtarif FROM stdtarif WHERE codecategorie LIKE '4%%'")
        tarifs = {ligne[0] for ligne in cursor.fetchall()}
    for id_tarif, ordre, description, champs in CATEGORIES:
        if id_tarif in tarifs:
            DommageCategorie.objects.get_or_create(IdTarif=id_tarif, defaults=dict(
                Ordre=ordre, Description=description, ChampsRisque=champs, SaisieOuverte=True, Prorata=False,
            ))
    ProduitParametre.objects.update_or_create(IdProduit=9, defaults=dict(
        Onglet="Dommages", ModuleSaisie="tous-dommages", SaisieOuverte=True,
    ))


def retablir(apps, schema_editor):
    # Valeurs de la migration 0073
    apps.get_model("configuration_api", "ProduitParametre").objects.filter(IdProduit=9).update(
        Onglet="MRH", ModuleSaisie="tous-dommages", SaisieOuverte=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('configuration_api', '0074_parametre_mention_agrement'),
    ]

    operations = [
        migrations.CreateModel(
            name='DommageCategorie',
            fields=[
                ('IdTarif', models.IntegerField(db_column='idtarif', primary_key=True, serialize=False)),
                ('SaisieOuverte', models.BooleanField(db_column='saisieouverte', default=True)),
                ('Ordre', models.PositiveSmallIntegerField(db_column='ordre', default=0)),
                ('Description', models.TextField(blank=True, db_column='description', default='')),
                ('Prorata', models.BooleanField(db_column='prorata', default=False)),
                ('ChampsRisque', models.JSONField(blank=True, db_column='champsrisque', default=list)),
                ('DateModification', models.DateTimeField(auto_now=True, db_column='datemodification')),
            ],
            options={
                'verbose_name': 'Catégorie Dommages',
                'verbose_name_plural': 'Catégories Dommages',
                'db_table': 'lephare_dommage_categorie',
                'ordering': ['Ordre', 'IdTarif'],
            },
        ),
        migrations.CreateModel(
            name='DommageGarantie',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('IdOffre', models.IntegerField(db_column='idoffre')),
                ('IdCompagnie', models.IntegerField(db_column='idcompagnie')),
                ('IdSousGarantie', models.IntegerField(db_column='idsousgarantie')),
                ('TauxDefaut', models.DecimalField(blank=True, db_column='tauxdefaut', decimal_places=4, max_digits=9, null=True)),
                ('Obligatoire', models.BooleanField(db_column='obligatoire', default=False)),
                ('DateModification', models.DateTimeField(auto_now=True, db_column='datemodification')),
            ],
            options={
                'verbose_name': 'Garantie Dommages',
                'verbose_name_plural': 'Garanties Dommages',
                'db_table': 'lephare_dommage_garantie',
            },
        ),
        migrations.AddConstraint(
            model_name='dommagegarantie',
            constraint=models.UniqueConstraint(fields=('IdOffre', 'IdCompagnie', 'IdSousGarantie'), name='lephare_dommage_garantie_unique'),
        ),
        migrations.RunPython(initialiser, retablir),
    ]
