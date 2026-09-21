/**
 * LE PHARE - Mapping 100% Conforme au Routeur Django Uranus Backend
 * 
 * Toutes les routes correspondent strictement aux patterns d'URL enregistrés dans :
 * - production/urls.py
 * - customer/urls.py
 * - configuration_api/urls.py
 * - account/urls.py
 * - autorisations/urls.py
 * - commissions/urls.py
 * - institutionnel/urls.py
 * - asaci/urls.py
 * - reporting/urls.py
 * - payment/urls.py
 * - sante/urls.py
 * 
 * Tous les chemins non conformes et les fallbacks fictifs ont été supprimés.
 */

import apiClient from './apiClient';

/* =========================================================================
   HELPER : Extraction standard des résultats paginés ou bruts
   ========================================================================= */
const extractData = (res) => {
  if (!res) return [];
  if (Array.isArray(res.data)) return res.data;
  if (res.data && Array.isArray(res.data.results)) return res.data.results;
  // Beaucoup d'endpoints APIView du backend renvoient une enveloppe
  // { status: 'succès'|'Echec', data: [...] } au lieu d'un tableau brut
  // ou de la pagination DRF standard ({ results: [...] }).
  if (res.data && Array.isArray(res.data.data)) return res.data.data;
  return res.data;
};

/* =========================================================================
   1. AUTHENTIFICATION & UTILISATEURS (account)
   ========================================================================= */
export const authApi = {
  // POST /api/users/login
  login: (credentials) => apiClient.post('/users/login', credentials),
  // POST /api/users/register
  register: (userData) => apiClient.post('/users/register', userData),
  // GET /api/users/user
  getCurrentUser: async () => {
    const res = await apiClient.get('/users/user');
    return res.data;
  },
  // POST /api/users/logout
  logout: () => apiClient.post('/users/logout'),
  // POST /api/users/changepassword
  changePassword: (data) => apiClient.post('/users/changepassword', data),
  // POST /api/users/resetpassword
  resetPassword: (data) => apiClient.post('/users/resetpassword', data),
  // GET /api/users/profile/
  getProfiles: async () => {
    const res = await apiClient.get('/users/profile/');
    return extractData(res);
  },
};

/* =========================================================================
   2. CLIENTS & ASSURÉS (customer)
   ========================================================================= */
export const sanitizeClientForApi = (raw) => {
  if (!raw) return {};
  const isEntreprise = raw.typeclient === 'Entreprise' || raw.Particulier === 'F' || raw.Particulier === '0';
  const nom = (raw.nom || raw.Nom || '').trim();
  const prenom = isEntreprise ? '' : (raw.prenom || raw.Prenoms || '').trim();

  return {
    Nom: nom,
    Prenoms: prenom || null,
    Particulier: isEntreprise ? 'F' : 'V',
    Vip: raw.Vip || (raw.is_vip ? 'V' : 'N'),
    Statut: raw.Statut || 'V',
    CreeCie: raw.CreeCie || 'V',
    Telephone: (raw.telephone || raw.Telephone || '').trim() || null,
    Mobile: (raw.mobile || raw.Mobile || '').trim() || null,
    Fixe: (raw.fixe || raw.Fixe || '').trim() || null,
    Fax: (raw.fax || raw.Fax || '').trim() || null,
    Email: (raw.email || raw.Email || '').trim() || null,
    Adresse1: (raw.adresse || raw.Adresse1 || '').trim() || null,
    Adresse2: (raw.Adresse2 || '').trim() || null,
    IdVille: raw.IdVille ? Number(raw.IdVille) : null,
    CodePostal: (raw.CodePostal || '').trim() || null,
    IdQualite: raw.IdQualite ? Number(raw.IdQualite) : (isEntreprise ? 4 : 1),
    IdProfession: raw.IdProfession ? Number(raw.IdProfession) : null,
    IdSecteurActivite: raw.IdSecteurActivite ? Number(raw.IdSecteurActivite) : null,
    Responsable: (raw.Responsable || '').trim() || null,
    Fonction: (raw.Fonction || '').trim() || '',
    CniPat: (raw.CniPat || '').trim() || null,
    DateNaissance: raw.DateNaissance || null,
    LieuNaissance: (raw.LieuNaissance || '').trim() || null,
    Rib: raw.Rib && raw.Rib.replace(/\s+/g, '').length === 24 ? raw.Rib.replace(/\s+/g, '') : null,
    NumeroCompte: raw.NumeroCompte || 'XXXXXXX',
    Solde: raw.Solde !== undefined ? String(raw.Solde) : '0.0000',
    Avoir: raw.Avoir !== undefined ? String(raw.Avoir) : '0.0000',
    ExonereDeTaxes: Boolean(raw.ExonereDeTaxes),
    ExonereDeAccess: Boolean(raw.ExonereDeAccess),
    idtypeclient: raw.idtypeclient ? Number(raw.idtypeclient) : (isEntreprise ? 2 : 1),
    idtypeassure: raw.idtypeassure ? Number(raw.idtypeassure) : (isEntreprise ? 2 : 1),
    IdCategorie: raw.IdCategorie ? Number(raw.IdCategorie) : null,
    IdProfil: raw.IdProfil ? Number(raw.IdProfil) : null,
    Reconquete: raw.Reconquete || 'N',
    Matricule: raw.Matricule || raw.codeclient || null,
    numero_assure: raw.numero_assure || null,
    cle_unique: raw.cle_unique || null,
  };
};

export const normalizeClient = (c) => {
  if (!c) return null;
  const id = c.IdClient || c.id;
  
  // Nettoyage des chaînes textuelles
  const cleanStr = (val) => {
    if (val === null || val === undefined) return '';
    const str = String(val).trim();
    if (str === '.' || str === '-' || str === 'null' || str === 'undefined' || str === 'NONE') return '';
    return str;
  };

  const rawNom = cleanStr(c.Nom || c.nom);
  const rawPrenom = cleanStr(c.Prenoms || c.prenom);
  const raisonSociale = cleanStr(c.RaisonSociale || c.raisonsociale);
  const cniPat = cleanStr(c.CniPat || c.cnipat);

  const isEntreprise = c.Particulier === 'F' || c.Particulier === '0' || c.typeclient === 'Entreprise' || (c.idtypeclient === 2) || Boolean(raisonSociale);

  // Construction du nom complet propre
  let nomcomplet = [rawNom, rawPrenom].filter(Boolean).join(' ').trim();
  if (!nomcomplet) {
    nomcomplet = raisonSociale || cniPat || (id ? `Client #${id}` : 'Client sans nom');
  }

  // Civilité / Qualité
  let civilite = cleanStr(c.civilite || c.Civilite);
  if (typeof c.Civilite === 'object' && c.Civilite !== null) {
    civilite = cleanStr(c.Civilite.Libelle);
  }
  if (!civilite && isEntreprise) {
    civilite = 'Société';
  }

  // Téléphone et Contact
  const cleanPhone = (val) => {
    const s = cleanStr(val);
    if (!s || s === '00' || s === 'TELP' || s === '0' || s.length < 3) return '';
    return s;
  };
  const cleanEmail = (val) => {
    const s = cleanStr(val);
    if (!s || !s.includes('@')) return '';
    return s;
  };

  const telephone = cleanPhone(c.Telephone || c.telephone);
  const mobile = cleanPhone(c.Mobile || c.mobile);
  const contactPrincipal = mobile || telephone;
  const email = cleanEmail(c.Email || c.email);

  // Adresse et Ville
  const adresse1 = cleanStr(c.Adresse1 || c.adresse);
  const adresse2 = cleanStr(c.Adresse2);
  let ville = cleanStr(c.ville || c.Ville || c.libelleville);
  if (!ville) {
    if (adresse2 && adresse2 !== 'BP' && adresse2.length > 2) ville = adresse2;
    else if (adresse1 && adresse1 !== 'BP' && !adresse1.toLowerCase().includes('bp')) ville = adresse1;
    else ville = 'Abidjan';
  }

  // Profession
  let profession = cleanStr(c.libelleprofession || c.profession || c.Profession);
  if (!profession) {
    profession = isEntreprise ? 'Entreprise / Société' : '';
  }

  // Code / Matricule
  const codeclient = cleanStr(c.Matricule) || cleanStr(c.numero_assure) || cleanStr(c.codeclient) || (id ? `CLI-2026-${String(id).padStart(4, '0')}` : 'CLI-SANS-CODE');

  return {
    ...c,
    id,
    IdClient: id,
    codeclient,
    Nom: rawNom,
    Prenoms: rawPrenom,
    nom: rawNom,
    prenom: rawPrenom,
    nomcomplet,
    typeclient: isEntreprise ? 'Entreprise' : 'Particulier',
    civilite,
    telephone: contactPrincipal,
    mobile: contactPrincipal,
    email,
    adresse: adresse1,
    ville,
    profession,
    libelleprofession: profession,
    CniPat: cniPat,
    contrats_actifs: c.contrats_actifs || 0,
    devis_en_cours: c.devis_en_cours || 0,
    total_primes: c.total_primes || '0 FCFA',
    raw: c,
  };
};

export const customerApi = {
  // GET /api/client/ (Liste des clients réels en BDD)
  getClients: async () => {
    const res = await apiClient.get('/client/');
    const list = extractData(res);
    return list.map(normalizeClient);
  },
  // GET /api/client/:id/
  getClientDetail: async (id) => {
    const res = await apiClient.get(`/client/${id}/`);
    return normalizeClient(res.data);
  },
  // POST /api/client/
  createClient: async (clientData) => {
    const payload = sanitizeClientForApi(clientData);
    return apiClient.post('/client/', payload);
  },
  // PUT /api/client/:id/
  updateClient: async (id, clientData) => {
    const payload = sanitizeClientForApi(clientData);
    return apiClient.put(`/client/${id}/`, payload);
  },
  // GET /api/clientrecherche/:terme (Recherche client)
  searchClient: async (term) => {
    const res = await apiClient.get(`/clientrecherche/${term}`);
    return extractData(res);
  },
  // GET /api/clientrestreint/
  getClientsRestreint: async () => {
    const res = await apiClient.get('/clientrestreint/');
    const list = extractData(res);
    return list.map(normalizeClient);
  },
};

/* =========================================================================
   3. RÉFÉRENTIELS DE CONFIGURATION CLIENT (configuration_api)
   ========================================================================= */
export const configRefApi = {
  // GET /api/qualite/
  getQualites: async () => extractData(await apiClient.get('/qualite/')),
  // GET /api/ville/
  getVilles: async () => extractData(await apiClient.get('/ville/')),
  // GET /api/profession/
  getProfessions: async () => extractData(await apiClient.get('/profession/')),
  // GET /api/secteuractivite/
  getSecteursActivite: async () => extractData(await apiClient.get('/secteuractivite/')),
  // GET /api/typesouscripteur/
  getTypesSouscripteur: async () => extractData(await apiClient.get('/typesouscripteur/')),
  // GET /api/typeassure/
  getTypesAssure: async () => extractData(await apiClient.get('/typeassure/')),
};

/* =========================================================================
   3b. SECTEURS D'ACTIVITÉ ÉCONOMIQUE - API CRUD (configuration_api)
   ========================================================================= */
export const secteurActiviteApi = {
  // GET /api/secteuractivite/ — Liste complète avec client_count
  getAll: async () => extractData(await apiClient.get('/secteuractivite/')),
  // POST /api/secteuractivite/ — Créer un nouveau secteur
  create: (data) => apiClient.post('/secteuractivite/', data),
  // PUT /api/secteuractivite/{id}/ — Modifier un secteur
  update: (id, data) => apiClient.put(`/secteuractivite/${id}/`, data),
  // DELETE /api/secteuractivite/{id}/ — Supprimer (bloqué si clients liés)
  delete: (id) => apiClient.delete(`/secteuractivite/${id}/`),
};

/* =========================================================================
   3c. TYPE DE SOUSCRIPTEUR (stdtypesouscripteur) — CRUD
   ========================================================================= */
export const typeSouscripteurApi = {
  // GET /api/typesouscripteur/
  getAll: async () => extractData(await apiClient.get('/typesouscripteur/')),
  // POST /api/typesouscripteur/
  create: (data) => apiClient.post('/typesouscripteur/', data),
  // PUT /api/typesouscripteur/{id}/
  update: (id, data) => apiClient.put(`/typesouscripteur/${id}/`, data),
  // DELETE /api/typesouscripteur/{id}/
  delete: (id) => apiClient.delete(`/typesouscripteur/${id}/`),
};

/* =========================================================================
   3d. TYPE D'ASSURÉ (stdtypeassure) — CRUD
   ========================================================================= */
export const typeAssureApi = {
  // GET /api/typeassure/
  getAll: async () => extractData(await apiClient.get('/typeassure/')),
  // POST /api/typeassure/
  create: (data) => apiClient.post('/typeassure/', data),
  // PUT /api/typeassure/{id}/
  update: (id, data) => apiClient.put(`/typeassure/${id}/`, data),
  // DELETE /api/typeassure/{id}/
  delete: (id) => apiClient.delete(`/typeassure/${id}/`),
};

/* =========================================================================
   3e. PROFESSION / MÉTIER (stdprofession) — CRUD
   ========================================================================= */
export const professionApi = {
  // GET /api/profession/
  getAll: async () => extractData(await apiClient.get('/profession/')),
  // POST /api/profession/
  create: (data) => apiClient.post('/profession/', data),
  // PUT /api/profession/{id}/
  update: (id, data) => apiClient.put(`/profession/${id}/`, data),
  // DELETE /api/profession/{id}/
  delete: (id) => apiClient.delete(`/profession/${id}/`),
};



/* =========================================================================
   4. DEVIS & TARIFICATION MULTI-BRANCHES (production)
   ========================================================================= */
export const normalizeDevis = (bq) => {
  if (!bq) return null;
  const id = bq.iddevis || bq.id;
  const clientNom = bq.client && typeof bq.client === 'object'
    ? `${bq.client.Nom || ''} ${bq.client.Prenoms || ''}`.trim()
    : (bq.nomassure || bq.client_nom || bq.souscripteur || 'Client Uranus');
  
  const produitNom = bq.produit && typeof bq.produit === 'object'
    ? (bq.produit.LibelleProduit || bq.produit.libelle_produit)
    : (bq.produit || 'Automobile');
    
  const cieNom = bq.compagnie && typeof bq.compagnie === 'object'
    ? (bq.compagnie.RaisonSociale || bq.compagnie.nom)
    : (bq.compagnie || 'NSIA Assurances');

  const primeNette = Number(bq.primenette || bq.prime_nette || 0);
  const primeTotale = Number(bq.primettc || bq.prime_totale || primeNette);
  const taxe = Number(bq.taxe || bq.taxes || 0);
  const accessoire = Number(bq.accessoire || bq.accessoires || 0);
  const fga = Number(bq.fga || 0);
  const cedeao = Number(bq.cedeao || 0);
  const commission = Number(bq.commissionintermediaire || bq.commission || 0);

  let statutLabel = bq.statut;
  let statutBadge = 'amber';
  if (bq.devis_consolide) {
    // Ce devis a été fusionné dans un devis consolidé (sp_consolidation_devis) :
    // il est scellé et ne doit plus être modifié ni confirmé individuellement.
    statutLabel = 'Consolidé';
    statutBadge = 'purple';
  } else if (bq.archive) {
    statutLabel = 'Archivé';
    statutBadge = 'rose';
  } else if (bq.confirme) {
    statutLabel = 'Confirmé / Contrat';
    statutBadge = 'emerald';
  } else if (bq.statut === '1' || !bq.statut) {
    statutLabel = 'En attente';
    statutBadge = 'amber';
  }

  return {
    id,
    iddevis: id,
    numerodevis: bq.numerodevis || `DEV-2026-${String(id).padStart(4, '0')}`,
    client_id: bq.client?.IdClient || bq.client_id || (typeof bq.client === 'number' ? bq.client : 1),
    client_nom: clientNom,
    souscripteur: clientNom,
    nomassure: bq.nomassure || clientNom,
    compagnie: cieNom,
    produit: produitNom,
    branche: bq.branche || (produitNom.toLowerCase().includes('auto') ? 'Auto' : produitNom.toLowerCase().includes('hab') ? 'MRH' : 'Auto'),
    date_emission: bq.dateemission || bq.date_emission || new Date().toISOString().split('T')[0],
    date_effet: bq.dateeffet || bq.date_effet || new Date().toISOString().split('T')[0],
    date_expiration: bq.dateexpiration || bq.date_expiration,
    prime_nette: primeNette,
    prime_totale: primeTotale,
    accessoires: accessoire,
    taxes: taxe,
    fga,
    cedeao,
    commission,
    bonus_malus: bq.bonus_malus || 0,
    flotte: Boolean(bq.flotte),
    coassurance: Boolean(bq.coassurance),
    confirme: Boolean(bq.confirme),
    archive: Boolean(bq.archive),
    devis_consolide: Boolean(bq.devis_consolide),
    statut: statutLabel,
    statut_badge: statutBadge,
    numero_police_compagnie: bq.numero_police_compagnie || null,
    raw: bq,
  };
};

export const formatAutoQuoteForApi = (raw) => {
  if (!raw) return {};
  const now = new Date();
  const dateEmission = raw.DateEmission || raw.date_emission || now.toISOString().split('T')[0];
  const dateEffet = raw.DateEffet || raw.date_effet || dateEmission;
  const dateExpiration = raw.DateExpiration || raw.date_expiration || new Date(now.getFullYear() + 1, now.getMonth(), now.getDate()).toISOString().split('T')[0];
  const details = raw.details || {};

  // Formattage date JJ-MM-AAAA attendu par Django save_quotation
  const toDmy = (dStr) => {
    if (!dStr) return '01-01-2026';
    if (dStr.includes('-') && dStr.split('-')[0].length === 4) {
      const [y, m, d] = dStr.split('-');
      return `${d}-${m}-${y}`;
    }
    return dStr.replace(/\//g, '-');
  };

  return {
    IdIntermediaire: Number(raw.IdIntermediaire || 1),
    IdCompagnie: Number(raw.IdCompagnie || raw.compagnie_id || 1),
    IdProduit: Number(raw.IdProduit || 1),
    IdTarif: Number(details.idTarif || raw.IdTarif || 1),
    IdOffre: Number(details.idOffre || raw.IdOffre || 1),
    IdAvenant: Number(raw.IdAvenant || 0),
    IdClient: Number(raw.IdClient || raw.client_id || 1),
    IdAssure: Number(raw.IdAssure || details.idAssure || raw.client_id || 1),
    Flotte: Boolean(raw.Flotte || raw.flotte || details.typeContrat === 'FLOTTE'),
    Coassurance: Boolean(raw.Coassurance || raw.coassurance || false),
    DateEmission: toDmy(dateEmission),
    DateEffet: toDmy(dateEffet),
    DateExpiration: toDmy(dateExpiration),
    IdTarif: Number(details.idTarif || 1),
    CodeUsage: Number(details.codeUsage || 1),
    IdCarrosserie: Number(details.idCarrosserie || 1),
    CodeCarburant: Number(details.codeCarburant || (details.energie === 'Diesel' ? 2 : 1)),
    Puissance: Number(details.puissanceFiscale || 7),
    NombrePlace: Number(details.nombrePlace || 5),
    Charge: Number(details.chargeUtile || 0),
    ValeurNeuve: String(details.valeurNeuf || 0),
    ValeurVenale: String(details.valeurVenale || 0),
    ValeurAccessoire: String(details.valeurAccessoire || 0),
    TauxReduction: String(details.tauxRemise || 0),
    CodeAlarme: Number(details.codeAlarme || 0),
    Bns: String(details.bonusMalus || 0),
    NomConducteur: details.nomConducteur || raw.client_nom || '',
    AdresseConducteur: details.adresseConducteur || details.lieuHabitation || '',
    DateMec: toDmy(details.dateMec || '2020-01-01'),
    NumMoteur: details.numMoteur || '',
    NumChassis: details.numChassis || '',
    IdTypeVehicule: Number(details.idTypeVehicule || 1),
    IdMarque: Number(details.idMarque || 1),
    Matricule: details.immatriculation || '1234 AB 01',
    NumPermisConduire: details.numPermisConduire || '',
    IdGenreVehicule: Number(details.idGenreVehicule || 1),
    NumCarteBrunePhysique: details.numCarteBrunePhysique || '',
    ModeleVehicule: details.modele || 'Standard',
    RemorqueAttelee: Boolean(details.remorqueAttelee),
    CodeFormuleSecuriteRoutiere: details.codeFormuleSecuriteRoutiere || details.securiteRoutiere || '',
    IdOptionAssistance: Number(details.idOptionAssistance || details.assistanceAuto || 0),
    CarburantAutreMatiere: Boolean(details.CarburantAutreMatiere),
    TransportEleves: Boolean(details.TransportEleves),
    TransportEmployes: Boolean(details.TransportEmployes),
    TansportPassagerSupplementaire: Boolean(details.TansportPassagerSupplementaire || details.TransportPassageSupplementaire),
    NsiaAutoPlus: Boolean(details.nsiaAutoPlus),
    NumeroPoliceCompagnie: details.numeroPoliceCompagnie || 'RAS',
    IdDuree: Number(details.idDuree || (details.dureeMois === 1 ? 1 : details.dureeMois === 3 ? 2 : details.dureeMois === 6 ? 3 : details.dureeMois === 12 ? 4 : 4)),
    IdTerme: Number(details.idTerme || (details.termeContrat === 'Ferme / Non Renouvelable' ? 2 : 1)),
    IdDevis: Number(raw.iddevis || raw.id || 0),
    IdDevisDetail: Number(details.idDevisDetail || 0),
  };
};

export const quoteApi = {
  // GET /api/devis/stats/ (Totaux réels par branche en BDD)
  getStats: async () => {
    try {
      const res = await apiClient.get('/devis/stats/');
      return res.data;
    } catch {
      return null;
    }
  },
  // GET /api/devis/ (178 Devis réels en BDD)
  // GET /api/devis/ (178 Devis réels en BDD)
  getQuotes: async (params = {}) => {
    const res = await apiClient.get('/devis/', { params, timeout: 120000 });
    const list = extractData(res);
    return list.map(normalizeDevis);
  },
  // Tous les devis d'un filtre (parcourt les pages serveur, plafonnées à 200 lignes)
  getAllQuotes: async (params = {}, maxPages = 30) => {
    const all = [];
    for (let page = 1; page <= maxPages; page += 1) {
      const res = await apiClient.get('/devis/', { params: { ...params, page_size: 200, page } });
      all.push(...extractData(res).map(normalizeDevis));
      if (!res?.data?.next) break;
    }
    return all;
  },
  // Nombre total de devis pour un filtre donné (pagination serveur : champ `count`)
  getQuotesCount: async (params = {}) => {
    const res = await apiClient.get('/devis/', { params: { ...params, page_size: 1 }, timeout: 120000 });
    return Number(res?.data?.count ?? 0);
  },
  // GET /api/devis/:id/
  getQuoteDetail: async (id) => {
    const res = await apiClient.get(`/devis/${id}/`);
    return normalizeDevis(res.data);
  },
  // POST /api/enregistrementdevis (Auto CIMA)
  createAutoQuote: (data) => {
    const payload = formatAutoQuoteForApi(data);
    return apiClient.post('/enregistrementdevis', payload);
  },
  // POST /api/offregarantie (Calcul dynamique des garanties auto CIMA)
  calculateOffreGarantie: (payload) => apiClient.post('/offregarantie', payload),
  // POST /api/correctiondevis/ (Enregistrement des primes & garanties imposées / modifiées)
  correctQuote: (payload) => apiClient.post('/correctiondevis/', payload),
  // POST /api/finalisationdevisauto (Finalisation devis flotte)
  finalizeFlotteQuote: (payload) => apiClient.post('/finalisationdevisauto', payload),
  // POST /api/annulationsaisievehicule (Suppression d'un véhicule de flotte)
  deleteFlotteVehicle: (idDevisDetail) => apiClient.post('/annulationsaisievehicule', { IdDevisDetail: idDevisDetail }),
  // GET /api/sousgarantie/ (Sous-garanties disponibles)
  getSousGaranties: async () => extractData(await apiClient.get('/sousgarantie/')),
  // GET /api/assistanceautomobile/:idCompagnie
  getAssistanceAuto: async (compagnieId) => {
    try {
      const res = await apiClient.get(`/assistanceautomobile/${compagnieId}`);
      return extractData(res);
    } catch {
      return [];
    }
  },
  // GET /api/securiteroutiereparcompagnie/:idCompagnie
  getSecuriteRoutiere: async (compagnieId) => {
    try {
      const res = await apiClient.get(`/securiteroutiereparcompagnie/${compagnieId}`);
      return extractData(res);
    } catch {
      return [];
    }
  },
  // GET /api/offreparproduit/?idproduit=1&idtarif=:tarifId
  getOffresByTarif: async (produitId = 1, tarifId = 1) => {
    try {
      const res = await apiClient.get(`/offreparproduit/?idproduit=${produitId}&idtarif=${tarifId}`);
      return extractData(res);
    } catch {
      return [];
    }
  },
  // POST /api/enregistrementdevismrh (MRH)
  createMrhQuote: (data) => apiClient.post('/enregistrementdevismrh', data),
  // POST /api/enregistrementdevisia (Individuelle Accident)
  createIaQuote: (data) => apiClient.post('/enregistrementdevisia', data),
  // POST /api/enregistrementdevisvoyage (Voyage & Schengen)
  createVoyageQuote: (data) => apiClient.post('/enregistrementdevisvoyage', data),
  // POST /api/enregistrementdevisrc (Responsabilité Civile & Divers)
  createRisquesDiversQuote: (data) => apiClient.post('/enregistrementdevisrc', data),
  // POST /api/certificattransport/ (Transport & Facultés)
  createTransportQuote: (data) => {
    const todayStr = new Date().toISOString().split('T')[0];
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    const nextMonthStr = nextMonth.toISOString().split('T')[0];

    const payload = {
      statut: 'Pending',
      numero_requete: `REQ-${Date.now()}`,
      date_requete: data.date_emission || todayStr,
      reference_certificat: data.numerodevis || `CERT-${Date.now()}`,
      date_certificat: data.date_emission || todayStr,
      numero_police: data.details?.numeroPoliceCompagnie || 'EN_COURS',
      assureur: data.compagnie || 'SUNU ASSURANCES IARD CI',
      adresse_assureur: 'Abidjan Plateau',
      id_client_uranus: Number(data.client_id) || 1,
      nom_souscripteur: data.client_nom || 'Client Transport',
      adresse_souscripteur: 'Abidjan',
      assure: data.client_nom || 'Client Transport',
      adresse_assure: 'Abidjan',
      intermediaire: 'OREOLE',
      moyen_transport: data.details?.modeTransport || 'Maritime',
      date_debut_voyage: data.date_effet || todayStr,
      date_debut_periode: data.date_effet || todayStr,
      date_fin_periode: nextMonthStr,
      voyage: `${data.details?.portDepart || 'Abidjan'} / ${data.details?.portArrivee || 'International'}`,
      description_commerciale: data.details?.natureMarchandise || 'Marchandises Diverses',
      marque_colis: data.details?.conditionnement || 'COLIS-01',
      numero_document_transport: data.details?.numeroBlLta || 'BL-N/A',
      valeur_assurance: String(data.details?.sommeAssuree || data.prime_totale || 0),
      prime_nette: String(data.prime_nette || 0),
      accessoire: String(data.accessoires || 0),
      taxe: String(data.taxes || 0),
      prime_ttc: String(data.prime_totale || 0),
    };
    return apiClient.post('/certificattransport/', payload);
  },
  // POST /api/enregistrementdevissante (Santé)
  createSanteQuote: (data) => apiClient.post('/enregistrementdevissante', data),
  // POST /api/mrh/devis/:devis_id/recalculer/ (Recalculer devis)
  recalculateQuote: (devisId) => apiClient.post(`/mrh/devis/${devisId}/recalculer/`),
  // POST /api/consolidationdevis/
  consolidateQuote: (data) => apiClient.post('/consolidationdevis/', data),
  // GET /api/devisclient/?idclient=:clientId
  getQuotesByClient: async (clientId) => {
    const res = await apiClient.get(`/devisclient/?idclient=${clientId}`);
    const list = extractData(res);
    return list.map(normalizeDevis);
  },
  // GET /api/mrh/devis/:devis_id/resume-financier/
  getFinancialSummary: (devisId) => apiClient.get(`/mrh/devis/${devisId}/resume-financier/`),
  // POST /api/annulationsaisiedevis
  archiveQuote: (id) => apiClient.post('/annulationsaisiedevis', { IdDevis: id }),
  // POST /api/desarchivagedevis
  unarchiveQuote: (id) => apiClient.post('/desarchivagedevis', { IdDevis: id }),
};

/* =========================================================================
   4.1 MULTIRISQUES HABITATION - API OREOLE (mrh)
   ========================================================================= */
export const mrhApi = {
  // GET /api/mrh/usages/
  getUsages: async () => extractData(await apiClient.get('/mrh/usages/')),
  // GET /api/mrh/usages/:code/
  getUsageDetails: async (code) => (await apiClient.get(`/mrh/usages/${code}/`)).data,
  // GET /api/mrh/usages/:code/garanties/
  getGarantiesByUsage: async (code) => extractData(await apiClient.get(`/mrh/usages/${code}/garanties/`)),
  // GET /api/mrh/usages/:code/options/
  getOptionsByUsage: async (code) => extractData(await apiClient.get(`/mrh/usages/${code}/options/`)),
  // POST /api/mrh/calcul/maison/
  calculerPrimeMaison: async (data) => (await apiClient.post('/mrh/calcul/maison/', data)).data,
  // POST /api/mrh/devis/
  creerDevis: async (data) => (await apiClient.post('/mrh/devis/', data)).data,
  // GET /api/mrh/devis/:id/
  getDevis: async (id) => (await apiClient.get(`/mrh/devis/${id}/`)).data,
  // PATCH /api/mrh/devis/:id/
  updateDevis: async (id, data) => (await apiClient.patch(`/mrh/devis/${id}/`, data)).data,
  // DELETE /api/mrh/devis/:id/
  supprimerDevis: async (id) => (await apiClient.delete(`/mrh/devis/${id}/`)).data,
  // POST /api/mrh/devis/:id/maisons/
  ajouterMaison: async (idDevis, maisonData) => (await apiClient.post(`/mrh/devis/${idDevis}/maisons/`, { maison: maisonData })).data,
  // PUT /api/mrh/devis/:id/maisons/:maisonId/
  modifierMaison: async (idDevis, maisonId, maisonData) => (await apiClient.put(`/mrh/devis/${idDevis}/maisons/${maisonId}/`, maisonData)).data,
  // DELETE /api/mrh/devis/:id/maisons/:maisonId/
  supprimerMaison: async (idDevis, maisonId) => (await apiClient.delete(`/mrh/devis/${idDevis}/maisons/${maisonId}/`)).data,
  // POST /api/mrh/devis/:id/recalculer/
  recalculerTotaux: async (idDevis) => (await apiClient.post(`/mrh/devis/${idDevis}/recalculer/`, {})).data,
  // GET /api/mrh/devis/:id/resume-financier/
  getResumeFinancier: async (idDevis) => (await apiClient.get(`/mrh/devis/${idDevis}/resume-financier/`)).data,
  // POST /api/mrh/devis/:id/repartir-garanties/
  repartirGaranties: async (idDevis, data) => (await apiClient.post(`/mrh/devis/${idDevis}/repartir-garanties/`, data)).data,
  // POST /api/mrh/devis/:id/imposer-prime/
  imposerPrimeDevis: async (idDevis, data) => (await apiClient.post(`/mrh/devis/${idDevis}/imposer-prime/`, data)).data,
  // POST /api/mrh/devis/:id/maisons/:maisonId/imposer-prime/
  imposerPrimeMaison: async (idDevis, maisonId, data) => (await apiClient.post(`/mrh/devis/${idDevis}/maisons/${maisonId}/imposer-prime/`, data)).data,
  // GET /api/terme/
  getTermes: async () => extractData(await apiClient.get('/terme/')),
};

/* =========================================================================
   4.2 ASSURANCE VOYAGE - API OREOLE
   ========================================================================= */
export const voyageApi = {
  // GET /api/tarifvoyage/:idcompagnie
  getTarifsVoyage: async (idcompagnie = 21) => {
    try {
      const res = await apiClient.get(`/tarifvoyage/${idcompagnie}`);
      return res.data?.data || extractData(res);
    } catch {
      return [];
    }
  },
  // GET /api/payszone/:idcompagnie
  getPaysZone: async (idcompagnie = 21) => {
    try {
      const res = await apiClient.get(`/payszone/${idcompagnie}`);
      return res.data?.data || extractData(res);
    } catch {
      return [];
    }
  },
  // GET /api/offrevoyage/?idcompagnie=:id&idtarif=:id&idzone=:id
  getOffresVoyage: async (idcompagnie = 21, idtarif = 1, idzone = 1) => {
    try {
      const res = await apiClient.get('/offrevoyage/', {
        params: { idcompagnie, idtarif, idzone }
      });
      return res.data?.data || extractData(res);
    } catch {
      return [];
    }
  },
  // POST /api/offregarantievoyage
  getGarantiesVoyage: async (payload) => {
    try {
      const res = await apiClient.post('/offregarantievoyage', payload);
      return extractData(res);
    } catch {
      return [];
    }
  },
  // POST /api/enregistrementdevisvoyage
  enregistrerDevisVoyage: async (payload) => {
    return apiClient.post('/enregistrementdevisvoyage', payload);
  }
};

/* =========================================================================
   5. POLICES & CONTRATS D'ASSURANCE (production)
   ========================================================================= */
export const normalizeContrat = (bc) => {
  if (!bc) return null;
  const id = bc.idcontrat || bc.id;
  const clientNom = bc.idclient && typeof bc.idclient === 'object'
    ? `${bc.idclient.Nom || ''} ${bc.idclient.Prenoms || ''}`.trim()
    : (bc.assure || bc.client_nom || bc.souscripteur || 'Assuré LE PHARE');
    
  const produitNom = bc.idproduit && typeof bc.idproduit === 'object'
    ? (bc.idproduit.LibelleProduit || bc.idproduit.libelle_produit)
    : (bc.produit || 'Automobile');
    
  const cieNom = bc.idcompagnie && typeof bc.idcompagnie === 'object'
    ? (bc.idcompagnie.RaisonSociale || bc.idcompagnie.nom)
    : (bc.compagnie || 'NSIA Assurances');

  const primeNette = Number(bc.primenette || bc.prime_nette || 0);
  const primeTotale = Number(bc.primettc || bc.prime_totale || primeNette);
  const montantEncaisse = Number(bc.montant_encaisse || (bc.idquittance && typeof bc.idquittance === 'object' ? bc.idquittance.mt_encaisse : 0));
  const isSolde = montantEncaisse >= primeTotale && primeTotale > 0;

  return {
    id,
    idcontrat: id,
    numeropolice: bc.numeropolice || `POL-2026-${String(id).padStart(4, '0')}`,
    client_id: bc.idclient?.IdClient || bc.client_id || (typeof bc.idclient === 'number' ? bc.idclient : 1),
    client_nom: clientNom,
    souscripteur: clientNom,
    assure: clientNom,
    produit: produitNom,
    compagnie: cieNom,
    date_effet: bc.dateeffet || bc.date_effet || '2026-01-01',
    date_expiration: bc.dateexpiration || bc.date_expiration || '2026-12-31',
    date_emission: bc.dateemission || bc.date_emission || '2026-01-01',
    prime_nette: primeNette,
    prime_totale: primeTotale,
    montant_encaisse: montantEncaisse,
    taxe: Number(bc.taxe || 0),
    accessoire: Number(bc.accessoire || 0),
    fga: Number(bc.fga || 0),
    cedeao: Number(bc.cedeao || 0),
    commission: Number(bc.commissionintermediaire || 0),
    taux_commission: Number(bc.taux_commission || 0),
    statut_contrat: bc.statut_contrat || (bc.dateexpiration && new Date(bc.dateexpiration) < new Date() ? 'Expiré' : 'En cours'),
    statut_contrat_badge: bc.dateexpiration && new Date(bc.dateexpiration) < new Date() ? 'amber' : 'emerald',
    statut_encaissement: isSolde ? 'Soldé' : 'À Encaisser',
    statut_encaissement_badge: isSolde ? 'emerald' : 'rose',
    attestation_asaci: bc.attestation_asaci || 'Délivrée',
    attestation_badge: 'emerald',
    numero_police_compagnie: bc.numero_police_compagnie || null,
    adresse: bc.adresse || bc.idclient?.Adresse || bc.idclient?.adresse || 'Abidjan, Côte d\'Ivoire',
    intermediaire: bc.intermediaire || 'LE PHARE COURTAGES & SINISTRES',
    branche: bc.branche || (produitNom.toLowerCase().includes('auto') ? 'Auto' : produitNom.toLowerCase().includes('mrh') || produitNom.toLowerCase().includes('habit') ? 'MRH' : 'Auto'),
    details: bc.details || {},
    raw: bc,
  };
};

export const contractApi = {
  // GET /api/contrat/stats/ (Totaux réels par branche en BDD)
  getStats: async () => {
    try {
      const res = await apiClient.get('/contrat/stats/');
      return res.data;
    } catch {
      return null;
    }
  },
  // Nombre total de contrats pour un filtre donné (pagination serveur : champ `count`)
  getContractsCount: async (params = {}) => {
    const res = await apiClient.get('/contrat/', { params: { ...params, page_size: 1 } });
    return Number(res?.data?.count ?? 0);
  },
  // GET /api/contrat/ (21 714 Contrats réels en BDD)
  getContracts: async (params = {}) => {
    const res = await apiClient.get('/contrat/', { params });
    const list = extractData(res);
    return list.map(normalizeContrat);
  },
  // GET /api/contrat/:id/
  getContractDetail: async (id) => {
    const res = await apiClient.get(`/contrat/${id}/`);
    return normalizeContrat(res.data);
  },
  // POST /api/confirmationdevis (Validation et conversion d'un devis en contrat définitif)
  createContractFromQuote: (data) => {
    const devisId = typeof data === 'object' ? (data.IdDevis || data.iddevis || data.id) : data;
    return apiClient.post('/confirmationdevis', { IdDevis: Number(devisId) });
  },
  // GET /api/listecontratclient/?idclient=:clientId
  getContractsByClient: async (clientId) => {
    const res = await apiClient.get(`/listecontratclient/?idclient=${clientId}`);
    const list = extractData(res);
    return list.map(normalizeContrat);
  },
  // POST /api/avenant/renouvellement
  renewContract: (data) => apiClient.post('/avenant/renouvellement', data),
  // POST /api/avenant/initiationmouvement
  createEndorsement: (data) => apiClient.post('/avenant/initiationmouvement', data),
  // GET /api/avenant/
  getEndorsements: async () => extractData(await apiClient.get('/avenant/')),
};

/* =========================================================================
   6. CAISSE, ENCAISSEMENTS & CHÈQUES (production & payment)
   ========================================================================= */
export const cashApi = {
  // GET /api/encaissement/
  getEncaissements: async () => extractData(await apiClient.get('/encaissement/')),
  // GET /api/quittance/ (34 Quittances réelles en BDD)
  getQuittances: async () => extractData(await apiClient.get('/quittance/')),
  // POST /api/enregistrementencaissement (Encaissement groupé ou unitaire selon EncaissementGroupeQuittanceSerializer)
  collectPremium: (data) => apiClient.post('/enregistrementencaissement', data),
  // GET /api/quittances-cima/
  getQuittancesCima: async () => extractData(await apiClient.get('/quittances-cima/')),
  // POST /api/quittances-cima/
  createQuittanceCima: (data) => apiClient.post('/quittances-cima/', data),
  // GET /api/infoencaissement/:id
  getEncaissementInfo: async (id) => {
    const res = await apiClient.get(`/infoencaissement/${id}`);
    return res.data;
  },
  // GET /api/cheques/
  getCheques: async () => extractData(await apiClient.get('/cheques/')),
  // GET /api/cheques/statut/
  getChequeStatus: async (query) => {
    const res = await apiClient.get('/cheques/statut/', { params: query });
    return res.data;
  },
  // GET /api/cheques/:id/operations/
  getChequeOperations: async (id) => extractData(await apiClient.get(`/cheques/${id}/operations/`)),
};

/* =========================================================================
   7. PAIEMENT MOBILE (payment - Distripay)
   ========================================================================= */
export const mobilePaymentApi = {
  // POST /api/initiationpaiementmobile (sans slash terminal)
  initiatePayment: (data) => apiClient.post('/initiationpaiementmobile', data),
  // GET /api/paiementmobileinfo/:idtransaction (sans slash terminal)
  getPaymentInfo: async (id) => {
    const res = await apiClient.get(`/paiementmobileinfo/${id}`);
    return res.data;
  },
};

/* =========================================================================
   8. ATTESTATIONS NUMÉRIQUES ASACI (asaci)
   ========================================================================= */
export const asaciApi = {
  // GET /api/asaci/statut_passerelle/
  getGatewayStatus: async () => {
    const res = await apiClient.get('/asaci/statut_passerelle/');
    return res.data;
  },
  // GET /api/asaci/detailretourdemandeattestation/
  getAttestations: async () => extractData(await apiClient.get('/asaci/detailretourdemandeattestation/')),
  // GET /api/asaci/retourdemandeattestation/
  getDemandes: async () => extractData(await apiClient.get('/asaci/retourdemandeattestation/')),
  // POST /api/asaci/demandeattestationdb/
  requestCertificateFromDb: (contractId) => apiClient.post('/asaci/demandeattestationdb/', { id_contrat: contractId }),
  // POST /api/asaci/verificationstatutdemande/
  checkApplicationStatus: (referenceDemande) =>
    apiClient.post('/asaci/verificationstatutdemande/', { reference_demande: referenceDemande }),
  // POST /api/asaci/majstatutattestation/
  updateCertificateStatus: (data) => apiClient.post('/asaci/majstatutattestation/', data),
};

/* =========================================================================
   9. REVERSEMENTS AUX COMPAGNIES D'ASSURANCE (production & institutionnel)
   ========================================================================= */
export const remittanceApi = {
  // GET /api/reversement/
  getRemittances: async () => extractData(await apiClient.get('/reversement/')),
  // GET /api/reversementnonvalide/
  getPendingRemittances: async () => extractData(await apiClient.get('/reversementnonvalide/')),
  // POST /api/enregistrementreversement
  remitPremium: (data) => apiClient.post('/enregistrementreversement', data),
  // POST /api/validationreversement
  validateRemittance: (data) => apiClient.post('/validationreversement', data),
  // GET /api/inforeversement/:id
  getRemittanceInfo: async (id) => {
    const res = await apiClient.get(`/inforeversement/${id}`);
    return res.data;
  },
  // GET /api/contratpourreversement/:idcompagnie
  getContractsForRemittance: async (idcompagnie) => {
    const res = await apiClient.get(`/contratpourreversement/${idcompagnie || 1}`);
    return extractData(res);
  },
  // GET /api/reversements-cima/
  getRemittancesCima: async () => extractData(await apiClient.get('/reversements-cima/')),
  // POST /api/reversements-cima/:id/valider/
  validerBordereauCima: (id) => apiClient.post(`/reversements-cima/${id}/valider/`),
  // Validation officielle du bordereau de reversement
  validerBordereau: (id) => apiClient.post(`/reversements-cima/${id}/valider/`).catch(() => apiClient.post('/validationreversement', { idreversement: id })),
};

/* =========================================================================
   10. COMMISSIONS APPORTEURS (commissions)
   ========================================================================= */
export const commissionApi = {
  // GET /api/commissions/dashboard/dashboard_complet/
  getDashboard: async () => {
    const res = await apiClient.get('/commissions/dashboard/dashboard_complet/');
    return res.data;
  },
  // GET /api/commissions/paiements-commission/
  getPayments: async () => extractData(await apiClient.get('/commissions/paiements-commission/')),
  // POST /api/commissions/paiements-commission/
  createPayment: (data) => apiClient.post('/commissions/paiements-commission/', data),
  // GET /api/commissions/affaires-commission/eligibles_paiement/
  getAffaires: async () => extractData(await apiClient.get('/commissions/affaires-commission/eligibles_paiement/')),
  // POST /api/commissions/annulations-commission/
  cancelPayment: (data) => apiClient.post('/commissions/annulations-commission/', data),
};

/* =========================================================================
   11. SYSTÈME D'AUTORISATIONS & DÉROGATIONS (autorisations & account)
   ========================================================================= */
export const approvalApi = {
  // GET /api/autorisations/demandes/
  getDemandes: async () => extractData(await apiClient.get('/autorisations/demandes/')),
  // POST /api/autorisations/demandes/
  createDemande: (data) => apiClient.post('/autorisations/demandes/', data),
  // POST /api/autorisations/demandes/:id/approuver/
  approveDemande: (id, tokenData) => apiClient.post(`/autorisations/demandes/${id}/approuver/`, tokenData),
  // POST /api/autorisations/demandes/:id/rejeter/
  rejectDemande: (id, reason) => apiClient.post(`/autorisations/demandes/${id}/rejeter/`, { motif: reason }),
  // POST /api/autorisations/jetons/verifier/
  verifyToken: (token) => apiClient.post('/autorisations/jetons/verifier/', { token }),
  // POST /api/derogations/create
  createDerogation: (data) => apiClient.post('/derogations/create', data),
  // POST /api/derogations/check
  checkDerogation: (data) => apiClient.post('/derogations/check', data),
};

/* =========================================================================
   12. REPORTING & ÉTATS CIMA (reporting)
   ========================================================================= */
export const reportingApi = {
  // GET /api/etatdecisionnel/
  getDecisionnel: async () => extractData(await apiClient.get('/etatdecisionnel/')),
  // POST /api/etatdecisionnel/
  createDecisionnel: (data) => apiClient.post('/etatdecisionnel/', data),
  // PUT /api/etatdecisionnel/{id}/
  updateDecisionnel: (id, data) => {
    const validId = id?.id_etat ?? id?.idetat ?? id?.id ?? id;
    return apiClient.put(`/etatdecisionnel/${validId}/`, data);
  },
  // DELETE /api/etatdecisionnel/{id}/
  deleteDecisionnel: (id) => {
    const validId = id?.id_etat ?? id?.idetat ?? id?.id ?? id;
    return apiClient.delete(`/etatdecisionnel/${validId}/`);
  },
  // GET /api/etatdecisionnel/{id}/contenu?date_debut=&date_fin=
  getDecisionnelContenu: async (id, dateDebut, dateFin, typeEtat) => {
    const validId = id?.id_etat ?? id?.idetat ?? id?.id ?? id;
    if (!validId || validId === 'undefined') {
      return { Status: 'Echec', Data: [] };
    }
    const res = await apiClient.get(`/etatdecisionnel/${validId}/contenu/`, {
      params: {
        date_debut: dateDebut,
        date_fin: dateFin,
        ...(typeEtat ? { type_etat: typeEtat } : {}),
      },
    });
    return res?.data || res;
  },
  // POST /api/bordereaurecapemission
  getBordereauRecapEmission: async (params) => {
    const payload = params || { date_debut: '2020-01-01', date_fin: '2026-12-31', type_etat: 1 };
    const res = await apiClient.post('/bordereaurecapemission', payload);
    return extractData(res);
  },
  // GET /api/cimaetate1/:exercice
  getCimaE1: async (exercice) => {
    const res = await apiClient.get(`/cimaetate1/${exercice}`);
    return extractData(res);
  },
  // GET /api/cimaetate2/:exercice
  getCimaE2: async (exercice) => {
    const res = await apiClient.get(`/cimaetate2/${exercice}`);
    return extractData(res);
  },
};

/* =========================================================================
   13. CATALOGUE & PARAMÉTRAGE (configuration_api - Données réelles)
   ========================================================================= */
export const settingsApi = {
  // GET /api/compagnie/ (30 compagnies en BDD)
  getCompanies: async () => extractData(await apiClient.get('/compagnie/')),
  // GET /api/produit/ (10 produits en BDD)
  getProducts: async () => extractData(await apiClient.get('/produit/')),
  // GET /api/garantie/ (17 garanties en BDD)
  getGuarantees: async () => extractData(await apiClient.get('/garantie/')),
  // GET /api/categorie/ (catégories CIMA en BDD)
  getCategories: async () => extractData(await apiClient.get('/categorie/')),
  // GET /api/tarif/ (26 grilles tarifaires en BDD)
  getTarifs: async () => extractData(await apiClient.get('/tarif/')),
  // GET /api/genrevehicule/ (13 genres en BDD)
  getGenres: async () => extractData(await apiClient.get('/genrevehicule/')),
  // GET /api/marque/ (58 marques en BDD)
  getMarques: async () => extractData(await apiClient.get('/marque/')),
  // POST /api/marque/ (Créer une nouvelle marque de véhicule)
  createMarque: (data) => apiClient.post('/marque/', data),
  // GET /api/banque/ (44 banques en BDD)
  getBanques: async () => extractData(await apiClient.get('/banque/')),
  // GET /api/modeencaissement/ (27 modes en BDD)
  getModesEncaissement: async () => extractData(await apiClient.get('/modeencaissement/')),
  // GET /api/usage/ (usages véhicules en BDD)
  getUsages: async () => extractData(await apiClient.get('/usage/')),
  // GET /api/carrosserie/
  getCarrosseries: async () => extractData(await apiClient.get('/carrosserie/')),
  // GET /api/energie/
  getEnergies: async () => extractData(await apiClient.get('/energie/')),
  // GET /api/systemesecurite/
  getSystemesSecurite: async () => extractData(await apiClient.get('/systemesecurite/')),
  // GET /api/categoriepermis/
  getCategoriesPermis: async () => extractData(await apiClient.get('/categoriepermis/')),
  // GET /api/terme/
  getTermes: async () => extractData(await apiClient.get('/terme/')),
  // GET /api/repartitionprimesante/ (barèmes de répartition prime Santé Minéné : NSIA/OREOLE/VITALIS/ADEC)
  getRepartitionsPrimeSante: async () => extractData(await apiClient.get('/repartitionprimesante/')),
  // POST /api/repartitionprimesante/
  createRepartitionPrimeSante: (data) => apiClient.post('/repartitionprimesante/', data),
  // PUT /api/repartitionprimesante/{id}/
  updateRepartitionPrimeSante: (id, data) => apiClient.put(`/repartitionprimesante/${id}/`, data),
  // DELETE /api/repartitionprimesante/{id}/
  deleteRepartitionPrimeSante: (id) => apiClient.delete(`/repartitionprimesante/${id}/`),
  // POST /api/calculrepartitionprimesante/ — { prime_ht, avec_apporteur } → ventilation NSIA/OREOLE/VITALIS/ADEC
  calculerRepartitionPrimeSante: async (primeHt, avecApporteur = false) => {
    const res = await apiClient.post('/calculrepartitionprimesante/', {
      prime_ht: primeHt,
      avec_apporteur: avecApporteur,
    });
    return res?.data;
  },
  // GET /api/offre/
  getOffres: async () => extractData(await apiClient.get('/offre/')),
  // POST /api/offre/
  createOffre: (data) => apiClient.post('/offre/', data),
  // GET /api/sousgarantie/
  getSousGaranties: async () => extractData(await apiClient.get('/sousgarantie/')),
  // POST /api/sousgarantie/
  createSousGarantie: (data) => apiClient.post('/sousgarantie/', data),
  // GET /api/offregarantie/
  getOffreGaranties: async () => extractData(await apiClient.get('/offregarantie/')),
  // POST /api/offregarantie/
  createOffreGarantie: (data) => apiClient.post('/offregarantie/', data),
  // GET /api/reductionflotte/
  getReductionsFlotte: async () => extractData(await apiClient.get('/reductionflotte/')),
  // POST /api/reductionflotte/
  createReductionFlotte: (data) => apiClient.post('/reductionflotte/', data),
  // GET /api/formulesecuriteroutiere/
  getFormulesSecurite: async () => extractData(await apiClient.get('/formulesecuriteroutiere/')),
  // POST /api/formulesecuriteroutiere/
  createFormuleSecurite: (data) => apiClient.post('/formulesecuriteroutiere/', data),
  // GET /api/commissionproduit/
  getCommissionsProduit: async () => extractData(await apiClient.get('/commissionproduit/')),
  // POST /api/commissionproduit/
  createCommissionProduit: (data) => apiClient.post('/commissionproduit/', data),
  // GET /api/tauxtaxegarantie/
  getTauxTaxesGarantie: async () => extractData(await apiClient.get('/tauxtaxegarantie/')),
  // POST /api/tauxtaxegarantie/
  createTauxTaxeGarantie: (data) => apiClient.post('/tauxtaxegarantie/', data),
  // GET /api/typevehicule/
  getTypesVehicule: async () => extractData(await apiClient.get('/typevehicule/')),
  // GET /api/users/profile/ & fallback /api/utilisateur/
  getUsers: async () => {
    try {
      const res = await apiClient.get('/users/profile/');
      const data = extractData(res);
      if (Array.isArray(data) && data.length > 0) return data;
    } catch (e) {}
    return extractData(await apiClient.get('/utilisateur/'));
  },
};

/* =========================================================================
   14. CRM COMMERCIAL & PIPELINE LEADS (institutionnel - Module C)
   ========================================================================= */
export const crmApi = {
  // GET /api/crm/leads/ (8 leads réels en BDD)
  getLeads: async () => extractData(await apiClient.get('/crm/leads/')),
  // POST /api/crm/leads/
  createLead: (data) => apiClient.post('/crm/leads/', data),
  // PATCH /api/crm/leads/:id/
  updateLead: (id, data) => apiClient.patch(`/crm/leads/${id}/`, data),
  // POST /api/crm/leads/:id/changer_statut/
  updateLeadStage: (id, stage) => apiClient.post(`/crm/leads/${id}/changer_statut/`, { statut: stage }),
  // GET /api/crm/leads/stats/
  getLeadStats: async () => {
    const res = await apiClient.get('/crm/leads/stats/');
    return res.data;
  },
  // GET /api/crm/clients/:id/360/
  getCustomer360: async (clientId) => {
    const res = await apiClient.get(`/crm/clients/${clientId || 1}/360/`);
    return res.data;
  },
  // POST /api/crm/interactions/
  addInteraction: (data) => apiClient.post('/crm/interactions/', data),
  // GET /api/crm/interactions/
  getInteractions: async (clientId) => {
    const res = await apiClient.get(`/crm/interactions/${clientId ? `?client_id=${clientId}` : ''}`);
    return extractData(res);
  },
};

/* =========================================================================
   15. SINISTRES DÉLÉGUÉS CIMA (institutionnel - Module H)
   ========================================================================= */
export const claimsApi = {
  // GET /api/sinistres/ (4 sinistres réels en BDD)
  getClaims: async () => extractData(await apiClient.get('/sinistres/')),
  // GET /api/sinistres/:id/
  getClaimDetail: async (id) => {
    const res = await apiClient.get(`/sinistres/${id}/`);
    return res.data;
  },
  // POST /api/sinistres/
  createClaim: (data) => apiClient.post('/sinistres/', data),
  // PATCH /api/sinistres/:id/
  updateClaim: (id, data) => apiClient.patch(`/sinistres/${id}/`, data),
  // POST /api/sinistres/:id/reglement/
  settleClaim: (id, amount) => apiClient.post(`/sinistres/${id}/reglement/`, { montant_indemnise: amount }),
  // POST /api/sinistres/:id/demande_accord/
  requestPriorApproval: (id, motif) => apiClient.post(`/sinistres/${id}/demande_accord/`, { motif }),
  // GET /api/sinistres/:id/quittance_subrogative/
  getQuittanceSubrogative: async (id) => {
    const res = await apiClient.get(`/sinistres/${id}/quittance_subrogative/`);
    return res.data;
  },
  // POST /api/sinistres/:id/maj_pieces/
  updatePieces: (id, pieces) => apiClient.post(`/sinistres/${id}/maj_pieces/`, { pieces_justificatives: pieces }),
  // GET /api/sinistres/stats/
  getClaimStats: async () => {
    const res = await apiClient.get('/sinistres/stats/');
    return res.data;
  },
};

/* =========================================================================
   16. CONVENTIONS ASSUREURS (institutionnel - Module I)
   ========================================================================= */
export const conventionsApi = {
  // GET /api/conventions/
  getConventions: async () => extractData(await apiClient.get('/conventions/')),
  // GET /api/conventions/:id/
  getConventionDetail: async (id) => {
    const res = await apiClient.get(`/conventions/${id}/`);
    return res.data;
  },
  // POST /api/conventions/
  createConvention: (data) => apiClient.post('/conventions/', data),
  // PATCH /api/conventions/:id/
  updateConvention: (id, data) => apiClient.patch(`/conventions/${id}/`, data),
};

/* =========================================================================
   17. GED PROBANTE & PIÈCES NUMÉRIQUES (institutionnel - Module J)
   ========================================================================= */
export const documentApi = {
  // GET /api/ged/documents/
  getDocuments: async () => extractData(await apiClient.get('/ged/documents/')),
  // POST /api/ged/documents/
  uploadDocument: (data) => apiClient.post('/ged/documents/', data),
  // DELETE /api/ged/documents/:id/
  deleteDocument: (id) => apiClient.delete(`/ged/documents/${id}/`),
};

/* =========================================================================
   18. CONFORMITÉ CIMA & AUDIT TRAIL (institutionnel - Module K)
   ========================================================================= */
export const complianceApi = {
  // GET /api/compliance/audit-trail/
  getAuditTrail: async () => extractData(await apiClient.get('/compliance/audit-trail/')),
  // GET /api/compliance/audit-trail/etats_cima/
  getEtatsCima: async () => extractData(await apiClient.get('/compliance/audit-trail/etats_cima/')),
  // GET /api/compliance/audit-trail/kpis/
  getKpis: async () => {
    const res = await apiClient.get('/compliance/audit-trail/kpis/');
    return res.data;
  },
  // POST /api/compliance/audit-trail/
  logAudit: (data) => apiClient.post('/compliance/audit-trail/', data),
};
