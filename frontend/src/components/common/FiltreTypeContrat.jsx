import React from 'react';

/* =========================================================================
   FILTRE MONO / FLOTTE
   Case « flotte » d'un contrat ou d'un devis : mono ou flotte en Automobile, individuel ou groupe dans les autres
   branches (Santé, IA, Vie…). Partagé par le Portefeuille des contrats, l'Administration des contrats et la
   Gestion des devis (demande du 2026-11-18).
   ========================================================================= */

export const TYPES_CONTRAT = ['tous', 'mono', 'flotte'];

/** Libellés du type selon la branche : Automobile (auto = true) ou autre. */
export const libellesTypeContrat = (auto) => (auto
  ? { tous: 'Tous', mono: 'Mono', flotte: 'Flotte' }
  : { tous: 'Tous', mono: 'Individuel', flotte: 'Groupe' });

/** Paramètre de l'API (?flotte=0 ou 1) d'un type choisi ; undefined pour « tous ». */
export const parametreFlotte = (type) => (type === 'mono' ? 0 : type === 'flotte' ? 1 : undefined);

const nombre = (n) => Number(n || 0).toLocaleString('fr-FR');

/**
 * valeur : 'tous' | 'mono' | 'flotte' ; comptes : { mono, flotte } (facultatif, « tous » en est la somme) ;
 * auto : libellés Mono / Flotte, sinon Individuel / Groupe.
 */
export const FiltreTypeContrat = ({ valeur, onChoisir, comptes, auto }) => {
  const libelles = libellesTypeContrat(auto);
  const compte = (cle) => (cle === 'tous' ? Number(comptes?.mono || 0) + Number(comptes?.flotte || 0) : comptes?.[cle]);
  return (
    <div className="filtre-type-contrat" role="radiogroup" aria-label={auto ? 'Mono ou flotte' : 'Individuel ou groupe'}>
      {TYPES_CONTRAT.map((cle) => (
        <button
          key={cle}
          type="button"
          role="radio"
          aria-checked={valeur === cle}
          className={`filtre-type-option${valeur === cle ? ' actif' : ''}`}
          onClick={() => onChoisir(cle)}
        >
          {libelles[cle]}
          {comptes && <span className="portefeuille-compte">{nombre(compte(cle))}</span>}
        </button>
      ))}
    </div>
  );
};
