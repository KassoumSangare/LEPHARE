# models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

User = get_user_model()


class Client(models.Model):
    """Client de l'assurance"""
    numero_client = models.CharField(max_length=50, unique=True, editable=False)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    adresse = models.TextField()
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'client'
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.numero_client} - {self.nom} {self.prenom}"
    
    def save(self, *args, **kwargs):
        if not self.numero_client:
            self.numero_client = f"CLI-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class Maison(models.Model):
    """
    Maison référence - Les caractéristiques ACTUELLES de la maison.
    Cette table contient toujours l'état le plus récent.
    """
    USAGE_CHOICES = [
        ('proprietaire_occupant_total', 'Propriétaire occupant total'),
        ('proprietaire_occupant_partiel', 'Propriétaire occupant partiel'),
        ('proprietaire_non_occupant_meuble', 'Propriétaire non occupant - Location meublée'),
        ('proprietaire_non_occupant', 'Propriétaire non occupant'),
        ('locataire_meuble', 'Locataire en meublé'),
        ('locataire_partiel', 'Locataire partiel'),
        ('logement_fonction', 'Logement de fonction'),
        ('locataire', 'Locataire'),
    ]
    
    numero_maison = models.CharField(max_length=50, unique=True, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='maisons')
    
    # Informations de la maison
    adresse = models.TextField()
    code_postal = models.CharField(max_length=10)
    ville = models.CharField(max_length=100)
    
    # Caractéristiques actuelles
    usage_habitation = models.CharField(max_length=50, choices=USAGE_CHOICES)
    valeur_maison = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    cout_location_mensuel = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    surface_m2 = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    nombre_pieces = models.IntegerField(null=True, blank=True)
    annee_construction = models.IntegerField(null=True, blank=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'maison'
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.numero_maison} - {self.adresse}"
    
    def save(self, *args, **kwargs):
        if not self.numero_maison:
            self.numero_maison = f"MAS-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class Devis(models.Model):
    """
    Devis produit par le courtier.
    Peut contenir plusieurs maisons.
    """
    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('envoye', 'Envoyé au client'),
        ('accepte', 'Accepté par le client'),
        ('refuse', 'Refusé par le client'),
        ('expire', 'Expiré'),
        ('annule', 'Annulé'),
    ]
    
    numero_devis = models.CharField(max_length=50, unique=True, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='devis')
    courtier = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='devis_crees',
        null=True,
        blank=True
    )
    
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_cours')
    date_emission = models.DateField(auto_now_add=True)
    date_validite = models.DateField(help_text="Date d'expiration du devis")
    
    # Prime totale calculée (somme de toutes les maisons)
    prime_totale_annuelle = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    prime_totale_mensuelle = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    remarques = models.TextField(blank=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'devis'
        ordering = ['-date_creation']
        verbose_name_plural = 'Devis'
    
    def __str__(self):
        return f"{self.numero_devis} - {self.client} - {self.get_statut_display()}"
    
    def save(self, *args, **kwargs):
        if not self.numero_devis:
            from datetime import datetime
            annee = datetime.now().year
            self.numero_devis = f"DEV-{annee}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def calculer_prime_totale(self):
        """Calcule et met à jour la prime totale du devis"""
        total_annuel = Decimal('0.00')
        
        for maison_devis in self.maisons_devis.all():
            maison_devis.calculer_prime()
            if maison_devis.prime_annuelle:
                total_annuel += maison_devis.prime_annuelle
        
        self.prime_totale_annuelle = total_annuel
        self.prime_totale_mensuelle = total_annuel / 12
        self.save(update_fields=['prime_totale_annuelle', 'prime_totale_mensuelle'])
        
        return {
            'prime_totale_annuelle': self.prime_totale_annuelle,
            'prime_totale_mensuelle': self.prime_totale_mensuelle
        }


class MaisonDevis(models.Model):
    """
    Snapshot des caractéristiques d'une maison AU MOMENT du devis.
    Cette table capture l'état historique pour le devis.
    """
    devis = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name='maisons_devis')
    maison = models.ForeignKey(
        Maison, 
        on_delete=models.PROTECT, 
        related_name='devis_historique',
        help_text="Référence à la maison (les caractéristiques peuvent avoir changé depuis)"
    )
    
    # SNAPSHOT des caractéristiques au moment du devis
    # On duplique les champs car ils peuvent changer dans Maison
    usage_habitation = models.CharField(max_length=50)
    valeur_maison = models.DecimalField(max_digits=12, decimal_places=2)
    cout_location_mensuel = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    surface_m2 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    nombre_pieces = models.IntegerField(null=True, blank=True)
    options = models.JSONField(default=dict, help_text="Options choisies pour cette maison")
    
    # Résultat du calcul
    prime_annuelle = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    prime_mensuelle = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    detail_garanties = models.JSONField(
        null=True, 
        blank=True,
        help_text="Détail de toutes les garanties calculées"
    )
    
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'maison_devis'
        unique_together = [['devis', 'maison']]
        ordering = ['devis', 'id']
    
    def __str__(self):
        return f"{self.devis.numero_devis} - {self.maison.numero_maison}"
    
    def save(self, *args, **kwargs):
        # Si pas de snapshot, on copie depuis la maison actuelle
        if not self.pk and not self.usage_habitation:
            self.copier_depuis_maison()
        super().save(*args, **kwargs)
    
    def copier_depuis_maison(self):
        """Copie les caractéristiques actuelles de la maison"""
        self.usage_habitation = self.maison.usage_habitation
        self.valeur_maison = self.maison.valeur_maison
        self.cout_location_mensuel = self.maison.cout_location_mensuel
        self.surface_m2 = self.maison.surface_m2
        self.nombre_pieces = self.maison.nombre_pieces
    
    def calculer_prime(self):
        """Appelle la fonction PL/pgSQL pour calculer la prime"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT calculer_prime_totale_mrh(
                    %s::VARCHAR,
                    %s::NUMERIC,
                    %s::NUMERIC,
                    %s::NUMERIC,
                    %s::INTEGER,
                    %s::JSONB
                )
            """, [
                self.usage_habitation,
                self.valeur_maison,
                self.cout_location_mensuel,
                self.surface_m2,
                self.nombre_pieces,
                self.options if self.options else {}
            ])
            
            result = cursor.fetchone()[0]
            
            self.prime_annuelle = Decimal(str(result['prime_totale_annuelle']))
            self.prime_mensuelle = Decimal(str(result['prime_totale_mensuelle']))
            self.detail_garanties = result['garanties']
            
            self.save(update_fields=[
                'prime_annuelle', 
                'prime_mensuelle', 
                'detail_garanties'
            ])
            
            return result


class Contrat(models.Model):
    """
    Contrat généré à partir d'un devis accepté.
    Un contrat peut couvrir plusieurs maisons.
    """
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('suspendu', 'Suspendu'),
        ('resilie', 'Résilié'),
        ('expire', 'Expiré'),
    ]
    
    numero_contrat = models.CharField(max_length=50, unique=True, editable=False)
    devis = models.OneToOneField(
        Devis, 
        on_delete=models.PROTECT, 
        related_name='contrat',
        help_text="Devis à l'origine de ce contrat"
    )
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='contrats')
    
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')
    date_effet = models.DateField(help_text="Date de début de couverture")
    date_echeance = models.DateField(help_text="Date de fin de couverture")
    
    # Prime au moment de la souscription (peut différer si renouvellement)
    prime_annuelle_initiale = models.DecimalField(max_digits=12, decimal_places=2)
    prime_mensuelle_initiale = models.DecimalField(max_digits=12, decimal_places=2)
    
    date_signature = models.DateField(null=True, blank=True)
    date_resiliation = models.DateField(null=True, blank=True)
    motif_resiliation = models.TextField(blank=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contrat'
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.numero_contrat} - {self.client} - {self.get_statut_display()}"
    
    def save(self, *args, **kwargs):
        if not self.numero_contrat:
            from datetime import datetime
            annee = datetime.now().year
            self.numero_contrat = f"CTR-{annee}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    @classmethod
    def creer_depuis_devis(cls, devis):
        """
        Crée un contrat à partir d'un devis accepté.
        Copie toutes les maisons du devis vers le contrat.
        """
        from datetime import datetime, timedelta
        from django.db import transaction
        
        if devis.statut != 'accepte':
            raise ValueError("Le devis doit être accepté pour générer un contrat")
        
        if hasattr(devis, 'contrat'):
            raise ValueError("Un contrat existe déjà pour ce devis")
        
        with transaction.atomic():
            # Créer le contrat
            contrat = cls.objects.create(
                devis=devis,
                client=devis.client,
                date_effet=datetime.now().date(),
                date_echeance=datetime.now().date() + timedelta(days=365),
                prime_annuelle_initiale=devis.prime_totale_annuelle,
                prime_mensuelle_initiale=devis.prime_totale_mensuelle,
                date_signature=datetime.now().date()
            )
            
            # Copier toutes les maisons du devis vers le contrat
            for maison_devis in devis.maisons_devis.all():
                MaisonContrat.objects.create(
                    contrat=contrat,
                    maison=maison_devis.maison,
                    usage_habitation=maison_devis.usage_habitation,
                    valeur_maison=maison_devis.valeur_maison,
                    cout_location_mensuel=maison_devis.cout_location_mensuel,
                    surface_m2=maison_devis.surface_m2,
                    nombre_pieces=maison_devis.nombre_pieces,
                    options=maison_devis.options,
                    prime_annuelle=maison_devis.prime_annuelle,
                    prime_mensuelle=maison_devis.prime_mensuelle,
                    detail_garanties=maison_devis.detail_garanties
                )
            
            return contrat


class MaisonContrat(models.Model):
    """
    Snapshot des caractéristiques d'une maison pour UN CONTRAT donné.
    À chaque renouvellement/avenant, on peut créer une nouvelle ligne
    si les caractéristiques ont changé.
    """
    contrat = models.ForeignKey(
        Contrat, 
        on_delete=models.CASCADE, 
        related_name='maisons_contrat'
    )
    maison = models.ForeignKey(
        Maison, 
        on_delete=models.PROTECT, 
        related_name='contrats_historique'
    )
    
    # SNAPSHOT des caractéristiques au moment du contrat
    usage_habitation = models.CharField(max_length=50)
    valeur_maison = models.DecimalField(max_digits=12, decimal_places=2)
    cout_location_mensuel = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    surface_m2 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    nombre_pieces = models.IntegerField(null=True, blank=True)
    options = models.JSONField(default=dict)
    
    # Prime calculée pour ce contrat
    prime_annuelle = models.DecimalField(max_digits=10, decimal_places=2)
    prime_mensuelle = models.DecimalField(max_digits=10, decimal_places=2)
    detail_garanties = models.JSONField(null=True, blank=True)
    
    # Période de validité de ces caractéristiques
    date_debut_validite = models.DateField(auto_now_add=True)
    date_fin_validite = models.DateField(null=True, blank=True)
    est_actif = models.BooleanField(default=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'maison_contrat'
        ordering = ['contrat', '-date_debut_validite']
        indexes = [
            models.Index(fields=['contrat', 'maison', 'est_actif']),
        ]
    
    def __str__(self):
        return f"{self.contrat.numero_contrat} - {self.maison.numero_maison}"
    
    def creer_avenant_modification(self, nouvelles_caracteristiques):
        """
        Crée un avenant pour modifier les caractéristiques de cette maison.
        Désactive l'ancien enregistrement et crée un nouveau.
        """
        from datetime import datetime
        from django.db import transaction
        
        with transaction.atomic():
            # Clôturer l'ancienne version
            self.est_actif = False
            self.date_fin_validite = datetime.now().date()
            self.save(update_fields=['est_actif', 'date_fin_validite'])
            
            # Créer la nouvelle version
            nouvelle_maison_contrat = MaisonContrat.objects.create(
                contrat=self.contrat,
                maison=self.maison,
                usage_habitation=nouvelles_caracteristiques.get(
                    'usage_habitation', 
                    self.usage_habitation
                ),
                valeur_maison=nouvelles_caracteristiques.get(
                    'valeur_maison', 
                    self.valeur_maison
                ),
                cout_location_mensuel=nouvelles_caracteristiques.get(
                    'cout_location_mensuel', 
                    self.cout_location_mensuel
                ),
                surface_m2=nouvelles_caracteristiques.get('surface_m2', self.surface_m2),
                nombre_pieces=nouvelles_caracteristiques.get('nombre_pieces', self.nombre_pieces),
                options=nouvelles_caracteristiques.get('options', self.options),
                est_actif=True
            )
            
            # Recalculer la prime avec les nouvelles caractéristiques
            nouvelle_maison_contrat.recalculer_prime()
            
            return nouvelle_maison_contrat
    
    def recalculer_prime(self):
        """Recalcule la prime avec les caractéristiques actuelles"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT calculer_prime_totale_mrh(
                    %s::VARCHAR,
                    %s::NUMERIC,
                    %s::NUMERIC,
                    %s::NUMERIC,
                    %s::INTEGER,
                    %s::JSONB
                )
            """, [
                self.usage_habitation,
                self.valeur_maison,
                self.cout_location_mensuel,
                self.surface_m2,
                self.nombre_pieces,
                self.options if self.options else {}
            ])
            
            result = cursor.fetchone()[0]
            
            self.prime_annuelle = Decimal(str(result['prime_totale_annuelle']))
            self.prime_mensuelle = Decimal(str(result['prime_totale_mensuelle']))
            self.detail_garanties = result['garanties']
            
            self.save(update_fields=[
                'prime_annuelle', 
                'prime_mensuelle', 
                'detail_garanties'
            ])
            
            return result