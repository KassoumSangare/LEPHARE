import { contractApi } from '../api/endpoints';
import { ouvrirApercuImpression } from './apercuImpression';
import { numberToFrenchWords } from './exportUtils';
import { logoCabinetEntete, nomCabinet, villeSignature } from './parametrage';

/* =========================================================================
   AVENANT IMPRIMÉ : RETRAIT, RÉSILIATION, CHANGEMENT D'IMMATRICULATION (production/avenants.py, 2026-11-19)
   L'avenant signé par le souscripteur et la compagnie matérialise le changement ; une résiliation à l'échéance
   n'a pas d'autre pièce. Montants négatifs = ristourne due au souscripteur.
   ========================================================================= */

const e = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const f = (v) => Math.round(Number(v) || 0).toLocaleString('fr-FR').replace(/[  ]/g, ' ');
const jma = (iso) => (iso ? String(iso).slice(0, 10).split('-').reverse().join('/') : '');
const veille = (iso) => {
  const d = new Date(`${String(iso).slice(0, 10)}T00:00:00`);
  d.setDate(d.getDate() - 1);
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
};

const TITRES = { RET: 'AVENANT DE RETRAIT', RES: 'AVENANT DE RÉSILIATION', CHI: 'AVENANT DE CHANGEMENT D’IMMATRICULATION' };

const STYLES = `
  .av { box-sizing: border-box; width: 100%; max-width: 210mm; min-height: 287mm; padding: 12mm 15mm; font-size: 10pt; line-height: 1.45; }
  .av-haut { display: flex; justify-content: space-between; align-items: flex-start; gap: 8mm; }
  .av-logo { height: 20mm; width: auto; }
  .av-ref { text-align: right; font-size: 9pt; }
  .av h1 { margin: 9mm 0 1mm; text-align: center; font-size: 15pt; letter-spacing: 0.04em; }
  .av-sous { text-align: center; margin: 0 0 7mm; font-size: 10pt; }
  .av table { width: 100%; border-collapse: collapse; }
  .av-infos td { padding: 1.4mm 2mm; border: 0.3mm solid #999; vertical-align: top; }
  .av-infos td.l { width: 38%; background: #f1f3f5; font-weight: bold; }
  .av h2 { margin: 7mm 0 2mm; font-size: 11pt; text-transform: uppercase; border-bottom: 0.4mm solid #111; padding-bottom: 1mm; }
  .av-texte { text-align: justify; margin: 0 0 3mm; }
  .av-objets th, .av-objets td { padding: 1.3mm 2mm; border: 0.3mm solid #999; }
  .av-objets th { background: #f1f3f5; text-align: left; font-size: 9pt; }
  .av-objets td.m, .av-montants td.m { text-align: right; white-space: nowrap; }
  .av-montants { width: 60% !important; margin-left: auto; }
  .av-montants td { padding: 1.3mm 2mm; border: 0.3mm solid #999; }
  .av-montants tr.total td { font-weight: bold; background: #f1f3f5; }
  .av-lettres { margin: 3mm 0 0; font-style: italic; }
  .av-fait { margin: 9mm 0 0; text-align: right; }
  .av-signatures { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6mm; margin-top: 6mm; text-align: center; font-weight: bold; font-size: 9pt; }
  .av-signatures div { min-height: 28mm; }
  .av-pied { margin-top: 8mm; font-size: 8pt; color: #444; text-align: center; }
`;

const texteAvenant = (d) => {
  const police = `la police n° <b>${e(d.NumeroPolice)}</b>${d.PoliceCompagnie && d.PoliceCompagnie !== 'RAS' ? ` (police compagnie ${e(d.PoliceCompagnie)})` : ''}`;
  if (d.Type === 'RES') {
    const echeance = d.Echeance && d.DateEffet > d.Echeance;
    return `Il est convenu que ${police} est résiliée ${echeance ? `à son échéance du <b>${jma(d.Echeance)}</b>` : `à compter du <b>${jma(d.DateEffet)}</b>, les garanties cessant le ${veille(d.DateEffet)} à minuit`}.`
      + (d.PrimeTtc < 0 ? ' La portion de prime afférente à la période restant à courir jusqu’à l’échéance est ristournée au souscripteur.'
        : ' La résiliation ne donne lieu à aucune ristourne.');
  }
  if (d.Type === 'CHI') {
    const o = d.Objets[0] || {};
    return `Il est convenu qu’à compter du <b>${jma(d.DateEffet)}</b>, le véhicule assuré par ${police}, précédemment immatriculé <b>${e(o.Ancienne)}</b>, `
      + `porte désormais l’immatriculation <b>${e(o.Matricule)}</b>. Toutes les autres clauses et conditions du contrat demeurent inchangées.`;
  }
  const pluriel = d.Objets.length > 1;
  return `Il est convenu qu’à compter du <b>${jma(d.DateEffet)}</b>, ${pluriel ? 'les risques désignés ci-après sont retirés' : 'le risque désigné ci-après est retiré'} des garanties de ${police}`
    + (d.PrimeTtc < 0 ? ', moyennant la ristourne de la prime correspondant à la période restant à courir jusqu’à l’échéance.' : ', sans ristourne de prime.')
    + ' Toutes les autres clauses et conditions du contrat demeurent inchangées.';
};

const corps = (d) => {
  const ristourne = d.PrimeTtc < 0;
  const objets = d.Type === 'RES' ? [] : d.Objets;
  return `<div class="av">
  <div class="av-haut">
    <img class="av-logo" src="${e(logoCabinetEntete())}" alt="${e(nomCabinet())}" onerror="this.style.display='none'" />
    <div class="av-ref">Avenant n° <b>${e(d.NumeroAvenant)}</b><br />Police n° <b>${e(d.NumeroPolice)}</b>${d.Quittance ? `<br />Quittance n° ${e(d.Quittance)}` : ''}</div>
  </div>
  <h1>${TITRES[d.Type]}</h1>
  <p class="av-sous">${e(d.Produit)} · ${e(d.Compagnie)}</p>
  <table class="av-infos">
    <tr><td class="l">Souscripteur</td><td>${e(d.Client)}${d.Adresse ? `<br />${e(d.Adresse)}` : ''}</td></tr>
    <tr><td class="l">Compagnie</td><td>${e(d.Compagnie)}</td></tr>
    <tr><td class="l">Date d’effet de l’avenant</td><td>${jma(d.DateEffet)}</td></tr>
    ${d.Echeance ? `<tr><td class="l">Échéance du contrat</td><td>${jma(d.Echeance)}</td></tr>` : ''}
    ${d.Motif ? `<tr><td class="l">Motif</td><td>${e(d.Motif)}</td></tr>` : ''}
  </table>
  <h2>Objet de l’avenant</h2>
  <p class="av-texte">${texteAvenant(d)}</p>
  ${objets.length ? `<table class="av-objets">
    <thead><tr><th>${d.Automobile ? 'Véhicule' : 'Risque'}</th>${d.Type === 'CHI' ? '<th>Ancienne immatriculation</th>' : ''}${ristourne ? '<th>Prime nette</th>' : ''}</tr></thead>
    <tbody>${objets.map((o) => `<tr><td>${e(o.Libelle)}</td>${d.Type === 'CHI' ? `<td>${e(o.Ancienne)}</td>` : ''}${ristourne ? `<td class="m">${f(o.PrimeNette)}</td>` : ''}</tr>`).join('')}</tbody>
  </table>` : ''}
  <h2>Décompte</h2>
  <table class="av-montants">
    <tr><td>Prime nette</td><td class="m">${f(d.PrimeNette)}</td></tr>
    ${d.Fga ? `<tr><td>Dont FGA</td><td class="m">${f(d.Fga)}</td></tr>` : ''}
    <tr><td>Accessoires</td><td class="m">${f(d.Accessoire)}</td></tr>
    <tr><td>Taxe</td><td class="m">${f(d.Taxe)}</td></tr>
    <tr class="total"><td>${ristourne ? 'Ristourne TTC' : 'Prime TTC'}</td><td class="m">${f(Math.abs(d.PrimeTtc))} FCFA</td></tr>
  </table>
  ${d.PrimeTtc ? `<p class="av-lettres">Arrêté ${ristourne ? 'la ristourne' : 'la prime'} à la somme de ${e(numberToFrenchWords(Math.round(Math.abs(d.PrimeTtc))))} francs CFA.</p>` : ''}
  <p class="av-fait">Fait à ${e(villeSignature())}, le ${jma(d.DateEmission)}.</p>
  <div class="av-signatures"><div>LE SOUSCRIPTEUR</div><div>LE COURTIER<br />${e(nomCabinet())}</div><div>LA COMPAGNIE</div></div>
  <p class="av-pied">Le présent avenant fait partie intégrante de la police n° ${e(d.NumeroPolice)}.</p>
</div>`;
};

/** Avenant de retrait, de résiliation ou de changement d'immatriculation d'un contrat (aperçu dans l'application). */
export const imprimerAvenantPolice = async (idContrat) => {
  const fenetre = ouvrirApercuImpression();
  if (!fenetre) return;
  const ecrire = (contenu, titre = 'Avenant') => {
    fenetre.document.open();
    fenetre.document.write(`<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8" /><title>${e(titre)}</title>
<style>@page { size: A4 portrait; margin: 0; } html, body { margin: 0; padding: 0; background: #fff; }
body { font-family: Arial, Helvetica, sans-serif; color: #111; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
${STYLES}</style></head><body>${contenu}</body></html>`);
    fenetre.document.close();
  };
  ecrire('<p>Préparation de l’avenant…</p>');
  try {
    const d = await contractApi.documentAvenant(idContrat);
    ecrire(corps(d), `${TITRES[d.Type]} ${d.NumeroPolice}`);
  } catch (err) {
    ecrire(`<p style="color:#b91c1c">${e(err?.response?.data?.error || 'Avenant indisponible pour le moment.')}</p>`);
  }
};

export const estAvenantPolice = (code) => Object.prototype.hasOwnProperty.call(TITRES, String(code || '').toUpperCase());
