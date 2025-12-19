"""
Module de récapitulatif des composantes de primes MRH
======================================================

Ce module fournit des fonctions pour créer un récapitulatif détaillé
des composantes de calcul de prime MRH, utile pour :
- Audit et traçabilité
- Affichage détaillé au client
- Reporting et analyse
- Reproduction des calculs

Structure du récapitulatif :
1. Informations générales du devis
2. Détail par maison
3. Détail par garantie
4. Détail des options appliquées
5. Calcul des accessoires
6. Totaux consolidés
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
import json
from django.db import transaction


class RecapitulatifPrimesMRH:
    """
    Classe pour créer et stocker un récapitulatif détaillé
    des composantes de calcul de prime MRH.
    """
    
    def __init__(self):
        self.recap = {
            'date_generation': datetime.now().isoformat(),
            'version': '1.0.0',
            'devis': {},
            'maisons': [],
            'totaux': {},
            'accessoires': {},
        }
    
    # ========================================================================
    # SECTION 1 : CRÉATION DU RÉCAPITULATIF
    # ========================================================================
    
    def creer_recap_devis(
        self,
        id_devis: int,
        numero_devis: str,
        client_info: Dict,
        date_effet: datetime,
        date_expiration: datetime,
        **kwargs
    ) -> None:
        """
        Ajoute les informations générales du devis au récapitulatif.
        
        Args:
            id_devis: ID du devis
            numero_devis: Numéro du devis
            client_info: Informations du client
            date_effet: Date d'effet du contrat
            date_expiration: Date d'expiration
            **kwargs: Autres informations (compagnie, intermédiaire, etc.)
        """
        self.recap['devis'] = {
            'id_devis': id_devis,
            'numero_devis': numero_devis,
            'client': client_info,
            'date_effet': date_effet.isoformat() if date_effet else None,
            'date_expiration': date_expiration.isoformat() if date_expiration else None,
            'id_compagnie': kwargs.get('id_compagnie'),
            'nom_compagnie': kwargs.get('nom_compagnie'),
            'id_intermediaire': kwargs.get('id_intermediaire'),
            'nom_intermediaire': kwargs.get('nom_intermediaire'),
            'id_produit': kwargs.get('id_produit'),
            'nom_produit': kwargs.get('nom_produit', 'MRH'),
            'reference_agent': kwargs.get('reference_agent', ''),
            'observation': kwargs.get('observation', ''),
        }
    
    def ajouter_maison(
        self,
        id_maison: int,
        resultat_calcul: Dict,
        ordre: int = 1
    ) -> None:
        """
        Ajoute une maison au récapitulatif avec tous ses détails.
        
        Args:
            id_maison: ID du DevisDetail
            resultat_calcul: Résultat du calcul de MRHCalculService.calculer_maison()
            ordre: Ordre d'affichage de la maison
        """
        maison_recap = {
            'ordre': ordre,
            'id': id_maison,
            'code_usage': resultat_calcul['code_usage'],
            'libelle_usage': resultat_calcul['libelle_usage'],
            'adresse': resultat_calcul.get('adresse'),
            'description': resultat_calcul.get('description'),
            
            # Paramètres de calcul
            'parametres': {
                'valeur_batiment': self._decimal_to_float(
                    resultat_calcul['parametres'].get('valeur_batiment')
                ),
                'valeur_contenu': self._decimal_to_float(
                    resultat_calcul['parametres'].get('valeur_contenu')
                ),
                'loyer_mensuel': self._decimal_to_float(
                    resultat_calcul['parametres'].get('loyer_mensuel')
                ),
                'capital_rvt': self._decimal_to_float(
                    resultat_calcul['parametres'].get('capital_rvt')
                ),
            },
            
            # Calculs
            'prime_base': self._decimal_to_float(resultat_calcul['prime_base']),
            'prime_nette_totale': self._decimal_to_float(resultat_calcul['prime_nette_totale']),
            'taxe_totale': self._decimal_to_float(resultat_calcul['taxe_totale']),
            'prime_ttc_totale': self._decimal_to_float(resultat_calcul['prime_ttc_totale']),
            
            # Garanties détaillées
            'sous_garanties': self._formater_garanties(resultat_calcul['sous_garanties']),
            
            # Options appliquées
            'options_appliquees': self._formater_options(
                resultat_calcul['options_appliquees']
            ),
            
            # Statistiques
            'nombre_sous_garanties_obligatoires': len([
                g for g in resultat_calcul['sous_garanties'] if g['type'] == 'OBLIGATOIRE'
            ]),
            'nombre_sous_garanties_optionnelles': len([
                g for g in resultat_calcul['sous_garanties'] if g['type'] == 'OPTIONNELLE'
            ]),
            'nombre_options': len(resultat_calcul['options_appliquees']),
        }
        
        self.recap['maisons'].append(maison_recap)
    
    def ajouter_accessoires(
        self,
        prime_nette_totale: Decimal,
        accessoire: Decimal,
        taxe_accessoire: Decimal,
        palier_info: Optional[Dict] = None
    ) -> None:
        """
        Ajoute les informations sur les accessoires au récapitulatif.
        
        Args:
            prime_nette_totale: Prime nette totale du devis
            accessoire: Montant de l'accessoire
            taxe_accessoire: Taxe sur l'accessoire
            palier_info: Informations sur le palier appliqué
        """
        self.recap['accessoires'] = {
            'prime_nette_base_calcul': self._decimal_to_float(prime_nette_totale),
            'accessoire': self._decimal_to_float(accessoire),
            'taxe_accessoire': self._decimal_to_float(taxe_accessoire),
            'taux_taxe': 14.5,  # 14,5%
            'accessoire_ttc': self._decimal_to_float(accessoire + taxe_accessoire),
            'palier': palier_info or {},
        }
    
    def calculer_totaux(self) -> None:
        """
        Calcule et ajoute les totaux consolidés au récapitulatif.
        """
        # Totaux des maisons
        prime_nette_maisons = sum(m['prime_nette_totale'] for m in self.recap['maisons'])
        taxe_garanties = sum(m['taxe_totale'] for m in self.recap['maisons'])
        prime_ttc_maisons = sum(m['prime_ttc_totale'] for m in self.recap['maisons'])
        
        # Accessoires
        accessoire = self.recap['accessoires'].get('accessoire', 0)
        taxe_accessoire = self.recap['accessoires'].get('taxe_accessoire', 0)
        
        # Totaux finaux
        taxe_totale = taxe_garanties + taxe_accessoire
        prime_annuelle = prime_nette_maisons
        fga = 0  # FGA = 0 pour MRH
        cedeao = 0  # CEDEAO = 0 pour MRH
        prime_ttc = prime_nette_maisons + accessoire + taxe_totale + fga + cedeao
        
        self.recap['totaux'] = {
            'nombre_maisons': len(self.recap['maisons']),
            'prime_nette_maisons': prime_nette_maisons,
            'taxe_garanties': taxe_garanties,
            'prime_ttc_maisons': prime_ttc_maisons,
            'accessoire': accessoire,
            'taxe_accessoire': taxe_accessoire,
            'taxe_totale': taxe_totale,
            'prime_annuelle': prime_annuelle,
            'fga': fga,
            'cedeao': cedeao,
            'prime_ttc': prime_ttc,
            
            # Statistiques globales
            'nombre_sous_garanties_total': sum(
                m['nombre_sous_garanties_obligatoires'] + m['nombre_sous_garanties_optionnelles']
                for m in self.recap['maisons']
            ),
            'nombre_options_total': sum(
                m['nombre_options'] for m in self.recap['maisons']
            ),
        }
    
    # ========================================================================
    # SECTION 2 : EXPORT DU RÉCAPITULATIF
    # ========================================================================
    
    def to_dict(self) -> Dict:
        """
        Retourne le récapitulatif sous forme de dictionnaire.
        """
        return self.recap
    
    def to_json(self, indent: int = 2) -> str:
        """
        Retourne le récapitulatif sous forme de JSON.
        
        Args:
            indent: Indentation du JSON (pour lisibilité)
        """
        return json.dumps(self.recap, indent=indent, ensure_ascii=False)
    
    def sauvegarder_en_base(
        self,
        id_devis: int,
        table_name: str = 'stdmrh_recap_prime'
    ) -> None:
        """
        Sauvegarde le récapitulatif dans une table dédiée.
        
        Args:
            id_devis: ID du devis
            table_name: Nom de la table (optionnel, pour personnalisation)
        """
        from django.db import connection
        
        json_recap = self.to_json()
        
        with connection.cursor() as cursor:
            # Vérifier si la table existe
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # Créer la table si elle n'existe pas
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id SERIAL PRIMARY KEY,
                        iddevis INTEGER NOT NULL UNIQUE,
                        recap_json JSONB NOT NULL,
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (iddevis) REFERENCES Devis(iddevis) ON DELETE CASCADE
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_iddevis 
                    ON {table_name}(iddevis);
                    
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_recap_json 
                    ON {table_name} USING gin(recap_json);
                """)
            
            # Insérer ou mettre à jour le récapitulatif
            cursor.execute(f"""
                INSERT INTO {table_name} (iddevis, recap_json, date_creation, date_modification)
                VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (iddevis) 
                DO UPDATE SET 
                    recap_json = EXCLUDED.recap_json,
                    date_modification = CURRENT_TIMESTAMP;
            """, [id_devis, json_recap])
    
    # ========================================================================
    # SECTION 3 : GÉNÉRATION DE RAPPORTS
    # ========================================================================
    
    def generer_resume_textuel(self) -> str:
        """
        Génère un résumé textuel du récapitulatif (pour affichage ou email).
        """
        lines = []
        lines.append("=" * 80)
        lines.append("RÉCAPITULATIF DEVIS MRH")
        lines.append("=" * 80)
        
        # Informations du devis
        devis = self.recap['devis']
        lines.append(f"\nDevis N° {devis['numero']}")
        lines.append(f"Client: {devis['client'].get('nom', 'N/A')}")
        lines.append(f"Date d'effet: {devis['date_effet']}")
        
        # Maisons
        lines.append(f"\n{'-' * 80}")
        lines.append(f"MAISONS ASSURÉES ({len(self.recap['maisons'])})")
        lines.append(f"{'-' * 80}")
        
        for idx, maison in enumerate(self.recap['maisons'], 1):
            lines.append(f"\nMaison {idx}: {maison['libelle_usage']}")
            if maison['adresse']:
                lines.append(f"Adresse: {maison['adresse']}")
            lines.append(f"Prime base: {maison['prime_base']:,.2f} FCFA")
            lines.append(f"Prime nette: {maison['prime_nette_totale']:,.2f} FCFA")
            lines.append(f"Taxe: {maison['taxe_totale']:,.2f} FCFA")
            lines.append(f"Prime TTC: {maison['prime_ttc_totale']:,.2f} FCFA")
            
            # Garanties
            lines.append(f"\n  Sous-Garanties ({maison['nombre_sous_garanties_obligatoires']} obligatoires + "
                        f"{maison['nombre_sous_garanties_optionnelles']} optionnelles):")
            for sous_garantie in maison['sous_garanties']:
                lines.append(f"    - {sous_garantie['libelle']}: "
                           f"{sous_garantie['prime_nette']:,.2f} FCFA "
                           f"(taxe: {sous_garantie['taxe']:,.2f})")
            
            # Options
            if maison['options_appliquees']:
                lines.append(f"\n  Options appliquées ({maison['nombre_options']}):")
                for option in maison['options_appliquees']:
                    signe = '+' if option['signe'] == '+' else '-'
                    lines.append(f"    {signe} {option['libelle']}: "
                               f"{option['montant_ajustement']:,.2f} FCFA")
        
        # Accessoires
        if self.recap['accessoires']:
            lines.append(f"\n{'-' * 80}")
            lines.append("ACCESSOIRES")
            lines.append(f"{'-' * 80}")
            acc = self.recap['accessoires']
            lines.append(f"Accessoire: {acc['accessoire']:,.2f} FCFA")
            lines.append(f"Taxe accessoire: {acc['taxe_accessoire']:,.2f} FCFA")
            lines.append(f"Accessoire TTC: {acc['accessoire_ttc']:,.2f} FCFA")
        
        # Totaux
        lines.append(f"\n{'-' * 80}")
        lines.append("TOTAUX")
        lines.append(f"{'-' * 80}")
        totaux = self.recap['totaux']
        lines.append(f"Prime nette totale: {totaux['prime_nette_maisons']:,.2f} FCFA")
        lines.append(f"Taxe garanties: {totaux['taxe_garanties']:,.2f} FCFA")
        lines.append(f"Accessoire: {totaux['accessoire']:,.2f} FCFA")
        lines.append(f"Taxe accessoire: {totaux['taxe_accessoire']:,.2f} FCFA")
        lines.append(f"Prime annuelle: {totaux['prime_annuelle']:,.2f} FCFA")
        lines.append(f"\nPRIME TTC TOTALE: {totaux['prime_ttc']:,.2f} FCFA")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def generer_tableau_garanties(self) -> List[Dict]:
        """
        Génère un tableau récapitulatif de toutes les garanties du devis.
        Utile pour affichage dans un tableau HTML ou export Excel.
        """
        tableau = []
        
        for idx, maison in enumerate(self.recap['maisons'], 1):
            for sous_garantie in maison['sous_garanties']:
                tableau.append({
                    'numero_maison': idx,
                    'usage_maison': maison['libelle_usage'],
                    'adresse_maison': maison['adresse'],
                    'code_sous_garantie': sous_garantie['code_sous_garantie'],
                    'libelle_sous_garantie': sous_garantie['libelle'],
                    'type_sosu_garantie': sous_garantie['type'],
                    'prime_nette': sous_garantie['prime_nette'],
                    'taux_taxe': sous_garantie['taux_taxe'],
                    'taxe': sous_garantie['taxe'],
                    'prime_ttc': sous_garantie['prime_ttc'],
                })
        
        return tableau
    
    # ========================================================================
    # MÉTHODES UTILITAIRES
    # ========================================================================
    
    def _decimal_to_float(self, value: Optional[Decimal]) -> Optional[float]:
        """Convertit Decimal en float pour JSON."""
        if value is None:
            return None
        return float(value)
    
    def _formater_garanties(self, garanties: List[Dict]) -> List[Dict]:
        """Formate la liste des garanties pour le récapitulatif."""
        return [
            {
                'code_sous_garantie': g['code_sous_garantie'],
                'libelle': g['libelle'],
                'type': g['type'],
                'prime_nette': self._decimal_to_float(g['prime_nette']),
                'taux_repartition': self._decimal_to_float(g.get('taux_repartition')),
                'taux_taxe': self._decimal_to_float(g['taux_taxe']),
                'taxe': self._decimal_to_float(g['taxe']),
                'prime_ttc': self._decimal_to_float(g['prime_ttc']),
                'code_sous_garantie_std': g.get('code_sous_garantie_std'),
                'id_sous_garantie_std': g.get('id_sous_garantie_std'),
            }
            for g in garanties
        ]
    
    def _formater_options(self, options: List[Dict]) -> List[Dict]:
        """Formate la liste des options pour le récapitulatif."""
        return [
            {
                'code_option': o['code_option'],
                'libelle': o['libelle'],
                'type': o['type'],
                'signe': o['signe'],
                'taux_ou_montant': self._decimal_to_float(o['taux_ou_montant']),
                'montant_ajustement': self._decimal_to_float(o['montant_ajustement']),
                'sous_garantie_cible_code': o['sous_garantie_cible_code'],
                'sous_garantie_cible_libelle': o['sous_garantie_cible_libelle'],
            }
            for o in options
        ]


# ============================================================================
# FONCTION UTILITAIRE HAUT NIVEAU
# ============================================================================

@transaction.atomic
def creer_recap_complet_devis(id_devis: int) -> RecapitulatifPrimesMRH:
    """
    Crée un récapitulatif complet à partir d'un devis existant.
    
    Args:
        id_devis: ID du devis
    
    Returns:
        Instance de RecapitulatifPrimesMRH avec toutes les données
    """
    from django.db import connection
    
    recap = RecapitulatifPrimesMRH()
    
    # Récupérer les informations du devis
    with connection.cursor() as cursor:
        # Devis principal
        cursor.execute("""
            SELECT d.iddevis, d.numerodevis, d.dateeffet, d.dateexpiration,
                   d.primenette, d.taxe, d.accessoire, d.primettc,
                   c.nom as client_nom, c.prenoms as client_prenom,
                   comp.raisonsociale as compagnie_nom, i.libelleintermediaire as intermediaire_nom,
                   p.nom as produit_nom,
                   d.referenceagent, d.observation
            FROM StdDevis d
            LEFT JOIN StdClient c ON d.idclient = c.idclient
            LEFT JOIN StdCompagnie comp ON d.idcompagnie = comp.idcompagnie
            LEFT JOIN StdIntermediaire i ON d.idintermediaire = i.idintermediaire
            LEFT JOIN StdProduit p ON d.idproduit = p.idproduit
            WHERE d.iddevis = %s
        """, [id_devis])
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Devis {id_devis} non trouvé")
        
        # Ajouter les infos du devis
        recap.creer_recap_devis(
            id_devis=row[0],
            numero_devis=row[1],
            client_info={
                'nom': f"{row[8]} {row[9] or ''}".strip(),
            },
            date_effet=row[2],
            date_expiration=row[3],
            compagnie_nom=row[10],
            intermediaire_nom=row[11],
            produit_nom=row[12],
            reference_agent=row[13],
            observation=row[14],
        )
        
        # Récupérer les maisons
        cursor.execute("""
            SELECT dd.iddevisdetail, dd.observation, dd.primenette, 
                   dd.taxeenregistrement, dd.primeannuelle,
                   dd.valeurneuve, dd.valeurvenale
            FROM DevisDetail dd
            WHERE dd.iddevis = %s
            ORDER BY dd.iddevisdetail
        """, [id_devis])
        
        maisons = cursor.fetchall()
        
        for idx, maison_row in enumerate(maisons, 1):
            # Récupérer les garanties de cette maison
            cursor.execute("""
                SELECT dg.IdGarantie, g.codesousgarantie, g.libellesousgarantie,
                       dg.PrimeNette, dg.taxe, dg.primeannuelle,
                       dg.Acquise
                FROM DevisDetGarantie dg
                JOIN stdsousgarantie g ON dg.IdGarantie = g.idsousgarantie
                WHERE dg.IdDevisDet = %s
                ORDER BY g.libellesousgarantie
            """, [maison_row[0]])
            
            garanties_db = cursor.fetchall()
            
            # Formater les garanties
            garanties = [
                {
                    'code_sous_garantie': g[1],
                    'libelle': g[2],
                    'type': 'OBLIGATOIRE' if g[6] else 'OPTIONNELLE',
                    'prime_nette': Decimal(str(g[3])),
                    'taux_repartition': None,
                    'taux_taxe': (Decimal(str(g[4])) / Decimal(str(g[3])) * 100) if g[3] != 0 else Decimal('0'),
                    'taxe': Decimal(str(g[4])),
                    'prime_ttc': Decimal(str(g[5])),
                    'code_sous_garantie_std': g[1],
                    'id_sous_garantie_std': g[0],
                }
                for g in garanties_db
            ]
            
            # Créer un résultat de calcul fictif pour ajouter la maison
            resultat_calcul = {
                'code_usage': 'N/A',  # Non stocké dans DevisDetail
                'libelle_usage': maison_row[1][:30] if maison_row[1] else 'N/A',
                'adresse': maison_row[1][33:] if len(maison_row[1] or '') > 33 else '',
                'description': '',
                'parametres': {
                    'valeur_batiment': Decimal(str(maison_row[5])),
                    'valeur_contenu': Decimal(str(maison_row[6])),
                    'loyer_mensuel': None,
                    'capital_rvt': None,
                },
                'prime_base': Decimal(str(maison_row[2])),  # Approximatif
                'prime_nette_totale': Decimal(str(maison_row[2])),
                'taxe_totale': Decimal(str(maison_row[3])),
                'prime_ttc_totale': Decimal(str(maison_row[4])),
                'sous_garanties': garanties,
                'options_appliquees': [],  # Non stocké
            }
            
            recap.ajouter_maison(
                id_maison=maison_row[0],
                resultat_calcul=resultat_calcul,
                ordre=idx
            )
        
        # Ajouter les accessoires
        recap.ajouter_accessoires(
            prime_nette_totale=Decimal(str(row[4])),
            accessoire=Decimal(str(row[6])),
            taxe_accessoire=Decimal(str(row[5])) - sum(
                Decimal(str(m[3])) for m in maisons
            ),
        )
    
    # Calculer les totaux
    recap.calculer_totaux()
    
    return recap