/**
 * Boîte de saisie du motif exigé par le serveur pour une opération sensible (réponse 428
 * « motif_requis » de la garde centrale) : confirmation explicite + justification, rejouée ensuite
 * avec l'en-tête X-Motif. Boîte commune de utils/dialogue.js (utilisable depuis apiClient, hors React).
 * Renvoie le motif saisi, ou null si l'utilisateur annule.
 */
import { saisirTexte } from './dialogue';

const LONGUEUR_MIN = 5;
let enCours = null;

export const demanderMotif = (libelleOperation) => {
  if (enCours) return enCours;
  enCours = saisirTexte({
    ton: 'attention',
    titre: "Confirmer l'opération",
    message: `« ${libelleOperation || 'Opération sensible'} » est une opération sensible : indiquez le motif.`,
    consequences: "Le motif sera enregistré au journal d'audit avec votre nom, la date et les valeurs avant / après.",
    placeholder: "Motif de l'opération…",
    minimum: LONGUEUR_MIN,
    confirmer: 'Confirmer avec ce motif',
  }).finally(() => { enCours = null; });
  return enCours;
};
