// Branches de devis ouvertes pendant la mise au point du module Automobile. Les autres restent
// affichées mais grisées (menu, boutons de création, « Modifier » du registre). Les clés sont
// celles des routes /user/quotes/<module> : ajouter une clé ici rouvre la branche partout.
export const MODULES_ACTIFS = ['auto'];

export const moduleActif = (module) => MODULES_ACTIFS.includes(module);

export const TITRE_MODULE_INACTIF = 'Module indisponible pour le moment : seul le module Automobile est ouvert';
