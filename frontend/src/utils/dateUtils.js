/**
 * Formate une date en jj/mm/aaaa, quel que soit le format reçu (ISO, timestamp...).
 * Utilisé pour tout affichage de date en lecture seule dans l'application — jamais
 * pour la valeur d'un <input type="date">, qui doit rester au format aaaa-mm-jj.
 */
export const formatDate = (value) => {
  if (!value) return '—';
  const d = new Date(value);
  if (isNaN(d.getTime())) return String(value);
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
};

/** Formate une date avec l'heure, en jj/mm/aaaa hh:mm. */
export const formatDateTime = (value) => {
  if (!value) return '—';
  const d = new Date(value);
  if (isNaN(d.getTime())) return String(value);
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
