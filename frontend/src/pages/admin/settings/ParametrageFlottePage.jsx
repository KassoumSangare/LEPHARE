import React from 'react';
import { Truck } from 'lucide-react';
import { EnTeteParametrage } from '../../../components/admin/EnTeteParametrage';
import { TableBareme } from '../../../components/admin/TableBareme';

// Réduction flotte par compagnie, produit et nombre de véhicules (stdreductionflotte)
const COLONNES = [
  { champ: 'compagnie', titre: 'Compagnie', type: 'compagnie', requis: true, filtre: true },
  { champ: 'produit', titre: 'Produit', type: 'produit', requis: true, filtre: true },
  { champ: 'nombre_minimum', titre: 'De (véhicules)', type: 'entier', requis: true, min: 1 },
  { champ: 'nombre_maximum', titre: 'À (véhicules)', type: 'entier', requis: true, min: 1 },
  { champ: 'taux_reduction', titre: 'Réduction flotte', type: 'pourcentage', requis: true, min: 0, max: 100 },
  { champ: 'taux_reduction_commerciale', titre: 'Réduction commerciale', type: 'pourcentage', requis: true, min: 0, max: 100, aide: 'Réduction commerciale accordée en plus, 0 sinon.' },
  { champ: 'debut_validite', titre: 'Début de validité', type: 'date', requis: true, role: 'debut' },
  { champ: 'fin_validite', titre: 'Fin de validité', type: 'date', requis: true, role: 'fin' },
];

// Tranches cohérentes : bornes dans l'ordre, sans chevauchement avec une autre tranche en vigueur en même temps
const controle = (ligne, autres) => {
  if (Number(ligne.nombre_minimum) > Number(ligne.nombre_maximum)) return 'Le nombre de véhicules « De » doit être inférieur ou égal à « À ».';
  const chevauche = autres.find((l) => Number(l.compagnie) === Number(ligne.compagnie) && Number(l.produit) === Number(ligne.produit)
    && String(l.debut_validite) <= String(ligne.fin_validite) && String(ligne.debut_validite) <= String(l.fin_validite)
    && Number(l.nombre_minimum) <= Number(ligne.nombre_maximum) && Number(ligne.nombre_minimum) <= Number(l.nombre_maximum));
  return chevauche ? `Cette tranche chevauche celle de ${chevauche.nombre_minimum} à ${chevauche.nombre_maximum} véhicules sur la même période.` : null;
};

export const ParametrageFlottePage = () => (
  <div style={{ padding: '1.5rem' }}>
    <EnTeteParametrage
      icone={Truck}
      titre="Réductions flotte"
      description="Remise accordée automatiquement selon le nombre de véhicules d'un même devis flotte, par compagnie."
      usage="Appliquée par le calcul des devis flotte (tranche du nombre de véhicules en vigueur à la date d'effet). Les devis déjà enregistrés gardent leur réduction."
    />
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      <TableBareme
        route="reductionflotte"
        cle="id_reduction_flotte"
        libelle="Tranche de réduction flotte"
        colonnes={COLONNES}
        valeursParDefaut={{ produit: 1, taux_reduction_commerciale: 0, fin_validite: '2050-12-31' }}
        controle={controle}
      />
    </div>
  </div>
);

export default ParametrageFlottePage;
