// Branches de devis ouvertes à la saisie : réglées dans Administration > Produits (colonne
// « Saisie ouverte », lephare_produit_parametre). Les autres restent affichées mais grisées
// (boutons de création, « Modifier » du registre). Les clés sont celles des routes /user/quotes/<module>.
// La création exige aussi le droit « Créer un devis » de l'utilisateur (Administration > Rôles).
import { moduleOuvert } from './parametrage';
import { aLeDroit } from './droits';

export const moduleActif = (module) => moduleOuvert(module) && aLeDroit('devis.create');

export const TITRE_MODULE_INACTIF =
  "Indisponible : la saisie de cette branche n'est pas ouverte (Administration > Produits) ou vos rôles ne permettent pas de créer un devis";
