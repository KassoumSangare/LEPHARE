// Registre des devis : uniquement les devis en attente de confirmation (ni archivés, ni
// confirmés, ni expirés). Un devis confirmé devient un contrat ; le Portefeuille des Contrats,
// lui, ne liste que des contrats.
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
