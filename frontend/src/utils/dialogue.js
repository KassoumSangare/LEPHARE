/* =========================================================================
   BOÎTES DE DIALOGUE DE LE PHARE (remplacent window.confirm / window.prompt)
   - confirmer({ titre, message, consequences, confirmer, annuler, ton }) → Promise<boolean>
   - saisirTexte({ titre, message, consequences, placeholder, minimum, maximum, confirmer, annuler, ton })
     → Promise<string | null> (null si l'utilisateur annule)
   ton : 'info' (par défaut), 'attention' ou 'danger' (action irréversible : le focus va sur « Annuler »,
   le bouton de confirmation est en rouge et porte le nom exact de l'action).
   Construites en DOM simple : utilisables hors de React (apiClient, utils/motif.js). Échap annule,
   Ctrl+Entrée valide une saisie, la tabulation reste dans la boîte, le focus revient ensuite où il était.
   Apparence et animations : section « MOTION DESIGN » de index.css.
   ========================================================================= */

const ICONES = {
  info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
  attention: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  danger: '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>',
};
const icone = (ton) => `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONES[ton] || ICONES.info}</svg>`;
const DUREE_SORTIE = 150;
const FOCALISABLES = 'button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

let compteur = 0;
// Une boîte à la fois : les demandes suivantes attendent la précédente
let file = Promise.resolve();

const ouvrir = (config) => new Promise((resolve) => {
  const ton = ['attention', 'danger'].includes(config.ton) ? config.ton : 'info';
  const id = `dialogue-${++compteur}`;
  const focusAvant = document.activeElement;

  const fond = document.createElement('div');
  fond.className = 'dialogue-fond';
  const boite = document.createElement('div');
  boite.className = `dialogue ${ton}`;
  boite.setAttribute('role', ton === 'info' ? 'dialog' : 'alertdialog');
  boite.setAttribute('aria-modal', 'true');
  boite.setAttribute('aria-labelledby', `${id}-titre`);
  boite.setAttribute('aria-describedby', `${id}-message`);

  const entete = document.createElement('div');
  entete.className = 'dialogue-entete';
  const pastille = document.createElement('span');
  pastille.className = 'dialogue-icone';
  pastille.innerHTML = icone(ton);
  const textes = document.createElement('div');
  const titre = document.createElement('h2');
  titre.className = 'dialogue-titre';
  titre.id = `${id}-titre`;
  titre.textContent = config.titre || 'Confirmer';
  const message = document.createElement('p');
  message.className = 'dialogue-message';
  message.id = `${id}-message`;
  message.textContent = config.message || '';
  textes.append(titre, message);
  entete.append(pastille, textes);
  boite.append(entete);

  if (config.consequences) {
    const consequences = document.createElement('p');
    consequences.className = 'dialogue-consequences';
    consequences.textContent = config.consequences;
    boite.append(consequences);
  }

  let zone = null;
  let aide = null;
  if (config.saisie) {
    const bloc = document.createElement('div');
    bloc.className = 'dialogue-saisie';
    zone = document.createElement('textarea');
    zone.className = 'form-control';
    zone.rows = 3;
    zone.maxLength = config.saisie.maximum || 1000;
    zone.placeholder = config.saisie.placeholder || '';
    zone.setAttribute('aria-labelledby', `${id}-titre`);
    zone.value = config.saisie.valeur || '';
    aide = document.createElement('div');
    aide.className = 'dialogue-aide';
    aide.setAttribute('aria-live', 'polite');
    bloc.append(zone, aide);
    boite.append(bloc);
  }

  const actions = document.createElement('div');
  actions.className = 'dialogue-actions';
  const annuler = document.createElement('button');
  annuler.type = 'button';
  annuler.className = 'btn btn-secondary';
  annuler.textContent = config.annuler || 'Annuler';
  const valider = document.createElement('button');
  valider.type = 'button';
  valider.className = `btn ${ton === 'danger' ? 'btn-danger' : 'btn-primary'}`;
  valider.textContent = config.confirmer || 'Confirmer';
  actions.append(annuler, valider);
  boite.append(actions);
  fond.append(boite);
  document.body.append(fond);

  // Action irréversible : le focus ne se pose pas sur le bouton qui l'exécute
  (zone || (ton === 'danger' ? annuler : valider)).focus();

  let termine = false;
  const fermer = (valeur) => {
    if (termine) return;
    termine = true;
    document.removeEventListener('keydown', clavier, true);
    fond.classList.add('sortie');
    setTimeout(() => fond.remove(), DUREE_SORTIE);
    if (focusAvant && typeof focusAvant.focus === 'function' && document.contains(focusAvant)) focusAvant.focus();
    resolve(valeur);
  };
  const confirmerSaisie = () => {
    if (!zone) { fermer(true); return; }
    const texte = zone.value.trim();
    const minimum = config.saisie.minimum ?? 1;
    if (minimum > 0 && texte.length < minimum) {
      aide.textContent = minimum > 1 ? `Saisissez au moins ${minimum} caractères.` : 'Ce champ est obligatoire.';
      zone.focus();
      return;
    }
    fermer(texte);
  };
  function clavier(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      fermer(zone ? null : false);
    } else if (e.key === 'Enter' && zone && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      confirmerSaisie();
    } else if (e.key === 'Tab') {
      // La tabulation reste dans la boîte
      const elements = [...boite.querySelectorAll(FOCALISABLES)];
      const premier = elements[0];
      const dernier = elements[elements.length - 1];
      if (e.shiftKey && document.activeElement === premier) { e.preventDefault(); dernier.focus(); }
      else if (!e.shiftKey && document.activeElement === dernier) { e.preventDefault(); premier.focus(); }
    }
  }
  if (zone) zone.addEventListener('input', () => { aide.textContent = ''; });
  annuler.addEventListener('click', () => fermer(zone ? null : false));
  valider.addEventListener('click', confirmerSaisie);
  fond.addEventListener('mousedown', (e) => { if (e.target === fond) fermer(zone ? null : false); });
  document.addEventListener('keydown', clavier, true);
});

const enFile = (config) => {
  const resultat = file.then(() => ouvrir(config));
  file = resultat.catch(() => {});
  return resultat;
};

/** Demande une confirmation ; renvoie true si l'utilisateur confirme. */
export const confirmer = (config) => enFile(typeof config === 'string' ? { message: config } : config);

/** Demande un texte (motif, commentaire) ; renvoie le texte saisi ou null si l'utilisateur annule. */
export const saisirTexte = ({ placeholder, minimum, maximum, valeur, ...config }) => enFile({
  ...config,
  saisie: { placeholder, minimum, maximum, valeur },
});
