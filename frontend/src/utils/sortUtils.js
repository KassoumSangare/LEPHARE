/**
 * Trie une liste par ordre alphabétique (locale FR, insensible à la casse/accents)
 * et retire les doublons selon la clé fournie, sans muter le tableau d'origine.
 * Utilisé pour toutes les listes déroulantes de l'application (clients, compagnies,
 * marques, offres, garanties, etc.) afin qu'elles restent lisibles et sans répétition.
 */
export const sortUniqueBy = (list, getKey) => {
  if (!Array.isArray(list)) return [];
  const seen = new Set();
  const unique = [];
  for (const item of list) {
    const key = String(getKey(item) ?? '').trim();
    const dedupeKey = key.toLocaleLowerCase('fr-FR');
    if (seen.has(dedupeKey)) continue;
    seen.add(dedupeKey);
    unique.push(item);
  }
  return unique.sort((a, b) =>
    String(getKey(a) ?? '').localeCompare(String(getKey(b) ?? ''), 'fr-FR', { sensitivity: 'base' })
  );
};
