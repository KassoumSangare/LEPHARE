/**
 * Automated Verification Script for Voyage & Transport Quotes and CIMA Policies
 */

// Mock localStorage and window for Node.js test environment
const store = {};
global.localStorage = {
  getItem: (key) => store[key] || null,
  setItem: (key, val) => { store[key] = String(val); },
  removeItem: (key) => { delete store[key]; },
  clear: () => { Object.keys(store).forEach(k => delete store[k]); }
};

global.window = {
  dispatchEvent: () => {},
  addEventListener: () => {},
  removeEventListener: () => {}
};
global.CustomEvent = class {
  constructor(type, opts) {
    this.type = type;
    this.detail = opts ? opts.detail : null;
  }
};

import { dataStore } from '../frontend/src/api/dataStore.js';
import { validateBusinessRule } from '../frontend/src/utils/rbac.js';

console.log('=== STARTING VOYAGE & TRANSPORT QUOTES VERIFICATION ===\n');

let testsPassed = 0;
let testsFailed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ PASS: ${message}`);
    testsPassed++;
  } else {
    console.error(`  ✗ FAIL: ${message}`);
    testsFailed++;
  }
}

// -------------------------------------------------------------
// 1. TEST CREATION: DEVIS ASSURANCE VOYAGE & SCHENGEN
// -------------------------------------------------------------
console.log('--- 1. Testing Devis Voyage Creation & Calculation ---');

const clients = dataStore.getClients();
const client = clients[0];

const voyagePayload = {
  client_nom: client.nomcomplet,
  client_id: client.id,
  produit: 'Assurance Voyage (Formule Schengen Standard)',
  branche: 'Voyage',
  compagnie: 'AXA Assurances Côte d’Ivoire',
  prime_nette: 30800,
  accessoires: 5000,
  taxes: 4466,
  prime_totale: 40266,
  date_emission: '2026-09-06',
  statut: 'En attente',
  statut_badge: 'amber',
  details: {
    zone: 'Zone 2 : Espace Schengen & Europe',
    paysDestination: 'France (Espace Schengen)',
    motifVoyage: 'Tourisme & Vacances',
    dureeJours: 14,
    formule: 'Formule Schengen Standard',
    plafondMedical: '30 000 € (~19 680 000 FCFA)',
    voyageurs: [
      { nom: 'KOUAME', prenom: 'Jean-Yves', passeport: '24CI99881', dateNaissance: '1985-06-12' },
    ],
  },
};

const savedVoyage = dataStore.saveQuote(voyagePayload);
assert(Boolean(savedVoyage.id), 'Voyage quote was assigned an ID');
assert(savedVoyage.numerodevis.startsWith('DEV-VOYAGE-2026-'), `Generated quote number is formatted (${savedVoyage.numerodevis})`);
assert(savedVoyage.branche === 'Voyage', 'Quote branch is Voyage');
assert(savedVoyage.prime_totale === 40266, 'Prime totale TTC is accurate');

// Verify quote appears in list
const quotesAfterVoyage = dataStore.getQuotes();
const foundVoyage = quotesAfterVoyage.find((q) => q.id === savedVoyage.id);
assert(Boolean(foundVoyage), 'Voyage quote is retrievable from dataStore');

// -------------------------------------------------------------
// 2. TEST CREATION: DEVIS ASSURANCE TRANSPORT (FACULTÉS)
// -------------------------------------------------------------
console.log('\n--- 2. Testing Devis Transport Creation & Calculation ---');

const transportPayload = {
  client_nom: client.nomcomplet,
  client_id: client.id,
  produit: 'Assurance Transport Facultés (Maritime)',
  branche: 'Transport',
  compagnie: 'SANLAM Assurances CI (Département Transport)',
  prime_nette: 88000,
  accessoires: 10000,
  taxes: 12760,
  prime_totale: 110760,
  date_emission: '2026-09-06',
  statut: 'En attente',
  statut_badge: 'amber',
  details: {
    modeTransport: 'Transport Maritime (FCL / LCL)',
    natureMarchandise: 'Marchandises Générales & Biens Manufacturés',
    incoterm: 'FOB (Free on Board)',
    typeGarantie: 'Tous Risques (All Risks / Clauses A)',
    portDepart: 'Shanghai (Chine)',
    portArrivee: 'Port Autonome d’Abidjan (Côte d’Ivoire)',
    numeroBlLta: 'MEDU-ABJ-2026-889',
    valeurFacture: 25000000,
    sommeAssuree: 27500000, // Facture + 10%
  },
};

const savedTransport = dataStore.saveQuote(transportPayload);
assert(Boolean(savedTransport.id), 'Transport quote was assigned an ID');
assert(savedTransport.numerodevis.startsWith('DEV-TRANSPORT-2026-'), `Generated quote number is formatted (${savedTransport.numerodevis})`);
assert(savedTransport.branche === 'Transport', 'Quote branch is Transport');
assert(savedTransport.prime_totale === 110760, 'Prime totale TTC is accurate');

// Verify quote appears in list
const quotesAfterTransport = dataStore.getQuotes();
const foundTransport = quotesAfterTransport.find((q) => q.id === savedTransport.id);
assert(Boolean(foundTransport), 'Transport quote is retrievable from dataStore');

// -------------------------------------------------------------
// 3. TEST CONVERSION TO CONTRACTS
// -------------------------------------------------------------
console.log('\n--- 3. Testing Conversion of Quotes into Policies ---');

// Convert Voyage quote
const { contract: voyageContract } = dataStore.convertQuoteToContract(savedVoyage);
assert(Boolean(voyageContract), 'Voyage contract was created');
assert(voyageContract.numeropolice.startsWith('POL-2026-'), `Policy number is formatted (${voyageContract.numeropolice})`);
assert(voyageContract.devis_origine === savedVoyage.numerodevis, 'Origin quote is referenced');

// Check that Voyage quote is now 'Consolidé'
const refreshedVoyageQuote = dataStore.getQuoteById(savedVoyage.id);
assert(refreshedVoyageQuote.statut === 'Consolidé', 'Voyage quote is now marked as "Consolidé"');

// Convert Transport quote
const { contract: transportContract } = dataStore.convertQuoteToContract(savedTransport);
assert(Boolean(transportContract), 'Transport contract was created');
assert(transportContract.numeropolice.startsWith('POL-2026-'), `Policy number is formatted (${transportContract.numeropolice})`);
assert(transportContract.devis_origine === savedTransport.numerodevis, 'Origin quote is referenced');

// Check that Transport quote is now 'Consolidé'
const refreshedTransportQuote = dataStore.getQuoteById(savedTransport.id);
assert(refreshedTransportQuote.statut === 'Consolidé', 'Transport quote is now marked as "Consolidé"');

// -------------------------------------------------------------
// 4. TEST CIMA RULES ON CONSOLIDATED VOYAGE & TRANSPORT
// -------------------------------------------------------------
console.log('\n--- 4. Testing CIMA Immutability on Consolidated Quotes ---');

const checkDeleteVoyage = validateBusinessRule('delete', 'quotes', refreshedVoyageQuote, dataStore);
assert(checkDeleteVoyage.allowed === false, 'Deleting consolidated Voyage quote is BLOCKED by CIMA');

const checkDeleteTransport = validateBusinessRule('delete', 'quotes', refreshedTransportQuote, dataStore);
assert(checkDeleteTransport.allowed === false, 'Deleting consolidated Transport quote is BLOCKED by CIMA');

const checkDeletePolicy = validateBusinessRule('delete', 'contracts', transportContract, dataStore);
assert(checkDeletePolicy.allowed === false, 'Deleting transport policy is ABSOLUTELY BLOCKED by Art. 13 CIMA');

console.log(`\n=== RESULTS: ${testsPassed} PASSED, ${testsFailed} FAILED ===\n`);
if (testsFailed > 0) {
  process.exit(1);
}
