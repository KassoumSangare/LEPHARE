# Tarifs automobiles NSIA « à lecture directe » (documents d'OREOLE reçus le 2026-10-16 : TARIF VP ESSENCE, TARIF VP
# DIESEL, TARIF TPC, TARIF TPM ; le cinquième, TARIFS POOL TPV, est déjà en place : 0086). Jusqu'ici les primes des
# devis Auto étaient imposées à la main (presque tous les devis 2026), les tarifs n'ayant pas été implémentés par
# l'équipe URANUS.
#
#   - lephare_auto_tarif_grille / _ligne : une grille par compagnie, catégorie et énergie ; une ligne par tranche et
#     par durée (12, 6, 3 mois), montants tels que publiés (prime nette, accessoires, taxes, FGA, CEDEAO, TTC). Les
#     tranches identiques du document (ex. 3, 4, 5, 6 CV) sont regroupées, comme dans le barème RC.
#   - Offres tarifées par la grille (réglables) : les « tiers simple » NSIA de la catégorie (201 : 4, 143, 44 ;
#     202 : 47, 48 ; 203 : 52). Catégorie 212 exclue (NSIA : RC + 5 % pour les personnes morales).
#   - lephare_parametre auto.coefficients_duree : coefficients de prime des contrats de moins d'un an, jusqu'ici
#     écrits dans fn_calcul_taux_prime_fractionnee (lus par la base depuis la migration production 0161).
#
# Ce que les documents confirment du moteur : RC = barème × (1 − 35 %), FGA = 2 % de la RC, CEDEAO 1 000 F non
# proratisée, taxe 14,5 % de (prime nette + accessoires), 6 mois = 53 % et 3 mois = 28 % de la prime annuelle ;
# accessoire selon la prime nette HORS FGA et CEDEAO (TPC 6 mois 9 à 11 T : 98 292 F → 6 000 F).
# Retour : python manage.py migrate configuration_api 0088

from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models

NSIA = 1
SOURCE = "Tarif NSIA à lecture directe (documents reçus d'OREOLE le 16/10/2026)"
# (libellé, borne min, borne max, usages, durée en mois, prime nette, accessoires, taxes, FGA, CEDEAO, prime TTC)
VP_ESSENCE = [
    ('1 à 2 CV', 0, 2, '', 12, 53993, 6000, 8699, 763, 1000, 70455),
    ('3 à 6 CV', 3, 6, '', 12, 59330, 6000, 9473, 870, 1000, 76673),
    ('7 à 9 CV', 7, 9, '', 12, 63574, 6000, 10088, 954, 1000, 81617),
    ('10 à 11 CV', 10, 11, '', 12, 90405, 6000, 13979, 1491, 1000, 112875),
    ('12 CV et plus', 12, None, '', 12, 99742, 6000, 15333, 1678, 1000, 123753),
    ('1 à 2 CV', 0, 2, '', 6, 28616, 6000, 5019, 404, 1000, 41040),
    ('3 à 6 CV', 3, 6, '', 6, 31445, 6000, 5430, 461, 1000, 44335),
    ('7 à 9 CV', 7, 9, '', 6, 33694, 6000, 5756, 506, 1000, 46956),
    ('10 à 11 CV', 10, 11, '', 6, 47915, 6000, 7818, 790, 1000, 63522),
    ('12 CV et plus', 12, None, '', 6, 52863, 6000, 8535, 889, 1000, 69288),
    ('1 à 2 CV', 0, 2, '', 3, 15118, 6000, 3062, 214, 1000, 25394),
    ('3 à 6 CV', 3, 6, '', 3, 16612, 6000, 3279, 243, 1000, 27134),
    ('7 à 9 CV', 7, 9, '', 3, 17801, 6000, 3451, 267, 1000, 28519),
    ('10 à 11 CV', 10, 11, '', 3, 25313, 6000, 4540, 417, 1000, 37271),
    ('12 CV et plus', 12, None, '', 3, 27928, 6000, 4920, 470, 1000, 40317),
]
VP_DIESEL = [
    ('1 CV', 0, 1, '', 12, 53993, 6000, 8699, 763, 1000, 70455),
    ('2 à 4 CV', 2, 4, '', 12, 59330, 6000, 9473, 870, 1000, 76673),
    ('5 à 6 CV', 5, 6, '', 12, 63574, 6000, 10088, 954, 1000, 81617),
    ('7 à 8 CV', 7, 8, '', 12, 90405, 6000, 13979, 1491, 1000, 112875),
    ('9 CV et plus', 9, None, '', 12, 99742, 6000, 15333, 1678, 1000, 123753),
    ('1 CV', 0, 1, '', 6, 28616, 6000, 5019, 404, 1000, 41040),
    ('2 à 4 CV', 2, 4, '', 6, 31445, 6000, 5430, 461, 1000, 44335),
    ('5 à 6 CV', 5, 6, '', 6, 33694, 6000, 5756, 506, 1000, 46956),
    ('7 à 8 CV', 7, 8, '', 6, 47915, 6000, 7818, 790, 1000, 63522),
    ('9 CV et plus', 9, None, '', 6, 52863, 6000, 8535, 889, 1000, 69288),
    ('1 CV', 0, 1, '', 3, 15118, 6000, 3062, 214, 1000, 25394),
    ('2 à 4 CV', 2, 4, '', 3, 16612, 6000, 3279, 243, 1000, 27134),
    ('5 à 6 CV', 5, 6, '', 3, 17801, 6000, 3451, 267, 1000, 28519),
    ('7 à 8 CV', 7, 8, '', 3, 25313, 6000, 4540, 417, 1000, 37271),
    ('9 CV et plus', 9, None, '', 3, 27928, 6000, 4920, 470, 1000, 40317),
]
TPC = [
    ('1 T', 0, 1000, '', 12, 93182, 6000, 14381, 1547, 1000, 116110),
    ('2 à 3 T', 1001, 3000, '', 12, 116728, 9000, 18231, 2017, 1000, 146976),
    ('4 à 5 T', 3001, 5000, '', 12, 139169, 9000, 21485, 2466, 1000, 173120),
    ('6 à 8 T', 5001, 8000, '', 12, 174856, 9000, 26659, 3180, 1000, 214695),
    ('9 à 11 T', 8001, 11000, '', 12, 185456, 9000, 28196, 3392, 1000, 227044),
    ('12 à 13 T', 11001, 13000, '', 12, 193569, 9000, 29373, 3554, 1000, 236496),
    ('14 à 15 T', 13001, 15000, '', 12, 229968, 9000, 34650, 4282, 1000, 278900),
    ('Plus de 15 T', 15001, None, '', 12, 296217, 9000, 44256, 5607, 1000, 356081),
    ('Tracteur routier', None, None, '017,022', 12, 317406, 9000, 47329, 6031, 1000, 380766),
    ('1 T', 0, 1000, '', 6, 49386, 6000, 8031, 820, 1000, 65237),
    ('2 à 3 T', 1001, 3000, '', 6, 61866, 6000, 9841, 1069, 1000, 79775),
    ('4 à 5 T', 3001, 5000, '', 6, 73760, 6000, 11565, 1307, 1000, 93632),
    ('6 à 8 T', 5001, 8000, '', 6, 92674, 6000, 14308, 1685, 1000, 115666),
    ('9 à 11 T', 8001, 11000, '', 6, 98292, 6000, 15122, 1798, 1000, 122212),
    ('12 à 13 T', 11001, 13000, '', 6, 102592, 9000, 16181, 1884, 1000, 130656),
    ('14 à 15 T', 13001, 15000, '', 6, 121883, 9000, 18978, 2270, 1000, 153131),
    ('Plus de 15 T', 15001, None, '', 6, 156995, 9000, 24069, 2972, 1000, 194036),
    ('Tracteur routier', None, None, '017,022', 6, 168225, 9000, 25698, 3196, 1000, 207119),
    ('1 T', 0, 1000, '', 3, 26091, 6000, 4653, 433, 1000, 38177),
    ('2 à 3 T', 1001, 3000, '', 3, 32684, 6000, 5609, 565, 1000, 45858),
    ('4 à 5 T', 3001, 5000, '', 3, 38967, 6000, 6520, 691, 1000, 53179),
    ('6 à 8 T', 5001, 8000, '', 3, 48960, 6000, 7969, 890, 1000, 64819),
    ('9 à 11 T', 8001, 11000, '', 3, 51928, 6000, 8400, 950, 1000, 68277),
    ('12 à 13 T', 11001, 13000, '', 3, 54199, 6000, 8729, 995, 1000, 70923),
    ('14 à 15 T', 13001, 15000, '', 3, 64391, 6000, 10207, 1199, 1000, 82797),
    ('Plus de 15 T', 15001, None, '', 3, 82941, 6000, 12896, 1570, 1000, 104407),
    ('Tracteur routier', None, None, '017,022', 3, 88874, 6000, 13757, 1689, 1000, 111319),
]
TPM = [
    ('1 T', 0, 1000, '', 12, 102630, 9000, 16186, 1736, 1000, 130552),
    ('2 à 3 T', 1001, 3000, '', 12, 127200, 9000, 19749, 2227, 1000, 159176),
    ('4 à 5 T', 3001, 5000, '', 12, 155605, 9000, 23868, 2795, 1000, 192267),
    ('6 à 9 T', 5001, 9000, '', 12, 191160, 9000, 29023, 3506, 1000, 233689),
    ('10 à 12 T', 9001, 12000, '', 12, 236465, 9000, 35592, 4412, 1000, 286469),
    ('13 à 15 T', 12001, 15000, '', 12, 304780, 9000, 45498, 5779, 1000, 366057),
    ('Plus de 15 T', 15001, None, '', 12, 333705, 9000, 49692, 6357, 1000, 399754),
    ('Tracteur routier', None, None, '017,022', 12, 333705, 9000, 49692, 6357, 1000, 399754),
    ('1 T', 0, 1000, '', 6, 54394, 6000, 8757, 920, 1000, 71071),
    ('2 à 3 T', 1001, 3000, '', 6, 67416, 6000, 10645, 1180, 1000, 86241),
    ('4 à 5 T', 3001, 5000, '', 6, 82470, 6000, 12828, 1481, 1000, 103780),
    ('6 à 9 T', 5001, 9000, '', 6, 101315, 9000, 15996, 1858, 1000, 129168),
    ('10 à 12 T', 9001, 12000, '', 6, 125326, 9000, 19477, 2338, 1000, 157142),
    ('13 à 15 T', 12001, 15000, '', 6, 161533, 9000, 24727, 3063, 1000, 199324),
    ('Plus de 15 T', 15001, None, '', 6, 176863, 9000, 26950, 3369, 1000, 217183),
    ('Tracteur routier', None, None, '017,022', 6, 176863, 9000, 26950, 3369, 1000, 217183),
    ('1 T', 0, 1000, '', 3, 28736, 6000, 5037, 486, 1000, 41259),
    ('2 à 3 T', 1001, 3000, '', 3, 35616, 6000, 6034, 624, 1000, 49274),
    ('4 à 5 T', 3001, 5000, '', 3, 43569, 6000, 7188, 783, 1000, 58540),
    ('6 à 9 T', 5001, 9000, '', 3, 53525, 6000, 8631, 982, 1000, 70138),
    ('10 à 12 T', 9001, 12000, '', 3, 66210, 6000, 10470, 1235, 1000, 84916),
    ('13 à 15 T', 12001, 15000, '', 3, 85338, 6000, 13244, 1618, 1000, 107200),
    ('Plus de 15 T', 15001, None, '', 3, 93437, 6000, 14418, 1780, 1000, 116636),
    ('Tracteur routier', None, None, '017,022', 3, 93437, 6000, 14418, 1780, 1000, 116636),
]
GRILLES = [
    # (libellé, catégories, énergie, critère, offres, lignes)
    ("VP essence (promenade et affaires)", "201", 1, "PUISSANCE", "4,143,44", VP_ESSENCE),
    ("VP diesel (promenade et affaires)", "201", 2, "PUISSANCE", "4,143,44", VP_DIESEL),
    ("TPC (transport pour propre compte)", "202", None, "CHARGE_UTILE", "47,48", TPC),
    ("TPM (transport public de marchandises)", "203", None, "CHARGE_UTILE", "52", TPM),
]
COEFFICIENTS = "5/10/19/28/37/45/53/61/69/77/85/93/100"
PARAMETRES = [
    ("auto.coefficients_duree", "auto_tarifs", "Coefficients de prime des contrats de moins d'un an",
     "Treize pourcentages de la prime annuelle séparés par « / » : 15 jours ou moins, puis 1 à 12 mois (un mois "
     "entamé compte pour un mois entier). Utilisés par le calcul NSIA ; les tarifs à lecture directe donnent "
     "6 mois = 53 % et 3 mois = 28 %.", "texte", COEFFICIENTS, "", None, None, 1),
]


def initialiser(apps, schema_editor):
    Grille = apps.get_model("configuration_api", "TarifAutoGrille")
    Ligne = apps.get_model("configuration_api", "TarifAutoGrilleLigne")
    if not Grille.objects.filter(IdCompagnie=NSIA).exists():
        for ordre, (libelle, categories, energie, critere, offres, lignes) in enumerate(GRILLES, start=1):
            grille = Grille.objects.create(IdCompagnie=NSIA, Libelle=libelle, Categories=categories, IdEnergie=energie,
                                           Critere=critere, Offres=offres, Source=SOURCE, Ordre=ordre)
            Ligne.objects.bulk_create([
                Ligne(Grille=grille, Libelle=lib, BorneMin=bmin, BorneMax=bmax, Usages=usages, DureeMois=mois,
                      PrimeNette=Decimal(pn), Accessoire=Decimal(acc), Taxe=Decimal(taxe), Fga=Decimal(fga),
                      Cedeao=Decimal(cedeao), PrimeTtc=Decimal(ttc), Ordre=i)
                for i, (lib, bmin, bmax, usages, mois, pn, acc, taxe, fga, cedeao, ttc) in enumerate(lignes, start=1)
            ])
    ParametreGeneral = apps.get_model("configuration_api", "ParametreGeneral")
    for cle, groupe, libelle, aide, type_, valeur, unite, minimum, maximum, ordre in PARAMETRES:
        ParametreGeneral.objects.get_or_create(Cle=cle, defaults=dict(
            Groupe=groupe, Libelle=libelle, Aide=aide, Type=type_, Valeur=valeur, ValeurOrigine=valeur,
            Unite=unite, Minimum=minimum, Maximum=maximum, Ordre=ordre,
        ))


def retirer(apps, schema_editor):
    apps.get_model("configuration_api", "ParametreGeneral").objects.filter(Cle__in=[p[0] for p in PARAMETRES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0088_arrondi_montants"),
    ]

    operations = [
        migrations.CreateModel(
            name="TarifAutoGrille",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("IdCompagnie", models.IntegerField(db_column="idcompagnie")),
                ("Libelle", models.CharField(db_column="libelle", max_length=100)),
                ("Categories", models.CharField(db_column="categories", max_length=100)),
                ("IdEnergie", models.IntegerField(blank=True, db_column="idenergie", null=True)),
                ("Critere", models.CharField(choices=[("PUISSANCE", "Puissance fiscale (CV)"), ("CHARGE_UTILE", "Charge utile (kg)")], db_column="critere", default="PUISSANCE", max_length=20)),
                ("Offres", models.CharField(blank=True, db_column="offres", default="", max_length=200)),
                ("Actif", models.BooleanField(db_column="actif", default=True)),
                ("Source", models.CharField(blank=True, db_column="source", default="", max_length=200)),
                ("Ordre", models.PositiveSmallIntegerField(db_column="ordre", default=0)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
                ("ModifiePar", models.CharField(blank=True, db_column="modifiepar", default="", max_length=150)),
            ],
            options={
                "verbose_name": "Tarif automobile à lecture directe",
                "verbose_name_plural": "Tarifs automobiles à lecture directe",
                "db_table": "lephare_auto_tarif_grille",
                "ordering": ["IdCompagnie", "Ordre", "id"],
            },
        ),
        migrations.CreateModel(
            name="TarifAutoGrilleLigne",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("Libelle", models.CharField(db_column="libelle", max_length=60)),
                ("BorneMin", models.IntegerField(blank=True, db_column="bornemin", null=True)),
                ("BorneMax", models.IntegerField(blank=True, db_column="bornemax", null=True)),
                ("Usages", models.CharField(blank=True, db_column="usages", default="", max_length=60)),
                ("DureeMois", models.PositiveSmallIntegerField(db_column="dureemois")),
                ("PrimeNette", models.DecimalField(db_column="primenette", decimal_places=2, max_digits=15)),
                ("Accessoire", models.DecimalField(db_column="accessoire", decimal_places=2, max_digits=15)),
                ("Taxe", models.DecimalField(db_column="taxe", decimal_places=2, max_digits=15)),
                ("Fga", models.DecimalField(db_column="fga", decimal_places=2, max_digits=15)),
                ("Cedeao", models.DecimalField(db_column="cedeao", decimal_places=2, max_digits=15)),
                ("PrimeTtc", models.DecimalField(db_column="primettc", decimal_places=2, max_digits=15)),
                ("Ordre", models.PositiveSmallIntegerField(db_column="ordre", default=0)),
                ("Grille", models.ForeignKey(db_column="grille", on_delete=django.db.models.deletion.CASCADE, related_name="lignes", to="configuration_api.tarifautogrille")),
            ],
            options={
                "verbose_name": "Tranche d'un tarif à lecture directe",
                "verbose_name_plural": "Tranches des tarifs à lecture directe",
                "db_table": "lephare_auto_tarif_grille_ligne",
                "ordering": ["Grille", "-DureeMois", "Ordre", "id"],
            },
        ),
        migrations.RunPython(initialiser, retirer),
    ]
