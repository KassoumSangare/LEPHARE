import React from 'react';
import { Info } from 'lucide-react';

/**
 * En-tête commun des écrans de paramétrage : icône, titre, phrase d'explication et, en dessous,
 * où le réglage est utilisé (pour que l'administrateur sache ce que sa modification change).
 */
export const EnTeteParametrage = ({ icone: Icone, titre, description, usage, actions }) => (
  <div style={{ marginBottom: '1.25rem' }}>
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
      <div style={{ display: 'flex', gap: '0.85rem', alignItems: 'flex-start', minWidth: 0 }}>
        {Icone && (
          <div style={{ width: 42, height: 42, borderRadius: 10, display: 'grid', placeItems: 'center', background: 'rgba(59,130,246,0.12)', color: 'var(--primary-500)', flexShrink: 0 }}>
            <Icone size={21} />
          </div>
        )}
        <div style={{ minWidth: 0 }}>
          <h1 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.01em' }}>{titre}</h1>
          {description && <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.3rem 0 0', maxWidth: 820 }}>{description}</p>}
        </div>
      </div>
      {actions && <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>{actions}</div>}
    </div>
    {usage && (
      <div style={{ display: 'flex', gap: '0.55rem', alignItems: 'flex-start', marginTop: '0.85rem', padding: '0.6rem 0.85rem', borderRadius: 8, background: 'rgba(59,130,246,0.07)', border: '1px solid rgba(59,130,246,0.18)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
        <Info size={15} style={{ color: 'var(--primary-500)', flexShrink: 0, marginTop: 1 }} />
        <span>{usage}</span>
      </div>
    )}
  </div>
);

/** Carte de section d'un écran de paramétrage. */
export const SectionParametrage = ({ icone: Icone, titre, description, children, actions }) => (
  <div className="glass-panel" style={{ padding: '1.25rem 1.35rem', marginBottom: '1.1rem' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
      <div>
        <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {Icone && <Icone size={17} style={{ color: 'var(--primary-500)' }} />}
          {titre}
        </h2>
        {description && <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0.3rem 0 0', maxWidth: 760 }}>{description}</p>}
      </div>
      {actions}
    </div>
    {children}
  </div>
);
