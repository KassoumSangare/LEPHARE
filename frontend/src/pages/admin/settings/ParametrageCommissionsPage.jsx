import React from 'react';
import { Coins } from 'lucide-react';
import { EnTeteParametrage } from '../../../components/admin/EnTeteParametrage';
import { TableBareme } from '../../../components/admin/TableBareme';

// Taux de commission du cabinet par compagnie et par produit (stdcommissionproduitcompagnie)
const COLONNES = [
  { champ: 'compagnie', titre: 'Compagnie', type: 'compagnie', requis: true, filtre: true },
  { champ: 'produit', titre: 'Produit', type: 'produit', requis: true, filtre: true },
  { champ: 'taux_commission', titre: 'Taux de commission', type: 'pourcentage', requis: true, min: 0, max: 100 },
  { champ: 'forfait', titre: 'Forfait', type: 'montant', requis: true, min: 0, aide: 'Montant fixe par quittance, 0 si la commission est seulement au taux.' },
  { champ: 'debut_validite', titre: 'Début de validité', type: 'date', requis: true, role: 'debut' },
  { champ: 'fin_validite', titre: 'Fin de validité', type: 'date', requis: true, role: 'fin' },
];

// Deux périodes qui se chevauchent pour la même compagnie et le même produit : le calcul n'en prendrait qu'une
const controle = (ligne, autres) => {
  const chevauche = autres.find((l) => Number(l.compagnie) === Number(ligne.compagnie) && Number(l.produit) === Number(ligne.produit)
    && String(l.debut_validite) <= String(ligne.fin_validite) && String(ligne.debut_validite) <= String(l.fin_validite));
  return chevauche
    ? `Une autre ligne couvre déjà cette compagnie et ce produit du ${chevauche.debut_validite} au ${chevauche.fin_validite} : arrêtez-la avant le début de la nouvelle.`
    : null;
};

export const ParametrageCommissionsPage = () => (
  <div style={{ padding: '1.5rem' }}>
    <EnTeteParametrage
      icone={Coins}
      titre="Taux de commission"
      description="Commission du cabinet sur chaque produit, compagnie par compagnie, avec sa période de validité."
      usage="Lu à l'émission des quittances (commission intermédiaire) et dans le suivi des reversements et des commissions. Une modification s'applique aux quittances émises ensuite."
    />
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      <TableBareme
        route="commissionproduit"
        cle="id_commission_produit"
        libelle="Taux de commission"
        colonnes={COLONNES}
        valeursParDefaut={{ forfait: 0, fin_validite: '2050-12-31' }}
        controle={controle}
      />
    </div>
  </div>
);

export default ParametrageCommissionsPage;
