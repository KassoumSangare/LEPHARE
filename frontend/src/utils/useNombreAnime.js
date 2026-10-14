import { useEffect, useRef, useState } from 'react';

/**
 * Nombre affiché avec une transition quand sa valeur réelle change (compteurs d'onglets, indicateurs) :
 * de l'ancienne valeur à la nouvelle en `duree` ms. Première valeur, valeur inchangée, valeur absente ou
 * préférence « réduire les animations » : affichage direct. La valeur finale est toujours la valeur réelle.
 */
const mouvementReduit = () => typeof window !== 'undefined'
  && typeof window.matchMedia === 'function'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export const useNombreAnime = (valeur, duree = 450) => {
  const [affiche, setAffiche] = useState(valeur);
  const afficheRef = useRef(valeur);

  useEffect(() => {
    const depart = afficheRef.current;
    const fixer = (v) => { afficheRef.current = v; setAffiche(v); };
    if (typeof valeur !== 'number' || typeof depart !== 'number' || depart === valeur || mouvementReduit()) {
      fixer(valeur);
      return undefined;
    }
    let image;
    const debut = performance.now();
    const pas = (instant) => {
      const p = Math.min(1, (instant - debut) / duree);
      const amorti = 1 - (1 - p) ** 3;
      fixer(p < 1 ? Math.round(depart + (valeur - depart) * amorti) : valeur);
      if (p < 1) image = requestAnimationFrame(pas);
    };
    image = requestAnimationFrame(pas);
    return () => cancelAnimationFrame(image);
  }, [valeur, duree]);

  return affiche;
};

export default useNombreAnime;
