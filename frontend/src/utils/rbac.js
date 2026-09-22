/**
 * RBAC & Business Rules Engine for LE PHARE (Uranus)
 * Conformité Code des Assurances CIMA & Droit Comptable OHADA
 */

export const ROLES = {
  ADMIN: 'ADMIN', // Direction Générale & Administrateur
  DIR_TECH: 'DIR_TECH', // Direction Technique & Souscription
  DIR_SINISTRES: 'DIR_SINISTRES', // Direction Sinistres & Gestion Déléguée
  FINANCE: 'FINANCE', // Finance, Trésorerie & Encaissements
  COMMERCIAL: 'COMMERCIAL', // Conseillère Commerciale & Production
  BACKOFFICE: 'BACKOFFICE', // Gestionnaire BackOffice & Émissions
  CONFORMITE: 'CONFORMITE', // Conformité CIMA & Contrôle Interne
};

export const ROLE_LABELS = {
  [ROLES.ADMIN]: 'Direction Générale (Admin)',
  [ROLES.DIR_TECH]: 'Direction Technique & Souscription',
  [ROLES.DIR_SINISTRES]: 'Direction Sinistres & Déléguée',
  [ROLES.FINANCE]: 'Finance & Trésorerie',
  [ROLES.COMMERCIAL]: 'Conseillère Commerciale',
  [ROLES.BACKOFFICE]: 'Gestionnaire BackOffice',
  [ROLES.CONFORMITE]: 'Conformité CIMA & Audit',
};

/**
 * Normalize role string from user object
 */
export const getUserRole = (user) => {
  if (!user) return ROLES.COMMERCIAL;
  if (user.is_admin === true || user.is_superuser === true) return ROLES.ADMIN;
  const roleCode = (user.role_code || user.role || '').toUpperCase();
  if (ROLES[roleCode]) return ROLES[roleCode];
  if (roleCode === 'DIR_GEN') return ROLES.ADMIN;
  if (roleCode === 'COMPTABLE' || roleCode === 'CAISSIER') return ROLES.FINANCE;
  if (roleCode === 'AGENT' || roleCode === 'USER') return ROLES.COMMERCIAL;
  return ROLES.COMMERCIAL;
};

/**
 * Retrieve current user from local storage or fallback
 */
export const getCurrentUser = () => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const saved = window.localStorage.getItem('uranus_user');
      if (saved) return JSON.parse(saved);
    }
  } catch (e) {
    // fallback
  }
  return { role: ROLES.ADMIN, username: 'admin', nom: 'Franck Gnogouri' };
};

/**
 * RBAC Permissions Matrix
 * Resources: 'clients', 'quotes', 'contracts', 'claims', 'cash', 'catalog', 'conventions', 'remittances', 'users', 'leads'
 * Actions: 'view', 'create', 'edit', 'delete', 'terminate', 'approve', 'extourne'
 */
export const PERMISSIONS_MATRIX = {
  [ROLES.ADMIN]: {
    clients: ['view', 'create', 'edit', 'delete', 'archive'],
    quotes: ['view', 'create', 'edit', 'delete', 'convert'],
    contracts: ['view', 'create', 'edit', 'terminate', 'cancel', 'endorse'],
    claims: ['view', 'create', 'edit', 'delete', 'settle', 'close'],
    cash: ['view', 'collect', 'extourne'],
    catalog: ['view', 'create', 'edit', 'delete'],
    conventions: ['view', 'create', 'edit', 'delete'],
    remittances: ['view', 'create', 'validate', 'export'],
    users: ['view', 'create', 'edit', 'delete', 'reset_password'],
    leads: ['view', 'create', 'edit', 'delete', 'convert'],
  },
  [ROLES.DIR_TECH]: {
    clients: ['view', 'create', 'edit'],
    quotes: ['view', 'create', 'edit', 'delete', 'convert'],
    contracts: ['view', 'create', 'edit', 'terminate', 'endorse'],
    claims: ['view', 'edit'],
    cash: ['view'],
    catalog: ['view', 'create', 'edit', 'delete'],
    conventions: ['view', 'edit'],
    remittances: ['view'],
    users: ['view'],
    leads: ['view', 'create', 'edit'],
  },
  [ROLES.DIR_SINISTRES]: {
    clients: ['view'],
    quotes: ['view'],
    contracts: ['view', 'endorse'],
    claims: ['view', 'create', 'edit', 'delete', 'settle', 'close'],
    cash: ['view'],
    catalog: ['view'],
    conventions: ['view'],
    remittances: ['view'],
    users: ['view'],
    leads: ['view'],
  },
  [ROLES.FINANCE]: {
    clients: ['view'],
    quotes: ['view'],
    contracts: ['view'],
    claims: ['view'],
    cash: ['view', 'collect', 'extourne'],
    catalog: ['view'],
    conventions: ['view'],
    remittances: ['view', 'create', 'validate', 'export'],
    users: ['view'],
    leads: ['view'],
  },
  [ROLES.COMMERCIAL]: {
    clients: ['view', 'create', 'edit'],
    quotes: ['view', 'create', 'edit', 'delete', 'convert'],
    contracts: ['view', 'create'],
    claims: ['view', 'create'],
    cash: ['view'],
    catalog: ['view'],
    conventions: ['view'],
    remittances: [],
    users: [],
    leads: ['view', 'create', 'edit', 'delete', 'convert'],
  },
  [ROLES.BACKOFFICE]: {
    clients: ['view', 'create', 'edit'],
    quotes: ['view', 'create', 'edit', 'convert'],
    contracts: ['view', 'create', 'endorse'],
    claims: ['view'],
    cash: ['view'],
    catalog: ['view'],
    conventions: ['view'],
    remittances: ['view'],
    users: [],
    leads: ['view'],
  },
  [ROLES.CONFORMITE]: {
    clients: ['view'],
    quotes: ['view'],
    contracts: ['view'],
    claims: ['view'],
    cash: ['view'],
    catalog: ['view'],
    conventions: ['view'],
    remittances: ['view'],
    users: ['view'],
    leads: ['view'],
  },
};

/**
 * Check if current user is allowed to perform action on resource
 */
export const canUser = (user, action, resource) => {
  const role = getUserRole(user);
  const userPerms = PERMISSIONS_MATRIX[role] || {};
  const resourcePerms = userPerms[resource] || [];
  return resourcePerms.includes(action);
};

/**
 * Detailed authorization check returning boolean + human-readable justification
 */
export const checkAuthorization = (user, action, resource) => {
  const allowed = canUser(user, action, resource);
  if (allowed) return { allowed: true };

  const role = getUserRole(user);
  const roleName = ROLE_LABELS[role] || role;

  const labels = {
    edit: 'la modification',
    delete: 'la suppression',
    create: 'la création',
    terminate: 'la résiliation',
    cancel: "l'annulation",
    settle: 'le règlement',
    extourne: "l'extourne",
    validate: 'la validation',
  };

  const actionLabel = labels[action] || action;
  return {
    allowed: false,
    reason: `Votre profil actuel (${roleName}) n'est pas habilité pour ${actionLabel} sur cette ressource. Veuillez contacter un administrateur ou la direction concernée.`,
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
