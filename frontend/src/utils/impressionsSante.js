/* =========================================================================
   SANTÉ MINENE : Conditions Particulières, barème, liste des assurés et liste des ayants droit.
   Modèles OREOLE (Desktop\_OREOLE ASSURANCE\SANTE : cp_MINENE.pdf, BAREME_70-80.pdf) et gabarits
   URANUS (scenes/Products/Documents/Sante : CPMinene, BaremeMinene, AffiliesList, AyantsDroitsList).
   Données : quittance de la proposition ou du contrat, saisie Santé du devis (couvertures,
   adhérents, affiliés) et, pour un contrat, ayants droit de l'IA MINENE rattachée à la police.
   ========================================================================= */
import { impressionSanteApi } from '../api/endpoints';
import { logoCabinetEntete, logoCabinetPied, parametre } from './parametrage';

// Formules 80 %-80 % (offre commerciale 153) ; les autres formules MINENE sont en 70 %-80 %
const FORMULES_80_80 = [175, 176, 181];
const TARIFS_MINENE = [87, 102, 153];

const MENTIONS_LEGALES = "SARL Unipersonnelle au capital de 5 000 000 FCFA I C.B : SGCI : CI008 01111 011157481298 32 I C.C : 1005723 Y I RCCM : CI-ABJ-01-2009-B13-06768 Centre des impôts de Cocody Contrat R C N°1186583100012N I Siège social : Cocody cité des arts, Bd Latrille, face SODEMI, Imm. « LES 7 COLONNES » BP : 27 B.P 112 Abj 27 Agrément N° 141/MEF/DGTCP/DA du 24 MARS 2010 Tél : +225 27 22 48 76 86 / + 225 27 22 48 73 49 / +225 27 22 48 71 24 / +225 27 22 22 13 57 Cel : +2250102938218 Site web : oreoleassurances-ci.com";

export const estDevisSante = (quote) => /sant/i.test(String(quote?.branche || quote?.produit || ''));

const echapper = (x) => String(x ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const texte = (x) => echapper(String(x ?? '').trim());
const montant = (x) => Math.round(Number(x) || 0).toLocaleString('fr-FR').replace(/[  ]/g, ' ');
const date = (x) => {
  const m = String(x || '').match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : '';
};
const annee = (x) => Number(String(x || '').slice(0, 4)) || new Date().getFullYear();

// Quittance reconstituée depuis la saisie du devis quand fn_quittance_proposition ne renvoie rien
// (devis 24697 par exemple)
const quittanceDepuisSaisie = (devis) => {
  if (!devis) return {};
  const jours = devis.dateeffet && devis.dateexpiration
    ? Math.round((new Date(devis.dateexpiration) - new Date(devis.dateeffet)) / 86400000) : 0;
  return {
    IdDevis: devis.iddevis, NumeroDevis: devis.numerodevis, RaisonSociale: devis.compagnie, LibelleIntermediaire: 'OREOLE ASSURANCES',
    NomClient: devis.client_nom, NomAssure: devis.client_nom, TypeAssure: 'Personne Physique',
    DateEffet: devis.dateeffet, DateExpiration: devis.dateexpiration, Duree: jours,
    PrimeNette: devis.primenette, PrimeNetteHorsFga: devis.primenette, Accessoire: devis.accessoire,
    TaxeEnregistrement: devis.taxe, FraisGestion: 0, PrimeTtc: devis.primettc,
  };
};

/** Données d'impression d'un devis ({ iddevis }) ou d'un contrat ({ idcontrat }) Santé. */
const charger = async (ids) => {
  const d = await impressionSanteApi.get(ids);
  if (!Object.keys(d.quittance || {}).length) d.quittance = quittanceDepuisSaisie(d.saisie?.devis);
  const detail = d.saisie?.detail || {};
  const filiales = d.saisie?.filiales || [];
  const adherents = d.saisie?.adherents || [];
  const formuleFiliale = Object.fromEntries(filiales.map((f) => [Number(f.idfiliale), f]));
  // Formule de chaque famille : celle de sa couverture, à défaut celle du devis
  const formuleAdherent = Object.fromEntries(adherents.map((a) => {
    const f = formuleFiliale[Number(a.idfiliale)];
    return [Number(a.idadherent), { id: Number(f?.idoffresante || detail.idoffre) || 0, libelle: f?.libelle_offre || detail.libelle_offre || '' }];
  }));
  const formules = [...new Set(Object.values(formuleAdherent).map((f) => f.id).filter(Boolean))];
  if (!formules.length && detail.idoffre) formules.push(Number(detail.idoffre));
  const minene = TARIFS_MINENE.includes(Number(detail.idtarif)) || String(detail.codecategorie || '') === '123'
    || /MINENE/i.test(`${detail.libelle_tarif || ''} ${d.quittance?.LibelleCategorie || ''}`);
  return {
    ...d,
    detail,
    formuleAdherent,
    minene,
    quatreVingt: formules.length > 0 && formules.every((f) => FORMULES_80_80.includes(f)),
    // Option imprimée : la formule si elle est unique, sinon « VOIR LISTE » (liste des assurés en annexe)
    option: formules.length > 1 ? 'VOIR LISTE' : (d.quittance?.LibelleOffre || detail.libelle_offre || ''),
  };
};

const STYLES = `
  @page { size: A4; margin: 10mm 14mm 8mm; }
  * { box-sizing: border-box; }
  body { font-family: 'Arial Narrow', Arial, sans-serif; font-size: 9.5pt; color: #111; margin: 0; }
  /* Chaque section est un tableau : l'en-tête (logo) et l'espace du pied se répètent sur chaque page
     imprimée, le pied (mentions légales) est fixé en bas de chaque page */
  .feuille { width: 100%; border-collapse: collapse; page-break-after: always; }
  .feuille:last-of-type { page-break-after: auto; }
  .feuille > thead td, .feuille > tfoot td, .feuille > tbody > tr > td { padding: 0; border: none; }
  .logo { height: 46px; margin-bottom: 12px; }
  .espace-pied { height: 17mm; }
  .pied { position: fixed; bottom: 0; left: 0; right: 0; display: flex; gap: 10px; align-items: center; font-size: 6.2pt; color: #333; }
  .pied img { height: 24px; }
  .bandeau { background: #2a7dd1; color: #fff; text-align: center; font-weight: 700; font-size: 11pt; padding: 3px 0; }
  .titre-bareme { background: #dbeafe; text-align: center; font-weight: 700; font-size: 12pt; padding: 4px 0; margin-bottom: 14px; }
  table { width: 100%; border-collapse: collapse; }
  .cadre { border: 1px solid #555; }
  .entete td { padding: 4px 8px; vertical-align: top; width: 50%; }
  .entete b { font-weight: 700; }
  .periode td { border: 1px solid #555; padding: 4px 8px; }
  .primes { margin-top: 8px; }
  .primes td { border: 1px solid #555; padding: 4px 8px; font-weight: 700; }
  .rubrique { font-weight: 700; text-decoration: underline; margin: 14px 0 6px; }
  p { margin: 6px 0; text-align: justify; line-height: 1.35; }
  .ajustement td { border: 1px solid #555; padding: 3px 8px; font-weight: 700; font-size: 9pt; }
  .signatures { display: flex; justify-content: space-between; margin-top: 46px; font-weight: 700; text-decoration: underline; }
  .bareme td { border: 1px solid #777; padding: 5px 8px; vertical-align: top; font-weight: 700; font-size: 9pt; }
  .bareme td:first-child { width: 50%; }
  .bareme .section td { background: #1e3a5f; color: #fff; text-align: center; font-size: 10pt; }
  .rouge { color: #d00; }
  .liste th, .liste td { border: 1px solid #777; padding: 4px 6px; text-align: left; font-size: 9pt; }
  .liste th { background: #e5e7eb; }
  .liste .famille td { background: #f3f4f6; font-weight: 700; }
  .titre-liste { text-align: center; font-weight: 700; font-size: 12pt; margin: 6px 0 12px; }
`;

// Adresse absolue : la fenêtre d'impression (about:blank) ne résout pas les chemins relatifs
const absolue = (chemin) => { try { return new URL(chemin, window.location.origin).href; } catch { return chemin; } };
const page = (corps) => `<table class="feuille">
  <thead><tr><td><img class="logo" src="${absolue(logoCabinetEntete())}" alt="OREOLE Assurances" /></td></tr></thead>
  <tfoot><tr><td><div class="espace-pied"></div></td></tr></tfoot>
  <tbody><tr><td>${corps}</td></tr></tbody></table>`;
const documentHtml = (titre, pages) => `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8" /><title>${echapper(titre)}</title>
<style>${STYLES}</style></head><body>
<div class="pied"><img src="${absolue(logoCabinetPied())}" alt="" /><div>${echapper(parametre('documents.mentions_legales', MENTIONS_LEGALES))}</div></div>
${pages.join('')}
<script>window.onload = function () { setTimeout(function () { window.print(); }, 400); };</script></body></html>`;

// ------------------------------------------------------------------ Conditions Particulières
const pagesCp = (d) => {
  const q = d.quittance || {};
  const physique = String(q.TypeAssure || 'Personne Physique').toLowerCase().includes('physique');
  const naissance = [date(q.DateNaissanceAssure), q.LieuNaissanceAssure].filter(Boolean).join(' à ');
  const duree = Number(q.Duree) ? Math.max(1, Math.round(Number(q.Duree) / 30.42)) : 12;
  const ligne = (l1, v1, l2, v2) => `<tr><td><b>${l1} :</b> ${v1}</td><td><b>${l2} :</b> ${v2}</td></tr>`;
  const numero = q.NumeroPolice || q.NumeroDevis || '';
  const page1 = `
    <div class="bandeau">CONDITIONS PARTICULIERES ${q.NumeroPolice ? 'POLICE' : 'DEVIS'} N° ${texte(numero)}</div>
    <table class="cadre entete">
      ${ligne('Compagnie', texte(q.RaisonSociale), physique ? 'Nom et Prénoms assuré' : 'Raison Sociale', texte(q.NomAssure || q.NomClient))}
      ${ligne('Nature du risque', 'MINENE SANTE', physique ? 'Date et lieu de naissance' : 'Numéro registre de commerce', texte(naissance))}
      ${ligne('Souscripteur', texte(q.NomClient), physique ? 'Profession' : 'Activité', texte(q.ProfessionClient))}
      ${ligne('Intermédiaire', texte(q.LibelleIntermediaire || 'OREOLE ASSURANCES'), 'Adresse Postale', texte(q.AdresseClient))}
      ${ligne('Gestionnaire Santé', texte(d.detail.gestionnairesante || 'VITALIS SANTE'), 'Adresse Mail', texte(q.EmailClient))}
      ${ligne('Type de Client', texte(q.TypeAssure || 'Personne Physique'), 'Numéro Mobile', texte(q.MobileClient || q.TelephoneClient))}
      ${ligne('Option', texte(d.option), physique ? 'Adresse Géographique' : 'Localisation', texte(q.AdresseGeographique))}
    </table>
    <table class="periode"><tr>
      <td>Date d'effet : <b>${date(q.DateEffet)}</b></td><td>Date d'écheance : <b>${date(q.DateExpiration)}</b></td><td>Durée : <b>${duree} Mois</b></td>
    </tr></table>
    <table class="primes">
      <tr><td>Prime Nette</td><td>Accessoires</td><td>Taxe</td><td>Frais de Gestion</td><td>Prime TTC</td></tr>
      <tr><td>${montant(q.PrimeNetteHorsFga ?? q.PrimeNette)}</td><td>${montant(q.Accessoire)}</td><td>${montant(q.TaxeEnregistrement)}</td><td>${montant(q.FraisGestion)}</td><td>${montant(q.PrimeTtc)}</td></tr>
    </table>
    <div class="rubrique">OBJET DU CONTRAT</div>
    <p><b>MINÉNÉ SANTÉ</b> est une offre composée de 3 produits d’assurances indissociables les uns des autres.<br />
    Se sont :<b>L’assurance Santé, L’assurance Individuelle, L’assurance Responsabilité Civile chef de famille</b></p>
    <div class="rubrique">NATURE DES GARANTIES</div>
    <p><b>MINÉNÉ SANTÉ</b> donne droit aux garanties suivantes conformément au barème en annexe :</p>
    <p><b>Au titre de la santé :</b></p>
    <p>- Le remboursement des frais engagés par l’Assuré pour les actes ci-après : Frais Médicaux, Frais Pharmaceutiques, Frais d’Hospitalisation, Frais Chirurgicaux, Frais de Soins Dentaires, Frais d’Optique, Frais d’Examens Médicaux</p>
    <p><b>Au titre de l’individuelle accident :</b></p>
    <p>- Le paiement à l’assuré principal d’une indemnité déterminé en fonction du <b>taux d’incapacité retenu par le Médecin- Expert en cas d’incapacité partielle.</b></p>
    <p>- Le paiement d’une indemnité de deux (02) millions <b>à l’Assuré principal en cas d’incapacité permanente totale</b> à la suite d’un accident survenu après la prise d’effet du contrat;</p>
    <p>- Le paiement d’un capital de deux (02) millions aux ayants-droits ou au bénéficiaire désigné au contrat conformément à la liste en annexe en cas de <b>décès par accident de l’assuré principal.</b></p>
    <p><b>Au titre de la Responsabilité Civile Chef de Famille :</b></p>
    <p>- La prise en charge des conséquences pécuniaires de la Responsabilité Civile délictuelle ou quasi-délictuelle pouvant incomber à l’assuré principal, Chef de Famille, en vertu des articles 1382 à 1386 du Code Civil, en raison des Dommages Corporels, Matériels et Immatériels consécutifs à des dommages couverts causés aux tiers par un accident dont l’assuré lui-même, son conjoint, ses enfants mineurs ou enfants à charge poursuivant des études, le personnel de maison, les choses ou animaux qu’il a sous sa garde sont responsables.</p>
    <div class="rubrique">EFFET ET DUREE DU CONTRAT</div>
    <p>Conformément à l’article 13 Nouveau du code CIMA, la prise d’effet du contrat est subordonnée au paiement intégral de la prime correspondante.<br />
    Le présent contrat prend effet à sa souscription au <b>${date(q.DateEffet)}.</b><br />
    Son échéance est fixée au <b>${date(q.DateExpiration)}.</b> Il se renouvellera au 1er janvier <b>${annee(q.DateEffet) + 1}</b> à zéro heure pour une durée de 12 mois.</p>
    <p><b>Il est convenu d’accord partie que le barème en annexe fait partie intégrante des présentes conditions particulières.</b></p>`;
  const page2 = `
    <div class="rubrique">DELAI DE CARENCE</div>
    <p>• <b>03</b> mois pour les soins courants (consultations, pharmacie, analyse biologique et radiologique)<br />
    • <b>03</b> mois pour les soins dentaires<br />
    • <b>10</b> mois pour les frais de lunetteries et d’optique médicale<br />
    • <b>10</b> mois pour la maternité (assuré(e) ou conjoint(e)s)<br />
    • <b>12</b> mois pour les prothèses dentaires (autres prothèses)<br />
    • <b>12</b> mois pour toute maladie chronique : maladie du foie et des voies biliaires, du rein et des voies urinaires, des yeux (cataracte, glaucome, etc.) du sang, maladies cardiovasculaires, des ganglions, du système nerveux, des glandes endocrines (diabète, thyroïde, pancréas, etc.), végétations, myxomatose utérine, tumeurs, etc., si elle survient pour la première fois pendant la période de garantie.</p>
    <div class="rubrique">ASSURÉS BENEFICIARES DES GARANTIES</div>
    <p>Sont assurées au titre de la présente police, les personnes figurant sur la liste jointe en annexe, ayant rempli et retourné à <b>OREOLE ASSURANCES</b> pour visa, un bulletin d'adhésion.</p>
    <p>Cette liste peut être modifiée en cours de contrat <b>pour les formules Famille et Famille Plus</b> par :</p>
    <p>• Incorporation, après accord préalable de la Compagnie sur le <b>bulletin d'adhésion dûment rempli</b> et paiement intégral ou au moins 50% de la prime d'incorporation avant l'émission.</p>
    <p>• Retrait, suite à la notification écrite du Souscripteur à l'Assureur avec retour de la carte d'assuré en cas de tiers payant, <b>étant précisé que les retraits ne donnent pas lieu au versement d'une ristourne.</b></p>
    <div class="rubrique">BENEFICIAIRES</div>
    <p>Pourra bénéficier des garanties de <b>MINÉNÉ SANTÉ</b> Toute personne vivant en Côte d’Ivoire et âgée de 69 maximum pour les adultes <b>conformément au barème annexé</b> et de 21 an maximum pour les enfants. Toutefois cet âge peut être porté à 25 ans sur <b>présentation du certificat de scolarité de l’année de l’assurance ou un rapport médical pour l’enfant en situation de handicap réduisant totalement sa mobilité</b></p>
    <p><b>Les pièces à fournir pour la souscription sont :</b><br />
    • Adulte : 01 photo d’identité + 01 copie de la Carte Nationale d’Identité<br />
    • Enfant : 01 photo d’identité + 01 copie de l’extrait d’acte de naissance<br />
    • Un bulletin d’adhésion dument renseigné et signé</p>
    <div class="rubrique">SURPRIMES POUR RISQUES AGGRAVÉS</div>
    <p>Les maladies antérieures à la date d’effet du contrat sont exclues. Toutefois, elles peuvent être couvertes par la présente police moyennant surprime pour risque aggravé après avis du médecin conseil.</p>
    <p><b>Un taux de 30%</b> de surprime sera appliqué pour chaque affection chronique, avec un maximum de 3 affections acceptées.</p>
    <p>Par conséquent la prime serait susceptible de changer après analyses et le prospect en sera informé pour validation.</p>
    <div class="rubrique">CLAUSE D’AJUSTEMENT APPLICABLE AUX CONTRATS D’ASSURANCE SANTÉ</div>
    <p>Les primes santé feront l'objet, dans les conditions fixées ci-après, d'un ajustement calculé selon le rapport Sinistres / Primes (S/P) définitif au 30 septembre de l'exercice, majoré de la simulation rapportée au 4ème trimestre, déterminé au plus tard dans un délai de 2 mois après cette échéance, dans lequel :</p>
    <p>- Les Sinistres (S) représentent le montant total <b>des factures des dépenses de santé réglées aux prestataires, sur 12 mois,</b> pendant la période du 1er janvier au 30 septembre de l’année n + une extrapolation sur le dernier trimestre de l’année N en tenant compte de la tendance</p>`;
  const page3 = `
    <p>- Les les Primes (cotisations) (P) représentent le montant total des primes nettes de taxes et de frais ; émises pendant la période du 1er janvier au 31 décembre de l’année de l'exercice N. Cet Ajustement est effectué sur les bases suivantes :</p>
    <table class="ajustement">
      <tr><td>Rapport S/P de :</td><td>Pourcentage d'ajustement</td></tr>
      ${[['à 50 %', 'Perte du bénéfice du tiers payant'], ['de 51% à 65%:', 'Réduction de 10%'], ['de 66% à 70% :', 'Aucune modification'],
    ['de 71 à 80% :', '15% de majoration'], ['de 81% à 90% :', '20% de majoration'], ['de 91% à 100% :', '30% de majoration'],
    ['de 101% à 110%:', '35% de majoration'], ['de 111% à 115%:', '45% de majoration'],
    ['Au-delà de 115%', 'Résiliation pour ordre de la police en vue d’une nouvelle étude statistique pour une éventuelle nouvelle offre']]
    .map(([sp, ajustement]) => `<tr><td>${sp}</td><td>${ajustement}</td></tr>`).join('')}
    </table>
    <p>L'ajustement est calculé <b>à la fin de chaque exercice d'assurance fixée au 31 décembre.</b><br />
    La modification des primes résultant de l'application de la présente clause d'ajustement est notifiée par l'assureur au Souscripteur, <b>au plus tard le 30 novembre de l’année de l’exercice</b> en cours et doit s'appliquer dès le <b>1er janvier de l'exercice suivant.</b><br />
    Si le Souscripteur refuse le nouveau montant de primes ainsi ajusté, le contrat sera résilié de plein droit et sans autre avis, à la date d'échéance fixée aux conditions particulières. <b>Soit le 1er janvier de l’année N+1.</b></p>
    <div class="rubrique">SYSTEME DE PRISE EN CHARGE DES FRAIS EXPOSES</div>
    <p>D'un commun accord entre les Parties, il est convenu que les assurés seront pris en charge selon le système " tiers payant " à charge pour eux de s’adresser au réseau de prestataires conventionnés par ${texte(d.detail.gestionnairesante || 'VITALIS SANTÉ')}, dont liste jointe</p>
    <p>Sur présentation de leur carte, ils s’acquitteront du ticket modérateur tel que prévu au contrat</p>
    <p><b>Lorsqu’ils s’adresseront à des prestataires non conventionnés, ils devront s’acquitter des frais et seront remboursés par l’assureur sur présentation des justificatifs selon les termes et dans les limites prévues au contrat.</b></p>
    <p>Il en sera de même lorsque :<br /><b>- Le taux de sinistralité de l’Assuré atteint le seuil de 50%</b><br />
    - L’assuré ne sera pas à jour du paiement de ses primes. Il ne pourra dans ce cas prétendre au remboursement des frais engagés qu’après paiement intégrale de la prime.</p>
    <p>Les demandes de remboursement doivent être adressées à OREOLE ASSUANCES dans un délai maximum de trois (3) mois après le dépôt des pièces justificatives. Ou alors directement sur la plateforme de ${texte(d.detail.gestionnairesante || 'VITALIS SANTÉ')} pour remboursement dans un délai de 72H.</p>
    <p>Les frais médicaux exposés par l'Assuré hors les centres conventionnés seront remboursés à hauteur du taux de couverture de l'assuré et dans la limite des plafonds définis dans la présente police et ce sur présentation des justificatifs acquittés (note d'honoraires, factures acquittées normalisées, tickets de caisse, etc.) dans un délai maximum de trois (3) jours (72 h) ouvrés après le dépôt des pièces justificatives.</p>
    <div class="signatures"><div>LE SOUSCRIPTEUR</div><div>LA COMPAGNIE</div></div>`;
  return [page(page1), page(page2), page(page3)];
};

// ------------------------------------------------------------------ Barème
const pageBareme = (d) => {
  const l = (libelle, valeur) => `<tr><td>${libelle}</td><td>${valeur}</td></tr>`;
  const taux = d.quatreVingt ? '80 % soins externes et 80 % frais d\'hospitalisations' : '70 % soins externes et 80 % frais d\'hospitalisations';
  return page(`
    <div class="titre-bareme">BAREME</div>
    <table class="bareme">
      <tr class="section"><td colspan="2">CAPITAL INDIVIDUELLE-ACCIDENTS</td></tr>
      ${l('Décès', '2 000 000 F CFA')}${l('IPT', '2 000 000 F CFA')}${l('Frais Médicaux', '100 000 F CFA')}
      <tr class="section"><td colspan="2">RC CHEF DE FAMILLE</td></tr>
      ${l('Dommages corporels', '50 000 000 Franchise néant')}${l('Intoxications alimentaires', '5 000 000 Franchise néant')}
      ${l('Dommages matériels', '10 000 000 / Franchise: 10% minimum 20 000 &amp; maximum 200 000')}
      <tr class="section"><td colspan="2">SANTE</td></tr>
      ${l('Taux de couverture assurance Maladie', taux)}${l('Etendue territoriale', 'Côte d\'ivoire exclusivement')}
      ${l('Plafond de remboursements :<br /><br />Frais de chambre en hospitalisation<br />Frais de transport en ambulance/SAMU<br />Frais d\'accouchement simple normal<br />Frais d\'accouchement gémellaire normal<br />Frais d\'accouchement par voie chirurgicale<br />Forfait accouchement hors structure privée',
    '<br /><br />20 000 F CFA par jour<br />20 000 F CFA par cas sur accord préalable<br />150 000 F CFA par cas<br />200 000 F CFA par cas<br />300 000 F CFA par cas<br />50 000 F CFA par cas')}
      ${l('Frais d\'optique', '50 000 F CFA/Adulte &amp; 40 000 F CFA/enfant chaque 2 ans')}
      ${l('Frais de soins et de prothèse dentaire', '50 000 F CFA/an/personne avec accord pour les prothèses')}
      ${l('Plafond annuel :<br /><br />Par famille toutes prestations confondue', '1 000 000 F CFA<br /><br />(Il s\'agit de la garantie maximale annuelle que prendra en charge l\'assureur pour l\'assuré et sa famille. Et non ce que l\'assuré a le droit d\'exposer comme frais)')}
      ${l('Quota d\'alerte automatique', 'A partir du 15 ème bon de prise en charge<br />A partir de 200 000 F CFA de frais pharmaceutique')}
      ${l('Surveillance du portefeuille', 'Basculement systématique en mode remboursement en cours de contrat, si le taux de sinistralité du client est supérieur ou égal à <span class="rouge">50 %</span>')}
      ${l('DELAIS DE CARENCE', '- Les délais de carence sont les suivants<br />- <span class="rouge">03</span> mois pour les soins courants (consultations, pharmacie, analyse biologique et radiologique) ;<br />- 03 mois pour les soins dentaires<br />- 10 mois pour la lunetterie (verres et montures);<br />- 10 mois pour la maternité (assuré(e) ou conjoint(e)s)<br />- 12 mois pour les prothèses dentaires (autres prothèses)<br />- 12 mois pour toutes les maladies chroniques (autres prothèses)')}
      ${l('Surprime pour chaque affection chronique. (Maxi 3 affections)', '<span class="rouge">30 %</span>')}
      ${l('Surprime d\'âge : de 61 à 65 ans', '<span class="rouge">30 %</span>')}
      ${l('Surprime d\'âge : de 65 à 69 ans', '<span class="rouge">50 %</span>')}
    </table>`);
};

// ------------------------------------------------------------------ Liste des assurés (affiliés)
const pageAffilies = (d) => {
  const q = d.quittance || {};
  const affilies = d.affilies || [];
  const plusieursFormules = new Set(Object.values(d.formuleAdherent).map((f) => f.id)).size > 1;
  let famille = null;
  const lignes = affilies.map((a) => {
    let entete = '';
    if (Number(a.idadherent) !== famille) {
      famille = Number(a.idadherent);
      const formule = d.formuleAdherent[famille];
      entete = plusieursFormules && formule ? `<tr class="famille"><td colspan="5">${texte(formule.libelle)}</td></tr>` : '';
    }
    return `${entete}<tr><td>${texte(a.lienparente || a.lien)}</td><td>${texte(a.nom)}</td><td>${texte(a.prenom)}</td><td>${date(a.datenaissance)}</td><td>${texte(a.numerocmu)}</td></tr>`;
  }).join('');
  return page(`
    <div class="titre-liste">LISTE DES ASSURÉS — ${q.NumeroPolice ? 'POLICE' : 'DEVIS'} N° ${texte(q.NumeroPolice || q.NumeroDevis)}</div>
    <p><b>Souscripteur :</b> ${texte(q.NomClient)} &nbsp;—&nbsp; <b>Option :</b> ${texte(d.option)}</p>
    <table class="liste">
      <tr><th>Statut</th><th>Nom</th><th>Prénoms</th><th>Date de naissance</th><th>Numéro CMU</th></tr>
      ${lignes || '<tr><td colspan="5">Aucun affilié enregistré pour ce devis.</td></tr>'}
    </table>`);
};

// ------------------------------------------------------------------ Ayants droit (IA MINENE)
const pageAyantsDroit = (d) => {
  const ayants = d.ayantsDroit || [];
  // Part : colonne seulement si l'assuré en a précisé une (0 en base = non précisée)
  const avecParts = ayants.some((a) => Number(a.part) > 0);
  return page(`
    <div class="titre-liste">LISTES DES AYANT DROITS — POLICE N° ${texte(d.quittance?.NumeroPolice)}</div>
    <table class="liste">
      <tr><th>Qualité</th><th>Nom</th><th>Prénoms</th>${avecParts ? '<th>Part</th>' : ''}</tr>
      ${ayants.map((a) => `<tr><td>${texte(a.libelle_qualite)}</td><td>${texte(a.nom_ayant_droit)}</td><td>${texte(a.prenoms_ayant_droit)}</td>${avecParts ? `<td>${Number(a.part) > 0 ? `${a.part} %` : ''}</td>` : ''}</tr>`).join('')
      || `<tr><td colspan="${avecParts ? 4 : 3}">Aucun ayant droit enregistré sur l'IA MINENE de cette police.</td></tr>`}
    </table>`);
};

const DOCUMENTS = {
  cp: { titre: 'Conditions Particulieres', pages: (d) => [...pagesCp(d), pageBareme(d), pageAffilies(d)] },
  bareme: { titre: 'Bareme MINENE', pages: (d) => [pageBareme(d)] },
  affilies: { titre: 'Liste des assures', pages: (d) => [pageAffilies(d)] },
  ayants: { titre: 'Liste des ayants droit', pages: (d) => [pageAyantsDroit(d)] },
};

/**
 * Imprime un document Santé MINENE d'un devis ({ iddevis }) ou d'un contrat ({ idcontrat }).
 * La fenêtre est ouverte au clic (sinon bloquée pendant l'appel API). Renvoie false si le devis
 * n'est pas un devis MINENE et que le document lui est réservé (CP, barème) : l'appelant imprime alors
 * son document générique dans la fenêtre fournie.
 */
export const imprimerDocumentSante = async (type, ids, fenetre = window.open('', '_blank')) => {
  const doc = DOCUMENTS[type];
  if (fenetre) fenetre.document.write('<p style="font-family:Arial;padding:20px;">Préparation du document…</p>');
  try {
    const d = await charger(ids);
    if (!d.minene && (type === 'cp' || type === 'bareme')) {
      if (type === 'bareme' && fenetre) {
        fenetre.document.open();
        fenetre.document.write('<p style="font-family:Arial;padding:20px;">Le barème MINENE ne concerne que les offres MINENE SANTÉ.</p>');
        fenetre.document.close();
      }
      return false;
    }
    const html = documentHtml(`${doc.titre} ${d.quittance?.NumeroPolice || d.quittance?.NumeroDevis || ''}`.trim(), doc.pages(d));
    if (fenetre) {
      fenetre.document.open();
      fenetre.document.write(html);
      fenetre.document.close();
    }
  } catch (err) {
    console.error('Erreur impression Santé :', err);
    if (fenetre) {
      fenetre.document.open();
      fenetre.document.write('<p style="font-family:Arial;padding:20px;color:#b91c1c;">Impossible de charger les données Santé pour ce document. Veuillez réessayer.</p>');
      fenetre.document.close();
    }
  }
  return true;
};
