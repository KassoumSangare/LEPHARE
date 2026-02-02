from django.db import models
from django.core.validators import MinLengthValidator
from djmoney.models.fields import MoneyField
from configuration_api.models import TypeAssure, TypeSouscripteur

# Create your models here.


class Client(models.Model):
    IdClient = models.AutoField(db_column="idclient", primary_key=True)
    Nom = models.CharField(db_column="nom", max_length=150)
    Prenoms = models.CharField(
        db_column="prenoms", max_length=150, null=True, blank=True
    )
    Vip = models.CharField(
        db_column="vip", max_length=1, validators=[MinLengthValidator(1)]
    )
    Adresse1 = models.CharField(
        db_column="adresse1", max_length=100, null=True, blank=True
    )
    Adresse2 = models.CharField(
        db_column="adresse2", max_length=100, null=True, blank=True
    )
    IdVille = models.IntegerField(db_column="idville", null=True, blank=True)
    Telephone = models.CharField(
        db_column="telephone", max_length=20, null=True, blank=True
    )
    Mobile = models.CharField(db_column="mobile", max_length=20, null=True, blank=True)
    Fax = models.CharField(db_column="fax", max_length=20, null=True, blank=True)
    Fixe = models.CharField(db_column="fixe", max_length=20, null=True, blank=True)
    IdQualite = models.IntegerField(db_column="idqualite", null=True, blank=True)
    IdProfession = models.IntegerField(db_column="idprofession", null=True, blank=True)
    IdSecteurActivite = models.IntegerField(
        db_column="idsecteuractivite", null=True, blank=True
    )
    Responsable = models.CharField(
        db_column="responsable", max_length=120, null=True, blank=True
    )
    Email = models.EmailField(db_column="email", null=True, blank=True)
    Particulier = models.CharField(
        db_column="particulier", max_length=1, validators=[MinLengthValidator(1)]
    )
    DateMaj = models.DateTimeField(db_column="datemaj", auto_now=True)
    CniPat = models.CharField(db_column="cnipat", max_length=50, null=True, blank=True)
    DateCreation = models.DateTimeField(db_column="datecreation", auto_now_add=True)
    Statut = models.CharField(
        db_column="statut", max_length=1, validators=[MinLengthValidator(1)]
    )
    Matricule = models.CharField(
        db_column="matricule", max_length=50, null=True, blank=True, unique=True
    )
    IdOperateur = models.IntegerField(db_column="idoperateur", null=True, blank=True)
    Rib = models.CharField(
        db_column="rib",
        max_length=24,
        null=True,
        blank=True,
        validators=[MinLengthValidator(24)],
    )
    DateNaissance = models.DateField(db_column="datenaissance", null=True, blank=True)
    LieuNaissance = models.CharField(
        max_length=100, db_column="lieunaissance", null=True, blank=True
    )
    Reconquete = models.CharField(
        db_column="reconquete",
        max_length=1,
        null=True,
        blank=True,
        validators=[MinLengthValidator(1)],
    )
    IdProfil = models.IntegerField(db_column="idprofil", null=True, blank=True)
    CreeCie = models.CharField(
        db_column="creecie", max_length=1, validators=[MinLengthValidator(1)]
    )
    CodePostal = models.CharField(
        db_column="codepostal", max_length=15, null=True, blank=True
    )
    IdCategorie = models.IntegerField(db_column="idcategorie", null=True, blank=True)
    ExonereDeTaxes = models.BooleanField(
        db_column="exoneredetaxes", null=True, blank=True
    )
    ExonereDeAccess = models.BooleanField(
        db_column="exoneredeaccess", null=True, blank=True
    )
    NumeroCompte = models.CharField(
        db_column="numerocompte", max_length=20, default="XXXXXXX"
    )
    Solde = models.DecimalField(
        db_column="solde", max_digits=19, decimal_places=4, null=True, default=0.0
    )
    Avoir = models.DecimalField(
        db_column="avoir", max_digits=19, decimal_places=4, null=True, default=0.0
    )
    Fonction = models.CharField(max_length=80, null=True, blank=True, default="")
    idtypeclient = models.ForeignKey(
        TypeSouscripteur,
        verbose_name="Type Souscripteur",
        db_column="idtypesouscripteur",
        null=True,
        on_delete=models.SET_NULL,
    )
    idtypeassure = models.ForeignKey(
        TypeAssure,
        verbose_name="Type Assuré",
        db_column="idtypeassure",
        null=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        if self.Prenoms:
            return self.Prenoms + " " + self.Nom
        return self.Nom

    class Meta:
        db_table = "stdclient"
