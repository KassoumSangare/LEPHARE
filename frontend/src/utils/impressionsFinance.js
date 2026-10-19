import { ouvrirApercuImpression } from './apercuImpression';
import { logoCabinetEntete, logoCabinetPied, nomCabinet, parametre } from './parametrage';

/* =========================================================================
   DOCUMENTS D'OREOLE AUX COMPAGNIES (dossier FInance_LEPHARE, 2026-10-19)
   - Bordereau de reversement de prime / de réclamation de commission : identique aux bordereaux 2117 (chèque
     d'OREOLE) et 1175 / 2088 de JCW (chèques du client à l'ordre de NSIA-CI, « Direct ») ; primes soldées et primes
     en arriéré en deux blocs, avec le reste dû.
   - Courrier de règlement de prime : modèle Word du courrier KOUMOUE et courriers JCW (texte composé par le serveur,
     production/views_bordereaux.py).
   - Courrier de réclamation de commission et son bordereau récapitulatif (réclamation RC-…).
   ========================================================================= */

const e = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
// Montants des documents d'OREOLE : 1 073 824 (espace simple, imprimée partout)
const f = (v) => Math.round(Number(v) || 0).toLocaleString('fr-FR').replace(/[  ]/g, ' ');
const jma = (iso) => (iso ? String(iso).slice(0, 10).split('-').reverse().join('/') : '');
const taux = (t) => `${Number(t || 0).toLocaleString('fr-FR', { maximumFractionDigits: 2 })}%`;
const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
const dateLettres = (iso) => {
  const [a, m, j] = String(iso || '').slice(0, 10).split('-').map(Number);
  return a ? `${String(j).padStart(2, '0')} ${MOIS[m - 1]} ${a}` : '';
};

const ecrire = (titre, styles, corps, paysage = false) => {
  const html = `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8" /><title>${e(titre)}</title>
<style>@page { size: A4 ${paysage ? 'landscape' : 'portrait'}; margin: 0; }
html, body { margin: 0; padding: 0; background: #fff; }
body { font-family: Arial, Helvetica, sans-serif; color: #111; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
${styles}</style></head><body>${corps}</body></html>`;
  const fenetre = ouvrirApercuImpression();
  if (fenetre) {
    fenetre.document.open();
    fenetre.document.write(html);
    fenetre.document.close();
  }
};

/* ------------------------------------------------------------------ bordereau */
const STYLES_BORDEREAU = `
  .brd { box-sizing: border-box; width: 100%; max-width: 297mm; min-height: 189mm; padding: 6mm 7mm 6mm; font-family: Arial, Helvetica, sans-serif; font-size: 8.4pt; }
  .brd-haut { display: grid; grid-template-columns: 62mm 1fr 62mm; align-items: start; }
  .brd-logo { height: 21mm; width: auto; margin: 2mm 0 0 4mm; }
  .brd-titre { justify-self: center; margin-top: 4mm; border: 1.3pt solid #111; padding: 2.2mm 22mm; font-weight: 700; font-size: 10pt; white-space: nowrap; }
  .brd-cie { text-align: center; font-weight: 700; font-size: 10pt; margin: 4mm 0 1mm; }
  .brd-infos { display: grid; grid-template-columns: 40mm 30mm 1fr; row-gap: 4mm; margin: 0 0 4mm 2mm; font-size: 9pt; align-items: center; }
  .brd-infos b { font-size: 9.5pt; }
  .brd-du { font-weight: 700; padding-left: 50mm; }
  table.brd-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
  .brd-table th { border: 0.9pt solid #111; padding: 2.4mm 0.6mm; font-weight: 700; font-size: 7.9pt; text-align: center; vertical-align: middle; }
  .brd-table td { border: 0.9pt solid #111; padding: 2.6mm 0.8mm; text-align: center; vertical-align: middle; line-height: 1.3; }
  .brd-table td.client { font-size: 8.6pt; }
  .brd-table .petit { display: block; font-size: 7pt; font-weight: 400; margin-top: 0.8mm; }
  .brd-table tr.bloc td { font-weight: 700; text-align: left; padding: 1.6mm 2mm; background: #f1f1f1; letter-spacing: 0.02em; }
  .brd-table tr.sous-total td { font-weight: 700; background: #fafafa; }
  .brd-table tr.total td { font-weight: 700; padding: 3.4mm 0.8mm; }
  .brd-table tr.total td.vide { border: none; }
  .brd-signatures { display: flex; justify-content: space-between; margin: 9mm 14mm 0 2mm; font-weight: 700; text-decoration: underline; font-size: 9pt; }
  .brd-signatures span:last-child { margin-right: 22mm; }
  .brd-cheques { margin: 22mm 0 0 34mm; font-size: 8.4pt; }
  .brd-cheques div { margin-top: 1.2mm; }
  .brd-cheques b { font-size: 9.5pt; margin-left: 4mm; }
`;

const COLONNES_BORDEREAU = [
  ['Nom du client', 9], ['Assurance', 7.4], ['N°Police', 8.4], ['Avt', 3.4], ['Effet', 6], ['Expiration', 6.4],
  ['Prime HT', 6.2], ['Prime TTC', 6.2], ['Encaissement', 7.6], ['Acc. Courtier', 5.4], ['Taux com.(%)', 5],
  ['Commission', 7], ['Frais gestion', 5], ['Com. Déduite', 5], ['Acc. déduits', 5], ['Montant Reversé', 6.6],
];

const celluleReverse = (b, montant) => (b.Direct ? 'Direct' : f(montant));

const ligneBordereau = (b, l) => `<tr>
    <td class="client">${e(l.Client)}${l.Soldee ? '' : `<span class="petit">Reste dû : ${f(l.ResteDu)}</span>`}</td>
    <td>${e(l.Assurance)}</td><td>${e(l.PoliceCompagnie || l.NumeroPolice)}</td><td>${e(l.Avenant)}</td>
    <td>${jma(l.DateEffet)}</td><td>${jma(l.DateExpiration)}</td>
    <td>${f(l.PrimeHT)}</td><td>${f(l.PrimeTtc)}</td><td>${f(l.Encaissement)}</td><td>${f(l.AccCourtier)}</td>
    <td>${taux(l.Taux)}</td><td>${f(l.Commission)}</td><td>0</td><td>0</td><td>0</td><td>${celluleReverse(b, l.MontantReverse)}</td>
  </tr>`;

// Ligne TOTAL du modèle : cellules vides sans cadre sous les quatre premières colonnes, « TOTAL » sous Effet /
// Expiration ; sous-total d'un bloc : libellé sur les six premières colonnes
const ligneTotal = (b, libelle, t, classe = 'total') => {
  const debut = classe === 'total'
    ? `<td class="vide"></td><td class="vide"></td><td class="vide"></td><td class="vide"></td><td colspan="2">${e(libelle)}</td>`
    : `<td colspan="6" style="text-align:left;padding-left:2mm">${e(libelle)}</td>`;
  return `<tr class="${classe}">${debut}
    <td>${f(t.PrimeHT)}</td><td>${f(t.PrimeTtc)}</td><td>${f(t.Encaissement)}</td><td>${f(t.AccCourtier)}</td><td>0</td>
    <td>${f(t.Commission)}</td><td>0</td><td>0</td><td>0</td><td>${celluleReverse(b, t.MontantReverse)}</td>
  </tr>`;
};

export const construireBordereau = (b) => {
  const blocs = b.Blocs || [];
  // Primes soldées et primes en arriéré dissociées (demande du 2026-10-19) ; un bordereau tout soldé garde la
  // présentation d'origine
  const dissocie = blocs.some((bloc) => !bloc.Soldees);
  const corps = dissocie
    ? blocs.map((bloc) => `<tr class="bloc"><td colspan="16">${e(bloc.Titre)}${bloc.Soldees ? '' : ` — reste dû par les clients : ${f(bloc.Totaux.ResteDu)} F`}</td></tr>
        ${bloc.Lignes.map((l) => ligneBordereau(b, l)).join('')}
        ${blocs.length > 1 ? ligneTotal(b, `Sous-total ${bloc.Soldees ? 'primes soldées' : 'primes en arriéré'}`, bloc.Totaux, 'sous-total') : ''}`).join('')
    : (b.Lignes || []).map((l) => ligneBordereau(b, l)).join('');
  const cheques = (b.Cheques || []).map((c) => `<div>CHÈQUE N° <b>${e(c.Numero)}</b>${c.Banque ? ` &nbsp; ${e(c.Banque)}` : ''}${c.Date ? ` du ${jma(c.Date)}` : ''} de FCFA ${f(c.Montant)}</div>`).join('');
  return `<div class="brd">
    <div class="brd-haut">
      <img class="brd-logo" src="${e(logoCabinetEntete())}" alt="${e(nomCabinet())}" />
      <div class="brd-titre">${e(b.Titre)}</div><div></div>
    </div>
    <div class="brd-cie">${e(b.NomBordereau || b.Compagnie)}</div>
    <div class="brd-infos">
      <span>Bordereau N°</span><b>${b.Numero ? f(b.Numero) : e(b.NumeroReversement)}</b><span></span>
      <span>Montant à reverser</span><b>${f(b.MontantAReverser)}</b><span class="brd-du">du &nbsp;${jma(b.DateBordereau)}</span>
    </div>
    <table class="brd-table">
      <colgroup>${COLONNES_BORDEREAU.map(([, l]) => `<col style="width:${l}%" />`).join('')}</colgroup>
      <tr>${COLONNES_BORDEREAU.map(([t]) => `<th>${e(t)}</th>`).join('')}</tr>
      ${corps}
      ${ligneTotal(b, 'TOTAL', b.Totaux || {})}
    </table>
    <div class="brd-signatures"><span>POUR ${e(nomCabinet().toUpperCase())}</span><span>POUR ${e(b.NomBordereau || b.Compagnie)}</span></div>
    ${cheques ? `<div class="brd-cheques">${cheques}</div>` : ''}
  </div>`;
};

export const imprimerBordereau = (b) => ecrire(`Bordereau ${b.Numero || b.NumeroReversement}`, STYLES_BORDEREAU, construireBordereau(b), true);

/* ------------------------------------------------------------------ courriers */
const STYLES_COURRIER = `
  .crr { position: relative; box-sizing: border-box; width: 100%; max-width: 210mm; min-height: 276mm; padding: 4mm 12mm 2mm 18mm; display: flex; flex-direction: column;
    font-family: Arial, Helvetica, sans-serif; font-size: 11pt; line-height: 1.35; }
  .crr-logo { height: 17mm; width: auto; align-self: flex-start; }
  .crr-dest { margin: 6mm 0 0 52%; white-space: nowrap; }
  .crr-dest .lieu { margin-bottom: 7mm; }
  .crr-dest .nom { font-weight: 700; font-size: 15pt; margin-bottom: 4mm; }
  .crr-dest .service { font-weight: 700; margin-bottom: 4mm; }
  .crr-dest .ville { font-weight: 700; text-decoration: underline; margin-bottom: 1.5mm; }
  .crr-dest .attention { font-weight: 700; text-decoration: underline; }
  .crr-objet { display: grid; grid-template-columns: 22mm 6mm 1fr; margin: 13mm 0 7mm; }
  .crr-objet .titre { font-weight: 400; }
  .crr-objet b { font-weight: 700; }
  .crr-corps p { margin: 0 0 4.5mm; text-align: justify; }
  .crr-corps b.ref { text-decoration: underline; }
  .crr-pj { margin: 0 0 4.5mm 9mm; padding: 0; list-style: none; }
  .crr-pj li { margin-bottom: 2.4mm; font-weight: 700; }
  .crr-pj li::before { content: '-'; display: inline-block; width: 9mm; margin-left: -9mm; font-weight: 400; }
  .crr-signature { margin: 9mm 0 0 55%; text-align: center; width: 72mm; }
  .crr-signature .pour { text-decoration: underline; font-variant: small-caps; font-size: 12pt; }
  .crr-signature .fonction { margin-top: 5mm; }
  .crr-signature .nom { margin-top: 20mm; }
  .crr-marque { position: absolute; left: 1mm; bottom: 80mm; writing-mode: vertical-rl; transform: rotate(180deg); font-size: 8pt; font-weight: 700; white-space: nowrap; }
  .crr-pied { margin-top: auto; padding-top: 10mm; display: flex; gap: 4mm; align-items: flex-end; }
  .crr-pied img { height: 10mm; width: auto; flex-shrink: 0; }
  .crr-pied div { font-size: 5.8pt; line-height: 1.4; font-weight: 700; white-space: pre-line; }
`;

// Référence du chèque soulignée dans le texte, comme sur les courriers JCW
const mettreEnValeur = (texte, references) => {
  let html = e(texte);
  references.filter(Boolean).forEach((ref) => {
    const sansArticle = ref.replace(/^(le |la |l'|notre |les )/, '');
    html = html.split(e(sansArticle)).join(`<b class="ref">${e(sansArticle)}</b>`);
  });
  return html;
};

const piedCourrier = () => {
  const mentions = String(parametre('documents.mentions_legales', '') || '').trim();
  const marque = String(parametre('documents.mention_marque', '') || '').trim();
  return `${marque ? `<div class="crr-marque">${e(marque)}</div>` : ''}
    <div class="crr-pied"><img src="${e(logoCabinetPied())}" alt="" />${mentions ? `<div>${e(mentions)}</div>` : ''}</div>`;
};

const signatureCourrier = (c) => `<div class="crr-signature">
    <div class="pour">Pour ${e(nomCabinet())}</div>
    <div class="fonction">${e(c.Fonction)}</div>
    <div class="nom">${e(c.Signataire)}</div>
  </div>`;

const enteteCourrier = (c) => `<img class="crr-logo" src="${e(logoCabinetEntete())}" alt="${e(nomCabinet())}" />
    <div class="crr-dest">
      <div class="lieu">${e(c.Lieu)}</div>
      <div class="nom">${e(c.Destinataire)}</div>
      ${c.Service ? `<div class="service">${e(c.Service)}</div>` : ''}
      ${c.Ville ? `<div class="ville">${e(c.Ville)}</div>` : ''}
      ${c.AttentionDe ? `<div class="attention">${e(c.AttentionDe)}</div>` : ''}
    </div>`;

export const construireCourrier = (c, references = []) => `<div class="crr">
    ${enteteCourrier(c)}
    <div class="crr-objet">
      <span class="titre">OBJET</span><span>:</span>
      <div>${e(c.Objet)}${c.Branche ? `<br/><b>${e(c.Branche)}</b>` : ''}${c.Periode ? `<br/>${e(c.Periode)}` : ''}${c.PourCompte ? `<br/>${e(c.PourCompte.replace(/^(P\/C )(.*)$/, '$1'))}<b>${e(c.PourCompte.replace(/^P\/C /, ''))}</b>` : ''}</div>
    </div>
    <div class="crr-corps">
      <p>${e(c.Appellation)}</p>
      ${(c.Paragraphes || []).map((p) => `<p>${mettreEnValeur(p, references)}</p>`).join('')}
      <p>Nous joignons également à la présente :</p>
      <ul class="crr-pj">${(c.PiecesJointes || []).map((pj) => `<li>${e(pj)}</li>`).join('')}</ul>
      <p>Nous vous souhaitons bonne réception de la présente.</p>
      <p>${e(c.Salutation)}</p>
      <p>PJ : Ci-dessus citées.</p>
    </div>
    ${signatureCourrier(c)}
    ${piedCourrier()}
  </div>`;

export const imprimerCourrier = (b) => ecrire(
  `Courrier ${b.NomBordereau || b.Compagnie} ${b.Numero || ''}`.trim(),
  STYLES_COURRIER,
  construireCourrier(b.Courrier, (b.Cheques || []).map((x) => x.TexteCourrier)),
);

/* ------------------------------------------------------------------ réclamation de commission */
/**
 * Courrier de réclamation de commission (bordereau récapitulatif RC-… de l'écran Commissions) : même en-tête et
 * même signature que les courriers de règlement ; reglages = réglages « Reversements » de la compagnie.
 */
export const imprimerCourrierReclamation = (rc, reglages = {}) => {
  const ville = String(parametre('documents.ville_signature', 'Abidjan') || 'Abidjan').toUpperCase();
  const appellation = reglages.Appellation || 'Monsieur';
  const lignes = rc.Lignes || [];
  const clients = [...new Set(lignes.map((l) => l.Client))];
  const c = {
    Lieu: `${ville}, le ${dateLettres(rc.DateEmission)}`,
    Destinataire: reglages.Destinataire || rc.Compagnie,
    Service: reglages.Service || '',
    Ville: reglages.Ville || 'ABIDJAN',
    AttentionDe: reglages.AttentionDe ? `A l'attention de ${reglages.AttentionDe}` : '',
    Objet: 'RECLAMATION DE COMMISSIONS',
    Branche: `Bordereau récapitulatif N° ${rc.Reference}`,
    Periode: `Période du ${jma(rc.PeriodeDebut)} au ${jma(rc.PeriodeFin)}`,
    PourCompte: clients.length === 1 ? `P/C ${clients[0]}` : 'P/C ASSURES DIVERS',
    Appellation: `${appellation},`,
    Paragraphes: [
      `Nous vous prions de bien vouloir trouver ci-joint le bordereau récapitulatif des primes reversées sur la période du ${jma(rc.PeriodeDebut)} au ${jma(rc.PeriodeFin)}, `
      + `soit ${lignes.length} quittance${lignes.length > 1 ? 's' : ''} pour un montant de FCFA ${f(rc.MontantPrimes)}.`,
      `Au titre de ces affaires, nos commissions s'élèvent à FCFA ${f(rc.MontantCommissions)}${rc.MontantPaye ? `, dont FCFA ${f(rc.MontantPaye)} déjà réglés, soit un reste dû de FCFA ${f(rc.Reste)}` : ''}. `
      + 'Nous vous saurions gré de bien vouloir procéder à leur règlement par chèque ou par virement.',
    ],
    PiecesJointes: ['le bordereau récapitulatif de réclamation de commission.'],
    Salutation: `Veuillez agréer, ${appellation}, nos distinguées salutations.`,
    Signataire: String(parametre('finance.courrier_signataire', 'Yvette DA') || ''),
    Fonction: String(parametre('finance.courrier_fonction', 'LE DIRECTEUR GENERAL') || ''),
  };
  ecrire(`Reclamation commissions ${rc.Reference}`, STYLES_COURRIER, construireCourrier(c, [`FCFA ${f(rc.Reste || rc.MontantCommissions)}`]));
};

const STYLES_RECAP = `${STYLES_BORDEREAU}
  .brd-table td.g { text-align: left; padding-left: 1.5mm; }
`;

/** Bordereau récapitulatif joint au courrier de réclamation : une ligne par quittance réclamée. */
export const imprimerRecapitulatifReclamation = (rc, reglages = {}) => {
  const lignes = rc.Lignes || [];
  const somme = (cle) => lignes.reduce((t, l) => t + (Number(l[cle]) || 0), 0);
  const colonnes = [['Nom du client', 11], ['Assurance', 8], ['N°Police', 9], ['Bordereau', 5.5], ['Date', 6], ['Prime HT', 7],
    ['Prime TTC', 7], ['Montant reversé', 7], ['Acc. Courtier', 6], ['Taux com.(%)', 5], ['Commission', 7], ['À percevoir', 7.2],
    ['Déjà réglé', 6.6], ['Reste dû', 7]];
  const nom = reglages.NomBordereau || rc.Compagnie;
  const corps = `<div class="brd">
    <div class="brd-haut">
      <img class="brd-logo" src="${e(logoCabinetEntete())}" alt="${e(nomCabinet())}" />
      <div class="brd-titre">BORDEREAU RECAPITULATIF DE RECLAMATION DE COMMISSION</div><div></div>
    </div>
    <div class="brd-cie">${e(nom)}</div>
    <div class="brd-infos">
      <span>Bordereau N°</span><b>${e(rc.Reference)}</b><span class="brd-du">du &nbsp;${jma(rc.DateEmission)}</span>
      <span>Commission réclamée</span><b>${f(rc.Reste || rc.MontantCommissions)}</b><span class="brd-du">période du ${jma(rc.PeriodeDebut)} au ${jma(rc.PeriodeFin)}</span>
    </div>
    <table class="brd-table">
      <colgroup>${colonnes.map(([, l]) => `<col style="width:${l}%" />`).join('')}</colgroup>
      <tr>${colonnes.map(([t]) => `<th>${e(t)}</th>`).join('')}</tr>
      ${lignes.map((l) => `<tr>
        <td class="g">${e(l.Client)}</td><td>${e(l.Branche)}</td><td>${e(l.PoliceCompagnie || l.NumeroPolice)}</td>
        <td>${e(l.NumeroBordereau || l.NumeroReversement)}</td><td>${jma(l.DateBordereau || l.DateReversement)}</td>
        <td>${f(l.PrimeHT)}</td><td>${f(l.PrimeTtc)}</td><td>${f(l.MontantReverse)}</td><td>${f(l.AccCourtier)}</td><td>${taux(l.Taux)}</td>
        <td>${f(l.CommissionHT)}</td><td>${f(l.CommissionDue)}</td><td>${f(l.CommissionPayee)}</td><td><b>${f(l.Reste)}</b></td>
      </tr>`).join('')}
      <tr class="total"><td class="vide"></td><td class="vide"></td><td class="vide"></td><td colspan="2">TOTAL</td>
        <td>${f(somme('PrimeHT'))}</td><td>${f(somme('PrimeTtc'))}</td><td>${f(somme('MontantReverse'))}</td><td>${f(somme('AccCourtier'))}</td><td></td>
        <td>${f(somme('CommissionHT'))}</td><td>${f(somme('CommissionDue'))}</td><td>${f(somme('CommissionPayee'))}</td><td>${f(somme('Reste'))}</td></tr>
    </table>
    <div class="brd-signatures"><span>POUR ${e(nomCabinet().toUpperCase())}</span><span>POUR ${e(nom)}</span></div>
  </div>`;
  ecrire(`Recapitulatif ${rc.Reference}`, STYLES_RECAP, corps, true);
};
