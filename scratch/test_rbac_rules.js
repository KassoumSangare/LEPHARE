/**
 * Automated Verification Script for RBAC Permissions & CIMA Business Rules
 */
import {
  ROLES,
  PERMISSIONS_MATRIX,
  canUser,
  validateBusinessRule,
} from '../frontend/src/utils/rbac.js';

console.log('=== STARTING RBAC & CIMA RULES VERIFICATION ===\n');

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
// 1. RBAC MATRIX CHECKS
// -------------------------------------------------------------
console.log('--- 1. Testing RBAC Role Permissions ---');

const adminUser = { role: ROLES.ADMIN };
const commercialUser = { role: ROLES.COMMERCIAL };
const financeUser = { role: ROLES.FINANCE };
const sinDirectorUser = { role: ROLES.DIR_SINISTRES };
const conformiteUser = { role: ROLES.CONFORMITE };

// Commercial permissions
assert(canUser(commercialUser, 'view', 'clients') === true, 'Commercial can view clients');
assert(canUser(commercialUser, 'create', 'quotes') === true, 'Commercial can create quotes');
assert(canUser(commercialUser, 'delete', 'contracts') === false, 'Commercial CANNOT delete contracts');
assert(canUser(commercialUser, 'delete', 'conventions') === false, 'Commercial CANNOT delete conventions');
assert(canUser(commercialUser, 'create', 'remittances') === false, 'Commercial CANNOT create remittances');

// Finance permissions
assert(canUser(financeUser, 'collect', 'cash') === true, 'Finance can collect cash');
assert(canUser(financeUser, 'create', 'remittances') === true, 'Finance can create remittances');
assert(canUser(financeUser, 'delete', 'clients') === false, 'Finance CANNOT delete clients');

// Sinistres Director permissions
assert(canUser(sinDirectorUser, 'settle', 'claims') === true, 'Sinistres Director can settle claims');
assert(canUser(sinDirectorUser, 'delete', 'remittances') === false, 'Sinistres Director CANNOT delete remittances');

// Conformite (Audit/Inspection) is Read-Only
assert(canUser(conformiteUser, 'view', 'contracts') === true, 'Conformite can view contracts');
assert(canUser(conformiteUser, 'create', 'quotes') === false, 'Conformite CANNOT create quotes');
assert(canUser(conformiteUser, 'edit', 'clients') === false, 'Conformite CANNOT edit clients');
assert(canUser(conformiteUser, 'delete', 'claims') === false, 'Conformite CANNOT delete claims');

// Admin permissions
assert(canUser(adminUser, 'delete', 'conventions') === true, 'Admin has delete permission on conventions');
assert(canUser(adminUser, 'create', 'users') === true, 'Admin can create users');
assert(canUser(adminUser, 'delete', 'users') === true, 'Admin can delete users');

// -------------------------------------------------------------
// 2. CIMA BUSINESS RULES: CLIENTS
// -------------------------------------------------------------
console.log('\n--- 2. Testing CIMA Client Deletion Rules ---');

const clientWithActiveContracts = {
  id: 1,
  nomcomplet: 'SOCIETE IVOIRIENNE DE TRANSPORT',
  codeclient: 'CL-2026-001',
  contrats_actifs: 3,
};

const clientClean = {
  id: 99,
  nomcomplet: 'Prospect Non Transforme',
  codeclient: 'CL-2026-099',
  contrats_actifs: 0,
};

const clientCheck1 = validateBusinessRule('delete', 'clients', clientWithActiveContracts);
assert(clientCheck1.allowed === false, 'Deleting client with active contracts is BLOCKED');
assert(clientCheck1.isBlockedByLaw === true, 'Client block is flagged as legal requirement (CIMA Art. 10 ans)');
assert(clientCheck1.alternativeAction === 'archive', 'Alternative action recommended is "archive"');

const clientCheck2 = validateBusinessRule('delete', 'clients', clientClean);
assert(clientCheck2.allowed === true, 'Deleting client with 0 contracts is ALLOWED');

// -------------------------------------------------------------
// 3. CIMA BUSINESS RULES: DEVIS (QUOTES)
// -------------------------------------------------------------
console.log('\n--- 3. Testing Quote Immutability Rules ---');

const consolidatedQuote = {
  id: 10,
  numerodevis: 'DEV-2026-001',
  statut: 'Consolidé',
};

const draftQuote = {
  id: 11,
  numerodevis: 'DEV-2026-011',
  statut: 'Provisoire',
};

const quoteCheck1 = validateBusinessRule('delete', 'quotes', consolidatedQuote);
assert(quoteCheck1.allowed === false, 'Deleting consolidated quote is BLOCKED');
assert(quoteCheck1.isBlockedByLaw === true, 'Consolidated quote is flagged as sealed audit proof');

const quoteCheck2 = validateBusinessRule('edit', 'quotes', consolidatedQuote);
assert(quoteCheck2.allowed === false, 'Editing consolidated quote is BLOCKED');

const quoteCheck3 = validateBusinessRule('delete', 'quotes', draftQuote);
assert(quoteCheck3.allowed === true, 'Deleting draft quote is ALLOWED');

// -------------------------------------------------------------
// 4. CIMA BUSINESS RULES: CONTRATS (POLICIES)
// -------------------------------------------------------------
console.log('\n--- 4. Testing Policy Deletion Prohibition (Art. 13) ---');

const activeContract = {
  id: 101,
  numeropolice: 'POL-2026-001',
  statut_encaissement: 'Soldé',
  montant_encaisse: 245000,
};

const contractDeleteCheck = validateBusinessRule('delete', 'contracts', activeContract);
assert(contractDeleteCheck.allowed === false, 'Direct deletion of contract is ABSOLUTELY PROHIBITED');
assert(contractDeleteCheck.alternativeAction === 'terminate', 'Alternative action recommended is "terminate" (Résiliation)');

const contractEditCheck = validateBusinessRule('edit', 'contracts', activeContract);
assert(contractEditCheck.allowed === false, 'Editing cashed contract without endorsement is BLOCKED');

// -------------------------------------------------------------
// 5. CIMA BUSINESS RULES: SINISTRES (CLAIMS)
// -------------------------------------------------------------
console.log('\n--- 5. Testing Claims Settlement Deletion Rules ---');

const settledClaim = {
  id: 501,
  numero_sinistre: 'SIN-2026-001',
  statut: 'Règlement validé',
  montant_indemnise: 850000,
};

const unindemnifiedClaim = {
  id: 502,
  numero_sinistre: 'SIN-2026-002',
  statut: 'Déclaré',
  montant_indemnise: 0,
};

const claimCheck1 = validateBusinessRule('delete', 'claims', settledClaim);
assert(claimCheck1.allowed === false, 'Deleting settled claim with disbursements is BLOCKED');

const claimCheck2 = validateBusinessRule('delete', 'claims', unindemnifiedClaim);
assert(claimCheck2.allowed === true, 'Deleting fresh unindemnified claim is ALLOWED');

// -------------------------------------------------------------
// 6. BUSINESS RULES: CRM LEADS
// -------------------------------------------------------------
console.log('\n--- 6. Testing CRM Lead Rules ---');

const wonLead = {
  id: 'PROSP-2026-001',
  nom_prospect: 'GROUPE SIFCA',
  statut: 'Gagné',
};

const incomingLead = {
  id: 'PROSP-2026-002',
  nom_prospect: 'NOUVEAU CONTACT',
  statut: 'Nouveau',
};

const leadCheck1 = validateBusinessRule('delete', 'leads', wonLead);
assert(leadCheck1.allowed === false, 'Deleting "Gagné" CRM lead is BLOCKED for conversion tracking');

const leadCheck2 = validateBusinessRule('delete', 'leads', incomingLead);
assert(leadCheck2.allowed === true, 'Deleting incoming lead is ALLOWED');

console.log(`\n=== RESULTS: ${testsPassed} PASSED, ${testsFailed} FAILED ===\n`);
if (testsFailed > 0) {
  process.exit(1);
}
