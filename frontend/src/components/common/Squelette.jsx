import React from 'react';

/* Lignes fantômes (skeletons) affichées pendant le chargement d'un tableau : la mise en page reste en
   place et l'attente se voit sans bloquer l'écran. Styles : .squelette dans index.css. */

// Largeurs variées mais stables d'un rendu à l'autre (pas de valeur aléatoire)
const largeur = (ligne, colonne) => `${50 + ((ligne * 7 + colonne * 13) % 45)}%`;

export const SqueletteLignes = ({ colonnes = 5, lignes = 6 }) => (
  <>
    {Array.from({ length: lignes }, (_, i) => (
      <tr key={i} className="squelette-ligne" aria-hidden="true">
        {Array.from({ length: colonnes }, (_, j) => (
          <td key={j}>
            <span className="squelette" style={{ width: largeur(i, j) }} />
            {j < 2 && <span className="squelette court" />}
          </td>
        ))}
      </tr>
    ))}
  </>
);

export const SqueletteTableau = ({ colonnes = 5, lignes = 6, libelle = 'Chargement en cours…' }) => (
  <div className="table-wrapper" role="status" aria-live="polite">
    <span className="visuellement-cache">{libelle}</span>
    <table className="data-table">
      <tbody>
        <SqueletteLignes colonnes={colonnes} lignes={lignes} />
      </tbody>
    </table>
  </div>
);

export default SqueletteTableau;
