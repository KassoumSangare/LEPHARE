import React from 'react';
import { TrafficCone } from 'lucide-react';
import { EnTeteParametrage } from '../../../components/admin/EnTeteParametrage';
import { TableBareme } from '../../../components/admin/TableBareme';

// Formules de la garantie Sécurité routière (personnes transportées) par compagnie (stdformulesecuriteroutiere)
const COLONNES = [
  { champ: 'compagnie', titre: 'Compagnie', type: 'compagnie', requis: true, filtre: true },
  { champ: 'libelle_formule', titre: 'Formule', type: 'texte', requis: true, longueur: 50, aide: 'Libellé proposé dans le devis (ex. FORMULE I, OPTION A).' },
  { champ: 'nombre_place', titre: 'Nombre de places', type: 'entier', requis: true, min: 0, aide: 'NSIA : prime selon les places du véhicule (3 = 3 places ou moins). Autres compagnies : 0, la formule vaut pour tout véhicule.' },
  { champ: 'capital_deces', titre: 'Capital décès', type: 'montant', requis: true, min: 0 },
  { champ: 'capital_ipp', titre: 'Capital invalidité (IPP)', type: 'montant', requis: true, min: 0 },
  { champ: 'capital_ft', titre: 'Frais de traitement', type: 'montant', requis: true, min: 0 },
  { champ: 'prime_nette', titre: 'Prime nette', type: 'montant', requis: true, min: 0 },
];

const ORDRE_ROMAIN = { I: 1, II: 2, III: 3, IV: 4, V: 5, VI: 6, VII: 7, VIII: 8, IX: 9, X: 10 };
const rangFormule = (libelle) => {
  const fin = String(libelle || '').trim().split(/\s+/).pop();
  return ORDRE_ROMAIN[fin] ?? (Number(fin) || fin);
};

export const ParametrageSecuritePage = () => (
  <div style={{ padding: '1.5rem' }}>
    <EnTeteParametrage
      icone={TrafficCone}
      titre="Sécurité routière"
      description="Formules de la garantie des personnes transportées : capitaux décès, invalidité et frais de traitement, prime nette."
      usage="Proposées dans les devis Automobile de la compagnie ; la prime de la formule choisie est reprise par le calcul. Les devis déjà enregistrés ne changent pas."
    />
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      <TableBareme
        route="formulesecuriteroutiere"
        cle="id_formule"
        libelle="Formule de sécurité routière"
        colonnes={COLONNES}
        valeursParDefaut={{ nombre_place: 0 }}
        tri={(a, b) => Number(a.compagnie) - Number(b.compagnie) || Number(a.nombre_place) - Number(b.nombre_place)
          || String(rangFormule(a.libelle_formule)).localeCompare(String(rangFormule(b.libelle_formule)), 'fr', { numeric: true })}
      />
    </div>
  </div>
);

export default ParametrageSecuritePage;
