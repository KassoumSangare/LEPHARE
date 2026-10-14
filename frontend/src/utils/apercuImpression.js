/* =========================================================================
   APERÇU D'IMPRESSION DANS L'APPLICATION
   Les documents imprimés (CP, devis, quittances, attestations, reçus, bordereaux…) s'affichent sur une
   feuille A4 (portrait ou paysage selon le gabarit) posée sur l'écran courant, au lieu d'un nouvel onglet :
   zoom, « Imprimer / PDF » (ou Ctrl+P), « Nouvel onglet », « Fermer » (ou Échap).
   ouvrirApercuImpression() renvoie un objet qui se manipule comme la fenêtre de window.open('')
   (document.open/write/close, print, focus, close) : les gabarits n'ont rien à changer. Un message
   écrit seul (« Préparation… », erreur) s'affiche en état d'attente ou d'erreur, pas sur la feuille ;
   l'impression ne part plus d'elle-même, elle se lance depuis l'aperçu.
   ========================================================================= */

const ID_STYLES = 'apercu-impression-styles';

// Icônes (tracés Lucide, comme le reste de l'application)
const ICONES = {
  document: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/>',
  imprimante: '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
  onglet: '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>',
  fermer: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  moins: '<line x1="5" y1="12" x2="19" y2="12"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  largeur: '<polyline points="18 8 22 12 18 16"/><polyline points="6 8 2 12 6 16"/><line x1="2" y1="12" x2="22" y2="12"/>',
  info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
  erreur: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
};
const icone = (nom, taille = 18) => `<svg xmlns="http://www.w3.org/2000/svg" width="${taille}" height="${taille}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONES[nom]}</svg>`;

const STYLES = `
.apercu-impression {
  position: fixed; inset: 0; z-index: 10000; display: flex; flex-direction: column;
  background: rgba(3, 7, 18, 0.72); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  font-family: var(--font-main, Inter, 'Segoe UI', sans-serif); color: var(--text-primary, #f8fafc);
  animation: apercu-fondu 0.18s ease-out;
}
.apercu-impression.apercu-sortie { animation: apercu-fondu-sortie 0.15s ease-in forwards; }
.apercu-impression [hidden] { display: none !important; }
.apercu-barre {
  display: flex; align-items: center; gap: 1rem; padding: 0.65rem 1.25rem;
  background: var(--bg-surface, #111827); border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
  box-shadow: 0 8px 24px -12px rgba(0, 0, 0, 0.5);
}
.apercu-entete { display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; }
.apercu-pastille {
  display: grid; place-items: center; flex: none; width: 40px; height: 40px; border-radius: var(--radius-lg, 10px);
  color: #fff; background: linear-gradient(135deg, var(--primary-500, #3b82f6), var(--primary-700, #1d4ed8));
  box-shadow: 0 6px 16px -6px var(--primary-glow, rgba(59,130,246,0.5));
}
.apercu-libelles { min-width: 0; }
.apercu-titre { font-weight: 700; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.apercu-sous-titre { font-size: 0.75rem; color: var(--text-muted, #94a3b8); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.apercu-zoom {
  display: flex; align-items: center; gap: 2px; padding: 3px; border-radius: var(--radius-md, 8px);
  background: var(--bg-surface-elevated, #1e293b); border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
}
.apercu-zoom-valeur {
  min-width: 3.6rem; height: 30px; border: none; background: transparent; color: inherit; cursor: pointer;
  font: inherit; font-size: 0.8rem; font-weight: 600; font-variant-numeric: tabular-nums; border-radius: var(--radius-sm, 6px);
}
.apercu-actions { display: flex; align-items: center; gap: 0.5rem; }
.apercu-separateur { width: 1px; height: 24px; margin: 0 0.25rem; background: var(--border-medium, rgba(255,255,255,0.14)); }
.apercu-bouton, .apercu-bouton-icone, .apercu-zoom-valeur { transition: background var(--transition-fast, 150ms), color var(--transition-fast, 150ms), opacity var(--transition-fast, 150ms), box-shadow var(--transition-fast, 150ms); }
.apercu-bouton {
  display: inline-flex; align-items: center; gap: 0.45rem; height: 36px; padding: 0 0.9rem; cursor: pointer;
  font: inherit; font-size: 0.85rem; font-weight: 600; color: var(--text-primary, #f8fafc);
  background: var(--bg-surface-elevated, #1e293b); border: 1px solid var(--border-medium, rgba(255,255,255,0.14)); border-radius: var(--radius-md, 8px);
}
.apercu-bouton:hover:not(:disabled) { background: var(--bg-surface-hover, #334155); }
.apercu-bouton-principal { color: #fff; border-color: transparent; background: var(--primary-600, #2563eb); box-shadow: 0 6px 16px -8px var(--primary-500, #3b82f6); }
.apercu-bouton-principal:hover:not(:disabled) { background: var(--primary-700, #1d4ed8); }
.apercu-bouton-icone {
  display: grid; place-items: center; width: 30px; height: 30px; padding: 0; cursor: pointer;
  color: var(--text-secondary, #b8c4d6); background: transparent; border: none; border-radius: var(--radius-sm, 6px);
}
.apercu-bouton-icone:hover:not(:disabled), .apercu-zoom-valeur:hover:not(:disabled) { background: var(--bg-surface-hover, #334155); color: var(--text-primary, #f8fafc); }
.apercu-fermer { width: 36px; height: 36px; }
.apercu-impression button:disabled { opacity: 0.4; cursor: not-allowed; }
.apercu-impression button:focus-visible { outline: 2px solid var(--border-focus, #3b82f6); outline-offset: 2px; }
.apercu-scene { flex: 1; overflow: auto; padding: 2rem 1.5rem 3rem; }
.apercu-support { position: relative; margin: 0 auto; }
.apercu-feuille {
  position: absolute; top: 0; left: 0; transform-origin: 0 0; box-sizing: border-box; padding: 10mm 8mm;
  background: #fff; border-radius: 3px;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.08), 0 24px 60px -12px rgba(0, 0, 0, 0.55), 0 8px 20px -8px rgba(0, 0, 0, 0.35);
  animation: apercu-monte 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.apercu-feuille iframe { display: block; width: 100%; border: none; background: #fff; }
.apercu-etat {
  min-height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem;
  text-align: center; animation: apercu-fondu 0.2s ease-out;
}
.apercu-etat-icone { display: grid; place-items: center; width: 64px; height: 64px; border-radius: 50%; background: var(--bg-surface, #111827); box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0,0,0,0.5)); color: var(--primary-500, #3b82f6); }
.apercu-impression[data-etat="erreur"] .apercu-etat-icone { color: var(--accent-rose, #f43f5e); }
.apercu-etat-texte { max-width: 28rem; margin: 0; font-size: 0.95rem; line-height: 1.5; color: #f1f5f9; }
.apercu-roue { width: 28px; height: 28px; border-radius: 50%; border: 3px solid var(--primary-glow, rgba(59,130,246,0.25)); border-top-color: var(--primary-500, #3b82f6); animation: apercu-tourne 0.8s linear infinite; }
@keyframes apercu-fondu { from { opacity: 0; } }
@keyframes apercu-fondu-sortie { to { opacity: 0; } }
@keyframes apercu-monte { from { opacity: 0; transform: translateY(14px) scale(var(--apercu-zoom, 1)); } }
@keyframes apercu-tourne { to { transform: rotate(360deg); } }
@media (max-width: 760px) {
  .apercu-barre { gap: 0.5rem; padding: 0.5rem 0.75rem; }
  .apercu-pastille, .apercu-zoom, .apercu-separateur, .apercu-bouton span { display: none; }
  .apercu-bouton { padding: 0 0.6rem; }
  .apercu-scene { padding: 1rem 0.75rem 2rem; }
}
@media (prefers-reduced-motion: reduce) {
  .apercu-impression, .apercu-feuille, .apercu-etat { animation: none; }
  .apercu-roue { animation-duration: 2s; }
}
`;

const injecterStyles = () => {
  if (document.getElementById(ID_STYLES)) return;
  const style = document.createElement('style');
  style.id = ID_STYLES;
  style.textContent = STYLES;
  document.head.appendChild(style);
};

// Feuilles A4 (mm) et niveaux de zoom proposés
const MM_EN_PX = 96 / 25.4;
const FORMATS = { portrait: { largeur: 210, hauteur: 297 }, paysage: { largeur: 297, hauteur: 210 } };
const MARGE_FEUILLE_MM = 10;
const ZOOMS = [0.5, 0.67, 0.75, 0.9, 1, 1.1, 1.25, 1.5, 1.75, 2];

// Message seul (« Préparation… », information, erreur en rouge) écrit par un gabarit à la place d'un document
const lireMessage = (html) => {
  if (!/^\s*<p\b[^>]*>[\s\S]*<\/p>\s*$/i.test(html)) return null;
  const texte = new DOMParser().parseFromString(html, 'text/html').body.textContent.trim();
  if (/(…|\.\.\.)$/.test(texte)) return { genre: 'attente', texte };
  return { genre: /#b91c1c/i.test(html) ? 'erreur' : 'info', texte };
};

// Les gabarits lancent l'impression à l'ouverture : dans l'aperçu, c'est l'utilisateur qui la lance
const sansImpressionAutomatique = (html) => html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, (s) => (/\.print\s*\(/.test(s) ? '' : s));

export const ouvrirApercuImpression = () => {
  // Un seul aperçu à la fois : une nouvelle impression remplace celle qui est affichée
  document.querySelectorAll('.apercu-impression').forEach((p) => p.dispatchEvent(new Event('apercu-fermer')));
  injecterStyles();

  const titreEcran = document.title;
  const debordementEcran = document.body.style.overflow;
  // Le reste de l'écran devient inerte (clavier, lecteurs d'écran) le temps de l'aperçu
  const rendusInertes = [...document.body.children].filter((el) => !el.inert);

  const panneau = document.createElement('div');
  panneau.className = 'apercu-impression';
  panneau.dataset.etat = 'attente';
  panneau.setAttribute('role', 'dialog');
  panneau.setAttribute('aria-modal', 'true');
  panneau.setAttribute('aria-label', 'Aperçu avant impression');
  panneau.innerHTML = `
    <header class="apercu-barre">
      <div class="apercu-entete">
        <span class="apercu-pastille">${icone('document', 20)}</span>
        <div class="apercu-libelles">
          <div class="apercu-titre">Aperçu avant impression</div>
          <div class="apercu-sous-titre">Préparation du document…</div>
        </div>
      </div>
      <div class="apercu-zoom" role="group" aria-label="Zoom">
        <button type="button" class="apercu-bouton-icone" data-action="zoom-moins" title="Réduire" aria-label="Réduire">${icone('moins')}</button>
        <button type="button" class="apercu-zoom-valeur" data-action="zoom-reel" title="Taille réelle (100 %)">100 %</button>
        <button type="button" class="apercu-bouton-icone" data-action="zoom-plus" title="Agrandir" aria-label="Agrandir">${icone('plus')}</button>
        <button type="button" class="apercu-bouton-icone" data-action="ajuster" title="Ajuster à la largeur de l'écran" aria-label="Ajuster à la largeur">${icone('largeur')}</button>
      </div>
      <div class="apercu-actions">
        <button type="button" class="apercu-bouton" data-action="onglet" title="Ouvrir le document dans un nouvel onglet du navigateur">${icone('onglet', 16)}<span>Nouvel onglet</span></button>
        <button type="button" class="apercu-bouton apercu-bouton-principal" data-action="imprimer" title="Imprimer ou enregistrer au format PDF (Ctrl+P)">${icone('imprimante', 16)}<span>Imprimer / PDF</span></button>
        <span class="apercu-separateur"></span>
        <button type="button" class="apercu-bouton-icone apercu-fermer" data-action="fermer" title="Fermer (Échap)" aria-label="Fermer l'aperçu">${icone('fermer', 20)}</button>
      </div>
    </header>
    <div class="apercu-scene">
      <div class="apercu-etat" role="status" aria-live="polite">
        <span class="apercu-etat-icone"><span class="apercu-roue"></span></span>
        <p class="apercu-etat-texte">Préparation du document…</p>
      </div>
      <div class="apercu-support" hidden><div class="apercu-feuille"><iframe title="Document à imprimer"></iframe></div></div>
    </div>`;

  const element = (selecteur) => panneau.querySelector(selecteur);
  const titre = element('.apercu-titre');
  const sousTitre = element('.apercu-sous-titre');
  const scene = element('.apercu-scene');
  const etat = element('.apercu-etat');
  const iconeEtat = element('.apercu-etat-icone');
  const texteEtat = element('.apercu-etat-texte');
  const support = element('.apercu-support');
  const feuille = element('.apercu-feuille');
  const cadre = element('iframe');
  const valeurZoom = element('.apercu-zoom-valeur');
  const actionsDocument = [...panneau.querySelectorAll('[data-action]:not([data-action="fermer"])')];

  let ferme = false;
  let source = '';
  let format = FORMATS.portrait;
  let zoom = 1;
  let zoomAutomatique = true;

  const activerActions = (actif) => actionsDocument.forEach((b) => { b.disabled = !actif; });

  // ------------------------------------------------------------------ zoom et taille de la feuille
  const zoomAjuste = () => {
    const disponible = scene.clientWidth - parseFloat(getComputedStyle(scene).paddingLeft) * 2;
    return Math.min(1, disponible / (format.largeur * MM_EN_PX));
  };
  const mettreEnPage = () => {
    if (ferme || support.hidden) return;
    const doc = cadre.contentDocument;
    if (doc?.documentElement) cadre.style.height = `${doc.documentElement.scrollHeight}px`;
    if (zoomAutomatique) zoom = zoomAjuste();
    feuille.style.transform = `scale(${zoom})`;
    feuille.style.setProperty('--apercu-zoom', zoom);
    support.style.width = `${feuille.offsetWidth * zoom}px`;
    support.style.height = `${feuille.offsetHeight * zoom}px`;
    valeurZoom.textContent = `${Math.round(zoom * 100)} %`;
  };
  const zoomer = (valeur) => {
    zoomAutomatique = valeur === 'ajuster';
    if (!zoomAutomatique) zoom = Math.min(ZOOMS[ZOOMS.length - 1], Math.max(ZOOMS[0], valeur));
    mettreEnPage();
  };
  const zoomSuivant = (sens) => {
    const suivant = sens > 0 ? ZOOMS.find((z) => z > zoom + 0.001) : [...ZOOMS].reverse().find((z) => z < zoom - 0.001);
    zoomer(suivant ?? zoom);
  };

  // ------------------------------------------------------------------ états
  const montrerEtat = ({ genre, texte }) => {
    panneau.dataset.etat = genre;
    support.hidden = true;
    etat.hidden = false;
    iconeEtat.innerHTML = genre === 'attente' ? '<span class="apercu-roue"></span>' : icone(genre, 28);
    texteEtat.textContent = texte;
    sousTitre.textContent = { attente: 'Préparation du document…', erreur: 'Document indisponible', info: 'Information' }[genre];
    activerActions(false);
  };

  const afficherDocument = (html) => {
    const message = lireMessage(html);
    if (message) {
      montrerEtat(message);
      return;
    }
    source = html;
    format = /size\s*:\s*A4\s+landscape/i.test(html) ? FORMATS.paysage : FORMATS.portrait;
    panneau.dataset.etat = 'document';
    etat.hidden = true;
    support.hidden = false;
    feuille.style.width = `${format.largeur}mm`;
    feuille.style.minHeight = `${format.hauteur}mm`;
    // Document court : la feuille entière, pour que les pieds de page fixes tombent en bas de page
    cadre.style.minHeight = `${format.hauteur - 2 * MARGE_FEUILLE_MM}mm`;
    cadre.style.height = '';
    const doc = cadre.contentDocument;
    doc.open();
    doc.write(sansImpressionAutomatique(html));
    doc.close();
    // Nom proposé par « Enregistrer au format PDF » : le navigateur reprend le titre de l'onglet
    const nom = doc.title || 'Document';
    titre.textContent = nom;
    document.title = nom;
    sousTitre.textContent = `Format A4 · ${format === FORMATS.paysage ? 'paysage' : 'portrait'}`;
    // Écrire un document efface les écouteurs du cadre : raccourcis remis à chaque document
    doc.addEventListener('keydown', surTouche, true);
    doc.fonts?.ready.then(mettreEnPage);
    activerActions(true);
    mettreEnPage();
    element('[data-action="imprimer"]').focus();
  };

  // ------------------------------------------------------------------ actions
  const imprimer = () => {
    if (ferme || panneau.dataset.etat !== 'document') return;
    cadre.contentWindow.focus();
    cadre.contentWindow.print();
  };

  // Ancien fonctionnement : le document dans un onglet à part (il s'y imprime à l'ouverture)
  const ouvrirOnglet = () => {
    if (!source) return;
    const onglet = window.open('', '_blank');
    if (!onglet) return;
    onglet.document.open();
    onglet.document.write(source);
    onglet.document.close();
    fermer();
  };

  function fermer() {
    if (ferme) return;
    ferme = true;
    document.removeEventListener('keydown', surTouche, true);
    window.removeEventListener('resize', mettreEnPage);
    rendusInertes.forEach((el) => { el.inert = false; });
    document.title = titreEcran;
    document.body.style.overflow = debordementEcran;
    panneau.classList.add('apercu-sortie');
    setTimeout(() => panneau.remove(), 150);
  }

  // Échap et Ctrl+P propres à l'aperçu (capture : une fenêtre modale ouverte dessous ne se ferme pas)
  function surTouche(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      fermer();
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'p') {
      e.preventDefault();
      e.stopPropagation();
      imprimer();
    }
  }

  const ACTIONS = {
    'zoom-moins': () => zoomSuivant(-1),
    'zoom-plus': () => zoomSuivant(1),
    'zoom-reel': () => zoomer(1),
    ajuster: () => zoomer('ajuster'),
    onglet: ouvrirOnglet,
    imprimer,
    fermer,
  };
  panneau.addEventListener('click', (e) => {
    const bouton = e.target.closest('[data-action]');
    if (bouton && !bouton.disabled) ACTIONS[bouton.dataset.action]();
  });
  panneau.addEventListener('apercu-fermer', fermer);
  // Images chargées (logos, QR) : hauteur de la feuille recalculée
  cadre.addEventListener('load', mettreEnPage);

  activerActions(false);
  document.body.appendChild(panneau);
  rendusInertes.forEach((el) => { el.inert = true; });
  document.body.style.overflow = 'hidden';
  document.addEventListener('keydown', surTouche, true);
  window.addEventListener('resize', mettreEnPage);
  element('[data-action="fermer"]').focus();

  // Ce que les gabarits écrivent : un message seul (attente, erreur) ou un document complet entre open() et close()
  let tampon = '';
  let enEcriture = false;
  const documentApercu = {
    open() { tampon = ''; enEcriture = true; },
    write(html) {
      if (ferme) return;
      if (enEcriture) {
        tampon += html;
        return;
      }
      const message = lireMessage(html);
      if (message) montrerEtat(message);
      else tampon += html;
    },
    close() {
      enEcriture = false;
      const html = tampon;
      tampon = '';
      if (!ferme && html) afficherDocument(html);
    },
  };

  return {
    document: documentApercu,
    get closed() { return ferme; },
    focus: () => cadre.contentWindow?.focus(),
    print: imprimer,
    close: fermer,
  };
};
