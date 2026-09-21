// Registre des devis : seuls les devis à confirmer (attente) sont listés.
// Les devis confirmés (statut confirmé / contrat) passent dans la liste des contrats,
// les devis archivés sont masqués.
// Un devis expiré (non confirmé) sort du registre : il est repris dans le Portefeuille des Contrats (à renouveler).
export const isExpiredQuote = (q) => {
  if (!q?.date_expiration) return false;
  const d = new Date(q.date_expiration);
  if (isNaN(d.getTime())) return false;
  return d < new Date(new Date().toISOString().split('T')[0]);
};

export const isRegistryQuote = (q) => {
  const s = (q?.statut || '').toLowerCase();
  return !q?.archive && !q?.confirme && !s.includes('confirm') && !s.includes('contrat') && !isExpiredQuote(q);
};
