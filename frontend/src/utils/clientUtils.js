import { trierParLibelle } from './sortUtils';

/**
 * Qualités (stdqualite) proposées selon le type de personne du client : les civilités
 * (typepersonne 1 : Monsieur, Madame, Mademoiselle, dans cet ordre) pour une personne physique,
 * les types d'entreprise (typepersonne 2 : entreprise privée, association, ONG…, de A à Z)
 * pour une personne morale.
 */
export const qualitesSelonPersonne = (qualites, entreprise) => {
  const typePersonne = entreprise ? 2 : 1;
  const liste = (qualites || []).filter((q) => Number(q.TypePersonne) === typePersonne);
  return entreprise
    ? trierParLibelle(liste, (q) => q.Libelle)
    : [...liste].sort((a, b) => a.IdQualite - b.IdQualite);
};
