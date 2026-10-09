/**
 * Droits d'action de LE PHARE côté écran, sur les droits effectifs du serveur (utils/droits.js,
 * chargés par AuthContext depuis GET /api/securite/moi/) et règles de gestion CIMA.
 *
 * canUser(user, action, ressource) garde la signature utilisée par les écrans (clients, devis,
 * contrats, sinistres, CRM…) ; l'ancienne matrice de profils codée en dur est remplacée par la
 * correspondance ci-dessous vers les droits réglés dans Administration > Rôles. Le serveur contrôle
 * de toute façon chaque appel (autorisations/garde.py).
 */
import { aLeDroit } from './droits';

// (ressource, action) de l'écran -> droit(s) du serveur
const DROITS_ACTIONS = {
  clients: { view: 'clients.view', create: 'clients.create', edit: 'clients.update', archive: 'clients.update', delete: 'clients.delete', merge: 'clients.merge' },
  quotes: { view: 'devis.view', create: 'devis.create', edit: 'devis.update', delete: 'devis.cancel', archive: 'devis.cancel', convert: 'devis.validate' },
  contracts: { view: 'contrats.view', create: 'devis.validate', edit: 'contrats.update', terminate: 'contrats.cancel', cancel: 'contrats.cancel', endorse: 'contrats.avenant' },
  claims: { view: 'sinistres.view', create: 'sinistres.create', edit: 'sinistres.update', delete: 'sinistres.update', close: 'sinistres.update', settle: 'sinistres.settle' },
  cash: { view: 'encaissements.view', collect: 'encaissements.create', extourne: 'encaissements.cancel', delete: 'encaissements.cancel' },
  catalog: { view: 'tarifs.view', create: 'tarifs.update', edit: 'tarifs.update', delete: 'tarifs.update' },
  conventions: { view: null, create: 'parametrage.update', edit: 'parametrage.update', delete: 'parametrage.update' },
  remittances: { view: 'reversements.view', create: 'reversements.create', validate: 'reversements.validate', export: 'reversements.view' },
  users: { view: 'users.view', create: 'users.create', edit: 'users.update', delete: 'users.disable', reset_password: 'users.password' },
  leads: { view: 'crm.view', create: 'crm.update', edit: 'crm.update', delete: 'crm.update', convert: 'crm.update' },
};

const LIBELLES_ACTIONS = {
  view: 'la consultation', edit: 'la modification', delete: 'la suppression', create: 'la création',
  terminate: 'la résiliation', cancel: "l'annulation", settle: 'le règlement', extourne: "l'extourne",
  validate: 'la validation', convert: 'la transformation', endorse: "l'avenant", collect: "l'encaissement",
};

/** Utilisateur de la session ouverte (localStorage), sans valeur inventée. */
export const getCurrentUser = () => {
  try {
    const session = JSON.parse(window.localStorage.getItem('lephare_session') || 'null');
    return session?.user || null;
  } catch {
    return null;
  }
};

/** L'utilisateur connecté peut-il faire cette action ? (le premier argument est conservé pour compatibilité) */
export const canUser = (_user, action, resource) => {
  const actions = DROITS_ACTIONS[resource];
  if (!actions || !(action in actions)) return false;
  return aLeDroit(actions[action]);
};

export const checkAuthorization = (user, action, resource) => {
  if (canUser(user, action, resource)) return { allowed: true };
  return {
    allowed: false,
    reason: `Vos rôles ne vous autorisent pas ${LIBELLES_ACTIONS[action] || action} sur cet élément. Adressez-vous à un administrateur (Administration > Utilisateurs).`,
  };
};

/**
 * CIMA & Business Rules Validation (Règles de Gestion Métier)
 * Evaluates whether an action is legally and operationally permissible for a specific entity
 */
export const validateBusinessRule = (action, resource, entity, dataStore) => {
  if (!entity) return { allowed: false, reason: 'Entité introuvable.' };

  // 1. CLIENTS
  if (resource === 'clients') {
    if (action === 'delete') {
      const activeCount = Number(entity.contrats_actifs || 0);
      const linkedContracts = (dataStore && typeof dataStore.getContracts === 'function')
        ? dataStore.getContracts().filter(
            (c) => (c.client_nom || '').toLowerCase() === (entity.nomcomplet || '').toLowerCase()
          )
        : [];

      if (activeCount > 0 || linkedContracts.length > 0) {
        const policeRef = linkedContracts[0]?.numeropolice || 'en portefeuille';
        return {
          allowed: false,
          isBlockedByLaw: true,
          reason: `Règle de gestion CIMA : Impossible de supprimer le client « ${entity.nomcomplet} » car il est titulaire de contrat(s) d'assurance (Police ${policeRef}). Le Code CIMA impose l'archivage et la conservation des données d'assurance pendant 10 ans.`,
          suggestion: 'Archiver la fiche client au lieu de la supprimer.',
          alternativeAction: 'archive',
        };
      }

      const linkedClaims = (dataStore && typeof dataStore.getClaims === 'function')
        ? dataStore.getClaims().filter(
            (cl) => (cl.assure_nom || '').toLowerCase() === (entity.nomcomplet || '').toLowerCase()
          )
        : [];
      if (linkedClaims.length > 0) {
        return {
          allowed: false,
          isBlockedByLaw: true,
          reason: `Règle de gestion CIMA : Impossible de supprimer ce client car un dossier sinistre historique (${linkedClaims[0].numero_sinistre}) lui est rattaché.`,
          suggestion: 'Archiver la fiche client.',
          alternativeAction: 'archive',
        };
      }

      return { allowed: true };
    }
  }

  // 2. DEVIS (QUOTES)
  if (resource === 'quotes') {
    if (action === 'edit' || action === 'delete') {
      if (entity.statut === 'Consolidé') {
        return {
          allowed: false,
          isBlockedByLaw: true,
          reason: `Règle de gestion CIMA : Le devis ${entity.numerodevis} est « Consolidé » (transformé en police d'assurance active). Il constitue une pièce probante scellée et ne peut plus être modifié ni supprimé.`,
          suggestion: 'Pour modifier les garanties ou primes du contrat correspondant, veuillez émettre un Avenant.',
        };
      }
      return { allowed: true };
    }
  }

  // 3. CONTRATS / POLICES (CONTRACTS)
  if (resource === 'contracts') {
    if (action === 'delete') {
      return {
        allowed: false,
        isBlockedByLaw: true,
        reason: `Interdiction Formelle Code CIMA : Une police d'assurance émise (${entity.numeropolice}) ne peut JAMAIS faire l'objet d'une suppression physique brute de la base de données.`,
        suggestion: 'Utilisez l’action « Résilier la Police » (Art. 13 non-paiement, vente, accord parties) ou « Annulation par Dérogation » avec Jeton.',
        alternativeAction: 'terminate',
      };
    }

    if (action === 'edit') {
      if (entity.statut_encaissement === 'Soldé' && Number(entity.montant_encaisse || 0) > 0) {
        return {
          allowed: false,
          isBlockedByLaw: true,
          reason: `Règle CIMA & Comptable : La police ${entity.numeropolice} a déjà fait l'objet d'un encaissement de prime validé (${Number(entity.montant_encaisse).toLocaleString('fr-FR')} FCFA). Toute modification des garanties ou de la prime doit impérativement faire l'objet d'un Avenant CIMA.`,
          suggestion: 'Créer un Avenant de modification dans le module Avenants.',
        };
      }
      return { allowed: true };
    }
  }

  // 4. SINISTRES (CLAIMS)
  if (resource === 'claims') {
    if (action === 'delete') {
      if (Number(entity.montant_indemnise || 0) > 0 || entity.statut === 'Règlement validé') {
        return {
          allowed: false,
          isBlockedByLaw: true,
          reason: `Règle de gestion CIMA : Le dossier sinistre ${entity.numero_sinistre} a fait l'objet d'une indemnisation financière (${Number(entity.montant_indemnise).toLocaleString('fr-FR')} FCFA). Il ne peut pas être supprimé.`,
          suggestion: 'Clôturer le dossier avec le statut « Archivé » ou « Sans suite ».',
        };
      }
      return { allowed: true };
    }
  }

  // 5. CAISSE & QUITTANCES
  if (resource === 'cash') {
    if (action === 'delete') {
      return {
        allowed: false,
        isBlockedByLaw: true,
        reason: "Inviolabilité de Quittance CIMA (Art. 13) : Une quittance officielle délivrée ne peut jamais être effacée. Seule une procédure d'extourne avec motif comptable et jeton de dérogation est admise.",
      };
    }
  }

  // 6. CATALOGUE & CONVENTIONS
  if (resource === 'catalog') {
    if (action === 'delete') {
      const contracts = (dataStore && typeof dataStore.getContracts === 'function') ? dataStore.getContracts() : [];
      const codeOrNom = entity.code_produit || entity.code || entity.nom;
      const isUsed = contracts.some((c) =>
        (c.produit || '').toLowerCase().includes((codeOrNom || '').toLowerCase())
      );
      if (isUsed) {
        return {
          allowed: false,
          isBlockedByLaw: false,
          reason: `Intégrité Référentielle : L'élément « ${entity.nom || entity.libelle || entity.code} » est utilisé par des contrats en cours d'exécution. Sa suppression corromprait les historiques.`,
          suggestion: 'Désactiver le produit plutôt que de le supprimer.',
        };
      }
      return { allowed: true };
    }
  }

  if (resource === 'conventions') {
    if (action === 'delete') {
      const contracts = (dataStore && typeof dataStore.getContracts === 'function') ? dataStore.getContracts() : [];
      const isUsed = contracts.some(
        (c) => (c.compagnie || '').toLowerCase() === (entity.compagnie || '').toLowerCase()
      );
      if (isUsed) {
        return {
          allowed: false,
          isBlockedByLaw: false,
          reason: `Règle de gestion : La convention ${entity.code} avec ${entity.compagnie} possède des contrats rattachés.`,
          suggestion: 'Modifier le protocole ou ajuster les plafonds de délégation.',
        };
      }
      return { allowed: true };
    }
  }

  // 7. CRM LEADS / PROSPECTS
  if (resource === 'leads') {
    if (action === 'delete') {
      if (entity.statut === 'Gagné') {
        return {
          allowed: false,
          isBlockedByLaw: false,
          reason: `Règle Commerciale & Traçabilité : L'opportunité « ${entity.nom_prospect} » est au stade « Gagnée » et a déjà été convertie en client/contrat d'assurance.`,
          suggestion: 'Conservez cette opportunité pour préserver le calcul des taux de transformation du CRM.',
        };
      }
      return { allowed: true };
    }
  }

  // Default allowed
  return { allowed: true };
};
