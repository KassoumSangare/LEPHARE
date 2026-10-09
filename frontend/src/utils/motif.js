/**
 * Boîte de saisie du motif exigé par le serveur pour une opération sensible (réponse 428
 * « motif_requis » de la garde centrale) : confirmation explicite + justification, rejouée ensuite
 * avec l'en-tête X-Motif. Construite en DOM simple pour être utilisable depuis apiClient (hors React).
 * Renvoie le motif saisi, ou null si l'utilisateur annule.
 */
const LONGUEUR_MIN = 5;
let enCours = null;

export const demanderMotif = (libelleOperation) => {
  if (enCours) return enCours;
  enCours = new Promise((resolve) => {
    const fond = document.createElement('div');
    fond.setAttribute('role', 'dialog');
    fond.setAttribute('aria-modal', 'true');
    fond.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(15,23,42,0.55);display:flex;align-items:center;justify-content:center;padding:16px;';
    const boite = document.createElement('div');
    boite.style.cssText = 'width:100%;max-width:480px;background:var(--bg-surface,#fff);color:var(--text-primary,#0f172a);border:1px solid var(--border-subtle,#e2e8f0);border-radius:14px;padding:20px 22px;box-shadow:0 20px 40px -12px rgba(0,0,0,0.35);font-family:inherit;';
    const titre = document.createElement('h2');
    titre.textContent = 'Confirmer l\'opération';
    titre.style.cssText = 'margin:0 0 6px;font-size:1.05rem;font-weight:800;';
    const texte = document.createElement('p');
    texte.textContent = `« ${libelleOperation || 'Opération sensible'} » est une opération sensible : indiquez le motif. Il sera enregistré au journal d'audit avec votre nom, la date et les valeurs avant / après.`;
    texte.style.cssText = 'margin:0 0 12px;font-size:0.85rem;color:var(--text-secondary,#475569);line-height:1.45;';
    const zone = document.createElement('textarea');
    zone.rows = 3;
    zone.maxLength = 1000;
    zone.placeholder = 'Motif de l\'opération…';
    zone.className = 'form-control';
    zone.style.cssText = 'width:100%;resize:vertical;font-size:0.9rem;';
    const aide = document.createElement('div');
    aide.style.cssText = 'font-size:0.75rem;color:var(--accent-rose,#e11d48);min-height:1.1em;margin-top:4px;';
    const actions = document.createElement('div');
    actions.style.cssText = 'display:flex;justify-content:flex-end;gap:8px;margin-top:14px;';
    const annuler = document.createElement('button');
    annuler.type = 'button';
    annuler.className = 'btn btn-secondary';
    annuler.textContent = 'Annuler';
    const valider = document.createElement('button');
    valider.type = 'button';
    valider.className = 'btn btn-primary';
    valider.textContent = 'Confirmer';
    actions.append(annuler, valider);
    boite.append(titre, texte, zone, aide, actions);
    fond.append(boite);
    document.body.append(fond);
    zone.focus();

    const fermer = (valeur) => {
      fond.remove();
      document.removeEventListener('keydown', clavier);
      enCours = null;
      resolve(valeur);
    };
    const confirmer = () => {
      const motif = zone.value.trim();
      if (motif.length < LONGUEUR_MIN) {
        aide.textContent = `Motif trop court (${LONGUEUR_MIN} caractères au moins).`;
        zone.focus();
        return;
      }
      fermer(motif);
    };
    const clavier = (e) => {
      if (e.key === 'Escape') fermer(null);
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) confirmer();
    };
    annuler.addEventListener('click', () => fermer(null));
    valider.addEventListener('click', confirmer);
    document.addEventListener('keydown', clavier);
  });
  return enCours;
};
