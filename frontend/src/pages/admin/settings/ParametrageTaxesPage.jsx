import React from 'react';
import { Percent } from 'lucide-react';
import { EnTeteParametrage } from '../../../components/admin/EnTeteParametrage';
import { TableBareme } from '../../../components/admin/TableBareme';

// Taux de taxe par produit et par sous-garantie (stdtauxtaxegarantieproduit : sa colonne idgarantie
// porte l'identifiant de la sous-garantie, une seule ligne par produit et sous-garantie)
const COLONNES = [
  { champ: 'produit', titre: 'Produit', type: 'produit', requis: true, filtre: true },
  { champ: 'garantie', titre: 'Garantie', type: 'sousgarantie', requis: true, filtre: true },
  { champ: 'tauxtaxe', titre: 'Taux de taxe', type: 'pourcentage', requis: true, min: 0, max: 100 },
  { champ: 'tauxtaxegroupe', titre: 'Taux contrats groupe', type: 'pourcentage', requis: true, min: 0, max: 100, aide: 'Santé : taux appliqué aux contrats groupe (0 pour les autres produits).' },
  { champ: 'debutvalidite', titre: 'Début de validité', type: 'date', requis: true, role: 'debut' },
  { champ: 'finvalidite', titre: 'Fin de validité', type: 'date', requis: true, role: 'fin' },
];

export const ParametrageTaxesPage = () => (
  <div style={{ padding: '1.5rem' }}>
    <EnTeteParametrage
      icone={Percent}
      titre="Taxes"
      description="Taux de taxe sur les contrats d'assurance, par produit et par garantie, avec leur période de validité."
      usage="Le calcul de chaque devis applique le taux de la garantie à la date d'effet ; une garantie sans taux pour le produit n'est pas taxée. Une seule ligne par produit et par garantie : pour changer un taux, modifiez la ligne."
    />
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      <TableBareme
        route="tauxtaxegarantie"
        cle="id"
        libelle="Taux de taxe"
        colonnes={COLONNES}
        valeursParDefaut={{ tauxtaxegroupe: 0, finvalidite: '2050-12-31' }}
        dupliquer={false}
        controle={(ligne, autres) => (autres.some((l) => Number(l.produit) === Number(ligne.produit) && Number(l.garantie) === Number(ligne.garantie))
          ? 'Cette garantie a déjà un taux pour ce produit : modifiez la ligne existante.' : null)}
      />
    </div>
  </div>
);

export default ParametrageTaxesPage;
