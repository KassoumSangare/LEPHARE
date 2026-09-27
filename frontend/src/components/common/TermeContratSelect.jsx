import React from 'react';
import { TERMES_CONTRAT, idTermeValide } from '../../utils/termesContrat';
import { trierParLibelle } from '../../utils/sortUtils';

// Menu « Terme du contrat » commun à tous les devis : Tacite reconduction, Ferme, Autre.
// value / onChange portent l'id du terme (stddevis.idterme).
export const TermeContratSelect = ({ value, onChange, className = 'form-control', ...props }) => (
  <select
    className={className}
    value={idTermeValide(value)}
    onChange={(e) => onChange(Number(e.target.value))}
    {...props}
  >
    {trierParLibelle(TERMES_CONTRAT, (t) => t.libelle).map((t) => (
      <option key={t.id} value={t.id}>
        {t.libelle}
      </option>
    ))}
  </select>
);

export default TermeContratSelect;
