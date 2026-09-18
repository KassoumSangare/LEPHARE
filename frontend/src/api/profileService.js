// Service de gestion et persistance des Profils d'Habilitation pour LE PHARE (CdC V2)

export const DEFAULT_PROFILES = [
  {
    id: 1,
    code: 'DIR_GEN',
    name: 'Direction Générale & Arbitrage',
    space: 'ALL',
    description: 'Pilotage global, validation des dérogations stratégiques, arbitrage conventions et reporting CIMA.',
    derogation_max: 30,
    auto_approve: true,
    user_count: 1,
    is_active: true,
    modules: ['cockpit', 'crm', 'quotes', 'contracts', 'cash', 'remittances', 'commissions', 'claims', 'conventions', 'ged', 'compliance', 'admin'],
  },
  {
    id: 2,
    code: 'DIR_TECH',
    name: 'Direction Technique & Souscription',
    space: 'ALL',
    description: 'Paramétrage produits, validation des souscriptions complexes, avenants et supervision du portefeuille.',
    derogation_max: 20,
    auto_approve: true,
    user_count: 2,
    is_active: true,
    modules: ['cockpit', 'quotes', 'contracts', 'asaci', 'endorsements', 'conventions', 'ged', 'approvals'],
  },
  {
    id: 3,
    code: 'DIR_SINISTRES',
    name: 'Direction Sinistres & Mandats Délégués',
    space: 'ALL',
    description: 'Ouverture, instruction, gestion des expertises, décisions sous délégation de gestion, règlements et recours.',
    derogation_max: 15,
    auto_approve: true,
    user_count: 2,
    is_active: true,
    modules: ['cockpit', 'claims', 'contracts', 'conventions', 'ged'],
  },
  {
    id: 4,
    code: 'FINANCE',
    name: 'Finance, Trésorerie & Recouvrement',
    space: 'ALL',
    description: 'Encaissements primes, portefeuille chèques, reversements assureurs (délai 30j), commissions et impayés.',
    derogation_max: 0,
    auto_approve: false,
    user_count: 3,
    is_active: true,
    modules: ['cockpit', 'cash', 'cheques', 'remittances', 'commissions', 'ged'],
  },
  {
    id: 5,
    code: 'COMMERCIAL',
    name: 'Commercial, Conseiller & CRM',
    space: 'USER',
    description: 'Prospection, pipeline leads, devis multi-branches, fiches 360°, relances et transformation.',
    derogation_max: 5,
    auto_approve: false,
    user_count: 6,
    is_active: true,
    modules: ['crm', 'quotes', 'contracts', 'asaci'],
  },
  {
    id: 6,
    code: 'BACKOFFICE',
    name: 'Gestionnaire BackOffice & Émissions',
    space: 'USER',
    description: 'Contrôle des pièces obligatoires avant émission, délivrance des attestations ASACI, avenants et mouvements.',
    derogation_max: 0,
    auto_approve: false,
    user_count: 4,
    is_active: true,
    modules: ['quotes', 'contracts', 'asaci', 'endorsements', 'ged'],
  },
  {
    id: 7,
    code: 'CONFORMITE',
    name: 'Conformité CIMA, Audit & Contrôle',
    space: 'ALL',
    description: 'Vérification de l\'agrément CIMA, suivi de la caution financière, consultation de l\'audit trail et états Livre V.',
    derogation_max: 0,
    auto_approve: false,
    user_count: 1,
    is_active: true,
    modules: ['compliance', 'audit', 'cima', 'conventions', 'ged'],
  },
  {
    id: 8,
    code: 'APPORTEUR',
    name: 'Apporteur d\'Affaires & Partenaire Réseau',
    space: 'USER',
    description: 'Dépôt des affaires nouvelles, consultation des contrats apportés et bordereaux de rétrocessions.',
    derogation_max: 0,
    auto_approve: false,
    user_count: 24,
    is_active: true,
    modules: ['quotes', 'contracts', 'commissions'],
  },
];

const STORAGE_KEY = 'lephare_profiles';

export const getProfiles = () => {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (data) {
      return JSON.parse(data);
    }
  } catch (err) {
    console.error('Erreur lecture profiles localStorage:', err);
  }
  return DEFAULT_PROFILES;
};

export const saveProfiles = (profiles) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profiles));
    window.dispatchEvent(new CustomEvent('uranus_profiles_updated', { detail: profiles }));
  } catch (err) {
    console.error('Erreur sauvegarde profiles localStorage:', err);
  }
};

export const addProfile = (newProfile) => {
  const current = getProfiles();
  const item = {
    ...newProfile,
    id: Date.now(),
    user_count: 0,
    is_active: true,
  };
  const updated = [item, ...current];
  saveProfiles(updated);
  return item;
};

export const updateProfile = (id, updatedData) => {
  const current = getProfiles();
  const updated = current.map((p) => (p.id === id ? { ...p, ...updatedData } : p));
  saveProfiles(updated);
  return updated;
};

export const deleteProfile = (id) => {
  const current = getProfiles();
  const updated = current.filter((p) => p.id !== id);
  saveProfiles(updated);
  return updated;
};
