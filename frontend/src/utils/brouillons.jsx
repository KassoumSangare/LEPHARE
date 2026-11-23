import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Save } from 'lucide-react';
import { brouillonApi } from '../api/endpoints';
import { useToast } from '../context/ToastContext';

/* =========================================================================
   Brouillons de saisie des devis (demande du 2026-11-23 : « pour toute saisie permettre de la mettre en brouillon »).
   L'état du formulaire est gardé tel quel en JSON (table lephare_brouillon, production.Brouillon) et repris depuis le
   registre des devis via ?brouillon=<id>, depuis n'importe quel poste. Auto et IA gardent leur code d'origine ; les
   autres écrans utilisent useBrouillon et BoutonBrouillon ci-dessous.
   ========================================================================= */

// Type -> écran de reprise et libellés des étapes (registre des devis)
export const TYPES_BROUILLON = {
  DEVIS_AUTO: { libelle: 'Automobile', route: '/user/quotes/auto', etapes: { 1: '1. Contrat', 2: '2. Véhicule', 3: '3. Offre & décompte', 4: '4. Client / conducteur' } },
  DEVIS_IA: { libelle: 'Individuelle Accidents', route: '/user/quotes/ia', etapes: { 1: '1. Contrat', 2: '2. Souscripteur & assurés', 3: '3. Récapitulatif' } },
  DEVIS_SANTE: { libelle: 'Santé', route: '/user/quotes/sante' },
  DEVIS_OREOLE: { libelle: 'Oreole Santé', route: '/user/quotes/oreole-sante/nouveau' },
  DEVIS_AFA: { libelle: 'Assistance funéraire', route: '/user/quotes/afa' },
  DEVIS_MRH: { libelle: 'Multirisque habitation', route: '/user/quotes/mrh' },
  DEVIS_RC: { libelle: 'Responsabilité civile', route: '/user/quotes/rc' },
  DEVIS_MRP: { libelle: 'Multirisque professionnelle', route: '/user/quotes/mrp' },
  DEVIS_TOUS_DOMMAGES: { libelle: 'Tous dommages', route: '/user/quotes/tous-dommages' },
  DEVIS_VOYAGE: { libelle: 'Voyage', route: '/user/quotes/voyage' },
  DEVIS_TRANSPORT: { libelle: 'Transport GUCE', route: '/user/quotes/transport/guce' },
  DEVIS_TRANSPORT_HORS_GUCE: { libelle: 'Transport hors GUCE', route: '/user/quotes/transport/hors-guce' },
};

export const lienBrouillon = (b) => `${TYPES_BROUILLON[b.type_brouillon]?.route || '/user/quotes/auto'}?brouillon=${b.id}`;
export const etapeBrouillon = (b) => TYPES_BROUILLON[b.type_brouillon]?.etapes?.[b.etape] || (b.etape ? `Étape ${b.etape}` : '');

/**
 * Brouillon d'un écran de devis.
 *   type    : clé de TYPES_BROUILLON
 *   champs  : { cle: [valeur, setter] } — l'état du formulaire à garder (valeurs JSON : pas de File ni de fonction)
 *   etape / setEtape : étape du parcours (facultatif)
 *   libelle : () => texte affiché dans le registre (souscripteur, objet…)
 *   iddevis : devis existant en cours de modification (facultatif)
 *   apresReprise : (donnees) => appelé une fois les champs remis (facultatif)
 * Renvoie { brouillonId, enregistrer, supprimer, enregistrement, chargement, repriseEnCours }.
 * repriseEnCours reste vrai le temps de la reprise : les effets qui remettent des champs à zéro (changement d'offre,
 * de compagnie…) doivent l'attendre, sinon ils effacent ce que le brouillon vient de remettre.
 */
export function useBrouillon({ type, champs, etape, setEtape, libelle, iddevis = null, apresReprise }) {
  const { success, error: toastError, info } = useToast();
  const [searchParams] = useSearchParams();
  const parametre = searchParams.get('brouillon');
  const [brouillonId, setBrouillonId] = useState(null);
  const [enregistrement, setEnregistrement] = useState(false);
  const [chargement, setChargement] = useState(Boolean(parametre));
  const [repriseEnCours, setRepriseEnCours] = useState(Boolean(parametre));
  const champsRef = useRef(champs);
  champsRef.current = champs;
  const titre = TYPES_BROUILLON[type]?.libelle || 'devis';

  const enregistrer = async () => {
    setEnregistrement(true);
    const donnees = Object.fromEntries(Object.entries(champsRef.current).map(([cle, [valeur]]) => [cle, valeur === undefined ? null : valeur]));
    let texte = '';
    try { texte = (typeof libelle === 'function' ? libelle() : libelle) || ''; } catch { texte = ''; }
    const charge = {
      type_brouillon: type, libelle: String(texte || `Devis ${titre} sans souscripteur`).slice(0, 255),
      etape: Math.max(1, Number(etape) || 1), donnees, iddevis: Number(iddevis) || null,
    };
    try {
      const res = brouillonId ? await brouillonApi.update(brouillonId, charge) : await brouillonApi.create(charge);
      setBrouillonId(res.data.id);
      success(`Brouillon ${titre} enregistré : vous pourrez le reprendre depuis le registre des devis.`);
    } catch (err) {
      console.error(`Enregistrement du brouillon ${type} impossible`, err);
      const detail = err?.response?.data?.detail || JSON.stringify(err?.response?.data || '') || err.message;
      toastError(`Le brouillon n'a pas été enregistré : ${detail}.`);
    } finally {
      setEnregistrement(false);
    }
  };

  // Devis enregistré pour de bon : le brouillon n'a plus lieu d'être
  const supprimer = async () => {
    if (!brouillonId) return;
    try {
      await brouillonApi.remove(brouillonId);
      setBrouillonId(null);
    } catch (err) {
      console.error(`Suppression du brouillon ${type} impossible`, err);
      toastError('Le devis est enregistré, mais le brouillon n’a pas pu être supprimé (supprimez-le depuis le registre des devis).');
    }
  };

  useEffect(() => {
    if (!parametre) return undefined;
    let actif = true;
    brouillonApi.get(parametre)
      .then((brouillon) => {
        if (!actif || !brouillon) return;
        if (brouillon.type_brouillon !== type) {
          toastError(`Ce brouillon est un devis ${TYPES_BROUILLON[brouillon.type_brouillon]?.libelle || brouillon.type_brouillon}.`);
          return;
        }
        const donnees = brouillon.donnees || {};
        Object.entries(champsRef.current).forEach(([cle, [, setter]]) => {
          if (Object.prototype.hasOwnProperty.call(donnees, cle) && typeof setter === 'function') setter(donnees[cle]);
        });
        setBrouillonId(brouillon.id);
        if (setEtape) setEtape(Number(brouillon.etape) || 1);
        if (apresReprise) apresReprise(donnees);
        info(`Brouillon « ${brouillon.libelle || brouillon.id} » repris.`);
      })
      .catch((err) => {
        if (actif) {
          console.error(`Reprise du brouillon ${type} impossible`, err);
          toastError('Impossible de reprendre le brouillon.');
        }
      })
      .finally(() => {
        if (!actif) return;
        setChargement(false);
        // Les effets déclenchés par les champs remis passent d'abord, avec repriseEnCours encore vrai
        setTimeout(() => { if (actif) setRepriseEnCours(false); }, 0);
      });
    return () => { actif = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parametre]);

  return { brouillonId, enregistrer, supprimer, enregistrement, chargement, repriseEnCours };
}

export function BoutonBrouillon({ brouillon, disabled = false, style }) {
  if (!brouillon) return null;
  return (
    <button
      type="button"
      className="btn btn-secondary"
      onClick={brouillon.enregistrer}
      disabled={disabled || brouillon.enregistrement || brouillon.chargement}
      title="Enregistrer la saisie en cours pour la reprendre depuis le registre des devis"
      style={{ padding: '0.5rem 0.95rem', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '0.35rem', ...style }}
    >
      <Save size={14} />
      {brouillon.enregistrement ? 'Enregistrement…' : (brouillon.brouillonId ? 'Mettre à jour le brouillon' : 'Enregistrer le brouillon')}
    </button>
  );
}
