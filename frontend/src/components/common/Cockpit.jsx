import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react';

import { formatDate } from '../../utils/dateUtils';
import { moduleDuProduit, moduleOuvert } from '../../utils/parametrage';
import { MODULES_EDITION_COMPLETE } from '../../utils/quoteRegistry';

// Pièces communes des écrans de chiffres : cockpit, tableau de bord, suivi commercial
export const francs = (n) => `${Math.round(Number(n) || 0).toLocaleString('fr-FR')} F`;
export const nombre = (n) => Number(n || 0).toLocaleString('fr-FR');
export const pluriel = (n, un, plusieurs) => `${nombre(n)} ${Number(n) > 1 ? plusieurs : un}`;
export const pourcent = (n) => (n === null || n === undefined ? '-' : `${Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %`);

// Devis : formulaire du produit rouvert s'il sait le faire, sinon registre des devis
export const cheminDevis = (idProduit, idDevis) => {
  const module = moduleDuProduit(Number(idProduit));
  return MODULES_EDITION_COMPLETE.includes(module) && moduleOuvert(module) ? `/user/quotes/${module}?edit=${idDevis}` : '/user/quotes';
};

const COULEURS_ICONE = {
  blue: { fond: 'rgba(59, 130, 246, 0.15)', texte: '#60a5fa', bord: 'rgba(59, 130, 246, 0.25)' },
  emerald: { fond: 'rgba(16, 185, 129, 0.15)', texte: '#34d399', bord: 'rgba(16, 185, 129, 0.25)' },
  amber: { fond: 'rgba(245, 158, 11, 0.15)', texte: '#fbbf24', bord: 'rgba(245, 158, 11, 0.25)' },
  purple: { fond: 'rgba(139, 92, 246, 0.15)', texte: '#c084fc', bord: 'rgba(139, 92, 246, 0.25)' },
  rose: { fond: 'rgba(244, 63, 94, 0.15)', texte: '#fb7185', bord: 'rgba(244, 63, 94, 0.25)' },
};

// Tuile d'indicateur : ouvre l'écran détaillé quand une destination est donnée
export const Tuile = ({ titre, valeur, icone: Icone, couleur = 'blue', lignes = [], vers, aide }) => {
  const navigate = useNavigate();
  const c = COULEURS_ICONE[couleur] || COULEURS_ICONE.blue;
  const ouvrir = vers ? () => navigate(vers) : undefined;
  return (
    <div
      className={`metric-card cockpit-tuile${vers ? ' cliquable' : ''}`}
      role={vers ? 'link' : undefined}
      tabIndex={vers ? 0 : undefined}
      onClick={ouvrir}
      onKeyDown={vers ? (e) => { if (e.key === 'Enter') ouvrir(); } : undefined}
      title={aide}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
        <span style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)' }}>{titre}</span>
        <div className="metric-card-icon" style={{ background: c.fond, color: c.texte, border: `1px solid ${c.bord}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icone size={20} />
        </div>
      </div>
      <div className="metric-value">{valeur}</div>
      {lignes.filter(Boolean).map((ligne, i) => (
        <div key={i} className="cockpit-tuile-ligne">{ligne}</div>
      ))}
    </div>
  );
};

// Évolution par rapport à la même date de l'an dernier : flèche + libellé, jamais la couleur seule
export const Evolution = ({ actuel, precedent, au }) => {
  if (!precedent) return null;
  const taux = ((actuel - precedent) * 100) / precedent;
  const hausse = taux >= 0;
  const Fleche = hausse ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={`cockpit-evolution ${hausse ? 'hausse' : 'baisse'}`}>
      <Fleche size={13} aria-hidden="true" />
      <strong>{hausse ? '+' : '−'}{Math.abs(taux).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %</strong>
      <span>{hausse ? 'en hausse' : 'en baisse'} par rapport au {formatDate(au)} ({francs(precedent)})</span>
    </span>
  );
};

// Jauge d'un taux (0 à 100 %)
export const Jauge = ({ taux, libelle }) => (
  <div className="cockpit-jauge" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={taux || 0} aria-label={libelle}>
    <span style={{ width: `${Math.min(100, Math.max(0, taux || 0))}%` }} />
  </div>
);

export const Section = ({ titre, sousTitre, action, children, className = '' }) => (
  <section className={`glass-panel cockpit-section ${className}`.trim()}>
    <div className="cockpit-section-entete">
      <div>
        <h2 className="title-md">{titre}</h2>
        {sousTitre && <p>{sousTitre}</p>}
      </div>
      {action}
    </div>
    {children}
  </section>
);

export const BoutonVoir = ({ libelle, vers }) => {
  const navigate = useNavigate();
  return (
    <button type="button" className="btn btn-secondary cockpit-voir" onClick={() => navigate(vers)}>
      {libelle}
      <ArrowRight size={14} />
    </button>
  );
};
