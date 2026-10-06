/**
 * Paramétrage réglé dans l'administration (GET /api/parametrage/, configuration_api/parametrage.py),
 * chargé une fois au démarrage (main.jsx) puis lu de façon synchrone par les écrans et les
 * documents imprimés. Serveur injoignable ou réglage absent : la valeur d'origine prévue ici
 * s'applique, l'application reste utilisable.
 */
import apiClient from '../api/apiClient';

// Valeurs d'origine (identiques aux valeurs de départ de la migration configuration_api 0073)
const PRODUITS_ORIGINE = [
  { IdProduit: 1, Libelle: 'AUTOMOBILE', Onglet: 'Auto', ModuleSaisie: 'auto', SaisieOuverte: true, Ordre: 1 },
  { IdProduit: 3, Libelle: 'ASSURANCE VOYAGE', Onglet: 'Voyage', ModuleSaisie: 'voyage', SaisieOuverte: true, Ordre: 2 },
  { IdProduit: 6, Libelle: 'TRANSPORT', Onglet: 'Transport', ModuleSaisie: 'transport', SaisieOuverte: true, Ordre: 3 },
  { IdProduit: 4, Libelle: 'MULTIRISQUES HABITATION', Onglet: 'MRH', ModuleSaisie: 'mrh', SaisieOuverte: true, Ordre: 4 },
  { IdProduit: 7, Libelle: 'MULTIRISQUES PROFESSIONNELLE', Onglet: 'MRH', ModuleSaisie: 'mrp', SaisieOuverte: false, Ordre: 5 },
  { IdProduit: 9, Libelle: 'TOUS DOMMAGES', Onglet: 'MRH', ModuleSaisie: 'tous-dommages', SaisieOuverte: false, Ordre: 6 },
  { IdProduit: 5, Libelle: 'SANTE', Onglet: 'Santé', ModuleSaisie: 'sante', SaisieOuverte: true, Ordre: 7 },
  { IdProduit: 10, Libelle: 'VIE', Onglet: 'Santé', ModuleSaisie: '', SaisieOuverte: false, Ordre: 8 },
  { IdProduit: 2, Libelle: 'INDIVIDUELLE ACCIDENTS', Onglet: 'IA', ModuleSaisie: 'ia', SaisieOuverte: true, Ordre: 9 },
  { IdProduit: 8, Libelle: 'RESPONSABILITE CIVILE', Onglet: 'RC', ModuleSaisie: 'rc', SaisieOuverte: false, Ordre: 10 },
];

let etat = { Cabinet: {}, Parametres: {}, Documents: [], Produits: PRODUITS_ORIGINE, charge: false };
let chargement = null;
const abonnes = new Set();

const normaliser = (texte) => String(texte || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

/** Charge (ou recharge après une modification dans l'admin) le paramétrage ; ne lève jamais d'erreur. */
export const chargerParametrage = (forcer = false) => {
  if (chargement && !forcer) return chargement;
  chargement = apiClient.get('/parametrage/', { timeout: 8000 })
    .then(({ data }) => {
      etat = {
        Cabinet: data?.Cabinet || {},
        Parametres: data?.Parametres || {},
        Documents: Array.isArray(data?.Documents) ? data.Documents : [],
        Produits: Array.isArray(data?.Produits) && data.Produits.length ? data.Produits : PRODUITS_ORIGINE,
        Modules: data?.Modules || [],
        charge: true,
      };
      abonnes.forEach((f) => f());
      return etat;
    })
    .catch((err) => {
      console.warn('Paramétrage indisponible, valeurs d\'origine appliquées :', err?.message || err);
      chargement = null;
      return etat;
    });
  return chargement;
};

/** Prévient `rappel` à chaque rechargement du paramétrage ; renvoie la fonction de désabonnement. */
export const surParametrage = (rappel) => {
  abonnes.add(rappel);
  return () => abonnes.delete(rappel);
};

// ------------------------------------------------------------------ règles de gestion
/** Valeur d'un paramètre (lephare_parametre), convertie selon son type, ou `defaut`. */
export const parametre = (cle, defaut) => {
  const p = etat.Parametres[cle];
  if (!p || p.Valeur === undefined || p.Valeur === null || String(p.Valeur).trim() === '') return defaut;
  if (['entier', 'decimal', 'montant', 'pourcentage'].includes(p.Type)) {
    const n = Number(String(p.Valeur).replace(',', '.'));
    return Number.isFinite(n) ? n : defaut;
  }
  if (p.Type === 'booleen') return ['1', 'true', 'oui', 'vrai'].includes(String(p.Valeur).toLowerCase());
  return p.Valeur;
};

export const villeSignature = () => parametre('documents.ville_signature', 'Abidjan');
// Identité du cabinet (Administration > Le cabinet, table stdparametresite)
export const identiteCabinet = () => etat.Cabinet || {};
export const nomCabinet = () => etat.Cabinet?.RaisonSociale || 'OREOLE ASSURANCES';
/** Ligne sous le nom du cabinet dans l'en-tête des états : agrément • siège • Code CIMA. */
export const mentionCabinet = () => [
  parametre('documents.mention_agrement', ''),
  etat.Cabinet?.AdresseGeographique ? `Siège social : ${etat.Cabinet.AdresseGeographique}` : '',
  'Code CIMA CRCA',
].filter(Boolean).join(' • ');
export const logoCabinetEntete = () => parametre('documents.logo_entete', '/assets/print/logo-oreole-entete.png');
export const logoCabinetPied = () => parametre('documents.logo_pied', '/assets/print/logo-oreole-pied.png');

// ------------------------------------------------------------------ compagnies
// Logos livrés avec l'application : seulement si la compagnie n'a aucun réglage de documents
const LOGOS_ORIGINE = [
  [/nsia/, '/assets/print/logo-nsia.jpg'],
  [/sunu/, '/assets/print/logo-sunu.png'],
  [/amsa/, '/assets/print/logo-amsa.png'],
];

/** Réglages des documents d'une compagnie, retrouvée par identifiant ou par raison sociale. */
export const documentsCompagnie = (compagnie) => {
  if (compagnie === undefined || compagnie === null || compagnie === '') return null;
  if (typeof compagnie === 'number' || /^\d+$/.test(String(compagnie))) {
    return etat.Documents.find((d) => Number(d.IdCompagnie) === Number(compagnie)) || null;
  }
  const nom = normaliser(compagnie);
  return etat.Documents.find((d) => normaliser(d.RaisonSociale) === nom)
    || etat.Documents.find((d) => d.RaisonSociale && (nom.includes(normaliser(d.RaisonSociale)) || normaliser(d.RaisonSociale).includes(nom)))
    || null;
};

export const logoCompagnie = (compagnie) => {
  const doc = documentsCompagnie(compagnie);
  if (doc) return doc.Logo || null;
  const nom = normaliser(compagnie);
  return LOGOS_ORIGINE.find(([motif]) => motif.test(nom))?.[1] || null;
};

/** Modèle d'impression tiré des réglages d'une compagnie ({ Logo, RaisonSociale, AttestationVoyage }). */
export const construireModeleAttestation = (doc) => {
  const a = doc?.AttestationVoyage || {};
  return {
    logo: doc.Logo || logoCompagnie(doc.RaisonSociale),
    signataire: a.Signataire || doc.RaisonSociale,
    convention: a.Convention || '',
    paysResidence: a.PaysResidence || '',
    garanties: a.Garanties || [],
    assistance: { telephone: a.Telephone || '', email: a.Email || '', whatsapp: a.Whatsapp || '' },
    exemplaires: a.Exemplaires?.length ? a.Exemplaires : ["Exemplaire de l'Assuré"],
  };
};

/** Modèle d'attestation voyage actif de la compagnie (fiche compagnie, onglet Attestation voyage), sinon null. */
export const modeleAttestationVoyage = (idCompagnie) => {
  const doc = documentsCompagnie(Number(idCompagnie));
  return doc?.AttestationVoyage?.Actif ? construireModeleAttestation(doc) : null;
};

// ------------------------------------------------------------------ produits
export const produitsParametres = () => etat.Produits;

const produitPar = (idProduit) => etat.Produits.find((p) => Number(p.IdProduit) === Number(idProduit));

/** Code de l'onglet du registre des devis (« AUTO », « MRH »…) d'un produit, ou null s'il est inconnu. */
export const codeOnglet = (libelleOnglet) => normaliser(libelleOnglet).replace(/[^a-z0-9]+/g, '_').toUpperCase();
export const ongletDuProduit = (idProduit) => {
  const p = produitPar(idProduit);
  return p?.Onglet ? codeOnglet(p.Onglet) : null;
};

/** Onglets du registre dans l'ordre des produits : [{ id, label }] sans doublon. */
export const ongletsRegistre = () => {
  const vus = new Map();
  [...etat.Produits].sort((a, b) => (a.Ordre ?? 99) - (b.Ordre ?? 99)).forEach((p) => {
    if (p.Onglet && !vus.has(codeOnglet(p.Onglet))) vus.set(codeOnglet(p.Onglet), p.Onglet);
  });
  return [...vus].map(([id, label]) => ({ id, label }));
};

/** Formulaire (route /user/quotes/<module>) qui rouvre un devis de ce produit, ou null. */
export const moduleDuProduit = (idProduit) => produitPar(idProduit)?.ModuleSaisie || null;

/** Saisie ouverte pour ce formulaire (au moins un produit qui l'utilise a la saisie ouverte). */
export const moduleOuvert = (module) => etat.Produits.some((p) => p.ModuleSaisie === module && p.SaisieOuverte);

export const libellesModulesOuverts = () => {
  const libelles = { auto: 'Automobile', ia: 'Individuelle Accidents', sante: 'Santé', voyage: 'Voyage', transport: 'Transport', mrh: 'Multirisques Habitation', rc: 'Responsabilité Civile', mrp: 'Multirisque Professionnelle', 'tous-dommages': 'Tous Dommages' };
  return [...new Set(etat.Produits.filter((p) => p.SaisieOuverte && p.ModuleSaisie).map((p) => libelles[p.ModuleSaisie] || p.ModuleSaisie))];
};
