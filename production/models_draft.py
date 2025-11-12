# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.core.validators import MinLengthValidator
from djmoney.models.fields import MoneyField






class Stdcollege(models.Model):
    idcollege = models.AutoField(primary_key=True)
    libellecollege = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'stdcollege'


class Stddecomptedet(models.Model):
    iddecomptedet = models.AutoField(primary_key=True)
    iddecompteidt = models.ForeignKey('Stddecompteidt', models.DO_NOTHING, db_column='iddecompteidt', blank=True, null=True)
    iddetailprestation = models.ForeignKey('Stddetailprestation', models.DO_NOTHING, db_column='iddetailprestation', blank=True, null=True)
    montant = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantaregler = models.DecimalField(max_digits=65535, decimal_places=65535)
    regler = models.CharField(max_length=1)
    idmotif = models.ForeignKey('Stdmotifrejet', models.DO_NOTHING, db_column='idmotif', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stddecomptedet'


class Stddecompteidt(models.Model):
    iddecompteidt = models.AutoField(primary_key=True)
    idetablissement = models.ForeignKey('Stdetablissement', models.DO_NOTHING, db_column='idetablissement')
    reglement = models.CharField(max_length=1)
    datereglement = models.DateTimeField()
    reference = models.CharField(max_length=50, blank=True, null=True)
    montant = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantaregler = models.DecimalField(max_digits=65535, decimal_places=65535)
    datevalidation = models.DateTimeField()
    valide = models.CharField(max_length=1)
    entreprise = models.CharField(max_length=1, blank=True, null=True)
    idbanque = models.IntegerField()
    beneficiaire = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stddecompteidt'


class Stddemandeprestation(models.Model):
    iddemandeprestation = models.AutoField(primary_key=True)
    iddetailprestation = models.ForeignKey('Stddetailprestation', models.DO_NOTHING, db_column='iddetailprestation')
    idcontroleur = models.IntegerField(blank=True, null=True)
    datedemande = models.DateTimeField()
    datedebut = models.DateTimeField(blank=True, null=True)
    nbrejdemande = models.IntegerField()
    nbrejaccorde = models.IntegerField()
    datevalidation = models.DateTimeField(blank=True, null=True)
    etatdemande = models.CharField(max_length=1)
    contrevisite = models.CharField(max_length=1)
    observationdemandeur = models.CharField(max_length=200)
    observationcontroleur = models.CharField(max_length=200)
    iduser = models.IntegerField()
    idservice = models.IntegerField(blank=True, null=True)
    idchambre = models.IntegerField(blank=True, null=True)
    idtypedemande = models.IntegerField(blank=True, null=True)
    montant = models.DecimalField(max_digits=65535, decimal_places=65535)
    idmedecin = models.IntegerField(blank=True, null=True)
    dateimport = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stddemandeprestation'


class Stddetailprestation(models.Model):
    iddetailprestation = models.AutoField(primary_key=True)
    iddossier = models.ForeignKey('Stddossiermedical', models.DO_NOTHING, db_column='iddossier')
    idacte = models.ForeignKey('Stdacte', models.DO_NOTHING, db_column='idacte')
    idsousacte = models.ForeignKey('Stdsousacte', models.DO_NOTHING, db_column='idsousacte')
    idetablissement = models.ForeignKey('Stdetablissement', models.DO_NOTHING, db_column='idetablissement')
    idetablissementexecutant = models.ForeignKey('Stdetablissement', models.DO_NOTHING, db_column='idetablissementexecutant', blank=True, null=True)
    idreferentiel = models.ForeignKey('Stdreferentiel', models.DO_NOTHING, db_column='idreferentiel', blank=True, null=True)
    numerolot = models.IntegerField()
    quantitedemandee = models.SmallIntegerField()
    quantiteservie = models.SmallIntegerField()
    prixunitaire = models.DecimalField(max_digits=65535, decimal_places=65535)
    idintervenant = models.IntegerField()
    idintervenant_executant = models.IntegerField(blank=True, null=True)
    idmodifrejet = models.IntegerField(blank=True, null=True)
    montantreel = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantrembourse = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantexclu = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantconvention = models.DecimalField(max_digits=65535, decimal_places=65535)
    ticketmoderateur = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantdecompte = models.DecimalField(max_digits=65535, decimal_places=65535)
    tauxcouverture = models.IntegerField(blank=True, null=True)
    tauxreduction = models.IntegerField()
    substitution = models.CharField(max_length=1)
    idsubstitution = models.IntegerField(blank=True, null=True)
    iduser = models.IntegerField()
    datecreation = models.DateTimeField()
    dateexecution = models.DateTimeField(blank=True, null=True)
    etatexecution = models.CharField(max_length=1)
    prestationdecompte = models.CharField(max_length=1, blank=True, null=True)
    iddecompte = models.IntegerField(blank=True, null=True)
    remarque = models.CharField(max_length=500, blank=True, null=True)
    dateimport = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stddetailprestation'



class Stddossiermedical(models.Model):
    iddossier = models.AutoField(primary_key=True)
    idadherent = models.IntegerField(blank=True, null=True)
    idaffilie = models.ForeignKey('Stdaffilie', models.DO_NOTHING, db_column='idaffilie')
    idoffresante = models.IntegerField()
    idetablissement = models.ForeignKey('Stdetablissement', models.DO_NOTHING, db_column='idetablissement')
    idnaturemaladie = models.ForeignKey('Stdnaturemaladie', models.DO_NOTHING, db_column='idnaturemaladie')
    idmaladie = models.ForeignKey('Stdmaladie', models.DO_NOTHING, db_column='idmaladie')
    datecreation = models.DateTimeField()
    montantreel = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantrembourse = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantexclu = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantconvention = models.DecimalField(max_digits=65535, decimal_places=65535)
    ticketmoderateur = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantdecompte = models.DecimalField(max_digits=65535, decimal_places=65535)
    etatdemande = models.CharField(max_length=1)
    datedemande = models.DateTimeField(blank=True, null=True)
    iduser = models.IntegerField()
    archive = models.CharField(max_length=1)
    datearchive = models.DateTimeField(blank=True, null=True)
    nature = models.CharField(max_length=1)
    centredesoin = models.CharField(max_length=100, blank=True, null=True)
    datesurvenance = models.DateTimeField(blank=True, null=True)
    dateimport = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stddossiermedical'


class Stdetablissement(models.Model):
    idetablissement = models.AutoField(primary_key=True)
    idtypeetablissement = models.ForeignKey('Stdtypeetablissement', models.DO_NOTHING, db_column='idtypeetablissement')
    codeetablissement = models.CharField(max_length=4)
    libelleetablissement = models.CharField(max_length=100)
    okcreerdossier = models.CharField(max_length=1)
    nomgerant = models.CharField(max_length=100)
    telephone = models.CharField(max_length=8)
    mobile = models.CharField(max_length=8)
    e_mail = models.CharField(max_length=60)
    adresse = models.CharField(max_length=60)
    actif = models.CharField(max_length=1)
    libelleimpressioncheque = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stdetablissement'


class Stdetablissementacte(models.Model):
    idetablissementacte = models.AutoField(primary_key=True)
    idetablissement = models.IntegerField()
    idacte = models.IntegerField()
    idetatavant = models.IntegerField(blank=True, null=True)
    idetatapres = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stdetablissementacte'


class Stdetablissementetats(models.Model):
    idetablissementetat = models.AutoField(primary_key=True)
    idetablissement = models.IntegerField()
    idetat = models.IntegerField()
    periode = models.CharField(max_length=1)

    class Meta:
        managed = False
        db_table = 'stdetablissementetats'


class Stdetablissementintervenant(models.Model):
    idetablissementintervenant = models.AutoField(primary_key=True)
    idetablissement = models.IntegerField()
    idintervenant = models.ForeignKey('Stdintervenant', models.DO_NOTHING, db_column='idintervenant')
    etatservice = models.CharField(max_length=1)
    datecreation = models.DateTimeField()
    datesortie = models.DateTimeField(blank=True, null=True)
    iduser = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'stdetablissementintervenant'


class Stdetablissementreseausanitaire(models.Model):
    idetablissementressanitaire = models.AutoField(primary_key=True)
    idetablissement = models.ForeignKey(Stdetablissement, models.DO_NOTHING, db_column='idetablissement')
    idreseausanitaire = models.ForeignKey('Stdreseausanitaire', models.DO_NOTHING, db_column='idreseausanitaire')
    datecreation = models.DateTimeField()
    iduser = models.IntegerField()
    okactivite = models.CharField(max_length=1)
    datesortie = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stdetablissementreseausanitaire'


class Stdetablissementsousacte(models.Model):
    idetablissementsousacte = models.AutoField(primary_key=True)
    idetablissementacte = models.ForeignKey(Stdetablissementacte, models.DO_NOTHING, db_column='idetablissementacte')
    idsousacte = models.ForeignKey('Stdsousacte', models.DO_NOTHING, db_column='idsousacte')
    montantreel = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantreelferie = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantconvention = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantconventionferie = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantmutuelle = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantmutuelleferie = models.DecimalField(max_digits=65535, decimal_places=65535)
    tauxreduction = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'stdetablissementsousacte'


class Stdetablissementtypechambre(models.Model):
    idetablissementtypechambre = models.AutoField(primary_key=True)
    idetablissment = models.ForeignKey(Stdetablissement, models.DO_NOTHING, db_column='idetablissment')
    idtypechambre = models.ForeignKey('Stdtypechambre', models.DO_NOTHING, db_column='idtypechambre')
    montantreel = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantconvention = models.DecimalField(max_digits=65535, decimal_places=65535)
    tauxreduction = models.IntegerField()
    actif = models.CharField(max_length=1)

    class Meta:
        managed = False
        db_table = 'stdetablissementtypechambre'


class Stdetablissementuser(models.Model):
    idetablissementuser = models.AutoField(primary_key=True)
    idetablissement = models.IntegerField()
    nom = models.CharField(max_length=50, blank=True, null=True)
    prenom = models.CharField(max_length=50, blank=True, null=True)
    login = models.CharField(max_length=50, blank=True, null=True)
    password = models.CharField(max_length=50, blank=True, null=True)
    actif = models.CharField(max_length=1, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stdetablissementuser'


class Stdextensionsadherentdet(models.Model):
    idaffilieextensiondet = models.AutoField(primary_key=True)
    idaffilieextension = models.ForeignKey('Stdextensionsadherentidt', models.DO_NOTHING, db_column='idaffilieextension')
    idacte = models.ForeignKey('Stdacte', models.DO_NOTHING, db_column='idacte')
    plafondsup = models.DecimalField(max_digits=65535, decimal_places=65535)

    class Meta:
        managed = False
        db_table = 'stdextensionsadherentdet'


class Stdextensionsadherentidt(models.Model):
    idaffilieextension = models.AutoField(primary_key=True)
    idadherent = models.ForeignKey('Stdadherent', models.DO_NOTHING, db_column='idadherent')
    iddevis = models.ForeignKey('Stddevis', models.DO_NOTHING, db_column='iddevis')
    idpolice = models.IntegerField(blank=True, null=True)
    extensiondu = models.DateTimeField()
    extensionau = models.DateTimeField()
    mtsurprime = models.DecimalField(max_digits=65535, decimal_places=65535)

    class Meta:
        managed = False
        db_table = 'stdextensionsadherentidt'


class Stdextensionsaffilieidt(models.Model):
    idaffilieextension = models.AutoField(primary_key=True)
    idaffilie = models.ForeignKey('Stdaffilie', models.DO_NOTHING, db_column='idaffilie')
    iddevis = models.IntegerField(blank=True, null=True)
    idpolice = models.IntegerField(blank=True, null=True)
    extensiondu = models.DateTimeField()
    extensionau = models.DateTimeField()
    mtsurprime = models.DecimalField(max_digits=65535, decimal_places=65535)
    lien = models.CharField(max_length=1)
    plafondsupaff = models.DecimalField(max_digits=65535, decimal_places=65535)

    class Meta:
        managed = False
        db_table = 'stdextensionsaffilieidt'


class Stdextenstionsaffiliedet(models.Model):
    idaffilieextensiondet = models.AutoField(primary_key=True)
    idaffilieextension = models.IntegerField()
    idacte = models.IntegerField()
    plafondsup = models.DecimalField(max_digits=65535, decimal_places=65535)

    class Meta:
        managed = False
        db_table = 'stdextenstionsaffiliedet'


class Stdfiliales(models.Model):
    idfiliale = models.AutoField(primary_key=True)
    iddevis = models.IntegerField()
    idcollege = models.IntegerField()
    idoffresante = models.IntegerField()
    police = models.CharField(max_length=50)
    actif = models.CharField(max_length=1)
    date_souscription = models.DateTimeField()
    date_effet = models.DateTimeField()
    date_expiration = models.DateTimeField(blank=True, null=True)
    source = models.CharField(max_length=1)
    idoperateur = models.IntegerField()
    datemaj = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'stdfiliales'




class Stdintervenant(models.Model):
    idintervenant = models.AutoField(primary_key=True)
    idspecialite = models.ForeignKey('Stdspecialite', models.DO_NOTHING, db_column='idspecialite')
    codeintervenant = models.CharField(max_length=4)
    nomintervenant = models.CharField(max_length=100)
    mobile = models.CharField(max_length=8)
    numeroordre = models.CharField(max_length=8)

    class Meta:
        managed = False
        db_table = 'stdintervenant'


class Stdjoursferies(models.Model):
    idjour = models.IntegerField(primary_key=True)
    datejour = models.DateTimeField(blank=True, null=True)
    ferie = models.CharField(max_length=1)

    class Meta:
        managed = False
        db_table = 'stdjoursferies'


class Stdmaladie(models.Model):
    idmaladie = models.AutoField(primary_key=True)
    idnaturemaladie = models.ForeignKey('Stdnaturemaladie', models.DO_NOTHING, db_column='idnaturemaladie')
    libellemaladie = models.CharField(max_length=60)
    codemaladie = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'stdmaladie'





class Stdmotifrejet(models.Model):
    idmotifrejet = models.AutoField(primary_key=True)
    libellemotifrejet = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'stdmotifrejet'


class Stdmouvementcompte(models.Model):
    numerocompte = models.CharField(primary_key=True, max_length=16)
    referencemouvement = models.CharField(max_length=20)
    libellemouvement = models.CharField(max_length=20, blank=True, null=True)
    datemouvement = models.DateTimeField(blank=True, null=True)
    montant = models.DecimalField(max_digits=65535, decimal_places=65535)

    class Meta:
        managed = False
        db_table = 'stdmouvementcompte'
        unique_together = (('numerocompte', 'referencemouvement'),)


class Stdmouvementintermediairecommission(models.Model):
    numerointermediaire = models.CharField(primary_key=True, max_length=16)
    idquittance = models.IntegerField()
    libellemouvement = models.CharField(max_length=20, blank=True, null=True)
    datemouvement = models.DateTimeField(blank=True, null=True)
    montant = models.DecimalField(max_digits=65535, decimal_places=65535)

    class Meta:
        managed = False
        db_table = 'stdmouvementintermediairecommission'
        unique_together = (('numerointermediaire', 'idquittance'),)


class Stdmouvementintermediairecompte(models.Model):
    numerointermediaire = models.CharField(primary_key=True, max_length=16)
    referencemouvement = models.CharField(max_length=20)
    libellemouvement = models.CharField(max_length=20, blank=True, null=True)
    datemouvement = models.DateTimeField(blank=True, null=True)
    montant = models.DecimalField(max_digits=65535, decimal_places=65535)

    class Meta:
        managed = False
        db_table = 'stdmouvementintermediairecompte'
        unique_together = (('numerointermediaire', 'referencemouvement'),)


class Stdnaturemaladie(models.Model):
    idnaturemaladie = models.AutoField(primary_key=True)
    libellenaturemaladie = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'stdnaturemaladie'


class Stdnumeros(models.Model):
    idligne = models.IntegerField(primary_key=True)
    numero = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'stdnumeros'


class Stdoffreintermediaire(models.Model):
    idoffre = models.IntegerField(primary_key=True)
    idintermediaire = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'stdoffreintermediaire'
        unique_together = (('idoffre', 'idintermediaire'),)


class Stdoffrereductions(models.Model):
    idoffrereduction = models.AutoField(primary_key=True)
    idoffre = models.IntegerField()
    idtarif = models.IntegerField()
    codenatureintermediaire = models.SmallIntegerField()
    tauxred = models.DecimalField(max_digits=65535, decimal_places=65535)
    redtarifaire = models.DecimalField(max_digits=65535, decimal_places=65535)
    redcommerciale = models.DecimalField(max_digits=65535, decimal_places=65535)
    validedu = models.DateTimeField()
    valideau = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'stdoffrereductions'



class Stdoffresante(models.Model):
    idoffre = models.AutoField(primary_key=True)
    datedebut = models.DateTimeField()
    datefin = models.DateTimeField(blank=True, null=True)
    etatoffre = models.CharField(max_length=1)
    mutuelle = models.CharField(max_length=1)
    datecreation = models.DateTimeField()
    libelleoffre = models.CharField(max_length=50, blank=True, null=True)
    plafondpolice = models.DecimalField(max_digits=65535, decimal_places=65535)
    plafondadherent = models.DecimalField(max_digits=65535, decimal_places=65535)
    plafondaffilie = models.DecimalField(max_digits=65535, decimal_places=65535)
    plafondchambre = models.DecimalField(max_digits=65535, decimal_places=65535)
    traitepar = models.CharField(max_length=20, blank=True, null=True)
    etattraitement = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stdoffresante'


class Stdoffresanteacte(models.Model):
    idoffresanteacte = models.AutoField(primary_key=True)
    idoffre = models.IntegerField()
    idacte = models.ForeignKey(Stdacte, models.DO_NOTHING, db_column='idacte')
    actif = models.CharField(max_length=1)
    plafondordonnance = models.DecimalField(max_digits=65535, decimal_places=65535)
    okautorisation = models.CharField(max_length=1)
    plafondacte = models.DecimalField(max_digits=65535, decimal_places=65535)
    nbresurvenance = models.SmallIntegerField()
    periodicite = models.SmallIntegerField()
    tauxcouverture = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'stdoffresanteacte'


class Stdoffresantenaturemaladie(models.Model):
    idoffresantenaturemaladie = models.AutoField(primary_key=True)
    idnaturemaladie = models.IntegerField()
    idoffresante = models.IntegerField()
    plafond = models.DecimalField(max_digits=65535, decimal_places=65535)

    class Meta:
        managed = False
        db_table = 'stdoffresantenaturemaladie'


class Stdoffresantereseausanitaire(models.Model):
    idoffresantereseausanitaire = models.AutoField(primary_key=True)
    idoffresante = models.IntegerField()
    idreseausanitaire = models.IntegerField()
    datecreation = models.DateTimeField()
    iduser = models.IntegerField()
    okactivite = models.CharField(max_length=1)
    datesortie = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stdoffresantereseausanitaire'


class Stdoffresantesousacte(models.Model):
    idoffresantesousacte = models.AutoField(primary_key=True)
    idoffresanteacte = models.IntegerField()
    idsousacte = models.IntegerField()
    okautorisation = models.CharField(max_length=1)
    actif = models.CharField(max_length=1)
    plafondprestation = models.DecimalField(max_digits=65535, decimal_places=65535)
    nbresurvenance = models.IntegerField()
    periodicite = models.IntegerField()
    valmodifiable = models.CharField(max_length=1)
    plafondvaleur = models.DecimalField(max_digits=65535, decimal_places=65535)

    class Meta:
        managed = False
        db_table = 'stdoffresantesousacte'


class Stdoffresantetypechambre(models.Model):
    idoffresantetypechambre = models.AutoField(primary_key=True)
    idoffre = models.IntegerField()
    idtypechambre = models.IntegerField()
    actif = models.CharField(max_length=1)

    class Meta:
        managed = False
        db_table = 'stdoffresantetypechambre'


class Stdoffresantetypeprd(models.Model):
    idoffresantetypeprd = models.AutoField(primary_key=True)
    idoffresante = models.IntegerField()
    idtypereferentiel = models.IntegerField()
    okautorisation = models.CharField(max_length=1)
    actif = models.CharField(max_length=1)

    class Meta:
        managed = False
        db_table = 'stdoffresantetypeprd'

class Stdoperateurs(models.Model):
    idoperateur = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=60)
    prenom = models.CharField(max_length=80, blank=True, null=True)
    nomconnexion = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    actif = models.CharField(max_length=1)
    niveau = models.IntegerField()
    visibilite = models.CharField(max_length=1)
    datecreation = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'stdoperateurs'



class Stdprestation(models.Model):
    idprestation = models.AutoField(primary_key=True)
    idactemere = models.IntegerField()
    iddossier = models.IntegerField()
    idoffre = models.IntegerField()
    idacte = models.IntegerField()
    idetablissement = models.IntegerField()
    idintervenant = models.IntegerField()
    montantreel = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantrembourse = models.DecimalField(max_digits=65535, decimal_places=65535)
    montantexclu = models.DecimalField(max_digits=65535, decimal_places=65535)
    datecreation = models.DateTimeField()
    dateexecution = models.DateTimeField()
    prestationexecute = models.CharField(max_length=1)
    iduser = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'stdprestation'


class Stdprofessions(models.Model):
    idprofession = models.AutoField(primary_key=True)
    libelle = models.CharField(max_length=100)
    codeprofession = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stdprofessions'


class Stdprofildroits(models.Model):
    idprofil = models.IntegerField(primary_key=True)
    idmenus = models.IntegerField()
    actif = models.CharField(max_length=1)
    executable = models.CharField(max_length=1)

    class Meta:
        managed = False
        db_table = 'stdprofildroits'
        unique_together = (('idprofil', 'idmenus'),)


class Stdprofils(models.Model):
    idprofil = models.AutoField(primary_key=True)
    libelleprofile = models.CharField(max_length=50)
    actif = models.CharField(max_length=1)
    executable = models.CharField(max_length=1)

    class Meta:
        managed = False
        db_table = 'stdprofils'


class Stdqualites(models.Model):
    idqualite = models.AutoField(primary_key=True)
    libelle = models.CharField(max_length=100)
    codequalite = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stdqualites'


class Stdreferentiel(models.Model):
    idreferentiel = models.AutoField(primary_key=True)
    idtypereferentiel = models.IntegerField()
    libellereferentiel = models.CharField(max_length=255)
    substituable = models.CharField(max_length=1)
    plafond = models.DecimalField(max_digits=65535, decimal_places=65535)
    remboursable = models.CharField(max_length=1)
    gestionlot = models.CharField(max_length=1)
    taillelot = models.IntegerField()
    frequencelot = models.IntegerField()
    actif = models.CharField(max_length=1)

    class Meta:
        managed = False
        db_table = 'stdreferentiel'



class Stdreseausanitaire(models.Model):
    idresausanitaire = models.AutoField(primary_key=True)
    libellereseausanitaire = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'stdreseausanitaire'


class Stdservices(models.Model):
    idservice = models.AutoField(primary_key=True)
    libelle = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stdservices'


class Stdsousacte(models.Model):
    idsousacte = models.AutoField(primary_key=True)
    idacte = models.IntegerField()
    idtypereferentiel = models.IntegerField(blank=True, null=True)
    codesousacte = models.CharField(max_length=6)
    libellesousacte = models.CharField(max_length=60)
    lettrecle = models.CharField(max_length=4)
    coefficient = models.IntegerField()
    homme = models.CharField(max_length=1)
    femme = models.CharField(max_length=1)
    enfant = models.CharField(max_length=1)
    useqte = models.CharField(max_length=1)
    maxqte = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'stdsousacte'


class Stdspecialite(models.Model):
    idspecialite = models.AutoField(primary_key=True)
    codespecialite = models.CharField(max_length=2)
    libellespecialite = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'stdspecialite'


class Stdsubstitution(models.Model):
    idreferentielfrom = models.IntegerField(primary_key=True)
    idreferentielto = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'stdsubstitution'
        unique_together = (('idreferentielfrom', 'idreferentielto'),)


class Stdtypecapitaux(models.Model):
    idtypecapitaux = models.AutoField(primary_key=True)
    libelletypecapitaux = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'stdtypecapitaux'


class Stdtypechambre(models.Model):
    idtypechambre = models.AutoField(primary_key=True)
    libelle = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'stdtypechambre'


class Stdtypeclient(models.Model):
    idtypeclient = models.IntegerField(primary_key=True)
    libelletypeclient = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'stdtypeclient'


class Stdtypedemande(models.Model):
    idtypedemande = models.AutoField(primary_key=True)
    libelle = models.CharField(max_length=60)
    interventionprog = models.CharField(max_length=1)
    idacte = models.IntegerField(blank=True, null=True)
    idsousacte = models.IntegerField(blank=True, null=True)
    idplafondacte = models.IntegerField(blank=True, null=True)
    idplafondsousacte = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stdtypedemande'


class Stdtypeetablissement(models.Model):
    idtypeetablissement = models.AutoField(primary_key=True)
    libelletypeetablissement = models.CharField(max_length=60)
    idmenu = models.SmallIntegerField()

    class Meta:
        managed = False
        db_table = 'stdtypeetablissement'


class Stdtypereferentiel(models.Model):
    idtypereferentiel = models.AutoField(primary_key=True)
    libelletypereferentiel = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'stdtypereferentiel'


class Stdzonecouverture(models.Model):
    idzonecouverture = models.AutoField(primary_key=True)
    libellezonecouverture = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = 'stdzonecouverture'


class Traitement(models.Model):
    idtraitement = models.AutoField()
    codetraitement = models.CharField(primary_key=True, max_length=2)
    numeroordre = models.SmallIntegerField()
    libelletraitement = models.CharField(max_length=60, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'traitement'
