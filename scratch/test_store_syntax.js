// Mock browser globals for Node.js
global.window = {};
global.localStorage = {
  _store: {},
  getItem(k) { return this._store[k] || null; },
  setItem(k, v) { this._store[k] = String(v); },
  removeItem(k) { delete this._store[k]; },
  clear() { this._store = {}; }
};
global.CustomEvent = class { constructor(type, detail) { this.type = type; this.detail = detail; } };
global.window.dispatchEvent = () => {};

import('../frontend/src/api/dataStore.js').then(({ dataStore }) => {
  console.log('--- TESTING DYNAMIC DATASTORE CONFIG ---');
  
  // 1. Test getTarifForBranch
  const autoTarif = dataStore.getTarifForBranch('Auto');
  console.log('Auto Tarif:', autoTarif);
  if (autoTarif.taxRate !== 0.145 || autoTarif.accessoires !== 15000) {
    throw new Error('Auto tarif mismatch');
  }

  const voyageTarif = dataStore.getTarifForBranch('Voyage');
  console.log('Voyage Tarif:', voyageTarif);
  if (voyageTarif.taxRate !== 0.145 || voyageTarif.accessoires !== 5000) {
    throw new Error('Voyage tarif mismatch');
  }

  const transportTarif = dataStore.getTarifForBranch('Transport');
  console.log('Transport Tarif:', transportTarif);
  if (transportTarif.taxRate !== 0.145 || transportTarif.accessoires !== 10000) {
    throw new Error('Transport tarif mismatch');
  }

  const santeTarif = dataStore.getTarifForBranch('Santé');
  console.log('Santé Tarif:', santeTarif);
  if (santeTarif.taxRate !== 0.0) {
    throw new Error('Santé tax should be 0');
  }

  // 2. Test dynamic modification of tariff
  dataStore.saveTarif({
    id: 99,
    produit: 'Voyage & Schengen',
    libelle: 'Tarif Spécial Test',
    taux_taxe: '18.0%',
    frais_accessoires: '7 500 FCFA',
    date_effet: '2026-09-01',
    statut: 'Vigueur'
  });
  const updatedVoyage = dataStore.getTarifForBranch('Voyage');
  console.log('Updated Voyage Tarif:', updatedVoyage);
  if (updatedVoyage.taxRate !== 0.18 || updatedVoyage.accessoires !== 7500) {
    throw new Error('Dynamic tariff update failed!');
  }

  // 3. Test active companies
  const activeVoyageComps = dataStore.getActiveCompanies('Voyage');
  console.log('Active Voyage Companies count:', activeVoyageComps.length);
  if (activeVoyageComps.length === 0) {
    throw new Error('Expected active voyage companies');
  }

  // 4. Test Voyage zones and formulas
  const zones = dataStore.getVoyageZones();
  const formules = dataStore.getVoyageFormules();
  console.log('Voyage zones count:', zones.length, 'Formules count:', formules.length);
  if (zones.length < 4 || formules.length < 3) {
    throw new Error('Voyage collections incomplete');
  }

  // 5. Test Transport modes and natures
  const modes = dataStore.getTransportModes();
  const natures = dataStore.getTransportNatures();
  console.log('Transport modes count:', modes.length, 'Natures count:', natures.length);
  if (modes.length < 4 || natures.length < 6) {
    throw new Error('Transport collections incomplete');
  }

  console.log('ALL DYNAMIC DATASTORE TESTS PASSED SUCCESSFULLY!');
}).catch((err) => {
  console.error('Test failed:', err);
  process.exit(1);
});
