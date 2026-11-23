import { useEffect, useRef } from 'react';

/**
 * Relit les chiffres d'un écran sans action de l'utilisateur (cockpit, tableau de bord : demande du 2026-11-23, « aucun
 * montant figé ») : toutes les `intervalle` ms tant que l'onglet est affiché, et dès le retour sur l'onglet ou la fenêtre
 * si la dernière lecture date de plus de `delaiRetour` ms. Onglet masqué : aucune lecture.
 * `majLe` : instant (ms) de la dernière lecture réussie, qu'elle vienne de ce hook ou du bouton « Actualiser ».
 */
export const useActualisationAuto = (actualiser, majLe, { intervalle = 60 * 1000, delaiRetour = 15 * 1000 } = {}) => {
  const rappel = useRef(actualiser);
  const derniere = useRef(Date.now());

  useEffect(() => { rappel.current = actualiser; }, [actualiser]);
  useEffect(() => { if (majLe) derniere.current = majLe; }, [majLe]);

  useEffect(() => {
    const visible = () => typeof document === 'undefined' || document.visibilityState === 'visible';
    // L'instant de la tentative compte aussi : une lecture en échec est retentée à l'intervalle suivant, pas en boucle
    const lire = () => { derniere.current = Date.now(); rappel.current(); };
    const minuterie = setInterval(() => {
      if (visible() && Date.now() - derniere.current >= intervalle) lire();
    }, Math.min(intervalle, 15 * 1000));
    const auRetour = () => { if (visible() && Date.now() - derniere.current > delaiRetour) lire(); };
    document.addEventListener('visibilitychange', auRetour);
    window.addEventListener('focus', auRetour);
    return () => {
      clearInterval(minuterie);
      document.removeEventListener('visibilitychange', auRetour);
      window.removeEventListener('focus', auRetour);
    };
  }, [intervalle, delaiRetour]);
};

export default useActualisationAuto;
