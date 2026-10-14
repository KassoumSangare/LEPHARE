# Compte rendu de la séance LE PHARE du 12-10-2026, ASSURANCE CAUTION :
#   - « Supprimer l'annexe au bas de la quittance » : la cotation d'une caution n'a plus de page « ANNEXE
#     TABLEAU DES GARANTIES », les garanties sont citées dans la cotation (lephare_dommage_categorie.annexecotation,
#     réglable par catégorie).
#   - « Ajouter aux pièces de production la quittance de prime ainsi que le document intitulé « GARANTIE DE LA
#     SOUMISSION » » (modèles joints : FACTURE DE PRIME N° 000034/07/26 et GARANTIE DE SOUMISSION NSIA) :
#     référence de la facture (« ASSURANCE CAUTION (AO… MAIRIE DE …) ») et documents de production par
#     catégorie (lephare_dommage_document), texte à champs entre accolades modifiable dans
#     Administration > Réglages Dommages.
#   - Rubriques du risque Caution ajoutées pour ces documents : bénéficiaire, n° de l'appel d'offres, date de
#     l'offre.

from django.db import migrations, models

ID_TARIF_CAUTION = 144
ID_NSIA = 1
CHAMPS_AJOUTES = [
    {"Cle": "beneficiaire", "Libelle": "Bénéficiaire (autorité contractante)", "Type": "texte", "Obligatoire": False},
    {"Cle": "numero_appel_offres", "Libelle": "N° de l'appel d'offres", "Type": "texte", "Obligatoire": False},
    {"Cle": "date_offre", "Libelle": "Date de dépôt de l'offre", "Type": "date", "Obligatoire": False},
]
REFERENCE_FACTURE = "{numero_appel_offres} {beneficiaire}"

GARANTIE_SOUMISSION = """**NSIA ASSURANCES CI** au capital de 5 000 031 412 FCFA, ayant son siège social à Immeuble Manzi, Avenue Noguès Rue A43 Plateau, 01 BP 1571 Abidjan 01, inscrite au registre du commerce sous le numéro CI-ABJ-1995-B183449, représentée par : **Monsieur Magloire DOCHAMOU, son Directeur Général,** ayant donné mandat à Monsieur **Leger KOFFI**, son **Directeur Central des Opérations**, autorisé à signer et à produire des engagements en son nom.

**Bénéficiaire : {beneficiaire}.**

**Date** : {date_effet}

**Garantie d'offre numéro : {numero_police}**

Nous avons été informés que **{souscripteur}** (ci-après dénommé « **le candidat** ») a répondu à votre appel d'offres numéro **N° {numero_appel_offres}** pour **{nature_travaux:maj}** et vous a soumis son offre en date du **{date_offre_lettres}** (ci-après dénommée « **l'Offre** »).

En vertu des dispositions du Dossier d'Appel d'Offres, l'Offre doit accompagner d'une garantie de soumission.

A la demande du candidat, nous **NSIA ASSURANCES COTE D'IVOIRE** nous engageons par la présente, sans réserve et irrévocablement à nous porter caution et à vous payer à première demande, toutes sommes d'argent que vous pourriez réclamer dans la limite de **{capital_lettres} ({capital}) Francs CFA.**

Votre demande en paiement doit accompagner d'une déclaration attestant que le candidat n'a pas exécuté une des obligations auxquelles il est tenu en vertu de l'Offre ou a fait l'objet de sanction pour faute commise dans le cadre de la procédure de passation du marché conformément aux articles **155** et **156** du Code des Marchés publics, à savoir :
a) s'il n'accepte pas les modifications de son offre suite à la correction des erreurs de calcul ; ou
b) s'il retire l'Offre pendant la période de validité qu'il a spécifiée dans la lettre de soumission de l'offre ; ou
c) si, s'étant vu notifier l'acceptation de l'Offre par l'Autorité Contractante pendant la période de validité telle qu'indiquée dans la lettre de soumission de l'offre ou prorogée par l'Autorité contractante avant l'expiration de cette période, il :
    1. ne signe pas le marché ; ou
    2. ne fournit pas la garantie de bonne exécution du marché, s'il est tenu de le faire ainsi qu'il est prévu dans les Instructions aux Candidats ; ou
d) s'il a fait l'objet d'une sanction des autorités compétentes ou de l'Autorité de Régulation de la commande publique ou d'une juridiction compétente, conduisant à la saisie des garanties qu'il a constituées dans le cadre de la passation du marché, conformément aux articles **155** et **156** du Code des marchés publics.

**La garantie d'offre demeurera valide 30 jours après l'expiration du délai de validité des offres (90 jours + 30 jours), soit 120 jours.**

La présente garantie expire (a) si le marché est octroyé au candidat, lorsque nous recevrons une copie du marché signé et du garantie de bonne exécution émis en votre nom, selon les instructions au candidat ; ou (b) si le marché n'est pas octroyé au candidat, à la première des dates suivantes : (i) lorsque nous recevrons copie de votre notification au candidat du nom du candidat retenu, ou (ii) trente (30) jours après la désignation de l'attributaire.
Toute demande de paiement au titre de la présente garantie doit reçue à cette date au plus tard.

La présente garantie de soumission est établie conformément à l'Acte Uniforme OHADA portant organisation des sûretés du 15 décembre 2010 (JO OHADA n° 22 du 15 février 2011) dont les articles 39 et 40 sont respectivement relatifs aux règles de formation de garantie et contre garantie autonomes et à ses mentions obligatoires."""


def reglages_caution(apps, schema_editor):
    DommageCategorie = apps.get_model("configuration_api", "DommageCategorie")
    DommageDocument = apps.get_model("configuration_api", "DommageDocument")
    categorie = DommageCategorie.objects.filter(IdTarif=ID_TARIF_CAUTION).first()
    if categorie is None:
        categorie = DommageCategorie(IdTarif=ID_TARIF_CAUTION, Ordre=999)
    categorie.AnnexeCotation = False
    if not categorie.ReferenceFacture:
        categorie.ReferenceFacture = REFERENCE_FACTURE
    champs = list(categorie.ChampsRisque or [])
    cles = {c.get("Cle") for c in champs if isinstance(c, dict)}
    champs += [dict(c) for c in CHAMPS_AJOUTES if c["Cle"] not in cles]
    categorie.ChampsRisque = champs
    categorie.save()
    if not DommageDocument.objects.filter(IdTarif=ID_TARIF_CAUTION, Titre="GARANTIE DE SOUMISSION").exists():
        DommageDocument.objects.create(
            IdTarif=ID_TARIF_CAUTION,
            IdCompagnie=ID_NSIA,
            Titre="GARANTIE DE SOUMISSION",
            ConditionChamp="type_cautionnement",
            ConditionValeur="SOUMISSION",
            Corps=GARANTIE_SOUMISSION,
            Signataire="Léger KOFFI\nDIRECTEUR CENTRAL DES OPERATIONS",
            MentionSignature="NSIA ASSURANCES COTE D'IVOIRE",
            Actif=True,
            Ordre=1,
        )


def annuler(apps, schema_editor):
    DommageCategorie = apps.get_model("configuration_api", "DommageCategorie")
    DommageDocument = apps.get_model("configuration_api", "DommageDocument")
    DommageDocument.objects.filter(IdTarif=ID_TARIF_CAUTION, Titre="GARANTIE DE SOUMISSION").delete()
    categorie = DommageCategorie.objects.filter(IdTarif=ID_TARIF_CAUTION).first()
    if categorie:
        ajoutees = {c["Cle"] for c in CHAMPS_AJOUTES}
        categorie.ChampsRisque = [c for c in (categorie.ChampsRisque or []) if not (isinstance(c, dict) and c.get("Cle") in ajoutees)]
        categorie.save()


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0086_pool_tpv"),
    ]

    operations = [
        migrations.AddField(
            model_name="dommagecategorie",
            name="AnnexeCotation",
            field=models.BooleanField(db_column="annexecotation", default=True),
        ),
        migrations.AddField(
            model_name="dommagecategorie",
            name="ReferenceFacture",
            field=models.CharField(blank=True, db_column="referencefacture", default="", max_length=200),
        ),
        migrations.CreateModel(
            name="DommageDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("IdTarif", models.IntegerField(db_column="idtarif")),
                ("IdCompagnie", models.IntegerField(db_column="idcompagnie", default=0)),
                ("Titre", models.CharField(db_column="titre", max_length=120)),
                ("ConditionChamp", models.CharField(blank=True, db_column="conditionchamp", default="", max_length=40)),
                ("ConditionValeur", models.CharField(blank=True, db_column="conditionvaleur", default="", max_length=120)),
                ("Corps", models.TextField(db_column="corps")),
                ("Signataire", models.TextField(blank=True, db_column="signataire", default="")),
                ("MentionSignature", models.CharField(blank=True, db_column="mentionsignature", default="", max_length=200)),
                ("Actif", models.BooleanField(db_column="actif", default=True)),
                ("Ordre", models.PositiveSmallIntegerField(db_column="ordre", default=0)),
                ("DateModification", models.DateTimeField(auto_now=True, db_column="datemodification")),
            ],
            options={
                "verbose_name": "Document de production Dommages",
                "verbose_name_plural": "Documents de production Dommages",
                "db_table": "lephare_dommage_document",
                "ordering": ["IdTarif", "Ordre", "id"],
            },
        ),
        migrations.RunPython(reglages_caution, annuler),
    ]
