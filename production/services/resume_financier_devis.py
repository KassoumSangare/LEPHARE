"""
Module de résumé financier des devis MRH
=========================================

Ce module fournit les fonctions pour calculer le résumé financier complet
d'un devis MRH avec tous les montants détaillés.

Calculs effectués :
- Prime nette totale (après options)
- Prime annuelle (avant options)
- Accessoires
- Taxe totale
- Prime TTC
- Liste des garanties acquises avec détails
"""

from decimal import Decimal
from typing import Dict, List
from django.db import transaction


class ResumeFinancierDevis:
    """
    Classe pour calculer le résumé financier complet d'un devis MRH.
    """
    
    # Constantes
    TAUX_TAXE_GARANTIE_25 = Decimal('0.25')  # 25%
    TAUX_TAXE_GARANTIE_145 = Decimal('0.145')  # 14.5%
    TAUX_TAXE_ACCESSOIRE = Decimal('0.145')  # 14.5%
    
    def __init__(self, id_devis: int):
        """
        Initialise le calculateur avec l'ID du devis.
        
        Args:
            id_devis: ID du devis à analyser
        """
        self.id_devis = id_devis
        self.devis = None
        self.maisons = []
        self.sous_garanties = []
    
    def charger_donnees(self):
        """
        Charge toutes les données du devis depuis la base.
        """
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Charger le devis
            cursor.execute("""
                SELECT iddevis, numerodevis, primenette, taxe, accessoire, primettc,
                       idproduit, idcompagnie
                FROM StdDevis
                WHERE iddevis = %s
            """, [self.id_devis])
            
            devis_row = cursor.fetchone()
            if not devis_row:
                raise ValueError(f"Devis {self.id_devis} non trouvé")
            
            self.devis = {
                'id': devis_row[0],
                'numero': devis_row[1],
                'primenette_db': Decimal(str(devis_row[2])) if devis_row[2] else Decimal('0'),
                'taxe_db': Decimal(str(devis_row[3])) if devis_row[3] else Decimal('0'),
                'accessoire_db': Decimal(str(devis_row[4])) if devis_row[4] else Decimal('0'),
                'primettc_db': Decimal(str(devis_row[5])) if devis_row[5] else Decimal('0'),
                'idproduit': devis_row[6],
                'idcompagnie': devis_row[7],
            }
            
            # Charger les maisons du devis
            cursor.execute("""
                SELECT iddevisdetail, primenette, taxeenregistrement, primeannuelle
                FROM StdDevisDetail
                WHERE iddevis = %s
                ORDER BY iddevisdetail
            """, [self.id_devis])
            
            self.maisons = [
                {
                    'id': row[0],
                    'primenette': Decimal(str(row[1])) if row[1] else Decimal('0'),
                    'taxe': Decimal(str(row[2])) if row[2] else Decimal('0'),
                    'primeannuelle': Decimal(str(row[3])) if row[3] else Decimal('0'),
                }
                for row in cursor.fetchall()
            ]
            
            # Charger toutes les garanties de toutes les maisons
            for maison in self.maisons:
                cursor.execute("""
                    SELECT dg.IdDevisDet, dg.IdGarantie, 
                           g.codesousgarantie, g.libellesousgarantie,
                           dg.PrimeNette, dg.taxe, dg.primeannuelle,
                           dg.Acquise
                    FROM StdDevisDetGarantie dg
                    JOIN stdsousgarantie g ON dg.IdGarantie = g.idsousgarantie
                    WHERE dg.IdDevisDet = %s
                    ORDER BY g.libellesousgarantie
                """, [maison['id']])
                
                for gar_row in cursor.fetchall():
                    self.sous_garanties.append({
                        'id_maison': gar_row[0],
                        'id_sous_garantie': gar_row[1],
                        'code_sous_garantie': gar_row[2],
                        'libelle_sous_garantie': gar_row[3],
                        'prime_nette': Decimal(str(gar_row[4])) if gar_row[4] else Decimal('0'),
                        'taxe': Decimal(str(gar_row[5])) if gar_row[5] else Decimal('0'),
                        'prime_ttc': Decimal(str(gar_row[6])) if gar_row[6] else Decimal('0'),
                        'acquise': gar_row[7],
                    })
    
    def calculer_prime_annuelle_avant_options(self) -> Decimal:
        """
        Calcule la prime annuelle AVANT application des options.
        
        La prime annuelle est stockée dans le champ 'primeannuelle' de DevisDetail,
        qui contient la somme des primes de toutes les garanties AVANT application des options.
        
        Returns:
            Prime annuelle avant options
        """
        # Avec la correction du service mrh_calcul_service.py,
        # le champ 'primeannuelle' de DevisDetail contient maintenant
        # la somme des primes AVANT options.
        prime_annuelle = sum(m['primeannuelle'] for m in self.maisons)
        return prime_annuelle
    
    def calculer_prime_nette_totale(self) -> Decimal:
        """
        Calcule la prime nette totale APRÈS application des options.
        
        C'est la somme des primes nettes de toutes les garanties de toutes les maisons
        après que les options aient été appliquées.
        
        Returns:
            Prime nette totale après options
        """
        # La prime nette dans DevisDetail est déjà après options
        prime_nette_totale = sum(m['primenette'] for m in self.maisons)
        return prime_nette_totale
    
    def calculer_accessoires(self, prime_nette_totale: Decimal) -> Dict:
        """
        Calcule les accessoires selon les paliers définis dans stdaccessoire.
        
        Args:
            prime_nette_totale: Prime nette totale sur laquelle calculer l'accessoire
        
        Returns:
            Dict avec accessoire, taxe_accessoire, accessoire_ttc
        """
        from django.db import connection
        
        accessoire = Decimal('0')
        palier_info = None
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, primemin, primemax, accessoires, montantforfait
                    FROM stdaccessoire
                    WHERE idproduit = %s 
                      AND idcompagnie = %s
                      AND %s BETWEEN primemin AND primemax
                    LIMIT 1
                """, [
                    self.devis['idproduit'],
                    self.devis['idcompagnie'],
                    prime_nette_totale
                ])
                
                row = cursor.fetchone()
                if row:
                    palier_info = {
                        'id': row[0],
                        'primemin': float(row[1]) if row[1] else 0,
                        'primemax': float(row[2]) if row[2] else 0,
                        'accessoires': float(row[3]) if row[3] else 0,
                        'montantforfait': float(row[4]) if row[4] else 0,
                    }
                    
                    # Logique COALESCE(NULLIF(montantforfait, 0), accessoires)
                    montantforfait = Decimal(str(row[4])) if row[4] else Decimal('0')
                    accessoires_val = Decimal(str(row[3])) if row[3] else Decimal('0')
                    
                    if montantforfait and montantforfait != 0:
                        accessoire = montantforfait
                    else:
                        accessoire = accessoires_val
        
        except Exception as e:
            # En cas d'erreur, accessoire reste à 0
            pass
        
        # Calculer la taxe sur accessoire (14.5%)
        taxe_accessoire = (accessoire * self.TAUX_TAXE_ACCESSOIRE).quantize(Decimal('0.01'))
        
        return {
            'accessoire': accessoire,
            'taxe_accessoire': taxe_accessoire,
            'accessoire_ttc': accessoire + taxe_accessoire,
            'palier': palier_info,
        }
    
    def calculer_taxe_totale(self, taxe_sous_garanties: Decimal, taxe_accessoire: Decimal) -> Decimal:
        """
        Calcule la taxe totale.
        
        Args:
            taxe_sous_garanties: Somme des taxes sur toutes les garanties
            taxe_accessoire: Taxe sur l'accessoire
        
        Returns:
            Taxe totale
        """
        return taxe_sous_garanties + taxe_accessoire
    
    def obtenir_sous_garanties_acquises(self) -> List[Dict]:
        """
        Retourne la liste des garanties acquises avec leurs détails.
        
        Returns:
            Liste des garanties acquises
        """
        sous_garanties_acquises = [
            {
                'id_sous_garantie': g['id_sous_garantie'],
                'code_sous_garantie': g['code_sous_garantie'],
                'libelle_sous_garantie': g['libelle_sous_garantie'],
                'prime_nette': g['prime_nette'],
                'taxe': g['taxe'],
                'prime_ttc': g['prime_ttc'],
            }
            for g in self.sous_garanties
            if g['acquise']  # Seulement les garanties acquises
        ]
        
        return sous_garanties_acquises
    
    def calculer_resume_complet(self) -> Dict:
        """
        Calcule le résumé financier complet du devis.
        
        Returns:
            Dict contenant tous les montants et détails
        """
        # Charger les données
        self.charger_donnees()
        
        # 1. Prime nette totale (après options)
        prime_nette_totale = self.calculer_prime_nette_totale()
        
        # 2. Prime annuelle (avant options)
        # NOTE : Comme expliqué dans la méthode, avec les données actuelles,
        # nous ne pouvons pas différencier avant/après options car les options
        # ne sont pas stockées. Les deux valeurs seront identiques.
        prime_annuelle = self.calculer_prime_annuelle_avant_options()
        
        # 3. Taxe sur les garanties (somme de toutes les taxes garanties)
        taxe_sous_garanties = sum(g['taxe'] for g in self.sous_garanties)
        
        # 4. Accessoires
        accessoires_info = self.calculer_accessoires(prime_nette_totale)
        accessoire = accessoires_info['accessoire']
        taxe_accessoire = accessoires_info['taxe_accessoire']
        
        # 5. Taxe totale
        taxe_totale = self.calculer_taxe_totale(taxe_sous_garanties, taxe_accessoire)
        
        # 6. Prime TTC
        prime_ttc = prime_nette_totale + taxe_totale + accessoire
        
        # 7. Liste des garanties acquises
        sous_garanties_acquises = self.obtenir_sous_garanties_acquises()
        
        # Retourner le résumé complet
        return {
            'id_devis': self.id_devis,
            'numero_devis': self.devis['numero'],
            
            # Montants principaux
            'prime_nette_totale': prime_nette_totale,
            'prime_annuelle': prime_annuelle,
            'accessoire': accessoire,
            'taxe_totale': taxe_totale,
            'prime_ttc': prime_ttc,
            
            # Détails des taxes
            'taxe_sous_garanties': taxe_sous_garanties,
            'taxe_accessoire': taxe_accessoire,
            
            # Détails accessoire
            'accessoire_details': {
                'accessoire': accessoire,
                'taxe_accessoire': taxe_accessoire,
                'accessoire_ttc': accessoires_info['accessoire_ttc'],
                'palier': accessoires_info['palier'],
            },
            
            # Statistiques
            'statistiques': {
                'nombre_maisons': len(self.maisons),
                'nombre_sous_garanties_total': len(self.sous_garanties),
                'nombre_sous_garanties_acquises': len(sous_garanties_acquises),
            },
            
            # Liste des garanties acquises
            'sous_garanties_acquises': sous_garanties_acquises,
        }


# ============================================================================
# FONCTION UTILITAIRE
# ============================================================================

def obtenir_resume_financier_devis(id_devis: int) -> Dict:
    """
    Fonction utilitaire pour obtenir le résumé financier d'un devis.
    
    Args:
        id_devis: ID du devis
    
    Returns:
        Dict contenant le résumé financier complet
    
    Example:
        >>> resume = obtenir_resume_financier_devis(456)
        >>> print(f"Prime TTC: {resume['prime_ttc']:,.2f} FCFA")
    """
    calculateur = ResumeFinancierDevis(id_devis)
    return calculateur.calculer_resume_complet()