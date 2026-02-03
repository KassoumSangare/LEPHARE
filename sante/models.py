from django.db import models
from account.models import UranusUser
from configuration_api.models import CollegeSante, Offre, ZoneCouvertureSante

# Create your models here.

GROUPE_SANGUIN = (
    ("O-", "O-"),
    ("O+", "O+"),
    ("A-", "A-"),
    ("A+", "A+"),
    ("B-", "B-"),
    ("B+", "B+"),
    ("AB-", "AB-"),
    ("AB+", "AB+"),
    ("NS", "INFO NON DISPONIBLE"),
)


class FilialeSante(models.Model):
    idfiliale = models.AutoField(
        primary_key=True, verbose_name="ID Filiale", db_column="idfiliale"
    )
    devis = models.IntegerField(verbose_name="Devis", db_column="iddevis")
    college = models.ForeignKey(
        CollegeSante,
        verbose_name="Collège",
        db_column="idcollege",
        on_delete=models.DO_NOTHING,
    )
    offresante = models.ForeignKey(
        Offre,
        db_column="idoffresante",
        verbose_name="Offre Santé",
        on_delete=models.DO_NOTHING,
    )
    zonecouverture = models.ForeignKey(
        ZoneCouvertureSante,
        db_column="idzonecouverture",
        verbose_name="Zone Couverture",
        on_delete=models.DO_NOTHING,
        default=1,
    )
    police = models.CharField(max_length=50, null=True)
    nomfiliale = models.CharField(
        max_length=150, db_column="nom_filiale", null=True, blank=True
    )
    actif = models.BooleanField()
    datesouscription = models.DateField(db_column="date_souscription")
    dateeffet = models.DateField(db_column="date_effet")
    dateexpiration = models.DateField(db_column="date_expiration")
    source = models.CharField(max_length=1)
    operateur = models.ForeignKey(
        UranusUser,
        verbose_name="Opérateur",
        db_column="idoperateur",
        on_delete=models.DO_NOTHING,
    )
    datemaj = models.DateTimeField(verbose_name="Date de mise à jour", auto_now=True)

    def __str__(self):
        return self.nomfiliale

    class Meta:
        db_table = "stdfiliale"
        verbose_name = "Filiale Santé"
        verbose_name_plural = "Filiales Santé"


class Adherent(models.Model):
    idadherent = models.AutoField(primary_key=True)
    filiale = models.ForeignKey(
        FilialeSante,
        db_column="idfiliale",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    nom = models.CharField(max_length=80)
    prenom = models.CharField(max_length=80)
    sexe = models.CharField(max_length=1)
    numerocni = models.CharField(max_length=50, db_column="cni", null=True, blank=True)
    fichier_piece = models.FileField(
        upload_to="uploads/adherents/", db_column="fichierpiece", null=True, blank=True
    )
    vip = models.BooleanField(default=False)
    adresseadherent = models.CharField(
        max_length=100, db_column="adresse", null=True, blank=True
    )
    mobile1 = models.CharField(max_length=20, blank=True, null=True)
    mobile2 = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    datenaissanceadherent = models.DateField(
        db_column="datenaissance", null=True, blank=True
    )
    dateadhesion = models.DateField(blank=True, null=True)  # Date d'effet (AFN, INC)
    datesortie = models.DateField(
        blank=True, null=True
    )  # Date de retrait, de résiliation
    actif = models.BooleanField()
    datemaj = models.DateTimeField(blank=True, null=True, auto_now=True)
    surprimeappliquee = models.BooleanField(blank=True, null=True, default=False)
    montantsurprime = models.DecimalField(
        blank=True, null=True, default=0, max_digits=19, decimal_places=4
    )
    nombrepathologie_adherent = models.IntegerField(
        db_column="nombrepathologie", blank=True, null=True, default=0
    )
    numerocmu_adherent = models.CharField(
        max_length=20, db_column="numerocmu", blank=True, null=True, default=""
    )
    operateur = models.ForeignKey(
        UranusUser,
        verbose_name="Opérateur",
        db_column="idoperateur",
        on_delete=models.CASCADE,
    )
    matriculeadherent = models.CharField(
        db_column="matricule", max_length=50, blank=True, null=True
    )
    groupesanguinadherent = models.CharField(
        db_column="groupesanguin",
        max_length=3,
        choices=GROUPE_SANGUIN,
        null=True,
        blank=True,
    )
    devis = models.IntegerField(db_column="iddevis", blank=True, null=True)
    debutconsommation = models.DateField(
        db_column="datedebutconsommation", null=True, blank=True
    )  # Date de début autorisé des prestations

    def __str__(self):
        if self.prenom:
            return "{} {}".format(self.prenom, self.nom)
        return self.nom

    class Meta:
        db_table = "stdadherent"
        verbose_name = "Adhérent"
        verbose_name_plural = "Adhérents"


class Affilie(models.Model):
    idaffilie = models.AutoField(primary_key=True)
    adherent = models.ForeignKey(
        Adherent,
        db_column="idadherent",
        verbose_name="Adhérent",
        on_delete=models.CASCADE,
    )
    lien = models.CharField(max_length=1)  # Lien juridique
    nom = models.CharField(max_length=80)
    prenom = models.CharField(max_length=80)
    numerocni = models.CharField(max_length=50, db_column="cni", null=True, blank=True)
    fichier_piece = models.FileField(
        upload_to="uploads/affilies", db_column="fichierpiece", null=True, blank=True
    )
    date_naissance = models.DateField(db_column="datenaissance", blank=True, null=True)
    mobile1_affilie = models.CharField(
        db_column="mobile1", max_length=20, blank=True, null=True
    )
    mobile2_affilie = models.CharField(
        db_column="mobile2", max_length=20, blank=True, null=True
    )
    dateadhesion = models.DateField(blank=True, null=True)  # Date effet (AFN, INC)
    datesortie = models.DateField(blank=True, null=True)  # Date effet (RET, RES)
    certificat = models.BooleanField(null=True, blank=True)
    datectrl = models.DateField(
        blank=True, null=True
    )  # Date de contrôle du certificat (pas saisi)
    matricule = models.CharField(max_length=50, blank=True, null=True)
    groupesanguinaffilie = models.CharField(
        db_column="groupesanguin",
        max_length=3,
        choices=GROUPE_SANGUIN,
        null=True,
        blank=True,
    )
    nombrepathologie_affilie = models.IntegerField(
        db_column="nombrepathologie", blank=True, null=True, default=0
    )
    numerocmu_affilie = models.CharField(
        max_length=20, db_column="numerocmu", blank=True, null=True, default=""
    )
    carte_en_vigueur = models.BooleanField(
        db_column="carte_vigueur", blank=True, null=True
    )
    anc_matricule = models.CharField(
        db_column="ancien_matricule", max_length=50, blank=True, null=True
    )
    date_dern_demande = models.DateField(
        db_column="date_dernier_demande", blank=True, null=True
    )
    observations_affilie = models.CharField(
        max_length=4000, db_column="observations", default="RAS", null=True, blank=True
    )
    handicape = models.BooleanField()
    sexe = models.CharField(max_length=1)
    actif = models.BooleanField()
    primeannuelle = models.DecimalField(max_digits=19, decimal_places=4)
    datemaj = models.DateTimeField(blank=True, null=True, auto_now=True)
    surprimeappliquee = models.BooleanField(blank=True, null=True, default=False)
    montantsurprime = models.DecimalField(
        blank=True, null=True, default=0, max_digits=19, decimal_places=4
    )
    operateur = models.ForeignKey(
        UranusUser,
        verbose_name="Opérateur",
        db_column="idoperateur",
        on_delete=models.DO_NOTHING,
    )
    devis = models.IntegerField(db_column="iddevis", blank=True, null=True)
    debutconsommation = models.DateField(
        db_column="datedebutconsommation", blank=True, null=True
    )  # Date de début de consommation (fin de la periode de carence)

    def __str__(self):
        if self.prenom:
            return "{} {}".format(self.prenom, self.nom)
        return self.nom

    class Meta:
        db_table = "stdaffilie"
        verbose_name = "Affilié"
        verbose_name_plural = "Affiliés"


########################## AffilieFn ###############################
class AffilieFn(models.Model):
    iddevis = models.IntegerField()
    idaffilie = models.IntegerField()
    idadherent = models.IntegerField()
    nom = models.CharField(max_length=80)
    prenom = models.CharField(max_length=80)
    lien = models.CharField(max_length=1)  # Lien juridique
    lienparente = models.CharField(max_length=10)
    datenaissance = models.DateField()
    sexe = models.CharField(max_length=1)
    numerocni = models.CharField(max_length=50)
    numerocmu = models.CharField(max_length=20)
    groupesanguin = models.CharField(max_length=3,
    )

    def __str__(self):
        if self.prenom:
            return "{} {}".format(self.prenom, self.nom)
        return self.nom

    class Meta:
        managed = False


class NumeroSaisieSante(models.Model):
    id = models.AutoField(verbose_name="ID", db_column="id", primary_key=True)
    operateur = models.ForeignKey(
        UranusUser,
        verbose_name="Opérateur",
        db_column="idoperateur",
        on_delete=models.CASCADE,
    )
    date_creation = models.DateTimeField(
        verbose_name="Date de création", db_column="datecreation", auto_now_add=True
    )
    date_maj = models.DateTimeField(
        verbose_name="Date de mise à jour", db_column="datemaj", auto_now=True
    )
    saisie_en_cours = models.BooleanField(
        default=True, verbose_name="Saisie en cours", db_column="saisieencours"
    )
    id_devis = models.IntegerField(
        verbose_name="ID Devis", db_column="iddevis", unique=True
    )

    def __str__(self):
        return "Saisie initiée le {}, numéro {}".format(self.date_creation, self.id)

    class Meta:
        db_table = "stdnumerosaisiesante"
        verbose_name = "Numéro de devis temporaire"
        verbose_name_plural = "Numéros de devis temporaire"


class AdherentSanteInsertionResult(models.Model):
    idadherent = models.IntegerField(default=0)
    devis = models.IntegerField(default=0)
    outputmessage = models.CharField(max_length=500, default="")

    def __str__(self):
        return "{}: Adhérent N° {}".format(self.outputmessage, self.idadherent)

    class Meta:
        managed = False


class AffilieSanteInsertionResult(models.Model):
    idaffilie = models.IntegerField(default=0)
    adherent = models.IntegerField()
    devis = models.IntegerField()
    outputmessage = models.CharField(max_length=500, default="")

    def __str__(self):
        return "{}: Affilié N° {} (Adhérent N° {})".format(
            self.outputmessage, self.idaffilie, self.adherent
        )

    class Meta:
        managed = False


class FilialeSanteInsertionResult(models.Model):
    idfiliale = models.IntegerField(default=0)
    devis = models.IntegerField()
    outputmessage = models.CharField(max_length=500, default="")

    def __str__(self):
        return "{}: Filiale N° {}".format(self.outputmessage, self.idfiliale)

    class Meta:
        managed = False


class SaisieDevisSanteEnCours(models.Model):
    devis = models.IntegerField()
    identifiant_devis = models.CharField(max_length=70)
    utilisateur = models.IntegerField()

    def __str__(self):
        return self.identifiant_devis

    class Meta:
        managed = False


class Person(models.Model):
    id_personne = models.AutoField(db_column="idpersonne", primary_key=True)
    nom = models.CharField(db_column="nom", max_length=80)
    prenoms = models.CharField(db_column="prenoms", max_length=80, null=True, blank=True)
    piece = models.FileField(db_column="piece", upload_to="uploads/personnes", null=True, blank=True)

    def __str__(self):
        res = self.nom
        if self.prenoms:
            res = self.prenoms + " " + res
        return res
    class Meta:
        db_table = "stdpersonnetest"