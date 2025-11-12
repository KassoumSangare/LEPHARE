from django.db import models

# Create your models here.
class DemandeAttestation(models.Model):
    id = models.AutoField(
        verbose_name="Id Demande Attestation",
        primary_key=True,
        db_column="id",
    )
    numero_demande = models.CharField(
        verbose_name="Numéro Demande",
        max_length=100,
        null=True,
        blank=True,
        db_column="numerodemande",
    )
    code_demandeur = models.CharField(
        verbose_name="Code Demandeur",
        max_length=100,
        db_column="codedemandeur",
    )
    code_compagnie = models.CharField(
        verbose_name="Code Compagnie", db_column="codecompagnie", max_length=100
    )
    code_intermediaire = models.CharField(
        verbose_name="Code Intermediaire", db_column="codeintermediaire", max_length=100
    )
    code_acces = models.CharField(
        verbose_name="Code Accès", db_column="codeacces", max_length=100
    )
    point_vente = models.CharField(
        verbose_name="Code Point Vente", db_column="pointvente", max_length=100
    )
    bureau = models.CharField(verbose_name="Bureau", db_column="bureau", max_length=100)

    class Meta:
        db_table = "stddemandeattestation"
        managed = False


class ItemDemandeAttestation(models.Model):
    id = models.AutoField(
        verbose_name="Id Item Demande", primary_key=True, db_column="id"
    )
    demande_attestation = models.ForeignKey(
        DemandeAttestation,
        on_delete=models.DO_NOTHING,
        verbose_name="Demande Atteststion",
        db_column="id_demande_attestation",
        related_name="liste_demande",
    )
    date_demande_edition = models.DateField(
        verbose_name="Date Demande",
        db_column="datedemandeedition",
    )
    date_souscription = models.DateField(
        verbose_name="Date Souscription", db_column="datesouscription"
    )
    date_effet = models.DateField(verbose_name="Date Effet", db_column="dateeffet")
    date_echeance = models.DateField(
        verbose_name="Date Echéance", db_column="dateecheance"
    )
    genre_vehicule = models.CharField(
        max_length=50,
        verbose_name="Genre Véhicule",
        db_column="genrevehicule",
    )
    numero_immatriculation = models.CharField(
        max_length=10,
        verbose_name="Numéro Immatriculation",
        db_column="numeroimmatriculation",
    )
    type_vehicule = models.CharField(
        verbose_name="Type Véhicule",
        db_column="typevehicule",
        max_length=20,
    )
    model_vehicule = models.CharField(
        max_length=20, verbose_name="Modèle Véhicule", db_column="modelvehicule"
    )
    categorie_vehicule = models.CharField(
        verbose_name="Catégorie Vehicule",
        db_column="categorievehicule",
        max_length=100,
    )
    usage_vehicule = models.CharField(
        verbose_name="Usage Véhicule",
        db_column="usagevehicule",
        max_length=50,
    )
    source_energie = models.CharField(
        verbose_name="Source Energie",
        db_column="sourceenergie",
        max_length=20,
    )
    nombre_place = models.CharField(
        verbose_name="Nombre Places",
        db_column="nombreplace",
        max_length=100,
    )
    marque_vehicule = models.CharField(
        max_length=50, verbose_name="Marque Véhicule", db_column="marquevehicule"
    )
    numero_chassis = models.CharField(
        max_length=20,
        verbose_name="Numéro Chassis",
        db_column="numerochassis",
        default="NA",
    )
    numero_moteur = models.CharField(
        max_length=30,
        verbose_name="Numéro Moteur",
        db_column="numeromoteur",
        default="NA",
    )
    numero_carte_brune_physique = models.CharField(
        max_length=50,
        verbose_name="Numéro Carte Brune Physique",
        db_column="numerocartebrunephysique",
    )
    numero_rccm = models.CharField(
        max_length=100,
        verbose_name="Numéro RCCM",
        db_column="numero_rccm",
        default="NA",
    )
    bureau_enregistreur = models.CharField(
        max_length=50,
        verbose_name="Bureau Enregistreur",
        db_column="bureauenregistreur",
        default="NA",
    )
    nom_souscripteur = models.CharField(
        max_length=100, verbose_name="Nom Souscripteur", db_column="nomsouscripteur"
    )
    type_souscripteur = models.CharField(
        verbose_name="Type Souscripteur",
        db_column="typesouscripteur",
        max_length=20,
    )
    adresse_mail_souscripteur = models.EmailField(
        verbose_name="Adresse Email Souscripteur", db_column="adressemailsouscripteur"
    )
    numero_telephone_souscripteur = models.CharField(
        max_length=20,
        verbose_name="Numéro Téléphone Souscripteur ",
        db_column="numerotelephonesouscripteur",
    )
    boite_postale_souscripteur = models.CharField(
        max_length=20,
        verbose_name="Boîte Postale Souscripteur",
        db_column="boitepostalesouscripteur",
        default="NA",
    )
    type_assure = models.CharField(
        verbose_name="Type Assuré", db_column="typeassure", max_length=50, default="NA"
    )
    nom_assure = models.CharField(
        max_length=50, verbose_name="Nom Assure", db_column="nomassure"
    )
    adresse_mail_assure = models.EmailField(
        verbose_name="Adresse Email Assure", db_column="adressemailassure"
    )
    boite_postale_assure = models.CharField(
        max_length=20,
        verbose_name="Boîte Postale Assure",
        db_column="boitepostaleassure",
        default="NA",
    )
    numero_police = models.CharField(
        max_length=50, verbose_name="Numéro Police", db_column="numeropolice"
    )
    numero_telephone_assure = models.CharField(
        max_length=20,
        verbose_name="Numero Téléphone Assuré",
        db_column="numerotelephoneassure",
    )
    profession_assure = models.CharField(
        verbose_name="Profession Assuré",
        db_column="professionassure",
        max_length=100,
    )
    type_point_vente_compagnie = models.CharField(
        max_length=50,
        verbose_name="Type Point Vente Compagnie",
        db_column="typepointventecompagnie",
        default="NA",
    )
    code_point_vente_compagnie = models.CharField(
        max_length=50,
        verbose_name="Code Point Vente Compagnie",
        db_column="codepointventecompagnie",
    )
    denomination_point_vente_compagnie = models.CharField(
        max_length=100,
        verbose_name="Dénomination Point Vente Compagnie",
        db_column="denominationpointventecompagnie",
    )
    rc = models.CharField(
        max_length=20, verbose_name="Responsabilité Civile", db_column="rc"
    )
    code_nature_attestation = models.CharField(
        max_length=10,
        verbose_name="Code Nature Attestation",
        db_column="codenatureattestation",
    )
    garantie = models.CharField(
        max_length=1000, verbose_name="Garantie", db_column="garantie", default="NA"
    )
    contrat = models.CharField(
        max_length=1000, verbose_name="Contrat", db_column="contrat", default="NA"
    )
    zone_circulation = models.CharField(
        verbose_name="Zone Circulation",
        db_column="codezonecirculation",
        default="NA",
        max_length=10,
    )
    date_premiere_mise_en_circulation = models.DateField(
        verbose_name="Date Première Mise En Circulation",
        db_column="datepremieremiseencirculation",
    )
    valeur_neuve = models.CharField(
        max_length=20, verbose_name="Valeur Neuve", db_column="valeurneuve"
    )
    valeur_venale = models.CharField(
        max_length=20, verbose_name="Valeur Vénale", db_column="valeurvenale"
    )
    montant_autres_garanties = models.CharField(
        max_length=20,
        verbose_name="Montant Autres Garanties",
        db_column="montantautresgaranties",
    )
    montant_prime_nette_total = models.CharField(
        max_length=20,
        verbose_name="Montant Prime Nette Totale",
        db_column="montantprimenettetotale",
    )
    montant_accessoires = models.CharField(
        max_length=20,
        verbose_name="Montant Accessoires",
        db_column="montantaccessoires",
    )
    montant_taxes = models.CharField(
        max_length=20, verbose_name="Montant Taxes", db_column="montanttaxes"
    )
    montant_carte_brune = models.CharField(
        max_length=20, verbose_name="Montant Carte Brune", db_column="montantcartebrune"
    )
    fga = models.CharField(
        max_length=20, verbose_name="Montant FGA", db_column="montantfga"
    )
    montant_prime_ttc = models.CharField(
        max_length=20, verbose_name="Montant Prime TTC", db_column="montantprimettc"
    )

    class Meta:
        db_table = "stditemdemandeattestation"
        managed = False


class RetourDemAttestation(models.Model):
    id = models.AutoField(
        verbose_name="Id Réponse Demande",
        db_column="id",
        primary_key=True,
    )
    date_creation = models.DateTimeField(
        verbose_name="Date Création", db_column="datecreation", auto_now_add=True
    )
    numero_demande = models.CharField(
        max_length=100, verbose_name="Numéro Demande", db_column="numerodemande"
    )
    statut = models.IntegerField(verbose_name="Statut", db_column="statut")

    def __str__(self):
        return self.numero_demande + "(" + str(self.id) + ")"

    class Meta:
        db_table = "stdretourdemattestation"
        verbose_name = "Réponse à une demande d'attestation"
        verbose_name_plural = "Réponses aux demandes d'attestation"


class DetailRetourDemAttestation(models.Model):
    id = models.AutoField(verbose_name="Infos", db_column="id", primary_key=True)
    numero_demande = models.CharField(
        max_length=100,
        verbose_name="Numéro Demande",
        db_column="numerodemande",
        default="XXXXXXXXXX",
    )
    id_demande = models.ForeignKey(
        RetourDemAttestation,
        related_name="infos",
        verbose_name="Reponse à la demande",
        db_column="id_retour_demande",
        on_delete=models.CASCADE,
    )
    statut = models.IntegerField(
        verbose_name="Statut", db_column="statut", default=-999
    )

    numero_attestation = models.CharField(
        max_length=20, verbose_name="Numéro Attestation", db_column="numeroattestation"
    )
    numero_immatriculation = models.CharField(
        max_length=10,
        verbose_name="Numéro Immatriculation",
        db_column="numeroimmatriculation",
    )
    numero_chassis = models.CharField(
        max_length=20, verbose_name="Numéro Chassis", db_column="numerochassis"
    )
    date_effet = models.CharField(
        max_length=20, verbose_name="Date Effet", db_column="dateeffet"
    )
    date_echeance = models.CharField(
        max_length=20, verbose_name="Date Echéance", db_column="dateecheance"
    )
    lien_pdf = models.CharField(
        max_length=255, verbose_name="Lien PDF", db_column="lienpdf"
    )
    lien_image = models.CharField(
        max_length=255, verbose_name="Lien Image", db_column="lienimage"
    )
    lien_qrcode = models.CharField(
        max_length=255, verbose_name="Lien QrCode", db_column="lienqrcode"
    )

    def __str__(self):
        return self.numero_demande + "- Immatriculation: " + self.numero_immatriculation

    class Meta:
        db_table = "stddetailretourdemattestation"
        verbose_name = "Détail de la réponse à une demande"
        verbose_name_plural = "Détails des réponses aux demandes"
