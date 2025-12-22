"""
Service de calcul des primes MRH (Multi-Risques Habitation)
Côte d'Ivoire

Ce service gère :
- Le calcul de la prime de base selon l'usage
- La répartition sur les garanties obligatoires
- L'application des options (TYPE1, TYPE2, FORFAIT)
- L'ajout des garanties optionnelles
- Le calcul des taxes
- Le calcul des accessoires par paliers
- L'enregistrement dans les modèles legacy (Devis, DevisDetail, DevisDetGarantie)
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.db import transaction
from django.core.exceptions import ValidationError


from configuration_api.models import (
    UsageHabitation,
    SousGarantieMRH,
    SousGarantieUsage,
    ParametresCalcul,
    Option,
    OptionUsage,
    SousGarantieForfait,
)
from production.services.recapitulatif_primes_mrh import RecapitulatifPrimesMRH
# TODO: Ajuster les imports selon votre structure
# from votre_app.models import (
#     Devis, DevisDetail, DevisDetGarantie,
#     Accessoire, Produit, Compagnie
# )

from datetime import date
from dateutil.relativedelta import relativedelta

from ..database import obtenir_nouveau_numero_devis, obtenir_code_categorie

def calculer_date_expiration(
    date_effet: date, 
    id_duree: int, 
    nombre_jours: int = 0
) -> date:
    """
    Calcule la date d'expiration d'un contrat.
    
    Args:
        date_effet: Date de début.
        id_duree: Identifiant de la durée (1: mois, 2: trim, 3: sem, 4: an, 5: custom).
        nombre_jours: Nombre de jours si id_duree est 5.
        
    Returns:
        Un objet datetime.date représentant le dernier jour du contrat.
    """
    
    
    # Mapping des durées avec relativedelta
    # On utilise un dictionnaire pour associer l'ID à l'intervalle correspondant
    choix_duree: dict[int, relativedelta] = {
        1: relativedelta(months=1),
        2: relativedelta(months=3),
        3: relativedelta(months=6),
        4: relativedelta(years=1),
        5: relativedelta(days=nombre_jours)
    }
    
    # Récupération du delta (par défaut 0 jour si l'ID est inconnu)
    delta: relativedelta = choix_duree.get(id_duree, relativedelta(days=0))
    
    # Calcul de la date d'expiration (Date + Durée - 1 jour)
    date_expiration: date = date_effet + delta - relativedelta(days=1)
    
    return date_expiration

def tarif_mrh(id_tarif:int) -> bool:
    from configuration_api.models import Tarif
    return Tarif.is_mrh(id_tarif)

class MRHCalculService:
    """
    Service principal pour le calcul des primes MRH.
    
    Usage:
        service = MRHCalculService()
        resultat = service.calculer_maison(
            code_usage='proprietaire_occupant_total',
            valeur_batiment=50000000,
            valeur_contenu=10000000,
            options=['presence_gardien'],
            garanties_optionnelles=['RC_MEMBRE']
        )
    """
    
    # Constantes de taxation
    TAUX_TAXE_INCENDIE = Decimal('0.25')  # 25%
    TAUX_TAXE_DOMMAGES_ELECTRIQUES = Decimal('0.25')  # 25%
    TAUX_TAXE_AUTRES = Decimal('0.145')  # 14,5%
    TAUX_TAXE_ACCESSOIRE = Decimal('0.145')  # 14,5%
    
    def __init__(self):
        """Initialise le service de calcul"""
        self.usage = None
        self.parametres = None
        self.sous_garanties_obligatoires = []
        self.sous_garanties_optionnelles_dispo = []
        self.options_applicables = []
    
    # ========================================================================
    # SECTION 1 : CALCUL DE LA PRIME DE BASE
    # ========================================================================
    
    def calculer_prime_base(
        self,
        code_usage: str,
        valeur_batiment: Optional[Decimal] = None,
        valeur_contenu: Optional[Decimal] = None,
        loyer_mensuel: Optional[Decimal] = None,
        capital_rvt: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calcule la prime de base selon l'usage et les paramètres fournis.
        
        Args:
            code_usage: Code de l'usage habitation
            valeur_batiment: Valeur du bâtiment en FCFA (optionnel selon usage)
            valeur_contenu: Valeur du contenu en FCFA (optionnel selon usage)
            loyer_mensuel: Loyer mensuel en FCFA (optionnel selon usage)
            capital_rvt: Capital RVT en FCFA (optionnel selon usage)
        
        Returns:
            Prime de base en FCFA (Decimal)
        
        Raises:
            ValidationError: Si les paramètres requis ne sont pas fournis
        """
        # Charger l'usage et les paramètres
        try:
            self.usage = UsageHabitation.objects.get(code=code_usage, actif=True)
            self.parametres = self.usage.parametres
        except UsageHabitation.DoesNotExist:
            raise ValidationError(f"Usage '{code_usage}' non trouvé ou inactif")
        except ParametresCalcul.DoesNotExist:
            raise ValidationError(f"Paramètres de calcul non trouvés pour l'usage '{code_usage}'")
        
        # Valider les paramètres requis
        self._valider_parametres_requis(
            valeur_batiment, valeur_contenu, loyer_mensuel, capital_rvt
        )
        
        # Calcul des composantes
        prime_base = Decimal('0')
        
        # Composante bâtiment
        if self.parametres.coeff_valeur_batiment and valeur_batiment:
            prime_base += valeur_batiment * self.parametres.coeff_valeur_batiment
        
        # Composante contenu
        if self.parametres.coeff_valeur_contenu and valeur_contenu:
            prime_base += valeur_contenu * self.parametres.coeff_valeur_contenu
        
        # Composante loyer (Loyer × 12 × 15 × coeff)
        if self.parametres.coeff_loyer and loyer_mensuel:
            prime_base += loyer_mensuel * 12 * 15 * self.parametres.coeff_loyer
        
        # Composante RVT
        if self.parametres.coeff_capital_rvt and capital_rvt:
            prime_base += capital_rvt * self.parametres.coeff_capital_rvt
        
        # Ajout du forfait fixe (pour Logement de Fonction)
        prime_base += self.parametres.forfait_fixe
        
        # Application du coefficient de réduction
        if self.parametres.coeff_reduction:
            prime_base = prime_base * self.parametres.coeff_reduction
        
        # Arrondir à 2 décimales
        return self._arrondir(prime_base)
    
    def _valider_parametres_requis(
        self,
        valeur_batiment: Optional[Decimal],
        valeur_contenu: Optional[Decimal],
        loyer_mensuel: Optional[Decimal],
        capital_rvt: Optional[Decimal],
    ) -> None:
        """Valide que les paramètres requis sont fournis"""
        errors = {}
        
        if self.parametres.param_valeur_batiment_requis and not valeur_batiment:
            errors['valeur_batiment'] = "La valeur du bâtiment est requise pour cet usage"
        
        if self.parametres.param_valeur_contenu_requis and not valeur_contenu:
            errors['valeur_contenu'] = "La valeur du contenu est requise pour cet usage"
        
        if self.parametres.param_loyer_requis and not loyer_mensuel:
            errors['loyer_mensuel'] = "Le loyer mensuel est requis pour cet usage"
        
        if self.parametres.param_capital_rvt_requis and not capital_rvt:
            errors['capital_rvt'] = "Le capital RVT est requis pour cet usage"
        
        if errors:
            raise ValidationError(errors)
    
    # ========================================================================
    # SECTION 2 : RÉPARTITION SUR LES GARANTIES OBLIGATOIRES
    # ========================================================================
    
    def repartir_prime_sous_garanties(self, prime_base: Decimal) -> List[Dict]:
        """
        Répartit la prime de base sur les sous-garanties obligatoires.
        
        Args:
            prime_base: Prime de base calculée
        
        Returns:
            Liste de dict contenant pour chaque sous-garantie:
            {
                'code_sous_garantie': str,
                'libelle_sous_garantie': str,
                'type_garantie': 'OBLIGATOIRE',
                'prime_nette': Decimal,
                'taux_repartition': Decimal,
                'taux_taxe': Decimal,
                'taxe': Decimal,
                'prime_ttc': Decimal,
                'code_sous_garantie_std': str,
                'id_sous_garantie_std': int
            }
        """
        sous_garanties_calculees = []
        
        # Récupérer les sous-garanties obligatoires pour cet usage
        self.sous_garanties_obligatoires = SousGarantieUsage.objects.filter(
            usage=self.usage,
            obligatoire=True,
            actif=True
        ).select_related('sous_garantie').order_by('ordre_affichage')
        
        for gu in self.sous_garanties_obligatoires:
            # Calcul de la prime nette de la sous-garantie
            prime_nette = self._arrondir(
                prime_base * (gu.taux_repartition / Decimal('100'))
            )
            
            # Déterminer le taux de taxe selon la sous-garantie
            taux_taxe = self._get_taux_taxe(gu.sous_garantie.code)
            
            # Calcul de la taxe
            taxe = self._arrondir(prime_nette * taux_taxe)
            
            # Prime TTC
            prime_ttc = prime_nette + taxe
            
            sous_garanties_calculees.append({
                'code_sous_garantie': gu.sous_garantie.code,
                'libelle_sous_garantie': gu.sous_garantie.libelle,
                'type_garantie': 'OBLIGATOIRE',
                'prime_nette': prime_nette,
                'taux_repartition': gu.taux_repartition,
                'taux_taxe': taux_taxe * 100,  # Convertir en pourcentage
                'taxe': taxe,
                'prime_ttc': prime_ttc,
                'code_sous_garantie_std': gu.sous_garantie.get_code_sous_garantie_std(),
                'id_sous_garantie_std': gu.sous_garantie.get_id_sous_garantie_std(),
            })
        
        return sous_garanties_calculees
    
    def _get_taux_taxe(self, code_sous_garantie: str) -> Decimal:
        """Retourne le taux de taxe selon la garantie"""
        if code_sous_garantie in ['INCENDIE', 'DOMMAGES_ELECTRIQUES']:
            return self.TAUX_TAXE_INCENDIE
        else:
            return self.TAUX_TAXE_AUTRES
    
    # ========================================================================
    # SECTION 3 : APPLICATION DES OPTIONS (TYPE1, TYPE2, FORFAIT)
    # ========================================================================
    
    def appliquer_options(
        self,
        sous_garanties: List[Dict],
        codes_options: List[str],
        prime_base: Decimal
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Applique les options sélectionnées et ajuste les primes des sous-garanties.
        
        Args:
            sous_garanties: Liste des sous-garanties calculées
            codes_options: Liste des codes d'options sélectionnées
            prime_base: Prime de base (pour TYPE1)
        
        Returns:
            Tuple (sous_garanties_ajustees, options_appliquees)
            - sous_garanties_ajustees: Liste des sous/garanties avec primes ajustées
            - options_appliquees: Liste des options appliquées avec détails
        """
        if not codes_options:
            return sous_garanties, []
        
        options_appliquees = []
        
        for sous_garantie in sous_garanties:
            sous_garantie['prime_avant_options'] = sous_garantie['prime_nette']  # Copie avant modification

        sous_garanties_map = {g['code_sous_garantie']: g for g in sous_garanties}
        
        # Récupérer les options
        options = Option.objects.filter(
            code__in=codes_options,
            actif=True
        ).select_related('sous_garantie_cible')
        
        for option in options:
            # Vérifier que l'option est applicable à cet usage
            if not OptionUsage.objects.filter(
                option=option,
                usage=self.usage,
                actif=True
            ).exists():
                raise ValidationError(
                    f"L'option '{option.code}' n'est pas applicable à l'usage '{self.usage.code}'"
                )
            
            sous_garantie_cible = sous_garanties_map.get(option.sous_garantie_cible.code)
            if not sous_garantie_cible:
                continue
            
            # Calculer l'ajustement selon le type
            montant_ajustement = self._calculer_ajustement_option(
                option, sous_garantie_cible, prime_base
            )
            
            # Appliquer l'ajustement
            if option.signe_ajustement == '+':
                sous_garantie_cible['prime_nette'] += montant_ajustement
            else:  # '-'
                sous_garantie_cible['prime_nette'] -= montant_ajustement
            
            # Recalculer la taxe et la prime TTC
            sous_garantie_cible['taxe'] = self._arrondir(
                sous_garantie_cible['prime_nette'] * (sous_garantie_cible['taux_taxe'] / 100)
            )
            sous_garantie_cible['prime_ttc'] = sous_garantie_cible['prime_nette'] + sous_garantie_cible['taxe']
            
            # Enregistrer l'option appliquée
            options_appliquees.append({
                'code_option': option.code,
                'libelle_option': option.libelle,
                'type_option': option.type_option,
                'type_ajustement': option.type_ajustement,
                'sous_garantie_cible': option.sous_garantie_cible.code,
                'sous_garantie_cible_libelle': option.sous_garantie_cible.libelle,
                'montant_ajustement': montant_ajustement,
                'signe': option.signe_ajustement,
            })
        
        return list(sous_garanties_map.values()), options_appliquees
    
    def _calculer_ajustement_option(
        self,
        option: Option,
        sous_garantie: Dict,
        prime_base: Decimal
    ) -> Decimal:
        """
        Calcule le montant d'ajustement selon le type d'option.
        
        TYPE1: Taux appliqué à la prime de base
        TYPE2: Taux appliqué à la prime nette de la garantie
        FORFAIT: Montant fixe
        """
        if option.type_ajustement == 'TYPE1':
            # Taux sur prime de base (en ‰)
            return self._arrondir(prime_base * (option.taux_ajustement / 1000))
        
        elif option.type_ajustement == 'TYPE2':
            # Taux sur prime garantie (en %)
            return self._arrondir(sous_garantie['prime_nette'] * (option.taux_ajustement / 100))
        
        elif option.type_ajustement == 'FORFAIT':
            # Montant fixe
            return option.montant_forfait
        
        else:
            raise ValidationError(f"Type d'ajustement inconnu: {option.type_ajustement}")
    
    # ========================================================================
    # SECTION 4 : AJOUT DES GARANTIES OPTIONNELLES
    # ========================================================================
    
    def ajouter_sous_garanties_optionnelles(
        self,
        sous_garanties: List[Dict],
        codes_sous_garanties_opt: List[str]
    ) -> List[Dict]:
        """
        Ajoute les sous-garanties optionnelles sélectionnées.
        
        Args:
            sous_garanties: Liste des sous-garanties obligatoires
            codes_sous_garanties_opt: Codes des gsous-aranties optionnelles à ajouter
        
        Returns:
            Liste complète des sous-garanties (obligatoires + optionnelles)
        """
        if not codes_sous_garanties_opt:
            return sous_garanties
        
        # Récupérer les garanties optionnelles
        sous_garanties_opt = SousGarantieMRH.objects.filter(
            code__in=codes_sous_garanties_opt,
            type='OPTIONNELLE',
            actif=True
        )
        
        for sous_gar_opt in sous_garanties_opt:
            # Vérifier la disponibilité pour cet usage
            if not SousGarantieUsage.objects.filter(
                sous_garantie=sous_gar_opt,
                usage=self.usage,
                obligatoire=False,
                actif=True
            ).exists():
                raise ValidationError(
                    f"La garantie '{sous_gar_opt.code}' n'est pas disponible pour l'usage '{self.usage.code}'"
                )
            
            # Récupérer la prime forfaitaire
            try:
                forfait = SousGarantieForfait.objects.get(sous_garantie=sous_gar_opt, actif=True)
                prime_nette = forfait.prime_nette
            except SousGarantieForfait.DoesNotExist:
                raise ValidationError(
                    f"Prime forfaitaire non définie pour la garantie '{sous_gar_opt.code}'"
                )
            
            # Calculer la taxe
            taux_taxe = self._get_taux_taxe(sous_gar_opt.code)
            taxe = self._arrondir(prime_nette * taux_taxe)
            prime_ttc = prime_nette + taxe
            
            sous_garanties.append({
                'code_sous_garantie': sous_gar_opt.code,
                'libelle_sous_garantie': sous_gar_opt.libelle,
                'type_garantie': 'OPTIONNELLE',
                'prime_nette': prime_nette,
                'prime_avant_options': prime_nette,
                'taux_repartition': None,
                'taux_taxe': taux_taxe * 100,
                'taxe': taxe,
                'prime_ttc': prime_ttc,
                'code_sous_garantie_std': sous_gar_opt.get_code_sous_garantie_std(),
                'id_sous_garantie_std': sous_gar_opt.get_id_sous_garantie_std(),
            })
        
        return sous_garanties
    
    # ========================================================================
    # SECTION 5 : CALCUL DES ACCESSOIRES PAR PALIERS
    # ========================================================================
    
    def calculer_accessoire(
        self,
        prime_nette_totale: Decimal,
        id_produit: int,
        id_compagnie: int
    ) -> Dict:
        """
        Calcule l'accessoire selon les paliers de prime nette définis dans stdaccessoire.
        
        La logique suit la requête SQL :
        SELECT COALESCE(NULLIF(montantforfait, 0), accessoires)
        FROM stdaccessoire
        WHERE idproduit = ? AND idcompagnie = ? 
          AND prime_nette_totale BETWEEN primemin AND primemax
        
        Args:
            prime_nette_totale: Prime nette totale du devis (après options)
            id_produit: ID du produit MRH
            id_compagnie: ID de la compagnie
        
        Returns:
            Dict contenant:
            {
                'accessoire': Decimal,  # Montant accessoire HT
                'taxe_accessoire': Decimal,  # Taxe sur accessoire (14,5%)
                'accessoire_ttc': Decimal  # Accessoire + taxe
            }
        """
        from configuration_api.models import Accessoire
        
        accessoire = Decimal('0')
        
        try:
            # Rechercher le palier applicable
            palier = Accessoire.objects.filter(
                produit_id=id_produit,
                compagnie_id=id_compagnie,
                primemin__lte=prime_nette_totale,
                primemax__gte=prime_nette_totale
            ).first()
            
            if palier:
                # Logique COALESCE(NULLIF(montantforfait, 0), accessoires)
                # Si montantforfait existe et n'est pas 0, on le prend, sinon on prend accessoires
                if palier.montantforfait and palier.montantforfait != 0:
                    accessoire = palier.montantforfait
                else:
                    accessoire = palier.accessoires or Decimal('0')
        
        except Exception as e:
            # En cas d'erreur, on continue avec accessoire = 0
            print(e)
        
        # Calcul de la taxe sur accessoire (14,5%)
        taxe_accessoire = self._arrondir(accessoire * self.TAUX_TAXE_ACCESSOIRE)
        
        return {
            'accessoire': accessoire,
            'taxe_accessoire': taxe_accessoire,
            'accessoire_ttc': accessoire + taxe_accessoire,
        }
    
    # ========================================================================
    # SECTION 6 : CALCUL COMPLET D'UNE MAISON
    # ========================================================================
    
    def calculer_maison(
        self,
        code_usage: str,
        valeur_batiment: Optional[Decimal] = None,
        valeur_contenu: Optional[Decimal] = None,
        loyer_mensuel: Optional[Decimal] = None,
        capital_rvt: Optional[Decimal] = None,
        options: Optional[List[str]] = None,
        sous_garanties_optionnelles: Optional[List[str]] = None,
        adresse: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict:
        """
        Calcule la prime complète d'une maison avec toutes ses garanties.
        
        Args:
            code_usage: Code de l'usage habitation
            valeur_batiment: Valeur du bâtiment (optionnel selon usage)
            valeur_contenu: Valeur du contenu (optionnel selon usage)
            loyer_mensuel: Loyer mensuel (optionnel selon usage)
            capital_rvt: Capital RVT (optionnel selon usage)
            options: Liste des codes d'options sélectionnées
            sous_garanties_optionnelles: Liste des codes de sous-garanties optionnelles
            adresse: Adresse de la maison
            description: Description supplémentaire
        
        Returns:
            Dict contenant tous les détails du calcul
        """
        options = options or []
        sous_garanties_optionnelles = sous_garanties_optionnelles or []
        
        # 1. Calculer la prime de base
        prime_base = self.calculer_prime_base(
            code_usage=code_usage,
            valeur_batiment=valeur_batiment,
            valeur_contenu=valeur_contenu,
            loyer_mensuel=loyer_mensuel,
            capital_rvt=capital_rvt,
        )
        
        # 2. Répartir sur les garanties obligatoires
        sous_garanties = self.repartir_prime_sous_garanties(prime_base)
        
        # 3. Appliquer les options
        sous_garanties, options_appliquees = self.appliquer_options(
            sous_garanties, options, prime_base
        )
        
        # 4. Ajouter les garanties optionnelles
        sous_garanties = self.ajouter_sous_garanties_optionnelles(
            sous_garanties, sous_garanties_optionnelles
        )
        
        # 5. Calculer les totaux
        prime_nette_totale = sum(g['prime_nette'] for g in sous_garanties)
        prime_annuelle_totale = sum(g.get('prime_avant_options', g['prime_nette']) for g in sous_garanties)
        taxe_totale = sum(g['taxe'] for g in sous_garanties)
        prime_ttc_totale = prime_nette_totale + taxe_totale
        
        # 6. Préparer le résultat
        return {
            'code_usage': code_usage,
            'libelle_usage': self.usage.libelle,
            'parametres': {
                'valeur_batiment': valeur_batiment,
                'valeur_contenu': valeur_contenu,
                'loyer_mensuel': loyer_mensuel,
                'capital_rvt': capital_rvt,
            },
            'prime_base': prime_base,
            'prime_annuelle_totale': prime_annuelle_totale,
            'prime_nette_totale': prime_nette_totale,
            'taxe_totale': taxe_totale,
            'prime_ttc_totale': prime_ttc_totale,
            'sous_garanties': sous_garanties,
            'options_appliquees': options_appliquees,
            'adresse': adresse,
            'description': description,
        }
    
    # ========================================================================
    # SECTION 7 : ENREGISTREMENT DANS LES MODÈLES LEGACY
    # ========================================================================
    
    @transaction.atomic
    def enregistrer_maison_dans_devis(
        self,
        id_devis: int,
        id_tarif: int,
        id_offre: int,
        resultat_calcul: Dict
    ) -> int:
        """
        Enregistre une maison calculée dans DevisDetail et DevisDetGarantie.
        
        Args:
            id_devis: ID du devis parent
            resultat_calcul: Résultat du calcul de calculer_maison()
        
        Returns:
            ID du DevisDetail créé
        """
        from ..models import Devis, DevisDetail, DevisDetGarantie
        from configuration_api.models import Offre
        
        # 1. Calculer la prime annuelle de la maison (avant options)
        prime_annuelle_maison = sum(g.get('prime_avant_options', g['prime_nette']) for g in resultat_calcul['sous_garanties'])
        
        # 2. Créer le DevisDetail (maison)
        nombre_maisons = DevisDetail.objects.filter(iddevis_id=id_devis).count()
        try:
            if nombre_maisons == 0:  #Première maison dans le devis
                devis = Devis.objects.get(pk=id_devis)
                if devis:
                    devis.offre = Offre.objects.get(pk=id_offre)
                    devis.save()
        except Devis.DoesNotExist:
            raise ValidationError({"erreur": f"Devis ID {id_devis} inexistant"})
        except Offre.DoesNotExist:
            raise ValidationError({"erreur": f"Offre ID {id_devis} inexistante"})
        
        devis_detail = DevisDetail.objects.create(
            iddevis_id=id_devis,
            idoffre=id_offre,  # NULL pour MRH
            idtarif=id_tarif,
            vehicule=0,  # 0 pour MRH (legacy auto)
            
            # Montants calculés
            primenette=resultat_calcul['prime_nette_totale'],
            taxeenregistrement=resultat_calcul['taxe_totale'],
             primeannuelle=prime_annuelle_maison,  
            
            # Champs utilisables pour stocker des infos MRH
            observation=self._formater_observation(resultat_calcul),
            
            # Valeurs stockées dans champs legacy
            valeurneuve=resultat_calcul['parametres'].get('valeur_batiment') or 0,
            valeurvenale=resultat_calcul['parametres'].get('valeur_contenu') or 0,
            
            # Valeurs par défaut pour compatibilité
            nombreplace=0,
            chargeutile=0,
            valeuraccessoire=0,
            fga=0,
            remorque=False,
            extincteur=False,
            provisoire=False,
            carteverte=False,
            matricule='MRH',
            typeimmat='M',
            attestation='',
        )
        
        # 2. Créer les DevisDetGarantie pour chaque garantie
        for sous_garantie in resultat_calcul['sous_garanties']:
            if not sous_garantie['id_sous_garantie_std']:
                # Skip si pas de mapping avec stdsousgarantie
                continue
            
            DevisDetGarantie.objects.create(
                IdDevisDet=devis_detail.iddevisdetail,
                IdGarantie_id=sous_garantie['id_sous_garantie_std'],
                Acquise=True,
                
                # Montants
                PrimeNette=sous_garantie['prime_nette'],
                taxe=sous_garantie['taxe'],
                primeannuelle=sous_garantie.get('prime_avant_options', sous_garantie['prime_nette']),
                
                # Champs optionnels (NULL pour MRH)
                Capital=None,
                Franchise=None,
                TexteFranchise=None,
                Formule=None,
                
                # Champs old_ pour historique
                old_acquise='1' if sous_garantie['type_garantie'] == 'OBLIGATOIRE' else '0',
                old_capital=0,
                old_franchise=0,
                old_formule=None,
                old_places=None,
                old_primenette=0,
                
                # Champs spécifiques (non utilisés pour MRH)
                deces=None,
                ipp=None,
                fraismed=None,
                hosp=None,
                minfranchise=0,
                maxfranchise=0,
            )
        
        return devis_detail.iddevisdetail
    
    @transaction.atomic
    def mettre_a_jour_totaux_devis(
        self,
        id_devis: int,
        id_produit: int,
        id_compagnie: int,
        inclure_accessoires: bool = True
    ) -> Dict:
        """
        Met à jour les totaux du devis après ajout/modification de maisons.
        
        Args:
            id_devis: ID du devis à mettre à jour
            id_produit: ID du produit MRH
            id_compagnie: ID de la compagnie
            inclure_accessoires: Si True, calcule et ajoute les accessoires
        
        Returns:
            Dict contenant les montants calculés
        """
        from ..models import Devis, DevisDetail  # Import local
        
        # 1. Récupérer toutes les maisons du devis
        maisons = DevisDetail.objects.filter(iddevis_id=id_devis)
        
        # 2. Calculer les totaux
        prime_annuelle_totale = sum(m.primeannuelle for m in maisons)
        prime_nette_totale = sum(m.primenette for m in maisons)
        taxe_garanties_totale = sum(m.taxeenregistrement for m in maisons)
        
        # 3. Calculer les accessoires si demandé
        accessoire = Decimal('0')
        taxe_accessoire = Decimal('0')
        
        if inclure_accessoires:
            result_accessoire = self.calculer_accessoire(
                prime_nette_totale=prime_nette_totale,
                id_produit=id_produit,
                id_compagnie=id_compagnie
            )
            accessoire = result_accessoire['accessoire']
            taxe_accessoire = result_accessoire['taxe_accessoire']
        
        # 4. Calculer les montants finaux
        taxe_totale = taxe_garanties_totale + taxe_accessoire
        primeannuelle = prime_annuelle_totale
        fga = Decimal('0')  # 0 pour MRH
        cedeao = Decimal('0')  # 0 pour MRH
        primettc = prime_nette_totale + accessoire + fga + cedeao + taxe_totale
        
        # 5. Mettre à jour le devis
        Devis.objects.filter(iddevis=id_devis).update(
            primenette=prime_nette_totale,
            taxe=taxe_totale,
            accessoire=accessoire,
            primeannuelle=primeannuelle,
            fga=fga,
            cedeao=cedeao,
            primettc=primettc,
        )
        
        # 6. Retourner les montants calculés
        return {
            'prime_nette_totale': prime_nette_totale,
            'taxe_garanties': taxe_garanties_totale,
            'accessoire': accessoire,
            'taxe_accessoire': taxe_accessoire,
            'taxe_totale': taxe_totale,
            'primeannuelle': primeannuelle,
            'fga': fga,
            'cedeao': cedeao,
            'primettc': primettc,
        }
    
    @transaction.atomic
    def creer_devis(
        self,
        idintermediaire: int,
        idcompagnie: int,
        idproduit: int,
        idtarif:int,
        idoffre: int,
        idclient: int,
        dateeffet: date,
        **kwargs
    ) -> int:
        """
        Crée un nouveau devis MRH vide.
        
        Args:
            idintermediaire: ID de l'intermédiaire
            idcompagnie: ID de la compagnie
            idproduit: ID du produit MRH
            idtarif: ID du tarif
            idoffre: ID de l'offre
            idclient: ID du client
            dateeffet: Date d'effet du contrat
            **kwargs: Autres champs optionnels (dateexpiration, idassure, etc.)
        
        Returns:
            ID du devis créé
        """
        from ..models import Devis 
        
        # Calculer dateexpiration si non fournie (1 an par défaut)
        dateexpiration = kwargs.get('dateexpiration')
        idduree = kwargs.get('idduree', 4) #idduree = 4 ==> Durée annuelle
        jours = kwargs.get('nombrejours', 0)
        
        if not dateexpiration:
            try:
                dateexpiration = calculer_date_expiration(date_effet=dateeffet, id_duree=idduree, nombre_jours=jours)
            except Exception as error:
                raise error
            
        codecategorie = obtenir_code_categorie(idtarif)
        numerodevis = obtenir_nouveau_numero_devis(id_intermediaire=idintermediaire, id_compagnie=idcompagnie,code_categorie=codecategorie)
                # Créer le devis
        dateemission = datetime.now() if not kwargs.get("dateemission") else kwargs.get("dateemission")
        numero_police_compagnie = kwargs.get('numeropolicecompagnie', '')
        devis = Devis.objects.create(
            intermediaire_id=idintermediaire,
            compagnie_id=idcompagnie,
            produit_id=idproduit,
            offre_id=idoffre,
            client_id=idclient,
            assure_id=kwargs.get('idassure', idclient),
            numerodevis=numerodevis,
            numero_police_compagnie=numero_police_compagnie,
            # Dates
            dateeffet=dateeffet,
            dateexpiration=dateexpiration,
            dateemission=dateemission,
            
            # Configuration
            flotte=kwargs.get('flotte', False),
            coassurance=kwargs.get('coassurance', False),
            renouvelable=kwargs.get('renouvelable', True),
            confirme=kwargs.get('confirme', False),
            prime_imposee=kwargs.get('prime_imposee', False),
            
            # Durée et périodicité
            idduree=kwargs.get('idduree', 4),
            idterme=kwargs.get('idterme', 1),
            periode=kwargs.get('periode', 'A'),
            
            # Informations
            referenceagent=kwargs.get('referenceagent', ''),
            observation=kwargs.get('observation', ''),
            
            # Montants (initialisés à 0, seront mis à jour lors de l'ajout de maisons)
            primenette=0,
            taxe=0,
            accessoire=0,
            primeannuelle=0,
            fga=0,
            cedeao=0,
            primettc=0,
            
            # Autres champs
            avenant_id=kwargs.get('idavenant', 1),
            aperiteur_id=kwargs.get('idaperiteur', idintermediaire),
            numeroavenant='',
            echeance='',
            nbreche=1,
            statut='ACTIF',
        )
        
        return devis.iddevis
    
    def _formater_observation(self, resultat_calcul: Dict) -> str:
        """
        Formate l'observation pour DevisDetail (max 50 caractères).
        Stocke l'usage et l'adresse si possible.
        """
        observation = resultat_calcul['libelle_usage'][:30]
        
        adresse = resultat_calcul.get('adresse', '')
        if adresse:
            # Ajouter l'adresse si il reste de la place
            espace_restant = 50 - len(observation) - 3  # -3 pour " - "
            if espace_restant > 0:
                observation += f" - {adresse[:espace_restant]}"
        
        return observation[:50]
    
    # ========================================================================
    # SECTION 8 : MÉTHODES HAUT NIVEAU (COMBINAISON)
    # ========================================================================
    
    @transaction.atomic
    def calculer_et_enregistrer_maison(
        self,
        id_devis: int,
        id_produit: int,
        id_compagnie: int,
        id_tarif: int,
        id_offre: int,
        code_usage: str,
        valeur_batiment: Optional[Decimal] = None,
        valeur_contenu: Optional[Decimal] = None,
        loyer_mensuel: Optional[Decimal] = None,
        capital_rvt: Optional[Decimal] = None,
        options: Optional[List[str]] = None,
        sous_garanties_optionnelles: Optional[List[str]] = None,
        adresse: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict:
        """
        Méthode combinée : calcule la prime d'une maison ET l'enregistre dans le devis.
        
        Args:
            id_devis: ID du devis parent
            id_produit: ID du produit MRH
            id_compagnie: ID de la compagnie
            id_tarif: ID du tarif 
            id_offre: ID de l'offre commerciale
            code_usage: Code de l'usage habitation
            valeur_batiment, valeur_contenu, etc.: Paramètres de calcul
            options: Liste des codes d'options
            sous_garanties_optionnelles: Liste des codes de sous-garanties optionnelles
            adresse: Adresse de la maison
            description: Description
        
        Returns:
            Dict contenant:
            {
                'id_maison': int,  # ID du DevisDetail créé
                'calcul': Dict,  # Résultat du calcul
                'totaux_devis': Dict  # Totaux mis à jour du devis
            }
        """
        # 1. Calculer la maison
        resultat_calcul = self.calculer_maison(
            code_usage=code_usage,
            valeur_batiment=valeur_batiment,
            valeur_contenu=valeur_contenu,
            loyer_mensuel=loyer_mensuel,
            capital_rvt=capital_rvt,
            options=options,
            sous_garanties_optionnelles=sous_garanties_optionnelles,
            adresse=adresse,
            description=description,
        )
        
        # 2. Enregistrer dans DevisDetail et DevisDetGarantie
        id_maison = self.enregistrer_maison_dans_devis(
            id_devis=id_devis,
            id_tarif = id_tarif,
            id_offre = id_offre,
            resultat_calcul=resultat_calcul
        )
        
        # 3. Mettre à jour les totaux du devis (avec accessoires)
        totaux_devis = self.mettre_a_jour_totaux_devis(
            id_devis=id_devis,
            id_produit=id_produit,
            id_compagnie=id_compagnie,
            inclure_accessoires=True
        )
        
        # 4. Retourner le résultat complet
        return {
            'id_maison': id_maison,
            'calcul': resultat_calcul,
            'totaux_devis': totaux_devis,
        }
    
        # ========================================================================
    # SECTION 9 : RÉCAPITULATIF DES COMPOSANTES DE PRIMES
    # ========================================================================
    
    @transaction.atomic
    def creer_et_sauvegarder_recapitulatif(
        self,
        id_devis: int,
        sauvegarder_en_base: bool = True
    ) -> RecapitulatifPrimesMRH:
        """
        Crée un récapitulatif complet des composantes de calcul du devis
        et le sauvegarde optionnellement en base de données.
        
        Cette méthode doit être appelée APRÈS avoir ajouté toutes les maisons au devis.
        
        Args:
            id_devis: ID du devis
            sauvegarder_en_base: Si True, sauvegarde dans stdmrh_recap_prime
        
        Returns:
            Instance de RecapitulatifPrimesMRH avec toutes les données
        
        Exemple:
            service = MRHCalculService()
            
            # Créer le devis et ajouter des maisons...
            
            # Créer le récapitulatif
            recap = service.creer_et_sauvegarder_recapitulatif(id_devis=456)
            
            # Obtenir le JSON
            json_recap = recap.to_json()
            
            # Obtenir le résumé textuel
            texte = recap.generer_resume_textuel()
            print(texte)
        """
        from ..models import Devis, DevisDetail
        
        # Récupérer le devis
        devis = Devis.objects.select_related(
            'client', 'compagnie', 'intermediaire', 'produit'
        ).get(iddevis=id_devis)
        
        # Initialiser le récapitulatif
        recap = RecapitulatifPrimesMRH()
        
        # Ajouter les informations du devis
        recap.creer_recap_devis(
            id_devis=devis.iddevis,
            numero_devis=devis.numerodevis or '',
            client_info={
                'id': devis.client_id,
                'nom': getattr(devis.client, 'nom', 'N/A'),
                'prenom': getattr(devis.client, 'prenom', ''),
            },
            date_effet=devis.dateeffet,
            date_expiration=devis.dateexpiration,
            compagnie_id=devis.compagnie_id,
            compagnie_nom=getattr(devis.compagnie, 'nom', 'N/A'),
            intermediaire_id=devis.intermediaire_id,
            intermediaire_nom=getattr(devis.intermediaire, 'nom', 'N/A'),
            produit_id=devis.produit_id,
            produit_nom=getattr(devis.produit, 'nom', 'MRH'),
            reference_agent=devis.referenceagent or '',
            observation=devis.observation or '',
        )
        
        # Récupérer et ajouter les maisons
        maisons = DevisDetail.objects.filter(iddevis_id=id_devis).order_by('iddevisdetail')
        
        for idx, maison in enumerate(maisons, 1):
            # Récupérer les garanties de cette maison
            from ..models import DevisDetGarantie
            garanties_db = DevisDetGarantie.objects.filter(
                IdDevisDet=maison.iddevisdetail
            ).select_related('IdGarantie')
            
            # Formater les garanties
            garanties = []
            for gar_db in garanties_db:
                garantie_std = gar_db.IdGarantie
                
                # Calculer le taux de taxe
                if gar_db.PrimeNette and gar_db.PrimeNette != 0:
                    taux_taxe = (gar_db.taxe / gar_db.PrimeNette) * Decimal('100')
                else:
                    taux_taxe = Decimal('0')
                
                garanties.append({
                    'code_garantie': garantie_std.codegarantie if garantie_std else 'N/A',
                    'libelle': garantie_std.libelle if garantie_std else 'N/A',
                    'type': 'OBLIGATOIRE' if gar_db.Acquise else 'OPTIONNELLE',
                    'prime_nette': gar_db.PrimeNette,
                    'taux_repartition': None,  # Non stocké dans DevisDetGarantie
                    'taux_taxe': taux_taxe,
                    'taxe': gar_db.taxe,
                    'prime_ttc': gar_db.primeannuelle,
                    'code_garantie_std': garantie_std.codegarantie if garantie_std else None,
                    'id_garantie_std': garantie_std.idgarantie if garantie_std else None,
                })
            
            # Créer un résultat de calcul pour cette maison
            resultat_calcul = {
                'code_usage': 'N/A',  # Non stocké explicitement
                'libelle_usage': maison.observation[:30] if maison.observation else 'N/A',
                'adresse': maison.observation[33:] if len(maison.observation or '') > 33 else '',
                'description': '',
                'parametres': {
                    'valeur_batiment': maison.valeurneuve,
                    'valeur_contenu': maison.valeurvenale,
                    'loyer_mensuel': None,
                    'capital_rvt': None,
                },
                'prime_base': maison.primenette,  # Approximatif
                'prime_nette_totale': maison.primenette,
                'taxe_totale': maison.taxeenregistrement,
                'prime_ttc_totale': maison.primeannuelle,
                'garanties': garanties,
                'options_appliquees': [],  # Non stocké dans les tables legacy
            }
            
            recap.ajouter_maison(
                id_maison=maison.iddevisdetail,
                resultat_calcul=resultat_calcul,
                ordre=idx
            )
        
        # Ajouter les accessoires
        # Calculer la taxe accessoire (taxe totale - somme des taxes garanties)
        taxe_garanties = sum(m.taxeenregistrement for m in maisons)
        taxe_accessoire = devis.taxe - taxe_garanties if devis.taxe else Decimal('0')
        
        recap.ajouter_accessoires(
            prime_nette_totale=devis.primenette or Decimal('0'),
            accessoire=devis.accessoire or Decimal('0'),
            taxe_accessoire=taxe_accessoire,
            palier_info=None  # Pourrait être enrichi en récupérant de stdaccessoire
        )
        
        # Calculer les totaux
        recap.calculer_totaux()
        
        # Sauvegarder en base si demandé
        if sauvegarder_en_base:
            recap.sauvegarder_en_base(id_devis=id_devis)
        
        return recap
    
    
    # ========================================================================
    # UTILITAIRES
    # ========================================================================
    
    def _arrondir(self, montant: Decimal) -> Decimal:
        """Arrondit un montant à 2 décimales"""
        return montant.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)