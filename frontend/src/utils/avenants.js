// Libellé d'un mouvement de police (stdavenant.codeavenant) : la table d'URANUS écrit en capitales sans accents
// (« RESILIATION »), les écrans affichent le libellé rédigé ; un code inconnu garde le libellé de la base.
export const LIBELLES_AVENANT = {
  AFN: 'Affaire nouvelle',
  REN: 'Renouvellement',
  INC: 'Incorporation',
  MOD: 'Modification',
  MPE: "Modification de prise d'effet",
  RPP: 'Reprise de portefeuille',
  TRP: 'Transfert de portefeuille',
  ANL: 'Annulation',
  ANP: 'Annulation pure',
  RET: 'Retrait',
  RES: 'Résiliation',
  CHI: "Changement d'immatriculation",
  CHV: 'Changement de véhicule',
  SUS: 'Suspension',
  REV: 'Remise en vigueur',
  PRG: 'Prorogation',
  ECT: 'Émission de certificat',
  ATP: 'Attestation provisoire',
};

export const libelleAvenant = (code, libelle = '') => {
  const connu = LIBELLES_AVENANT[String(code || '').trim().toUpperCase()];
  if (connu) return connu;
  const texte = String(libelle || '').trim();
  return texte ? texte.charAt(0) + texte.slice(1).toLowerCase() : String(code || '');
};
