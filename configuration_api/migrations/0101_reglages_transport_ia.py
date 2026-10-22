# Réglages par branche (demande du 2026-10-21 : « booste le paramétrage pour éviter au maximum les interventions dans
# le code source », pour toutes les branches de production actives).
#
#   - Transport hors GUCE : modes de transport (lephare_transport_mode) et garanties avec leur taux proposé par mode
#     (lephare_transport_garantie), qui étaient écrits dans production/views_transport_hors_guce.py ; les taux déjà
#     réglés (paramètres transport.taux_* et transport.surprime_*, migration 0099) y sont repris puis retirés ;
#     primes minimums, coûts de police et taxe passent au groupe transport_tarif ; listes de saisie (état,
#     emballages, conditionnements, risques spéciaux) en paramètres, une valeur par ligne.
#   - Individuelle Accidents NSIA : taux par classe d'activité (lephare_ia_taux_classe) et accessoires par tranche
#     de prime nette (lephare_ia_accessoire_tranche), écrits jusqu'ici dans fn_calcul_prime_ia_nsia et
#     fn_get_accessoire_ia_nsia (lus par leurs versions 2, migration production 0173). Valeurs identiques.
# Retour : python manage.py migrate configuration_api 0100 (après production 0172)

from decimal import Decimal

from django.db import migrations, models

MODES = [
    ("MARITIME", "Maritime", "611", "Connaissement (B/L)", "Navire", ["En cale, sous pont", "En pontée, sur le pont", "En conteneur"]),
    ("AERIEN", "Aérien", "612", "Lettre de transport aérien (LTA)", "Compagnie aérienne et n° de vol", ["En soute", "En conteneur aérien"]),
    ("TERRESTRE", "Terrestre", "614", "Lettre de voiture", "Camion et immatriculation",
     ["Camion bâché", "Camion plateau", "Camion citerne", "Camion frigorifique", "En conteneur"]),
    ("FERROVIAIRE", "Ferroviaire", "613", "Lettre de voiture ferroviaire", "Train", ["Wagon couvert", "Wagon plat", "Wagon citerne", "En conteneur"]),
    ("FLUVIAL", "Fluvial ou lagunaire", "619", "Connaissement fluvial", "Barge ou bateau",
     ["En cale, sous pont", "En pontée, sur le pont", "En conteneur"]),
]
CODES_MODES = [m[0] for m in MODES]

# code, groupe, sous-garantie, libellé, description, paramètre du taux (« {mode} » : un par mode), taux minimum
GARANTIES = [
    ("TOUS_RISQUES", "BASE", "19011", "Tous risques",
     "La couverture la plus large : dommages et pertes de la marchandise pendant le transport, quelle qu'en soit la "
     "cause, sauf exclusions de la police.", "transport.taux_tous_risques_{mode}", False),
    ("FAP_SAUF", "BASE", "30022", "FAP Sauf, accidents majeurs",
     "Franc d'avaries particulières sauf : seuls les événements majeurs sont couverts, comme le naufrage, "
     "l'échouement, l'abordage, l'incendie ou la chute du colis.", "transport.taux_fap_sauf", True),
    ("ACCIDENTS_CARACTERISES", "BASE", "50028", "Accidents caractérisés et vols consécutifs",
     "Dommages dus à un accident du moyen de transport, collision, renversement ou incendie, et vols qui en "
     "résultent. Usuelle en transport terrestre.", "transport.taux_accidents_caracterises", False),
    ("GUERRE", "EXTENSION", "19001", "Risques de guerre", "Guerre, hostilités et risques assimilés. Taux unique.",
     "transport.taux_guerre", False),
    ("GREVES", "EXTENSION", "14008", "Grèves et émeutes", "Grèves, émeutes et mouvements populaires.",
     "transport.taux_greves", False),
    ("TRANSBORDEMENT", "EXTENSION", "30021", "Transbordement",
     "Surprime quand la marchandise change de navire ou de véhicule en cours de route.", "transport.surprime_transbordement", False),
    ("EMBALLAGE", "EXTENSION", "30023", "Emballage, clause 53",
     "Surprime quand l'emballage lui-même est assuré, pas seulement son contenu.", "transport.surprime_emballage", False),
    ("CHARGEMENT", "EXTENSION", "30024", "Chargement et déchargement",
     "Dommages survenus pendant la manutention au départ et à l'arrivée.", "transport.taux_chargement", False),
]
MONTANTS = ["transport.prime_minimum", "transport.prime_minimum_police_voyage", "transport.cout_police_voyage",
            "transport.cout_par_voyage", "transport.cout_police_annuelle", "transport.taux_taxe"]
LISTES = [
    ("transport.liste_etats", "État de la marchandise", "Neuve\nUsagée"),
    ("transport.liste_emballages", "Emballages proposés",
     "Caisses pleines\nCaisses à claire-voie\nCartons\nBalles fermées et cerclées\nSacs de jute neufs\n"
     "Sacs papier multiplis\nFûts\nBouteilles\nPalettes filmées\nSans emballage"),
    ("transport.liste_conditionnements", "Conditionnements proposés",
     "Conteneur complet porte à porte\nConteneur de groupage\nConteneur réfrigéré\nConventionnel simple\n"
     "Conventionnel palettisé\nVrac"),
    ("transport.liste_risques_speciaux", "Risques spéciaux proposés",
     "Rouille\nOxydation\nDéformation\nDenrées périssables\nCasse\nCoulage\nMouille\nAnimaux vivants"),
]

CLASSES_IA = [("01", "0.85", "1.5"), ("02", "1.15", "2.5"), ("03", "1.3", "3"), ("04", "1.8", "4"), ("05", "3", "5")]
TRANCHES_IA = [(25000, 3000), (100000, 6000), (500000, 10000), (1000000, 20000), (2000000, 25000), (3000000, 30000),
               (5000000, 50000)]


def amorcer(apps, schema_editor):
    Parametre = apps.get_model("configuration_api", "ParametreGeneral")
    Mode = apps.get_model("configuration_api", "TransportMode")
    Garantie = apps.get_model("configuration_api", "TransportGarantie")
    valeurs = {p.Cle: (p.Valeur or "").strip() for p in Parametre.objects.filter(Cle__startswith="transport.")}
    for ordre, (code, libelle, categorie, document, moyen, chargements) in enumerate(MODES, start=1):
        Mode.objects.get_or_create(Code=code, defaults=dict(Libelle=libelle, CodeCategorie=categorie, Document=document,
                                                            Moyen=moyen, Chargements=chargements, Ordre=ordre))
    cles_taux = set()
    for ordre, (code, groupe, sg, libelle, description, cle, minimum) in enumerate(GARANTIES, start=1):
        taux = {}
        for mode in CODES_MODES:
            cle_mode = cle.replace("{mode}", mode.lower())
            cles_taux.add(cle_mode)
            taux[mode] = valeurs.get(cle_mode) or None
        Garantie.objects.get_or_create(Code=code, defaults=dict(
            Groupe=groupe, CodeSousGarantie=sg, Libelle=libelle, Description=description, Taux=taux,
            TauxMinimum=minimum, Ordre=ordre))
    Parametre.objects.filter(Cle__in=cles_taux).delete()
    Parametre.objects.filter(Cle__in=MONTANTS).update(Groupe="transport_tarif")
    for ordre, (cle, libelle, valeur) in enumerate(LISTES, start=1):
        Parametre.objects.get_or_create(Cle=cle, defaults=dict(
            Groupe="transport_listes", Libelle=libelle, Aide="Proposés à la cotation, une valeur par ligne ; « Autre » reste possible.",
            Type="texte_long", Valeur=valeur, ValeurOrigine=valeur, Ordre=ordre))

    Classe = apps.get_model("configuration_api", "IaTauxClasse")
    Tranche = apps.get_model("configuration_api", "IaAccessoireTranche")
    for classe, deces, frais in CLASSES_IA:
        Classe.objects.get_or_create(IdCompagnie=1, Classe=classe, defaults=dict(
            Libelle=f"Classe {int(classe)}", TauxDeces=Decimal(deces), TauxInvalidite=Decimal(deces),
            TauxFraisMedicaux=Decimal(frais)))
    if not Tranche.objects.filter(IdCompagnie=1).exists():
        for plafond, montant in TRANCHES_IA:
            Tranche.objects.create(IdCompagnie=1, PrimeMax=Decimal(plafond), Montant=Decimal(montant))
        Tranche.objects.create(IdCompagnie=1, PrimeMax=None, Montant=Decimal(50000), TauxAuDela=Decimal("0.5"))


def retirer(apps, schema_editor):
    """Paramètres de taux Transport recréés depuis les garanties (avant suppression des tables)."""
    Parametre = apps.get_model("configuration_api", "ParametreGeneral")
    Garantie = apps.get_model("configuration_api", "TransportGarantie")
    libelles = {m[0]: m[1].lower() for m in MODES}
    for ordre, (code, _groupe, _sg, libelle, _d, cle, _m) in enumerate(GARANTIES, start=2):
        g = Garantie.objects.filter(Code=code).first()
        modes = CODES_MODES if "{mode}" in cle else [CODES_MODES[0]]
        for mode in modes:
            valeur = str(((g.Taux if g else {}) or {}).get(mode) or "")
            Parametre.objects.get_or_create(Cle=cle.replace("{mode}", mode.lower()), defaults=dict(
                Groupe="transport", Libelle=f"{libelle} — {libelles[mode]}" if "{mode}" in cle else libelle,
                Type="pourcentage", Valeur=valeur, ValeurOrigine="", Unite="%", Minimum=Decimal("0"), Maximum=Decimal("100"),
                Ordre=ordre))
    Parametre.objects.filter(Cle__in=MONTANTS).update(Groupe="transport")
    Parametre.objects.filter(Cle__in=[l[0] for l in LISTES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0100_produit_compagnie_defaut"),
    ]

    operations = [
        migrations.CreateModel(
            name="TransportMode",
            fields=[
                ("Code", models.CharField(db_column="code", max_length=12, primary_key=True, serialize=False)),
                ("Libelle", models.CharField(db_column="libelle", max_length=60)),
                ("CodeCategorie", models.CharField(db_column="codecategorie", max_length=3)),
                ("Document", models.CharField(blank=True, db_column="document", default="", max_length=80)),
                ("Moyen", models.CharField(blank=True, db_column="moyen", default="", max_length=80)),
                ("Chargements", models.JSONField(db_column="chargements", default=list)),
                ("Ordre", models.PositiveSmallIntegerField(db_column="ordre", default=0)),
                ("Actif", models.BooleanField(db_column="actif", default=True)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
                ("ModifiePar", models.CharField(blank=True, db_column="modifiepar", default="", max_length=150)),
            ],
            options={"verbose_name": "Mode de transport", "verbose_name_plural": "Modes de transport",
                     "db_table": "lephare_transport_mode", "ordering": ["Ordre", "Code"]},
        ),
        migrations.CreateModel(
            name="TransportGarantie",
            fields=[
                ("Code", models.CharField(db_column="code", max_length=30, primary_key=True, serialize=False)),
                ("Groupe", models.CharField(choices=[("BASE", "Garantie de base"), ("EXTENSION", "Extension ou surprime")], db_column="groupe", max_length=10)),
                ("Libelle", models.CharField(db_column="libelle", max_length=80)),
                ("Description", models.TextField(blank=True, db_column="description", default="")),
                ("CodeSousGarantie", models.CharField(db_column="codesousgarantie", max_length=10)),
                ("Taux", models.JSONField(db_column="taux", default=dict)),
                ("TauxMinimum", models.BooleanField(db_column="tauxminimum", default=False)),
                ("Ordre", models.PositiveSmallIntegerField(db_column="ordre", default=0)),
                ("Active", models.BooleanField(db_column="active", default=True)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
                ("ModifiePar", models.CharField(blank=True, db_column="modifiepar", default="", max_length=150)),
            ],
            options={"verbose_name": "Garantie Transport", "verbose_name_plural": "Garanties Transport",
                     "db_table": "lephare_transport_garantie", "ordering": ["Groupe", "Ordre", "Code"]},
        ),
        migrations.CreateModel(
            name="IaTauxClasse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("IdCompagnie", models.IntegerField(db_column="idcompagnie")),
                ("Classe", models.CharField(db_column="classe", max_length=2)),
                ("Libelle", models.CharField(blank=True, db_column="libelle", default="", max_length=120)),
                ("TauxDeces", models.DecimalField(db_column="tauxdeces", decimal_places=4, max_digits=8)),
                ("TauxInvalidite", models.DecimalField(db_column="tauxinvalidite", decimal_places=4, max_digits=8)),
                ("TauxFraisMedicaux", models.DecimalField(db_column="tauxfraismedicaux", decimal_places=4, max_digits=8)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
                ("ModifiePar", models.CharField(blank=True, db_column="modifiepar", default="", max_length=150)),
            ],
            options={"verbose_name": "Taux IA par classe d'activité", "verbose_name_plural": "Taux IA par classe d'activité",
                     "db_table": "lephare_ia_taux_classe", "ordering": ["IdCompagnie", "Classe"]},
        ),
        migrations.AddConstraint(
            model_name="iatauxclasse",
            constraint=models.UniqueConstraint(fields=("IdCompagnie", "Classe"), name="lephare_ia_taux_classe_unique"),
        ),
        migrations.CreateModel(
            name="IaAccessoireTranche",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("IdCompagnie", models.IntegerField(db_column="idcompagnie")),
                ("PrimeMax", models.DecimalField(blank=True, db_column="primemax", decimal_places=2, max_digits=15, null=True)),
                ("Montant", models.DecimalField(db_column="montant", decimal_places=2, max_digits=15)),
                ("TauxAuDela", models.DecimalField(blank=True, db_column="tauxaudela", decimal_places=4, max_digits=8, null=True)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
                ("ModifiePar", models.CharField(blank=True, db_column="modifiepar", default="", max_length=150)),
            ],
            options={"verbose_name": "Tranche d'accessoires IA", "verbose_name_plural": "Tranches d'accessoires IA",
                     "db_table": "lephare_ia_accessoire_tranche", "ordering": ["IdCompagnie", "PrimeMax"]},
        ),
        migrations.RunPython(amorcer, retirer),
    ]
