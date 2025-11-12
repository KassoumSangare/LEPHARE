from django.db import models

# Create your models here.


class BordereauEmissionInput(models.Model):
    date_debut = models.DateField()
    date_fin = models.DateField()
    type_etat = models.SmallIntegerField()

    def __str__(self):
        return

    class Meta:
        managed = False


class BordereauEmissionResultSet(models.Model):
    numero_police = models.CharField(max_length=16)
    numero_quittance = models.CharField(max_length=16)
    numero_avenant = models.CharField(max_length=16)
    date_emission = models.DateField()
    date_effet = models.DateField()
    date_expiration = models.DateField()
    prime_nette = models.DecimalField(max_digits=19, decimal_places=4)
    accessoire = models.DecimalField(max_digits=19, decimal_places=4)
    taxe = models.DecimalField(max_digits=19, decimal_places=4)
    prime_ttc = models.DecimalField(max_digits=19, decimal_places=4)
    id_client = models.IntegerField()
    nom_client = models.CharField(max_length=125)
    id_produit = models.IntegerField()
    libelle_produit = models.CharField(max_length=60)
    id_compagnie = models.IntegerField()
    nom_compagnie = models.CharField(max_length=100)
    accessoire_intermediaire = models.DecimalField(max_digits=19, decimal_places=4)
    commission_intermediaire = models.DecimalField(max_digits=19, decimal_places=4)
    id_offre = models.IntegerField()
    libelle_offre = models.CharField(max_length=120)
    montant_encaissement = models.DecimalField(max_digits=19, decimal_places=4)
    montant_arriere = models.DecimalField(max_digits=19, decimal_places=4)

    def __str__(self):
        return "Emission {} du {} pour le client {} sur {}".format(
            self.libelle_produit,
            self.date_emission,
            self.nom_client,
            self.nom_compagnie,
        )

    class Meta:
        managed = False


class EtatDecisionnel(models.Model):
    id_etat = models.AutoField(
        db_column="idetat", primary_key=True, verbose_name="ID Etat"
    )
    code_etat = models.CharField(
        db_column="codeetat", verbose_name="Code Etat", max_length=3, unique=True
    )
    libelle_etat = models.CharField(
        db_column="libelleetat", verbose_name="Libellé Etat", max_length=255
    )
    actif = models.BooleanField(default=True, db_column="actif")

    url = models.CharField(max_length=255, db_column="url", default="DETAIL")

    def __str__(self):
        return self.libelle_etat

    class Meta:
        db_table = "stdetatdecisionnel"
        verbose_name = "Etat (Reporting)"
        verbose_name_plural = "Etats (Reporting)"


class EtatCimaE1Emissions(models.Model):
    libelle = models.CharField(max_length=255)
    assurance_des_personnes = models.DecimalField(
        max_digits=19, decimal_places=4, default=0
    )
    automobile_responsabilite_civile = models.DecimalField(
        max_digits=19, decimal_places=4, default=0
    )
    automobile_autres_risques = models.DecimalField(
        max_digits=19, decimal_places=4, default=0
    )
    incendie_et_multirisque = models.DecimalField(
        max_digits=19, decimal_places=4, default=0
    )
    autres_dommages_aux_biens = models.DecimalField(
        max_digits=19, decimal_places=4, default=0
    )
    responsabilite_civile = models.DecimalField(
        max_digits=19, decimal_places=4, default=0
    )
    transport_terrestre = models.DecimalField(
        max_digits=19, decimal_places=4, default=0
    )
    transport_maritime = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    corps = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    vie = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    capitalisation = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    ensemble = models.DecimalField(max_digits=19, decimal_places=4, default=0)

    def __str__(self):
        return self.libelle

    class Meta:
        managed = False


class EtatCimaE2Arrieres(models.Model):
    exercice_inventaire = models.IntegerField()
    libelle = models.CharField(max_length=255)
    annee_souscription_moins_deux = models.DecimalField(
        max_digits=19, decimal_places=4, default=0
    )
    annee_souscription_moins_un = models.DecimalField(
        max_digits=19, decimal_places=4, default=0
    )
    annee_souscription = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    total = models.DecimalField(max_digits=19, decimal_places=4, default=0)

    def __str__(self):
        return self.libelle + "(" + str(self.exercice_inventaire) + ")"

    class Meta:
        managed = False


class RubriqueEtatCima(models.Model):
    id_rubrique = models.AutoField(db_column="idrubrique", primary_key=True)
    code_rubrique = models.CharField(
        db_column="coderubrique", max_length=6, unique=True
    )
    code_etat = models.CharField(max_length=3, db_column="codeetat")
    libelle_rubrique = models.CharField(max_length=100, db_column="libellerubrique")

    def __str__(self):
        return "{} ({})".format(self.libelle_rubrique, self.code_rubrique)

    class Meta:
        db_table = "stdrubriqueetatcima"
        verbose_name = "Rubrique Etat CIMA"
        verbose_name_plural = "Rubriques Etat CIMA"


class LigneEtatCima(models.Model):
    id_ligne = models.AutoField(db_column="idligne", primary_key=True)
    code_rubrique = models.ForeignKey(
        RubriqueEtatCima,
        to_field="code_rubrique",
        db_column="coderubrique",
        on_delete=models.CASCADE,
    )
    clef_colonne = models.CharField(db_column="clefcolonne", max_length=50)
    valeur_colonne = models.DecimalField(
        db_column="valeurcolonne", max_digits=19, decimal_places=4
    )

    def __str__(self):
        return "{} ({})".format(self.clef_colonne, self.id_rubrique)

    class Meta:
        db_table = "stdligneetatcima"
        verbose_name = "Ligne Etat CIMA"
        verbose_name_plural = "Lignes Etat CIMA"
