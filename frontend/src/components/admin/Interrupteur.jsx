import React from 'react';

/** Interrupteur oui / non des écrans de paramétrage (rôle « switch », lisible au clavier et par les lecteurs d'écran). */
export const Interrupteur = ({ actif, onChange, desactive, titre, libelle }) => (
  <button type="button" role="switch" aria-checked={actif} aria-label={libelle || titre} title={titre} disabled={desactive} onClick={() => onChange(!actif)}
    style={{ width: 40, height: 22, flex: 'none', borderRadius: 999, border: 'none', cursor: desactive ? 'not-allowed' : 'pointer', position: 'relative', background: actif ? 'var(--accent-emerald)' : 'var(--border-medium)', opacity: desactive ? 0.45 : 1, transition: 'background var(--mouvement-rapide, 0.15s)' }}>
    <span style={{ position: 'absolute', top: 3, left: actif ? 21 : 3, width: 16, height: 16, borderRadius: '50%', background: '#fff', transition: 'left var(--mouvement-rapide, 0.15s) var(--courbe-entree, ease)' }} />
  </button>
);

export default Interrupteur;
