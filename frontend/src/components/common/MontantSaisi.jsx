import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';

/* =========================================================================
   MONTANT SAISI AU FORMAT MILLIERS (demande du 2026-11-25 : « les champs de saisie des montants au format milliers pour une
   bonne lecture »). Regroupé par milliers pendant la frappe (« 1 250 000 »), centimes après la virgule (« 4 684 163,34 »,
   le point est lu comme une virgule), curseur gardé à sa place quand les espaces s'ajoutent.
   value : nombre ou chaîne numérique ; onChange(nombre | null) : null quand le champ est vide.
   À la différence d'AmountInput (montants entiers des devis), les centimes sont gardés.
   ========================================================================= */

const ESPACE = ' ';

export const formaterMontant = (texte, { decimales = true, negatif = false } = {}) => {
  const brut = String(texte ?? '').replace(/\./g, ',');
  const signe = negatif && brut.trim().startsWith('-') ? '-' : '';
  const [entier = '', ...reste] = brut.replace(/[^\d,]/g, '').split(',');
  const chiffres = entier.replace(/^0+(?=\d)/, '');
  const groupe = chiffres.replace(/\B(?=(\d{3})+(?!\d))/g, ESPACE);
  if (!decimales || !brut.includes(',')) return signe + groupe;
  return `${signe}${groupe || '0'},${reste.join('').slice(0, 2)}`;
};

export const lireMontant = (texte) => {
  const propre = String(texte ?? '').replace(/\s/g, '').replace(',', '.');
  if (!propre || propre === '-' || propre === '.') return null;
  const n = Number(propre);
  return Number.isFinite(n) ? n : null;
};

// Valeur reçue -> texte affiché (« 4684163.34 » -> « 4 684 163,34 »)
const depuisValeur = (valeur, options) => {
  if (valeur === null || valeur === undefined || valeur === '') return '';
  const n = Number(String(valeur).replace(',', '.'));
  if (!Number.isFinite(n)) return '';
  return formaterMontant(String(Math.round(n * 100) / 100).replace('.', ','), options);
};

// Caractères qui comptent pour replacer le curseur (les espaces de regroupement ne comptent pas)
const significatifs = (texte) => (texte.match(/[\d,-]/g) || []).length;

export const MontantSaisi = ({
  value, onChange, decimales = true, negatif = false, suffixe = '', className = 'form-control', style, ...attributs
}) => {
  const options = { decimales, negatif };
  const [texte, setTexte] = useState(() => depuisValeur(value, options));
  const champ = useRef(null);
  const curseur = useRef(null);

  // Valeur changée de l'extérieur (montant repris, remise à zéro) : affichée ; pas pendant la frappe d'une virgule
  useEffect(() => {
    const courant = lireMontant(texte);
    const recu = value === null || value === undefined || value === '' ? null : Number(String(value).replace(',', '.'));
    if (courant !== recu && !(courant === null && recu === null)) setTexte(depuisValeur(value, options));
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => {
    if (curseur.current === null || !champ.current || document.activeElement !== champ.current) return;
    let position = 0;
    let vus = 0;
    while (position < texte.length && vus < curseur.current) {
      if (/[\d,-]/.test(texte[position])) vus += 1;
      position += 1;
    }
    champ.current.setSelectionRange(position, position);
    curseur.current = null;
  }, [texte]);

  const saisir = (e) => {
    const brut = e.target.value;
    curseur.current = significatifs(brut.slice(0, e.target.selectionStart ?? brut.length).replace(/\./g, ','));
    const formate = formaterMontant(brut, options);
    setTexte(formate);
    onChange?.(lireMontant(formate));
  };

  const input = (
    <input
      ref={champ}
      type="text"
      inputMode={decimales ? 'decimal' : 'numeric'}
      autoComplete="off"
      className={className}
      value={texte}
      onChange={saisir}
      style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', ...(suffixe ? { paddingRight: '2.6rem' } : {}), ...style }}
      {...attributs}
    />
  );
  if (!suffixe) return input;
  return (
    <div style={{ position: 'relative' }}>
      {input}
      <span aria-hidden="true" style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', fontSize: '0.78rem',
        color: 'var(--text-muted)', pointerEvents: 'none' }}>{suffixe}</span>
    </div>
  );
};

export default MontantSaisi;
