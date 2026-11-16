import React from 'react';
import { HeartPulse, Link2, ShieldCheck, Umbrella } from 'lucide-react';
import { mineneApi } from '../../../api/endpoints';

// Écrans IA et RC : un devis créé avec un devis Santé MINENE (il en porte le numéro) se modifie depuis l'écran Santé, qui le
// réécrit à chaque enregistrement ; comme redirigerSiOreole
export const redirigerSiMinene = (idDevis, navigate) => {
  if (!Number(idDevis)) return undefined;
  let actif = true;
  mineneApi.devis(idDevis)
    .then((p) => {
      const lie = p?.Minene && !p.Confirme && ['IA', 'RC'].some((cle) => Number(p.Produits?.[cle]?.IdDevis) === Number(idDevis) && p.Produits[cle].AuDevisSante);
      if (actif && lie) navigate(`/user/quotes/sante?edit=${p.IdDevis}`, { replace: true });
    })
    .catch(() => {});
  return () => { actif = false; };
};

/* =========================================================================
   Package MINENE d'un devis (production/minene_package.py), comme le package Oreole Santé : la Santé, l'Individuelle
   Accidents et la RC chef de famille, créées ensemble à l'enregistrement du devis Santé, émises ensemble à la
   confirmation de l'un des trois devis et réglées en une fois à la caisse. Affiché sur l'écran de saisie Santé et sur
   la fiche d'un devis Santé, IA ou RC MINENE.
   ========================================================================= */
const PRODUITS = [
  ['Sante', 'Santé MINENE', HeartPulse, 'var(--accent-emerald, #10b981)'],
  ['IA', 'Individuelle Accidents', ShieldCheck, 'var(--primary-500, #3b82f6)'],
  ['RC', 'RC chef de famille', Umbrella, 'var(--accent-amber, #f59e0b)'],
];
const fcfa = (v) => Math.round(Number(v) || 0).toLocaleString('fr-FR');

const reference = (p) => {
  if (p.Etat === 'Non souscrite') return 'Non souscrite (case décochée)';
  if (p.Etat === 'Emise') return `Police ${p.NumeroPolice}`;
  if (p.Etat === 'Devis') return p.NumeroDevis ? `Devis ${p.NumeroDevis}` : 'En devis';
  return 'Créée à l\'enregistrement du devis Santé';
};

export default function BlocPackageMinene({ donnees, style }) {
  if (!donnees?.Minene) return null;
  const produits = donnees.Produits || {};
  const adherents = Number(donnees.Adherents) || 0;
  return (
    <div className="glass-panel" style={{ padding: '1.1rem 1.25rem', border: '1px solid color-mix(in srgb, var(--accent-emerald, #10b981) 35%, transparent)', ...style }}>
      <div style={{ fontWeight: 800, color: 'var(--accent-emerald, #10b981)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <Link2 size={16} /> Package MINENE : devis liés, une seule validation
      </div>
      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0.8rem' }}>
        {donnees.Confirme
          ? 'Polices émises ensemble ; elles se règlent en une fois à la caisse.'
          : `L'IA et la RC cochées suivent la Santé à chaque enregistrement (${adherents} adhérent${adherents > 1 ? 's' : ''}). Confirmer l'un des devis émet toutes les polices du package ensemble ; un seul règlement à la caisse.`}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', gap: '0.6rem' }}>
        {PRODUITS.map(([cle, libelle, Icone, couleur]) => {
          const p = produits[cle] || {};
          const exclue = p.Etat === 'Non souscrite';
          return (
            <div key={cle} style={{ padding: '0.7rem 0.85rem', borderRadius: 10, border: `1px ${exclue ? 'dashed' : 'solid'} var(--border-medium)`, borderTop: `3px solid ${exclue ? 'var(--border-medium)' : couleur}`, display: 'flex', flexDirection: 'column', gap: '0.2rem', opacity: exclue ? 0.6 : 1 }}>
              <b style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem' }}><Icone size={15} color={couleur} /> {libelle}</b>
              <span style={{ fontSize: '1.05rem', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>{fcfa(p.PrimeTtc)} F</span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{reference(p)}</span>
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', fontSize: '0.9rem', paddingTop: '0.7rem' }}>
        <span style={{ fontWeight: 700 }}>
          {(() => {
            const nombre = PRODUITS.filter(([cle]) => produits[cle] && produits[cle].Etat !== 'Non souscrite').length;
            return `Total MINENE (${nombre} police${nombre > 1 ? 's' : ''})`;
          })()}
        </span>
        <strong style={{ color: 'var(--accent-emerald, #10b981)', fontFamily: 'var(--font-mono)' }}>{fcfa(donnees.Totaux?.PrimeTtc)} F</strong>
      </div>
    </div>
  );
}
