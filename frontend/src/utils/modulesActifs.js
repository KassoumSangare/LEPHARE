// Branches de devis ouvertes à la saisie : réglées dans Administration > Produits (colonne
// « Saisie ouverte », lephare_produit_parametre). Les autres restent affichées mais grisées
// (boutons de création, « Modifier » du registre). Les clés sont celles des routes /user/quotes/<module>.
import { moduleOuvert } from './parametrage';

export const moduleActif = (module) => moduleOuvert(module);

export const TITRE_MODULE_INACTIF =
  "Module indisponible pour le moment : la saisie de cette branche n'est pas ouverte (Administration > Produits)";
