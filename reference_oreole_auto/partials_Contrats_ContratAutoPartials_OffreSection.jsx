import { useEffect, useState, useRef, useMemo } from "react";
import { postOffre, reset, updateOffres, setHasModifications, clearModifications, selectOffresByDevisId, selectHasModsByDevisId } from "features/Offre/offreSlice";
import { useDispatch, useSelector } from "react-redux";
import moment from "moment";
import { ButtonNext, OutlineButton } from "partials/UI/Button/Button";
import { toast } from "react-hot-toast";
import { correctionDevis } from "features/CorrectionDevis/correctionDevisSlice";
import {
  setEditingMode,
  updateEditedPrimes,
  clearEditedPrimes
} from "features/Garanties/garantieSlice";



function OffreSection({

  nextStep,
  offre,
  setOffre,
  prevStep,

  compagnie,

  premiereCirculation,

  reduction,

  systemeSecurites,

  dateEffet,

  dateEmission,

  nsiaAutoPlus,

  dateExpiration,

  bonusmalus,

  offreSectionData,

  categorie,

  valeurNeuf,

  valeurVenale,

  valeurAccessoire,

  puissancefiscale,

  chargeUtile,

  energie,

  setCheckedState,

  setPrimeAnnuelle,

  setPrimeNette,

  PrimeAnnuelle,

  PrimeNette,

  checkedState,

  typeContrat,

  remorqueAttelee,

  securiteRoutiere,

  nbrPlace,

  CarburantAutreMatiere,

  TransportEleves,

  TransportEmployes,

  TransportPassageSupplementaire,

  usage,

  assistanceAuto,

  offreState,

  isEditPolice,

  onCorrectionDataReady,

}) {

  const dispatch = useDispatch();

  const offresList = offreSectionData.offres;
  console.log("RRRoffresList:",offresList);



  const [cumulPrimeTTC, setCumulPrimeTTC] = useState(0);

  const [showAddDropdown, setShowAddDropdown] = useState(false);
  const [selectedGarantieId, setSelectedGarantieId] = useState("");
  const [newGarantieForm, setNewGarantieForm] = useState({
    acquise: true,
    capital: "0",
    prime_annuelle: "0",
    prime_nette: "0",
    montant_franchise: "0",
    taux_franchise: "0",
    franchise_minimum: "0",
    franchise_maximum: "0",
    capital_deces: "0",
    capital_ipp: "0",
    capital_ft: "0",
    reduction_commerciale: "0",
    reduction_bns: "0",
  });
  const [hydrated, setHydrated] = useState(false); // évite le fetch avant restauration locale
  const [loadedFromCache, setLoadedFromCache] = useState(false); // indique qu'on a restauré des offres corrigées
  const [restorationSource, setRestorationSource] = useState(null); // 'localStorage' ou 'api' ou null
  const devisSavedState = useSelector((state) => state.devis?.devisSaved);
  const [sousGarantiesAll, setSousGarantiesAll] = useState([]);
  const [deletedGaranties, setDeletedGaranties] = useState([]); // IDs des garanties supprimées
  const [editedExtras, setEditedExtras] = useState({ taxe: "", accessoire: "", cedeao: "", fga: "" });
  const [editedTotals, setEditedTotals] = useState({ pa: "", pn: "", ttc: "" });
  const [detailsBeforeEdit, setDetailsBeforeEdit] = useState(null);
  console.log("RRRdetailsBeforeEdit:",detailsBeforeEdit);

  // Normalisation fiable des nombres venant de l'API ou saisis (espaces, virgules, libellés)
  const toNumber = (value) => {
    try {
      if (value === null || value === undefined) return 0;

      if (typeof value === 'number' && Number.isFinite(value)) return value;
      let str = String(value).trim();
      if (!str) return 0;
      const lower = str.toLowerCase();
      if (["neant", "néant", "xx", "x", "n/a", "na", "-"].includes(lower)) return 0;
      str = str.replace(/\s+/g, '').replace(/,/g, '.');
      str = str.replace(/[^0-9.+-]/g, '');
      const n = parseFloat(str);
      return Number.isNaN(n) ? 0 : n;
    } catch {
      return 0;
    }
  };

  // Helper pour CEDEAO: valeur par défaut 1000 si non définie ou <= 0, et arrondi au multiple de 1000
  const ensureCedeaoMin = (value, fallback = 0) => {
    try {
      const num = toNumber(value);
      if (num <= 0) return fallback;
      // Arrondir au multiple de 1000 le plus proche
      return Math.round(num / 1000) * 1000;
    } catch {
      return fallback;
    }
  };

  // Formatage français pour l'affichage (séparateurs de milliers)
  const formatFr = (val) => {
    try {
      if (val === '' || val === null || val === undefined) return '';
      const n = toNumber(val);
      if (isNaN(n)) return '';
      return new Intl.NumberFormat('fr-FR').format(n);
    } catch {
      return '';
    }
  };

  // Dé-formatage d'une saisie utilisateur vers une chaîne numérique brute
  const unformat = (str) => {
    try {
      if (str == null) return '';
      const s = String(str).replace(/\s+/g, '').replace(/\u00A0/g, '').replace(/,/g, '.').replace(/[^0-9.+-]/g, '');
      return s;
    } catch {
      return '';
    }
  };
  // Sauvegarde explicite: applique les valeurs, persiste, quitte l'édition et rafraîchit l'affichage
  const saveToLocal = (devisId, payload) => {
    try {
      const key = `offres_editees_${devisId}`;
      const prev = JSON.parse(localStorage.getItem(key) || '{}');
      localStorage.setItem(key, JSON.stringify({ ...prev, ...payload }));
    } catch (_) { }
  };

  // (supprimé) Ancienne implémentation locale de handleSavePrimes — la version principale se trouve plus bas

  // Sécuriser les messages destinés aux toasts pour éviter de passer des objets React non valides
  const toHumanMessage = (val) => {
    try {
      if (val == null) return '';
      if (typeof val === 'string') return val;
      if (typeof val === 'number' || typeof val === 'boolean') return String(val);
      if (typeof val === 'object') {
        // Si l'objet possède un champ 'message' texte, le privilégier
        if (typeof val.message === 'string' && val.message.trim()) return val.message;
        // Sinon, sérialiser proprement
        return JSON.stringify(val);
      }
      return String(val);
    } catch (_) {
      return 'Erreur inconnue';
    }
  };

  // Essayer de récupérer l'id_devis depuis l'URL si le state Redux n'est pas encore initialisé
  const routeDevisId = useMemo(() => {
    try {
      const path = window?.location?.pathname || '';
      // Supporter /edition-devis/:produit/:id et /details-devis/:id
      const matchEdition = path.match(/edition-devis\/(?:\d+)\/(\d+)/);
      const matchDetails = path.match(/details-devis\/(\d+)/);
      const id = matchEdition ? parseInt(matchEdition[1], 10) : (matchDetails ? parseInt(matchDetails[1], 10) : null);
      return Number.isFinite(id) ? id : null;
    } catch {
      return null;
    }
  }, []);
  const draftKeyRef = useRef(`draft_${Date.now()}`);
  const devisId = devisSavedState?.IdDevis || devisSavedState?.id_devis || devisSavedState?.id || routeDevisId;
  const effectiveDevisId = Number.isFinite(parseInt(devisId)) ? parseInt(devisId) : routeDevisId || draftKeyRef.current;
  const offres = useSelector((state) => selectOffresByDevisId(state, effectiveDevisId));
  const hasModifications = useSelector((state) => selectHasModsByDevisId(state, effectiveDevisId));
  const { isError, isSucess, message } = useSelector((state) => state.offres);
  const { user, token } = useSelector((state) => state.auth);
  const isRestoringRef = useRef(false);
  const isFinalizedRef = useRef(false);
  const authoritativeGarantiesRef = useRef(null);

  // Résolution fiable de l'ID devis (priorité: Redux -> URL -> effectiveDevisId numérique)
  const getResolvedDevisId = () => {
    try {
      const fromRedux = devisSaved?.IdDevis || devisSaved?.id_devis || devisSaved?.id || devisSavedState?.IdDevis || devisSavedState?.id_devis || devisSavedState?.id;
      const candidates = [fromRedux, routeDevisId, effectiveDevisId];
      for (const c of candidates) {
        const n = parseInt(c);
        if (Number.isFinite(n) && n > 0) return n;
      }
    } catch (_) { }
    return null;
  };

  const devisSaved = useSelector((state) => state.devis?.devisSaved);

  const correctionsState = useSelector((state) => state.corrections || {});

  const correctionError = correctionsState?.isError || false;

  const correctionSuccess = correctionsState?.isSuccess || false;

  const correctionMessage = correctionsState?.message || '';



  // Récupérer les données depuis Redux

  const { isEditing, editedPrimes } = useSelector((state) => state.garanties);

  // Récupérer les détails du devis depuis le backend (pour afficher les valeurs originales)
  useEffect(() => {
    const fetchDetailsBeforeEdit = async () => {
      if (!effectiveDevisId || !token) return;
      try {
        const apiUrl = `${process.env.REACT_APP_API_URL || ''}devis/${effectiveDevisId}/`;
        const response = await fetch(apiUrl, {
          method: 'GET',
          headers: {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json',
          },
        });
        if (response.ok) {
          const data = await response.json();
          setDetailsBeforeEdit(data);
        }
      } catch (e) {
        console.warn('Erreur lors de la récupération des détails du devis:', e);
      }
    };
    fetchDetailsBeforeEdit();
  }, [effectiveDevisId, token]);

  // Charger les sous-garanties depuis l'API quand on ouvre le dropdown
  // Fonction déplacée ici pour avoir accès au token depuis Redux
  const fetchSousGaranties = async () => {
    try {
      console.log('🔄 Chargement des sous-garanties...');
      const apiUrl = `${process.env.REACT_APP_API_URL || ''}sousgarantie/`;
      console.log('🔗 URL API:', apiUrl);
      console.log('🔑 Token disponible:', !!token);
      const response = await fetch(apiUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json',
        },
      });
      console.log('📡 Réponse API:', response.status, response.statusText);

      if (response.ok) {
        const data = await response.json();
        console.log('📊 Données reçues (type):', typeof data);
        console.log('📊 Données reçues (structure complète):', data);
        console.log('📊 Est un tableau?', Array.isArray(data));
        console.log('📊 Clés de l\'objet:', Object.keys(data));

        // Gérer les deux cas: tableau direct ou objet paginé avec 'results'
        let garantiesArray = [];
        if (Array.isArray(data)) {
          garantiesArray = data;
          console.log('✅ Format tableau direct détecté');
        } else if (data && typeof data === 'object') {
          // Vérifier si c'est un objet paginé avec 'results'
          if (Array.isArray(data.results)) {
            garantiesArray = data.results;
            console.log('✅ Format paginé détecté (results)');
          } else if (Array.isArray(data.data)) {
            garantiesArray = data.data;
            console.log('✅ Format avec propriété data détecté');
          } else {
            console.warn('⚠️ Structure de réponse non reconnue:', data);
          }
        }

        console.log('🔍 Nombre de garanties extraites:', garantiesArray.length);
        console.log('🔍 Première garantie (exemple):', garantiesArray[0]);
        console.log('🔍 Champs disponibles:', garantiesArray[0] ? Object.keys(garantiesArray[0]) : 'Aucune donnée');

        setSousGarantiesAll(garantiesArray);
        console.log('✅ Sous-garanties chargées:', garantiesArray.length);
      } else {
        console.error('❌ Erreur API:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('❌ Erreur lors du chargement des sous-garanties:', error);
    }

  };

  // Charger la FGA depuis les Conditions Particulières si absente de la ligne agrégée
  // Utiliser un ref pour éviter la réinitialisation à chaque changement de cumulPrimeTTC
  const hasInitializedTotals = useRef(false);
  useEffect(() => {
    if (isEditing && !hasInitializedTotals.current) {
      const ligne0 = (offres || []).find((x) => x.IdGarantie === 0) || {};
      const ligneFga = (offres || []).find((x) => x.LibelleSousGarantie === "FGA") || {};
      const ligneCdeao = (offres || []).find((x) => x.LibelleSousGarantie === "CDEAO") || {};
      const ligneRc = (offres || []).find((x) => x.LibelleSousGarantie === "RESPONSABILITÉ CIVILE") || {};
      // Initialiser FGA avec FGAImpose si disponible, sinon Fga de la ligne agrégée
      // const fgaValue = ligne0?.FGAImpose ?? ligne0?.Fga ?? "";
      console.log("RRRligne0 pour init extras:",ligneFga, ligneRc);
      // Initialiser CEDEAO avec valeur par défaut 1000 si non définie
      // const cedeaoValue = ensureCedeaoMin(ligne0?.CEDEAO ?? "");

      // Pour un nouveau contrat (typeContrat === 0), calculer FGA = 2% de la prime nette de RESPONSABILITÉ CIVILE
      let fgaInitValue = String(ligneFga?.PrimeNette ?? "");
      if (typeContrat === 0) {
        const primeNetteRc = toNumber(ligneRc?.PrimeNette ?? 0);
        if (primeNetteRc > 0) {
          fgaInitValue = String(Math.round(primeNetteRc * 0.02));
        }
      }

      setEditedExtras({
        taxe: ligne0?.Taxe ?? "",
        accessoire: ligne0?.MontantAccessoire ?? "",
        cedeao: String(ligneCdeao?.PrimeNette ?? ""),
        fga: fgaInitValue,
      });
      // Initialiser les totaux imposés avec les valeurs affichées actuelles si disponibles
      try {
        const paVal = Number.isFinite(parseFloat(PrimeAnnuelle)) ? String(PrimeAnnuelle) : "";
        const pnVal = Number.isFinite(parseFloat(PrimeNette)) ? String(PrimeNette) : "";
        const ttcVal = Number.isFinite(parseFloat(cumulPrimeTTC)) ? String(cumulPrimeTTC) : "";
        setEditedTotals({ pa: paVal, pn: pnVal, ttc: ttcVal });
        hasInitializedTotals.current = true;
      } catch (_) {
        setEditedTotals({ pa: "", pn: "", ttc: "" });
        hasInitializedTotals.current = true;
      }
    }
    // Réinitialiser le flag quand on quitte le mode édition
    if (!isEditing) {
      hasInitializedTotals.current = false;
    }
  }, [isEditing, offres, PrimeAnnuelle, PrimeNette, cumulPrimeTTC, typeContrat]);

  // Synchroniser editedExtras.fga avec FGAImpose depuis Redux quand offres change en mode édition
  // Utiliser un ref pour suivre la dernière valeur FGAImpose vue et éviter les mises à jour en boucle
  const lastFgaImposeRef = useRef(null);
  useEffect(() => {
    if (isEditing && hasInitializedTotals.current) {
      const ligne0 = (offres || []).find((x) => x.IdGarantie === 0) || {};
      const fgaImpose = ligne0?.FGAImpose;
      // Mettre à jour editedExtras.fga seulement si FGAImpose a changé depuis la dernière fois
      // Cela permet de synchroniser l'input avec la valeur dans Redux après une sauvegarde
      if (fgaImpose !== undefined && fgaImpose !== null && lastFgaImposeRef.current !== fgaImpose) {
        setEditedExtras((prev) => {
          const prevFga = prev.fga ? toNumber(prev.fga) : null;
          // Mettre à jour seulement si la valeur a réellement changé (tolérance 0.01 pour arrondi)
          if (prevFga === null || Math.abs(prevFga - fgaImpose) > 0.01) {
            return { ...prev, fga: String(fgaImpose) };
          }
          return prev;
        });
        lastFgaImposeRef.current = fgaImpose;
      } else if (fgaImpose === undefined || fgaImpose === null) {
        lastFgaImposeRef.current = null;
      }
    }
    // Réinitialiser le ref quand on quitte le mode édition
    if (!isEditing) {
      lastFgaImposeRef.current = null;
    }
  }, [isEditing, offres]);

  // Montant FGA: priorité aux CP (ligne agrégée)
  const fgaAmount = useMemo(() => {
    try {
      const ligne0 = (offres || []).find((x) => x.LibelleSousGarantie === "FGA") || {};
      // console.log("RRRligne0 pour fgaAmount:",ligne0);
      // Prioriser FGAImpose si disponible (valeur imposée), sinon Fga
      return toNumber(ligne0?.PrimeNette?? "");
    } catch {
      return 0;
    }
  }, [offres]);
  // Montant CDEAO: priorité aux CP (ligne agrégée)
  const cdeaoAmount = useMemo(() => {
    try {
      const ligne0 = (offres || []).find((x) => x.LibelleSousGarantie === "CEDEAO") || {};
      // Prioriser CDEAOImpose si disponible (valeur imposée), sinon CDEAO
      return toNumber(ligne0?.PrimeNette ?? "");
    } catch {
      return 0;
    }
  }, [offres]);

  // Synchroniser editedExtras.cedeao avec la garantie CEDEAO du tableau quand elle change
  useEffect(() => {
    if (!isEditing) return;
    // Trouver l'index de la garantie CEDEAO dans offres
    const cedeaoIndex = (offres || []).findIndex((o) =>
      (o?.LibelleSousGarantie || '').trim().toUpperCase().includes('CEDEAO') &&
      o?.IdGarantie !== 0 && o?.IdSousGarantie !== 0
    );
    if (cedeaoIndex !== -1 && editedPrimes[cedeaoIndex]?.PrimeNette !== undefined) {
      const newCedeaoValue = String(editedPrimes[cedeaoIndex].PrimeNette);
      // Éviter les boucles infinies - ne mettre à jour que si la valeur est différente
      if (newCedeaoValue !== editedExtras.cedeao) {
        setEditedExtras((prev) => ({ ...prev, cedeao: newCedeaoValue }));
      }
    }
  }, [isEditing, editedPrimes, offres, editedExtras.cedeao]);

  // En mode édition, recalculer le TTC lorsque champs changent (inclut FGA et prend en compte prime TTC saisie)
  useEffect(() => {
    if (!isEditing) return;
    try {
      // Si un TTC imposé est saisi, il prime sur le calcul
      const ttcImpose = editedTotals?.ttc ? toNumber(editedTotals.ttc) : null;
      if (ttcImpose !== null && !isNaN(ttcImpose)) {
        setCumulPrimeTTC(ttcImpose);
        return;
      }
      const taxeEdit = toNumber(editedExtras.taxe || 0);
      const accEdit = toNumber(editedExtras.accessoire || 0);
      const cedeaoEdit = ensureCedeaoMin(editedExtras.cedeao || 0);
      const fgaEdit = toNumber(editedExtras.fga || 0);
      const pnBase = editedTotals?.pn ? toNumber(editedTotals.pn) : toNumber(PrimeNette || 0);
      const total = pnBase + taxeEdit + accEdit + cedeaoEdit + fgaEdit;
      setCumulPrimeTTC(total);
    } catch { }
  }, [isEditing, editedExtras, editedTotals, PrimeNette]);

  const handleTotalsChange = (field, value) => {
    const sanitized = String(value).replace(/[^0-9.,-]/g, "").replace(/,/g, "");
    setEditedTotals((prev) => ({ ...prev, [field]: sanitized }));
    // Mettre à jour l'affichage en direct sans toucher aux lignes
    try {
      if (field === 'pa') setPrimeAnnuelle(toNumber(sanitized));
      if (field === 'pn') {
        const newPn = toNumber(sanitized);
        setPrimeNette(newPn);
        // Recalculer automatiquement la prime TTC avec la nouvelle prime nette
        const ligne0 = (offres || []).find((x) => x.IdGarantie === 0 || x.IdSousGarantie === 0) || {};
        const taxe = toNumber(editedExtras.taxe !== "" ? editedExtras.taxe : (ligne0.Taxe || 0));
        const accessoire = toNumber(editedExtras.accessoire !== "" ? editedExtras.accessoire : (ligne0.MontantAccessoire || 0));
        const fga = toNumber(editedExtras.fga !== "" ? editedExtras.fga : (fgaAmount || 0));
        const newTtc = newPn + taxe + accessoire + fga;
        setCumulPrimeTTC(newTtc);
        setEditedTotals((prev) => ({ ...prev, ttc: String(newTtc) }));
      }
      if (field === 'ttc') setCumulPrimeTTC(toNumber(sanitized));
    } catch (_) { }
  };

  // Gestion de la saisie Taxe/Accessoire/FGA/Totaux en mode édition
  const handleExtrasChange = (field, value) => {
    const sanitized = String(value).replace(/[^0-9.,-]/g, "").replace(/,/g, "");
    // Les totaux ne doivent pas être éditables: ignorer toute tentative de modification
    if (["primeAnnuelle", "primeNette", "primeTtc"].includes(field)) {
      return;
    }
    // Pour CEDEAO, normaliser avec ensureCedeaoMin pour garantir la valeur par défaut
    const nextValue = field === 'cedeao'
      ? String(ensureCedeaoMin(sanitized))
      : sanitized;
    setEditedExtras((prev) => ({ ...prev, [field]: nextValue }));

    // Pour une meilleure UX: ne pas envoyer dans Redux à chaque frappe pour les totaux (déjà ignorés ci-dessus)

    // Mise à jour immédiate dans Redux pour Taxe / Accessoire / CEDEAO / FGA
    try {
      const currentOffres = Array.isArray(offres) ? [...offres] : [];
      const idx0 = currentOffres.findIndex((o) => o?.IdGarantie === 0 || o?.IdSousGarantie === 0);
      if (idx0 !== -1) {
        const ligne0 = currentOffres[idx0] || {};
        const imposedTaxe = field === 'taxe'
          ? toNumber(sanitized)
          : toNumber((editedExtras?.taxe ?? ligne0?.Taxe) || 0);
        const imposedAcc = field === 'accessoire'
          ? toNumber(sanitized)
          : toNumber((editedExtras?.accessoire ?? ligne0?.MontantAccessoire) || 0);
        const imposedCedeao = field === 'cedeao'
          ? ensureCedeaoMin(sanitized)
          : ensureCedeaoMin((editedExtras?.cedeao ?? ligne0?.CEDEAO) || 0);
        const imposedFga = field === 'fga'
          ? toNumber(sanitized)
          : toNumber((editedExtras?.fga ?? ligne0?.FGAImpose) || 0);

        currentOffres[idx0] = {
          ...ligne0,
          Taxe: imposedTaxe,
          MontantAccessoire: imposedAcc,
          CEDEAO: imposedCedeao,
          // stocker FGA imposé sur la ligne agrégée pour usage ultérieur (CP)
          FGAImpose: imposedFga,
        };

        // Dispatcher tout de suite pour mettre à jour Redux + hasModifications
        dispatch(updateOffres({ devisId: effectiveDevisId, offres: currentOffres }));
        dispatch(setHasModifications({ devisId: effectiveDevisId, value: true }));

        // Persister immédiatement en localStorage pour que la page détails consomme la valeur imposée
        try {
          localStorage.setItem(
            `offres_${effectiveDevisId}`,
            JSON.stringify({ offres: currentOffres, deletedGaranties })
          );
        } catch (_) { }

        // Notifier les autres vues (DevisDetails) de rafraîchir
        try { window.dispatchEvent(new CustomEvent('offres:updated', { detail: { id_devis: effectiveDevisId } })); } catch (_) { }

        // Recalculer automatiquement la prime TTC quand Taxe, Accessoire, CEDEAO ou FGA change
        if (['taxe', 'accessoire', 'fga'].includes(field)) {
          const pn = editedTotals?.pn !== "" ? toNumber(editedTotals.pn) : toNumber(PrimeNette || 0);
          const newTtc = pn + imposedTaxe + imposedAcc + imposedFga;
          setCumulPrimeTTC(newTtc);
          setEditedTotals((prev) => ({ ...prev, ttc: String(newTtc) }));
        }
      }
    } catch (_) { }

  };

  // Commit des valeurs vers Redux lors du blur pour les totaux
  const handleExtrasBlur = (field) => {
    try {
      const currentOffres = Array.isArray(offres) ? [...offres] : [];
      const idx0 = currentOffres.findIndex((o) => o?.IdGarantie === 0 || o?.IdSousGarantie === 0);
      if (idx0 === -1) return;
      const ligne0 = currentOffres[idx0] || {};

      const imposedTaxe = toNumber(editedExtras?.taxe ?? ligne0?.Taxe ?? 0);
      const imposedAcc = toNumber(editedExtras?.accessoire ?? ligne0?.MontantAccessoire ?? 0);
      const imposedFga = toNumber(editedExtras?.fga ?? ligne0?.Fga ?? 0);
      const imposedPA = toNumber(editedExtras?.primeAnnuelle ?? ligne0?.PrimeAnnuelle ?? 0);
      const imposedPN = toNumber(editedExtras?.primeNette ?? ligne0?.PrimeNette ?? 0);
      const imposedTTC = toNumber(editedExtras?.primeTtc ?? ligne0?.PrimeTtc ?? 0);

      currentOffres[idx0] = {
        ...ligne0,
        Taxe: imposedTaxe,
        MontantAccessoire: imposedAcc,
        Fga: imposedFga,
        PrimeAnnuelle: imposedPA,
        PrimeNette: imposedPN,
        PrimeTtc: imposedTTC,
      };

      dispatch(updateOffres({ devisId: effectiveDevisId, offres: currentOffres }));
      dispatch(setHasModifications({ devisId: effectiveDevisId, value: true }));
    } catch (_) { }
  };


  // Vérifier si des modifications existent déjà dans Redux au montage du composant
  useEffect(() => {
    if (offres && offres.length > 0) {
      // Si on a des données Redux, on considère qu'il pourrait y avoir des modifications
      // On ne rechargera pas automatiquement
      // console.log("🔍 Données Redux détectées au montage, pas de rechargement automatique");
    }
  }, []);


  useEffect(() => {

    if (!offres || isEditing || Object.keys(editedPrimes).length > 0) return;

    const garantie0 = offres.find(n => n.IdGarantie === 0 && n.LibelleSousGarantie);

    if (!garantie0) return;

    const pa = toNumber(garantie0.PrimeAnnuelle ?? 0);

    const pn = toNumber(garantie0.PrimeNette ?? 0);

    const t = toNumber(garantie0.Taxe ?? 0);

    const acc = toNumber(garantie0.MontantAccessoire ?? 0);

    const nextPA = isNaN(pa) ? 0 : pa;

    const nextPN = isNaN(pn) ? 0 : pn;

    const nextTTC = (isNaN(t) ? 0 : t) + (isNaN(acc) ? 0 : acc) + fgaAmount + (isNaN(pn) ? 0 : pn);

    if (PrimeAnnuelle !== nextPA) setPrimeAnnuelle(nextPA);

    if (PrimeNette !== nextPN) setPrimeNette(nextPN);

    if (cumulPrimeTTC !== nextTTC) setCumulPrimeTTC(nextTTC);

  }, [offres, isEditing, editedPrimes, fgaAmount]);



  useEffect(() => {

    if (isError) toast.error(toHumanMessage(message));

    dispatch(reset());

  }, [offres, isError, message, dispatch, isSucess]);



  useEffect(() => {

    if (correctionError) toast.error(toHumanMessage(correctionMessage) || "Erreur lors de la correction");

    //if (correctionSuccess) toast.success("Correction envoyée avec succès !");
  }, [correctionError, correctionSuccess, correctionMessage]);



  useEffect(() => {

    if (!offres?.length) return;

    setCheckedState((prev) => {

      const next = Array.from({ length: offres.length }, (_, i) => prev?.[i] ?? true);

      return next;

    });

  }, [offres]);


  // Recalculer en continu les totaux affichés en bas du tableau (en privilégiant les valeurs imposées)
  useEffect(() => {
    if (!offres || offres.length === 0) return;
    let totalPA = 0;
    let totalPN = 0;
    let linesProcessed = 0;
    (offres || []).forEach((o, index) => {
      if (o.IdGarantie === 0 || o.IdSousGarantie === 0) return; // ignorer ligne agrégée
      // Filtrer les garanties qui ne doivent jamais s'afficher
      if (estGarantieExclue(o)) return; // Exclure du calcul des totaux
      const isTaken = checkedState[index] ?? true;
      if (!isTaken) return;
      // Utiliser les primes modifiées si disponibles, sinon les primes originales
      const pa = isEditing && editedPrimes[index]?.PrimeAnnuelle !== undefined
        ? toNumber(editedPrimes[index].PrimeAnnuelle)
        : toNumber(o.PrimeAnnuelle);
      const pn = isEditing && editedPrimes[index]?.PrimeNette !== undefined
        ? toNumber(editedPrimes[index].PrimeNette)
        : toNumber(o.PrimeNette);
      totalPA += pa;
      totalPN += pn;
      linesProcessed += 1;
    });
    // Si aucune ligne éligible n'a été traitée, ne pas écraser l'affichage avec des zéros
    if (linesProcessed === 0) return;
    const ligne0 = (offres || []).find((x) => x.IdGarantie === 0 || x.IdSousGarantie === 0) || {};
    // En mode édition, utiliser les valeurs de editedExtras si disponibles
    const taxe = isEditing && editedExtras.taxe !== "" ? toNumber(editedExtras.taxe) : toNumber(ligne0.Taxe || 0);
    const accessoire = isEditing && editedExtras.accessoire !== "" ? toNumber(editedExtras.accessoire) : toNumber(ligne0.MontantAccessoire || 0);
    const cedeao = isEditing && editedExtras.cedeao !== "" ? ensureCedeaoMin(editedExtras.cedeao) : ensureCedeaoMin(ligne0.CEDEAO || 0);
    const fga = isEditing && editedExtras.fga !== "" ? toNumber(editedExtras.fga) : fgaAmount;
    // Utiliser les valeurs imposées uniquement si elles sont réellement définies (> 0)
    // et que l'on n'est PAS en mode édition (en édition on veut voir le calcul dynamique).
    const imposedPA = isEditing ? 0 : toNumber(ligne0.TotalPrimeAnnuelleImposee ?? 0);
    const imposedPN = isEditing ? 0 : toNumber(ligne0.TotalPrimeNetteImposee ?? 0);
    const imposedTTC = isEditing ? 0 : toNumber(ligne0.TotalTTCImpose ?? 0);
    const displayedPA = imposedPA > 0 ? imposedPA : totalPA;
    const displayedPN = imposedPN > 0 ? imposedPN : totalPN;
    const displayedTTC = imposedTTC > 0 ? imposedTTC : (displayedPN + taxe + accessoire + fga);

    if (PrimeAnnuelle !== displayedPA) {
      setPrimeAnnuelle(displayedPA);
      if (isEditing) {
        setEditedTotals((prev) => ({ ...prev, pa: String(displayedPA) }));
      }
    }
    if (PrimeNette !== displayedPN) {
      setPrimeNette(displayedPN);
      if (isEditing) {
        setEditedTotals((prev) => ({ ...prev, pn: String(displayedPN) }));
      }
    }
    if (cumulPrimeTTC !== displayedTTC) {
      setCumulPrimeTTC(displayedTTC);
      if (isEditing) {
        setEditedTotals((prev) => ({ ...prev, ttc: String(displayedTTC) }));
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offres, editedPrimes, checkedState, isEditing, deletedGaranties, editedExtras]);


  useEffect(() => {

    if (onCorrectionDataReady) {

      const hasModificationsValue = hasModifications || Object.keys(editedPrimes).length > 0 || deletedGaranties.length > 0;
      // console.log("🔍 Correction functions updated:", {
      //   hasModifications: hasModificationsValue,
      //   reduxHasModifications: hasModifications,
      //   editedPrimesCount: Object.keys(editedPrimes).length,
      //   deletedGarantiesCount: deletedGaranties.length
      // });

      onCorrectionDataReady({

        getCorrectionData,

        applyCorrection,

        applyCorrectionWithDevisId,

        hasModifications: hasModificationsValue,
      });

    }

  }, [editedPrimes, hasModifications, deletedGaranties, onCorrectionDataReady]);


  // Hydrate offres/hasModifications depuis localStorage au montage
  useEffect(() => {

    // Forcer la restauration API si un flag de session est présent (après "Confirmer le mouvement")
    try {
      const forceFlag = sessionStorage.getItem(`forceRenewalRestore_${effectiveDevisId}`);
      if (forceFlag) {
        console.log('🚩 Restauration forcée demandée (post-renouvellement)');
        // Ne pas court-circuiter par les offres Redux; laisser le useEffect principal faire l'appel API
      } else if (offres && offres.length > 0) {
        // 0) Si Redux a déjà des offres (revenu d'une autre page), s'en servir d'abord
        setLoadedFromCache(true);
        setHydrated(true);
        return;
      }
    } catch (_) { }
    // Ne pas restaurer de brouillon global: uniquement par devis connu
    if (!effectiveDevisId) {
      setHydrated(true);
      return;
    }
    try {
      const key = `offres_${effectiveDevisId}`;
      const persisted = localStorage.getItem(key);
      if (persisted) {
        const parsed = JSON.parse(persisted);
        if (parsed?.offres?.length) {
          dispatch(updateOffres({ devisId: effectiveDevisId, offres: parsed.offres }));
          if (parsed?.deletedGaranties?.length) {
            setDeletedGaranties(parsed.deletedGaranties);
          }
          dispatch(setHasModifications({ devisId: effectiveDevisId, value: true }));
          setLoadedFromCache(true);
          console.log('♻️ Données offres restaurées depuis localStorage');
        }
      }
    } catch (e) {
      console.warn('Impossible de restaurer les offres locales', e);
    }
    setHydrated(true);
  }, [effectiveDevisId]);

  // Isoler l'état par devis: réinitialiser lorsque l'ID du devis change
  const prevDevisIdRef = useRef();
  useEffect(() => {
    const currentId = devisSaved?.IdDevis;
    if (!currentId) return;
    if (prevDevisIdRef.current && prevDevisIdRef.current !== currentId) {
      // Nouveau devis: on remet à zéro l'état offres local pour éviter les fuites
      dispatch(reset());
      dispatch(clearEditedPrimes());
      dispatch(setHasModifications({ devisId: effectiveDevisId, value: false }));
      console.log('🔁 Changement de devis détecté: réinitialisation des offres');
    }
    prevDevisIdRef.current = currentId;
  }, [devisSaved?.IdDevis]);

  // Ré-hydrater dès que l'IdDevis réel est connu (après chargement du devis)
  useEffect(() => {
    if (!devisSaved?.IdDevis) return;
    try {
      const key = `offres_${devisSaved.IdDevis}`;
      const persisted = localStorage.getItem(key);
      if (persisted) {
        const parsed = JSON.parse(persisted);
        if (parsed?.offres?.length) {
          dispatch(updateOffres({ devisId: effectiveDevisId, offres: parsed.offres }));
          if (parsed?.deletedGaranties?.length) {
            setDeletedGaranties(parsed.deletedGaranties);
          }
          dispatch(setHasModifications({ devisId: effectiveDevisId, value: true }));
          setLoadedFromCache(true);
          console.log('♻️ Données offres restaurées via IdDevis');
        }
      }
    } catch (e) {
      console.warn('Impossible de restaurer via IdDevis', e);
    }
  }, [devisSaved?.IdDevis]);

  // Persister offres, garanties supprimées et le flag de modification à chaque changement (par devis uniquement)
  useEffect(() => {
    try {
      if (!effectiveDevisId) return;
      const payload = {
        offres,
        deletedGaranties,
        hasModifications: hasModifications || Object.keys(editedPrimes).length > 0 || deletedGaranties.length > 0
      };
      localStorage.setItem(`offres_${effectiveDevisId}`, JSON.stringify(payload));
    } catch (e) {
      console.warn('Impossible de persister les offres locales', e);
    }
  }, [offres, hasModifications, editedPrimes, deletedGaranties, effectiveDevisId]);

  // Charger les garanties corrigées depuis les détails du devis lors du renouvellement
  const loadCorrectedGuaranteesFromDevis = async (devisId) => {
    if (!devisId) return null;

    try {
      console.log('🔄 Chargement des garanties corrigées depuis garantiesouscritedevis:', devisId);

      // Essayer d'abord avec id_avenant=2 (renouvellement), puis sans paramètre
      const endpoints = [
        `${process.env.REACT_APP_API_URL || ''}garantiesouscritedevis/${devisId}?id_avenant=2`,
        `${process.env.REACT_APP_API_URL || ''}garantiesouscritedevis/${devisId}`
      ];

      for (const endpoint of endpoints) {
        try {
          const response = await fetch(endpoint, {
            method: 'GET',
            headers: {
              'Authorization': `Token ${token}`,
              'Content-Type': 'application/json',
            }
          });

          if (response.ok) {
            const raw = await response.json();
            console.log('📊 Garanties corrigées reçues depuis garantiesouscritedevis:', raw);

            // Normaliser la liste quelle que soit la forme: [..], {Data:[..]}, {data:[..]}
            const list = Array.isArray(raw)
              ? raw
              : (Array.isArray(raw?.Data) ? raw.Data : (Array.isArray(raw?.data) ? raw.data : []));

            if (list && list.length > 0) {
              // Transformer les données pour correspondre au format attendu par OffreSection
              const correctedGuarantees = list.map(garantie => ({
                IdGarantie: garantie.IdGarantie || garantie.id_garantie || garantie.idsousgarantie || 0,
                IdSousGarantie: garantie.IdSousGarantie || garantie.id_sous_garantie || garantie.idsousgarantie || garantie.IdGarantie || garantie.id_garantie || garantie.idsousgarantie,
                LibelleSousGarantie: garantie.LibelleSousGarantie || garantie.libelle_sous_garantie || garantie.libellesousgarantie || garantie.libelle || 'Garantie',
                PrimeAnnuelle: toNumber(garantie.PrimeAnnuelle ?? garantie.prime_annuelle ?? garantie.primeannuelle ?? garantie.prime_ann ?? garantie.primeannuelle ?? 0),
                PrimeNette: toNumber(garantie.PrimeNette ?? garantie.prime_nette ?? garantie.primenette ?? garantie.prime_net ?? garantie.primenette ?? 0),
                Capital: toNumber(garantie.Capital ?? garantie.capital ?? garantie.textecapital ?? garantie.capital_garantie ?? garantie.capital ?? 0),
                Franchise: toNumber(garantie.Franchise ?? garantie.franchise ?? garantie.montant_franchise ?? garantie.franchise ?? 0),
                TauxFranchise: toNumber(garantie.TauxFranchise ?? garantie.taux_franchise ?? garantie.tauxfranchise ?? 0),
                FranchiseMin: toNumber(garantie.FranchiseMin ?? garantie.franchise_min ?? garantie.franchisemin ?? 0),
                FranchiseMax: toNumber(garantie.FranchiseMax ?? garantie.franchise_max ?? garantie.franchisemax ?? 0),
                CapitalDeces: toNumber(garantie.CapitalDeces ?? garantie.capital_deces ?? garantie.deces ?? 0),
                CapitalIPP: toNumber(garantie.CapitalIPP ?? garantie.capital_ipp ?? garantie.ipp ?? 0),
                CapitalFT: toNumber(garantie.CapitalFT ?? garantie.capital_ft ?? garantie.ft ?? 0),
                ReductionCommerciale: toNumber(garantie.ReductionCommerciale ?? garantie.reduction_commerciale ?? garantie.reductioncommerciale ?? 0),
                ReductionBns: toNumber(garantie.ReductionBns ?? garantie.reduction_bns ?? garantie.reductionbns ?? 0),
                TexteFranchise: garantie.TexteFranchise || garantie.texte_franchise || garantie.textefranchise || (toNumber(garantie.Franchise ?? garantie.montant_franchise) > 0 ? `${toNumber(garantie.Franchise ?? garantie.montant_franchise)} FCFA` : "NEANT"),
                Acquise: (garantie.Acquise ?? garantie.souscrite ?? true) !== false,
                IdDevisDetail: garantie.IdDevisDetail || garantie.id_devis_detail || devisId,
                // Marquer comme restauré depuis les conditions particulières
                is_restored_from_cp: true
              }));

              console.log('✅ Garanties corrigées transformées depuis garantiesouscritedevis:', correctedGuarantees.length);
              console.log('🔍 Exemple de garantie transformée:', correctedGuarantees[0]);
              return correctedGuarantees;
            }
          }
        } catch (endpointError) {
          console.warn(`⚠️ Erreur avec l'endpoint ${endpoint}:`, endpointError);
          continue;
        }
      }

      console.log('⚠️ Aucune garantie trouvée dans garantiesouscritedevis');
      return null;
    } catch (error) {
      console.error('❌ Erreur lors du chargement des garanties corrigées:', error);
      return null;
    }
  };

  useEffect(() => {
    // Attendre l'hydratation locale pour éviter d'écraser les valeurs corrigées
    if (!hydrated) return;

    console.log("🔍 Debug useEffect - Variables:", {
      hydrated,
      isEditPolice,
      devisSavedId: devisSaved?.IdDevis,
      effectiveDevisId,
      hasOffres: !!offres,
      offresLength: offres?.length || 0,
      hasModifications,
      restorationSource
    });

    // Tenter la restauration API (garanties corrigées) pour tout devis connu
    const targetDevisIdForRenewal = devisSaved?.IdDevis || effectiveDevisId;

    // Vérifier si c'est un renouvellement (flag de session ou isEditPolice)
    const isRenewalFlow = !!(isEditPolice || sessionStorage.getItem(`forceRenewalRestore_${effectiveDevisId}`));

    // Si une correction finalisée a été persistée précédemment pour ce devis, hydrater depuis localStorage si possible
    try {
      const finalizedFlag = sessionStorage.getItem(`finalizedCorrection_${effectiveDevisId}`);
      if (finalizedFlag === '1') {
        isFinalizedRef.current = true;
        setRestorationSource('finalized');
        try {
          const persisted = localStorage.getItem(`offres_${effectiveDevisId}`);
          if (persisted) {
            const parsed = JSON.parse(persisted);
            if (parsed?.offres?.length) {
              dispatch(updateOffres({ devisId: effectiveDevisId, offres: parsed.offres }));
              if (parsed?.deletedGaranties?.length) setDeletedGaranties(parsed.deletedGaranties);
              const restoredCheckedState = parsed.offres.map(g => g.Acquise !== false);
              setCheckedState(restoredCheckedState);
              return; // hydratation locale suffisante
            }
          }
        } catch (_) { }
      }
    } catch (_) { }

    console.log("🔍 Détection du renouvellement:", {
      isEditPolice,
      forceFlag: sessionStorage.getItem(`forceRenewalRestore_${effectiveDevisId}`),
      isRenewalFlow,
      targetDevisIdForRenewal,
      restorationSource
    });

    // Si déjà finalisé (corrections persistées) et aucune donnée locale, on continue la restauration API ci-dessous
    if (isFinalizedRef.current && restorationSource === 'finalized') {
      // on n'a rien trouvé en localStorage, on tentera l'API plus bas
    }
    // Essayer TOUJOURS de charger les garanties corrigées si on a un ID devis valide
    if (targetDevisIdForRenewal && restorationSource !== 'api' && !isRestoringRef.current) {
      console.log("🔄 Tentative de restauration depuis garantiesouscritedevis", {
        targetDevisIdForRenewal,
        isEditPolice,
        forceFlag: !!sessionStorage.getItem(`forceRenewalRestore_${effectiveDevisId}`),
        isRenewalFlow
      });
      // Empêcher les appels multiples concurrentiels
      isRestoringRef.current = true;
      setRestorationSource(prev => prev || 'api_pending');

      // Essayer d'abord l'API garantiesouscritedevis qui contient les vraies données corrigées
      loadCorrectedGuaranteesFromDevis(parseInt(targetDevisIdForRenewal)).then(async correctedGuarantees => {
        if (correctedGuarantees && correctedGuarantees.length > 0) {
          console.log("✅ Garanties corrigées restaurées depuis les conditions particulières:", correctedGuarantees.length);
          console.log("🔍 Exemple de garantie restaurée:", correctedGuarantees[0]);

          // Log des données avant envoi à Redux
          console.log("📤 Envoi des garanties corrigées à Redux:", correctedGuarantees.slice(0, 3));

          // Fusionner avec la ligne agrégée (Taxe/Accessoire) pour aligner les totaux TTC
          const merged = await mergeWithBaselineTaxes(correctedGuarantees);
          try { authoritativeGarantiesRef.current = correctedGuarantees?.filter(g => (g?.IdGarantie || g?.IdSousGarantie) && (g?.IdGarantie !== 0 && g?.IdSousGarantie !== 0)); } catch (_) { }

          // Restaurer les garanties corrigées dans Redux
          dispatch(updateOffres({ devisId: effectiveDevisId, offres: merged }));
          dispatch(setHasModifications({ devisId: effectiveDevisId, value: true }));
          // Persister aussi côté localStorage pour éviter une future réhydratation avec d'anciennes valeurs
          try {
            localStorage.setItem(
              `offres_${effectiveDevisId}`,
              JSON.stringify({ offres: merged, deletedGaranties })
            );
          } catch (_) { }
          // Persister immédiatement côté backend pour que les pages de détails affichent les bonnes valeurs
          console.log("🛰️ Demande de persistance automatique des corrections (correctiondevis)", { id_devis: effectiveDevisId });
          try {
            const res = await applyCorrectionWithDevisId(effectiveDevisId);
            if (res?.success) {
              isFinalizedRef.current = true;
              try { sessionStorage.setItem(`finalizedCorrection_${effectiveDevisId}`, '1'); } catch (_) { }
              setRestorationSource('finalized');
              console.log("✅ Persistance correction réussie (correctiondevis)", { id_devis: effectiveDevisId, response: res });
              try { window.dispatchEvent(new CustomEvent('offres:updated', { detail: { id_devis: effectiveDevisId } })); } catch (_) { }
            }
          } catch (e) {
            console.warn('Impossible d\'appliquer automatiquement les corrections après restauration API', e);
          }

          // Mettre à jour l'état des checkboxes pour toutes les garanties restaurées
          const restoredCheckedState = merged.map(g => g.Acquise !== false);
          setCheckedState(restoredCheckedState);

          // Marquer la source de restauration
          setRestorationSource('api');
          try { sessionStorage.removeItem(`forceRenewalRestore_${effectiveDevisId}`); } catch (_) { }

          //toast.success(`✅ ${correctedGuarantees.length} garanties corrigées restaurées depuis les conditions particulières`);
          isRestoringRef.current = false;
          return; // Sortir de la fonction, pas besoin de recalculer
        } else {
          console.log("ℹ️ Aucune garantie corrigée trouvée dans garantiesouscritedevis, tentative localStorage fallback");

          // Si pas de données dans l'API, essayer localStorage comme fallback
          try {
            const key = `offres_${targetDevisIdForRenewal}`;
            const persisted = localStorage.getItem(key);
            if (persisted) {
              const parsed = JSON.parse(persisted);
              if (parsed?.offres?.length) {
                console.log("✅ Données corrigées trouvées dans localStorage:", parsed.offres.length, "garanties");

                // S'assurer d'inclure la ligne agrégée (Taxe/Accessoire) si absente
                const hasAggregate = (parsed.offres || []).some(o => o?.IdGarantie === 0 || o?.IdSousGarantie === 0);
                const mergedFromLocal = hasAggregate ? parsed.offres : await mergeWithBaselineTaxes(parsed.offres || []);
                try { authoritativeGarantiesRef.current = (parsed.offres || []).filter(o => (o?.IdGarantie || o?.IdSousGarantie) && (o?.IdGarantie !== 0 && o?.IdSousGarantie !== 0)); } catch (_) { }
                // Restaurer les données corrigées depuis localStorage
                dispatch(updateOffres({ devisId: effectiveDevisId, offres: mergedFromLocal }));
                if (parsed?.deletedGaranties?.length) {
                  setDeletedGaranties(parsed.deletedGaranties);
                }
                dispatch(setHasModifications({ devisId: effectiveDevisId, value: true }));
                // Réécrire la version fusionnée en localStorage pour stabiliser les prochaines restaurations
                try {
                  localStorage.setItem(
                    `offres_${effectiveDevisId}`,
                    JSON.stringify({ offres: mergedFromLocal, deletedGaranties: parsed?.deletedGaranties || [] })
                  );
                } catch (_) { }
                // Persister immédiatement côté backend
                console.log("🛰️ Demande de persistance automatique des corrections (correctiondevis)", { id_devis: effectiveDevisId });
                try {
                  const res = await applyCorrectionWithDevisId(effectiveDevisId);
                  if (res?.success) {
                    isFinalizedRef.current = true;
                    try { sessionStorage.setItem(`finalizedCorrection_${effectiveDevisId}`, '1'); } catch (_) { }
                    setRestorationSource('finalized');
                    console.log("✅ Persistance correction réussie (correctiondevis)", { id_devis: effectiveDevisId, response: res });
                    try { window.dispatchEvent(new CustomEvent('offres:updated', { detail: { id_devis: effectiveDevisId } })); } catch (_) { }
                  }
                } catch (e) {
                  console.warn('Impossible d\'appliquer automatiquement les corrections après restauration localStorage', e);
                }

                // Mettre à jour l'état des checkboxes pour toutes les garanties restaurées
                const restoredCheckedState = (mergedFromLocal || []).map(g => g.Acquise !== false);
                setCheckedState(restoredCheckedState);

                // Marquer la source de restauration
                setRestorationSource('localStorage');

                toast.success(`✅ ${parsed.offres.length} garanties corrigées restaurées depuis les données sauvegardées`);
                isRestoringRef.current = false;
                return; // Sortir de la fonction, pas besoin de recalculer
              }
            }
          } catch (error) {
            console.error("❌ Erreur lors de la lecture du localStorage:", error);
          }

          // Si c'est un renouvellement et qu'on n'a pas trouvé de données corrigées, afficher un message
          if (isRenewalFlow) {
            console.log("⚠️ Renouvellement détecté mais aucune donnée corrigée trouvée");
            toast.warning("⚠️ Aucune donnée corrigée trouvée pour ce renouvellement. Calcul des primes standard en cours...");
          }

          console.log("ℹ️ Aucune donnée corrigée trouvée, passage au recalcul standard");
          // Forcer un recalcul de l'offre même en renouvellement
          dispatch(setHasModifications({ devisId: effectiveDevisId, value: false }));
          dispatch(updateOffres({ devisId: effectiveDevisId, offres: [] }));
          dispatch(
            postOffre({
              CodeCarburant: energie,
              CodeAlarme: systemeSecurites,
              IdOffre: parseInt(offre),
              IdTarif: categorie,
              NsiaAutoPlus: nsiaAutoPlus,
              IdCompagnie: parseInt(compagnie),
              ValNeuve: parseFloat(valeurNeuf.replace(/ /g, "")),
              ValVenale: parseFloat(valeurVenale.replace(/ /g, "")),
              ValAccessoire: parseFloat(valeurAccessoire.replace(/ /g, "")),
              Puissance: parseInt(puissancefiscale),
              Tonnage: chargeUtile,
              TauxReduction: reduction,
              DateEffet: handleDate(dateEffet),
              DateExpiration: dateExpiration,
              DateMec: handleDate(premiereCirculation),
              Bns: bonusmalus,
              RemorqueAttelee: remorqueAttelee,
              CodeFormuleSecuriteRoutiere: securiteRoutiere,
              NombrePlace: nbrPlace,
              CodeUsage: parseInt(usage),
              CarburantAutreMatiere: CarburantAutreMatiere,
              TransportEleves: TransportEleves,
              TransportEmployes: TransportEmployes,
              TansportPassagerSupplementaire: TransportPassageSupplementaire,
              IdOptionAssistance: parseInt(assistanceAuto),
            })
          ).then((action) => {
            if (action?.type?.endsWith('/fulfilled')) {
              const data = action.payload;
              if (Array.isArray(data) && data.length > 0) {
                dispatch(updateOffres({ devisId: effectiveDevisId, offres: data }));
              }
            }
            isRestoringRef.current = false;
          });
        }
      }).catch(error => {
        console.error("❌ Erreur lors de la restauration des garanties corrigées:", error);

        // En cas d'erreur API, essayer localStorage comme fallback
        try {
          const key = `offres_${targetDevisIdForRenewal}`;
          const persisted = localStorage.getItem(key);
          if (persisted) {
            const parsed = JSON.parse(persisted);
            if (parsed?.offres?.length) {
              console.log("✅ Fallback localStorage - données corrigées trouvées:", parsed.offres.length, "garanties");

              // Restaurer les données corrigées depuis localStorage
              dispatch(updateOffres({ devisId: effectiveDevisId, offres: parsed.offres }));
              if (parsed?.deletedGaranties?.length) {
                setDeletedGaranties(parsed.deletedGaranties);
              }
              dispatch(setHasModifications({ devisId: effectiveDevisId, value: true }));

              // Mettre à jour l'état des checkboxes pour toutes les garanties restaurées
              const restoredCheckedState = parsed.offres.map(g => g.Acquise !== false);
              setCheckedState(restoredCheckedState);

              // Marquer la source de restauration
              setRestorationSource('localStorage');

              toast.success(`✅ ${parsed.offres.length} garanties corrigées restaurées depuis les données sauvegardées (fallback)`);
              return; // Sortir de la fonction, pas besoin de recalculer
            }
          }
        } catch (localStorageError) {
          console.error("❌ Erreur lors de la lecture du localStorage:", localStorageError);
        }

        // Forcer un recalcul standard en cas d'erreur
        dispatch(setHasModifications({ devisId: effectiveDevisId, value: false }));
        dispatch(updateOffres({ devisId: effectiveDevisId, offres: [] }));
        dispatch(
          postOffre({
            CodeCarburant: energie,
            CodeAlarme: systemeSecurites,
            IdOffre: parseInt(offre),
            IdTarif: categorie,
            NsiaAutoPlus: nsiaAutoPlus,
            IdCompagnie: parseInt(compagnie),
            ValNeuve: parseFloat(valeurNeuf.replace(/ /g, "")),
            ValVenale: parseFloat(valeurVenale.replace(/ /g, "")),
            ValAccessoire: parseFloat(valeurAccessoire.replace(/ /g, "")),
            Puissance: parseInt(puissancefiscale),
            Tonnage: chargeUtile,
            TauxReduction: reduction,
            DateEffet: handleDate(dateEffet),
            DateExpiration: dateExpiration,
            DateMec: handleDate(premiereCirculation),
            Bns: bonusmalus,
            RemorqueAttelee: remorqueAttelee,
            CodeFormuleSecuriteRoutiere: securiteRoutiere,
            NombrePlace: nbrPlace,
            CodeUsage: parseInt(usage),
            CarburantAutreMatiere: CarburantAutreMatiere,
            TransportEleves: TransportEleves,
            TransportEmployes: TransportEmployes,
            TansportPassagerSupplementaire: TransportPassageSupplementaire,
            IdOptionAssistance: parseInt(assistanceAuto),
          })
        ).then((action) => {
          if (action?.type?.endsWith('/fulfilled')) {
            const data = action.payload;
            if (Array.isArray(data) && data.length > 0) {
              dispatch(updateOffres({ devisId: effectiveDevisId, offres: data }));
            }
          }
          isRestoringRef.current = false;
        });
      });
    }

    // Pour le renouvellement sans garanties corrigées ou pour les nouveaux devis, recalculer les primes
    // Ne pas recalculer si on a déjà des données et qu'on n'est pas en mode renouvellement
    const shouldRecalculate = (!offres || offres.length === 0) && !hasModifications && !isRenewalFlow;

    if (shouldRecalculate) {
      console.log("🔄 Rechargement des données depuis l'API...");
      dispatch(

        postOffre({

          CodeCarburant: energie,

          CodeAlarme: systemeSecurites,

          IdOffre: parseInt(offre),

          IdTarif: categorie,

          NsiaAutoPlus: nsiaAutoPlus,

          IdCompagnie: parseInt(compagnie),

          ValNeuve: parseFloat(valeurNeuf.replace(/ /g, "")),

          ValVenale: parseFloat(valeurVenale.replace(/ /g, "")),

          ValAccessoire: parseFloat(valeurAccessoire.replace(/ /g, "")),

          Puissance: parseInt(puissancefiscale),

          Tonnage: chargeUtile,

          TauxReduction: reduction,

          DateEffet: handleDate(dateEffet),

          DateExpiration: dateExpiration,

          DateMec: handleDate(premiereCirculation),

          Bns: bonusmalus,

          RemorqueAttelee: remorqueAttelee,

          CodeFormuleSecuriteRoutiere: securiteRoutiere,

          NombrePlace: nbrPlace,

          CodeUsage: parseInt(usage),

          CarburantAutreMatiere: CarburantAutreMatiere,

          TransportEleves: TransportEleves,

          TransportEmployes: TransportEmployes,

          TansportPassagerSupplementaire: TransportPassageSupplementaire,

          IdOptionAssistance: parseInt(assistanceAuto),

        })

      ).then((action) => {
        if (action?.type?.endsWith('/fulfilled')) {
          const data = action.payload;
          if (Array.isArray(data) && data.length > 0) {
            dispatch(updateOffres({ devisId: effectiveDevisId, offres: data }));
          }
        }
      });
    } else {
      console.log("🚫 Rechargement bloqué - données existantes ou modifications en cours:", {
        hasOffres: offres && offres.length > 0,
        hasModifications: hasModifications
      });
    }
  }, [offre, hasModifications, hydrated, loadedFromCache, isEditPolice, devisSaved?.IdDevis]);


  const handleDate = (date) => moment(date).format("DD-MM-YYYY");


  // Formatage monétaire cohérent (fr-FR) avec suffixe FCFA
  const formatCurrency = (value) => {
    try {
      const n = Number.isFinite(value) ? value : toNumber(value);
      return `${new Intl.NumberFormat('fr-FR').format(Math.round(n))} FCFA`;
    } catch {
      return `${value ?? 0} FCFA`;
    }
  };

  // Fonction utilitaire pour vérifier si une garantie doit être exclue
  const estGarantieExclue = (offre) => {
    const garantiesAExclure = [
      'FGA',
      '*** Capital Décès',
      '*** Incapacité',
      '*** Frais Médicaux'
    ];

    const libelle = offre?.LibelleSousGarantie || '';
    const isExcluded = garantiesAExclure.some(exclusion =>
      libelle.toLowerCase().includes(exclusion.toLowerCase())
    );

    // Debug log
    if (libelle.toLowerCase().includes('fga')) {
      console.log('🚫 FGA détecté et exclu:', libelle, 'isExcluded:', isExcluded);
    }

    return isExcluded;
  };

  // Fusionner les garanties corrigées avec la ligne agrégée (Taxe/Accessoire/CEDEAO + totaux imposés)
  // IMPORTANT: on PRÉSERVE Taxe/Accessoire/CEDEAO et les totaux imposés déjà présents dans Redux (saisies utilisateur)
  const mergeWithBaselineTaxes = async (correctedGuarantees) => {
    try {
      const action = await dispatch(
        postOffre({
          CodeCarburant: energie,
          CodeAlarme: systemeSecurites,
          IdOffre: parseInt(offre),
          IdTarif: categorie,
          NsiaAutoPlus: nsiaAutoPlus,
          IdCompagnie: parseInt(compagnie),
          ValNeuve: parseFloat(String(valeurNeuf).replace(/ /g, "")),
          ValVenale: parseFloat(String(valeurVenale).replace(/ /g, "")),
          ValAccessoire: parseFloat(String(valeurAccessoire).replace(/ /g, "")),
          Puissance: parseInt(puissancefiscale),
          Tonnage: chargeUtile,
          TauxReduction: reduction,
          DateEffet: handleDate(dateEffet),
          DateExpiration: dateExpiration,
          DateMec: handleDate(premiereCirculation),
          Bns: bonusmalus,
          RemorqueAttelee: remorqueAttelee,
          CodeFormuleSecuriteRoutiere: securiteRoutiere,
          NombrePlace: nbrPlace,
          CodeUsage: parseInt(usage),
          CarburantAutreMatiere: CarburantAutreMatiere,
          TransportEleves: TransportEleves,
          TransportEmployes: TransportEmployes,
          TansportPassagerSupplementaire: TransportPassageSupplementaire,
          IdOptionAssistance: parseInt(assistanceAuto),
        })
      );

      let aggregateLine = null;
      if (action?.type?.endsWith('/fulfilled')) {
        const baseline = action.payload;
        if (Array.isArray(baseline)) {
          const l0 = baseline.find((x) => x?.IdGarantie === 0 || x?.IdSousGarantie === 0);
          // Préférer les valeurs Taxe/Accessoire/CEDEAO et totaux imposés actuellement dans Redux si disponibles
          const currentAggregate = (offres || []).find(o => o?.IdGarantie === 0 || o?.IdSousGarantie === 0) || {};
          if (l0) {
            aggregateLine = {
              IdGarantie: 0,
              IdSousGarantie: 0,
              LibelleSousGarantie: 'TOTAL',
              PrimeAnnuelle: toNumber(l0.PrimeAnnuelle ?? 0),
              PrimeNette: toNumber(l0.PrimeNette ?? 0),
              Taxe: toNumber(currentAggregate?.Taxe ?? l0.Taxe ?? 0),
              MontantAccessoire: toNumber(currentAggregate?.MontantAccessoire ?? l0.MontantAccessoire ?? 0),
              CEDEAO: toNumber(currentAggregate?.CEDEAO ?? l0.CEDEAO ?? 0),
              TotalPrimeAnnuelleImposee: toNumber(currentAggregate?.TotalPrimeAnnuelleImposee ?? l0.TotalPrimeAnnuelleImposee ?? 0),
              TotalPrimeNetteImposee: toNumber(currentAggregate?.TotalPrimeNetteImposee ?? l0.TotalPrimeNetteImposee ?? 0),
              TotalTTCImpose: toNumber(currentAggregate?.TotalTTCImpose ?? l0.TotalTTCImpose ?? 0),
            };
          }
        }
      }

      if (!aggregateLine) {
        const currentAggregate = (offres || []).find(o => o?.IdGarantie === 0 || o?.IdSousGarantie === 0) || {};
        const sumPA = (correctedGuarantees || []).reduce((acc, g) => {
          const isAgg = g?.IdGarantie === 0 || g?.IdSousGarantie === 0;
          if (isAgg) return acc;
          return acc + toNumber(g?.PrimeAnnuelle ?? 0);
        }, 0);
        const sumPN = (correctedGuarantees || []).reduce((acc, g) => {
          const isAgg = g?.IdGarantie === 0 || g?.IdSousGarantie === 0;
          if (isAgg) return acc;
          return acc + toNumber(g?.PrimeNette ?? 0);
        }, 0);
        const base = {
          IdGarantie: 0,
          IdSousGarantie: 0,
          LibelleSousGarantie: 'TOTAL',
          PrimeAnnuelle: sumPA,
          PrimeNette: sumPN,
          Taxe: toNumber(currentAggregate?.Taxe ?? 0),
          MontantAccessoire: toNumber(currentAggregate?.MontantAccessoire ?? 0),
          CEDEAO: toNumber(currentAggregate?.CEDEAO ?? 0),
        };
        const imposed = {};
        if (currentAggregate?.TotalPrimeAnnuelleImposee != null) imposed.TotalPrimeAnnuelleImposee = toNumber(currentAggregate.TotalPrimeAnnuelleImposee);
        if (currentAggregate?.TotalPrimeNetteImposee != null) imposed.TotalPrimeNetteImposee = toNumber(currentAggregate.TotalPrimeNetteImposee);
        if (currentAggregate?.TotalTTCImpose != null) imposed.TotalTTCImpose = toNumber(currentAggregate.TotalTTCImpose);
        aggregateLine = { ...base, ...imposed };
      }

      return [...correctedGuarantees, aggregateLine];
    } catch (e) {
      console.warn('Fusion baseline taxes échouée, utilisation des garanties seules', e);
      // Même en cas d'erreur, tenter d'ajouter la ligne agrégée basée sur Redux si dispo
      try {
        const currentAggregate = (offres || []).find(o => o?.IdGarantie === 0 || o?.IdSousGarantie === 0);
        if (currentAggregate) {
          const aggregateLine = {
            IdGarantie: 0,
            IdSousGarantie: 0,
            LibelleSousGarantie: 'TOTAL',
            PrimeAnnuelle: toNumber(currentAggregate?.PrimeAnnuelle ?? 0),
            PrimeNette: toNumber(currentAggregate?.PrimeNette ?? 0),
            Taxe: toNumber(currentAggregate?.Taxe ?? 0),
            MontantAccessoire: toNumber(currentAggregate?.MontantAccessoire ?? 0),
            CEDEAO: toNumber(currentAggregate?.CEDEAO ?? 0),
            TotalPrimeAnnuelleImposee: toNumber(currentAggregate?.TotalPrimeAnnuelleImposee ?? 0),
            TotalPrimeNetteImposee: toNumber(currentAggregate?.TotalPrimeNetteImposee ?? 0),
            TotalTTCImpose: toNumber(currentAggregate?.TotalTTCImpose ?? 0),
          };
          return [...correctedGuarantees, aggregateLine];
        }
      } catch (_) { }
      return correctedGuarantees;
    }
  };

  // Détection FGA: certaines lignes (FGA) doivent être exclues du total Prime Nette
  // Règle: on considère FGA si le libellé contient "FGA" (majuscules/minuscules) ou si l'identifiant correspond à la valeur connue (par ex. 169)
  const isFGA = (o) => {
    try {
      const id = parseInt(o?.IdSousGarantie || o?.IdGarantie);
      const lib = String(o?.LibelleSousGarantie || '').toLowerCase();
      return id === 169 || lib.includes('fga');
    } catch {
      return false;
    }
  };

  // Détection CEDEAO: certaines lignes (CEDEAO) doivent être exclues du total Prime Nette
  // car elles sont ajoutées séparément dans le calcul du TTC
  const isCEDEAO = (o) => {
    try {
      const lib = String(o?.LibelleSousGarantie || '').toUpperCase();
      return lib.includes('CEDEAO') || lib === 'CDEAO';
    } catch {
      return false;
    }
  };


  // Changement d'offre (incl. renouvellement): purge contrôlée + fetch immédiat des garanties
  const handleChangeOffre = async (nextOffre) => {
    try {
      // 1) Mettre à jour l'offre sélectionnée (prop parent)
      setOffre(nextOffre);

      // 2) Sortir du mode édition et nettoyer les modifications locales
      dispatch(setEditingMode(false));
      dispatch(clearEditedPrimes());
      setDeletedGaranties([]);

      // 3) Purger l'état offres pour afficher un skeleton propre
      dispatch(updateOffres({ devisId: effectiveDevisId, offres: [] }));
      dispatch(setHasModifications({ devisId: effectiveDevisId, value: false }));
      setLoadedFromCache(false);

      // 4) Nettoyer les flags de restauration/renouvellement pour éviter d'écraser la nouvelle offre
      try {
        sessionStorage.removeItem(`finalizedCorrection_${effectiveDevisId}`);
        sessionStorage.removeItem(`forceRenewalRestore_${effectiveDevisId}`);
        localStorage.removeItem(`offres_${effectiveDevisId}`);
      } catch { }

      // 5) Appel direct API de calcul pour l'offre choisie
      const action = await dispatch(
        postOffre({
          CodeCarburant: energie,
          CodeAlarme: systemeSecurites,
          IdOffre: parseInt(nextOffre),
          IdTarif: categorie,
          NsiaAutoPlus: nsiaAutoPlus,
          IdCompagnie: parseInt(compagnie),
          ValNeuve: parseFloat(valeurNeuf.replace(/ /g, "")),
          ValVenale: parseFloat(valeurVenale.replace(/ /g, "")),
          ValAccessoire: parseFloat(valeurAccessoire.replace(/ /g, "")),
          Puissance: parseInt(puissancefiscale),
          Tonnage: chargeUtile,
          TauxReduction: reduction,
          DateEffet: handleDate(dateEffet),
          DateExpiration: dateExpiration,
          DateMec: handleDate(premiereCirculation),
          Bns: bonusmalus,
          RemorqueAttelee: remorqueAttelee,
          CodeFormuleSecuriteRoutiere: securiteRoutiere,
          NombrePlace: nbrPlace,
          CodeUsage: parseInt(usage),
          CarburantAutreMatiere: CarburantAutreMatiere,
          TransportEleves: TransportEleves,
          TransportEmployes: TransportEmployes,
          TansportPassagerSupplementaire: TransportPassageSupplementaire,
          IdOptionAssistance: parseInt(assistanceAuto),
        })
      );

      if (action?.type?.endsWith('/fulfilled') && Array.isArray(action.payload)) {
        // 6) Injecter immédiatement les garanties de la nouvelle offre dans Redux
        dispatch(updateOffres({ devisId: effectiveDevisId, offres: action.payload }));
        // Reset des affichages agrégés sera fait par les useEffect existants
      }
    } catch (e) {
      console.warn('Changement d\'offre échoué:', e);
    }
  };


  const handleEditPrimes = () => {

    dispatch(setEditingMode(!isEditing));

    if (!isEditing) {

      const initialEditedPrimes = {};

      offres.forEach((offre, index) => {

        if (offre.IdGarantie !== 0 && offre.IdSousGarantie !== 0) {

          initialEditedPrimes[index] = {
            PrimeAnnuelle: offre.PrimeAnnuelle || 0,
            PrimeNette: offre.PrimeNette || 0,
            Capital: offre.Capital || 0,
            Franchise: offre.Franchise || 0,
            TauxFranchise: offre.TauxFranchise || 0,
            FranchiseMin: offre.FranchiseMin || 0,
            FranchiseMax: offre.FranchiseMax || 0,
            Acquise: checkedState[index] ?? true,
          };

        }

      });

      dispatch(updateEditedPrimes(initialEditedPrimes));

    } else {

      dispatch(clearEditedPrimes());
      setDeletedGaranties([]); // Réinitialiser les garanties supprimées

    }

  };



  const handlePrimeChange = (index, field, value) => {

    const sanitized = String(value).replace(/[^0-9.,-]/g, "").replace(",", ".");

    const normalized = sanitized === "" || sanitized === "-" ? "" : sanitized;

    dispatch(updateEditedPrimes({

      [index]: { ...editedPrimes[index], [field]: normalized },

    }));
    // Réinitialiser les totaux pour qu'ils soient recalculés au prochain cycle si on est en mode édition
    if (field === 'PrimeNette' || field === 'PrimeAnnuelle' || field === 'Acquise') {
      hasInitializedTotals.current = false;
    }

    // Si on modifie la PrimeNette de la garantie CEDEAO du bas, synchroniser vers le champ CEDEAO du haut
    if (field === 'PrimeNette') {
      const garantie = offres?.[index];
      const libelle = (garantie?.LibelleSousGarantie || '').trim().toUpperCase();
      if (libelle === "CEDEAO" || libelle.includes("CEDEAO")) {
        const cedeaoValue = ensureCedeaoMin(normalized);
        setEditedExtras((prev) => ({ ...prev, cedeao: String(cedeaoValue) }));
      }
    }

  };


  // Fonction pour calculer la Prime Nette totale à partir des garanties
  const calculatePrimeNette = (garanties) => {
    let totalPN = 0;
    let linesProcessed = 0;
    
    (garanties || []).forEach((o, index) => {
      if (o.IdGarantie === 0 || o.IdSousGarantie === 0) return;
      if (estGarantieExclue(o)) return;
      const isTaken = checkedState[index] ?? true;
      if (!isTaken) return;
      
      const pn = isEditing && editedPrimes[index]?.PrimeNette !== undefined
        ? toNumber(editedPrimes[index].PrimeNette)
        : toNumber(o.PrimeNette);
      
      totalPN += pn;
      linesProcessed += 1;
    });
    
    const ligne0 = (garanties || []).find((x) => x.IdGarantie === 0 || x.IdSousGarantie === 0) || {};
    // En mode édition, on ignore la prime nette imposée pour refléter immédiatement les modifications
    const imposedPN = isEditing ? 0 : toNumber(ligne0.TotalPrimeNetteImposee ?? 0);
    
    return imposedPN > 0 ? imposedPN : totalPN;
  };

  // Ajouter une nouvelle garantie à la liste locale pour ce devis
  const handleAddGarantie = () => {
    const chosenId = selectedGarantieId;
    // 1) Sélection obligatoire
    if (!chosenId) {
      toast.error("Sélectionnez une sous-garantie");
      return;
    }

    // 2) Empêcher les doublons (même sous-garantie déjà ajoutée)
    const duplicate = (offres || []).some(
      (o) => String(o.IdSousGarantie || o.IdGarantie) === String(chosenId)
    );
    if (duplicate) {
      toast.error("Cette sous-garantie a déjà été ajoutée");
      return;
    }

    // 3) Normalisation/validation des champs numériques (>= 0)
    const toNumberNonNeg = (v) => {
      // Utilise le parseur robuste déjà défini (gère espaces, libellés, virgules)
      const n = toNumber(v);
      if (Number.isNaN(n) || n < 0) return 0;
      return n;
    };

    const capital = toNumberNonNeg(newGarantieForm.capital);
    const primeAnnuelle = toNumberNonNeg(newGarantieForm.prime_annuelle);
    const primeNette = toNumberNonNeg(newGarantieForm.prime_nette);
    const montantFranchise = toNumberNonNeg(newGarantieForm.montant_franchise);
    const tauxFranchise = toNumberNonNeg(newGarantieForm.taux_franchise);
    const franchiseMin = toNumberNonNeg(newGarantieForm.franchise_minimum);
    const franchiseMax = toNumberNonNeg(newGarantieForm.franchise_maximum);
    const capitalDeces = toNumberNonNeg(newGarantieForm.capital_deces);
    const capitalIPP = toNumberNonNeg(newGarantieForm.capital_ipp);
    const capitalFT = toNumberNonNeg(newGarantieForm.capital_ft);
    const reductionCommerciale = toNumberNonNeg(newGarantieForm.reduction_commerciale);
    const reductionBns = toNumberNonNeg(newGarantieForm.reduction_bns);

    // 4) Exiger au moins une valeur métier non nulle (prime ou capital)
    if (capital === 0 && primeAnnuelle === 0 && primeNette === 0) {
      toast.error("Renseignez au moins une valeur (capital, prime annuelle ou prime nette)");
      return;
    }

    // 5) Libellé de la sous-garantie
    const selectedSousGarantie = sousGarantiesAll.find(
      (sg) => String(sg.IdSousGarantie || sg.IdGarantie) === String(chosenId)
    );
    const libelle = selectedSousGarantie?.LibelleSousGarantie || `Garantie ${chosenId}`;

    // 6) Création de la ligne conforme à l’API/affichage
    const created = {
      IdGarantie: parseInt(chosenId, 10),
      IdSousGarantie: parseInt(chosenId, 10),
      LibelleSousGarantie: libelle,
      PrimeAnnuelle: primeAnnuelle,
      PrimeNette: primeNette,
      Capital: capital,
      Franchise: montantFranchise,
      TauxFranchise: tauxFranchise,
      FranchiseMin: franchiseMin,
      FranchiseMax: franchiseMax,
      CapitalDeces: capitalDeces,
      CapitalIPP: capitalIPP,
      CapitalFT: capitalFT,
      ReductionCommerciale: reductionCommerciale,
      ReductionBns: reductionBns,
      // Affichage
      TexteFranchise: montantFranchise > 0 ? `${montantFranchise} FCFA` : "NEANT",
      Acquise: !!newGarantieForm.acquise,
      // Marqueur local utile pour différencier dans la construction JSON
      is_new_garantie: true,
    };

    // 7) Injection immédiate dans le tableau + marquage modification
    const next = [...(offres || []), created];
    dispatch(updateOffres({ devisId: effectiveDevisId, offres: next }));
    dispatch(setHasModifications({ devisId: effectiveDevisId, value: true }));

    // 8) Mise à jour des cases à cocher (cochée par défaut selon le formulaire)
    const newCheckedState = [...(checkedState || [])];
    newCheckedState[next.length - 1] = true; // Cocher la nouvelle garantie par défaut
    setCheckedState(newCheckedState);
    
    // Forcer le recalcul des totaux du récapitulatif
    hasInitializedTotals.current = false;
    
    // Forcer la mise à jour de la Prime Nette immédiatement en utilisant la même logique que le useEffect
    const newPrimeNette = calculatePrimeNette(next);
    setPrimeNette(newPrimeNette);
    // En mode édition, synchroniser également le champ de saisie "Total Prime Nette"
    if (isEditing) {
      setEditedTotals((prev) => ({
        ...prev,
        pn: String(newPrimeNette),
      }));
    }
    // Mettre également à jour immédiatement la Prime TTC (Prime Nette + Accessoire + Taxe d'enregistrement + CEDEAO + FGA)
    try {
      const ligne0 = (next || []).find((x) => x.IdGarantie === 0 || x.IdSousGarantie === 0) || {};
      const taxe = toNumber(ligne0.Taxe || 0);
      const accessoire = toNumber(ligne0.MontantAccessoire || 0);
      const cedeao = ensureCedeaoMin(ligne0.CEDEAO || 0);
      const fga = fgaAmount || 0;
      const newTTC = newPrimeNette + taxe + accessoire + cedeao + fga;
      setCumulPrimeTTC(newTTC);
      if (isEditing) {
        setEditedTotals((prev) => ({
          ...prev,
          ttc: String(newTTC),
        }));
      }
    } catch (_) {}
    
    // Notifier le composant parent de la mise à jour de la prime nette
    try {
      window.dispatchEvent(new CustomEvent('devis:updated', { 
        detail: { 
          id_devis: effectiveDevisId,
          prime_nette: newPrimeNette
        } 
      }));
    } catch (_) {}

    // 9) Reset propre du formulaire et fermeture
    setShowAddDropdown(false);
    setSelectedGarantieId("");
    setNewGarantieForm({
      acquise: true,
      capital: "0",
      prime_annuelle: "0",
      prime_nette: "0",
      montant_franchise: "0",
      taux_franchise: "0",
      franchise_minimum: "0",
      franchise_maximum: "0",
      capital_deces: "0",
      capital_ipp: "0",
      capital_ft: "0",
      reduction_commerciale: "0",
      reduction_bns: "0",
    });

    toast.success("Garantie ajoutée avec succès");
  };


  const handleSavePrimes = async () => {

    let newTotalPrimeAnnuelle = 0;

    let newTotalPrimeNette = 0;



    // Créer une copie modifiable des offres (les garanties supprimées ont déjà été retirées)
    const updatedOffres = [...offres];
    // Appliquer les valeurs imposées pour Taxe / Accessoire / CEDEAO sur la ligne agrégée (IdGarantie === 0)
    try {
      const idx0 = updatedOffres.findIndex((o) => o.IdGarantie === 0);
      if (idx0 !== -1) {
        const imposedTaxe = editedExtras.taxe !== "" ? toNumber(editedExtras.taxe) : toNumber(updatedOffres[idx0]?.Taxe || 0);
        const imposedAcc = editedExtras.accessoire !== "" ? toNumber(editedExtras.accessoire) : toNumber(updatedOffres[idx0]?.MontantAccessoire || 0);
        const imposedCedeao = ensureCedeaoMin(editedExtras.cedeao !== "" ? editedExtras.cedeao : updatedOffres[idx0]?.CEDEAO || 0);
        const imposedFga = editedExtras.fga !== "" ? toNumber(editedExtras.fga) : toNumber(updatedOffres[idx0]?.FGAImpose ?? updatedOffres[idx0]?.Fga ?? 0);
        // Persister aussi les totaux imposés sur la ligne agrégée SANS impacter les lignes
        const imposedPA = editedTotals.pa !== "" ? toNumber(editedTotals.pa) : undefined;
        const imposedPN = editedTotals.pn !== "" ? toNumber(editedTotals.pn) : undefined;
        const imposedTTC = editedTotals.ttc !== "" ? toNumber(editedTotals.ttc) : undefined;
        updatedOffres[idx0] = {
          ...updatedOffres[idx0],
          Taxe: imposedTaxe,
          MontantAccessoire: imposedAcc,
          CEDEAO: imposedCedeao,
          FGAImpose: imposedFga,
          TotalPrimeAnnuelleImposee: imposedPA ?? updatedOffres[idx0]?.TotalPrimeAnnuelleImposee,
          TotalPrimeNetteImposee: imposedPN ?? updatedOffres[idx0]?.TotalPrimeNetteImposee,
          TotalTTCImpose: imposedTTC ?? updatedOffres[idx0]?.TotalTTCImpose,
        };
      }
    } catch { }

    // Mettre à jour les primes dans la copie filtrée
    Object.keys(editedPrimes).forEach((index) => {

      const prime = editedPrimes[index];

      const pa = toNumber(prime?.PrimeAnnuelle ?? "");

      const pn = toNumber(prime?.PrimeNette ?? "");

      // Vérifier si cette garantie doit être exclue
      const offre = updatedOffres[index];
      if (offre && estGarantieExclue(offre)) {
        return; // Exclure du calcul des totaux
      }

      if (!isNaN(pa) && !isNaN(pn)) {
        // Mettre à jour la copie
        if (updatedOffres[index]) {
          updatedOffres[index] = {
            ...updatedOffres[index],
            PrimeAnnuelle: pa,
            PrimeNette: pn
          };
        }
        newTotalPrimeAnnuelle += pa;
        newTotalPrimeNette += pn;
      }
    });

    // Calculer les totaux pour les garanties non modifiées
    updatedOffres.forEach((offre, index) => {
      if (!editedPrimes[index] && offre.IdGarantie !== 0) {

        // Filtrer les garanties qui ne doivent jamais s'afficher
        if (estGarantieExclue(offre)) return; // Exclure du calcul des totaux

        const pa = toNumber(offre.PrimeAnnuelle ?? 0) || 0;

        const pn = toNumber(offre.PrimeNette ?? 0) || 0;

        newTotalPrimeAnnuelle += pa;
        newTotalPrimeNette += pn;

      }

    });



    // Mettre à jour le state Redux avec les nouvelles données (sans les garanties supprimées)
    dispatch(updateOffres({ devisId: effectiveDevisId, offres: updatedOffres }));

    // Marquer qu'il y a des modifications pour éviter le rechargement
    dispatch(setHasModifications({ devisId: effectiveDevisId, value: true }));

    // Persister immédiatement dans le localStorage pour éviter la réinitialisation au retour
    try {
      localStorage.setItem(
        `offres_${effectiveDevisId}`,
        JSON.stringify({ offres: updatedOffres, deletedGaranties })
      );
    } catch (_) { }

    const taxe = toNumber(updatedOffres.find(o => o.IdGarantie === 0)?.Taxe || 0);
    const accessoire = toNumber(updatedOffres.find(o => o.IdGarantie === 0)?.MontantAccessoire || 0);
    const cedeao = ensureCedeaoMin(updatedOffres.find(o => o.IdGarantie === 0)?.CEDEAO || 0);
    // Appliquer les totaux imposés à l'affichage si fournis
    const displayedPA = editedTotals.pa !== "" ? toNumber(editedTotals.pa) : newTotalPrimeAnnuelle;
    const displayedPN = editedTotals.pn !== "" ? toNumber(editedTotals.pn) : newTotalPrimeNette;
    const displayedTTC = editedTotals.ttc !== "" ? toNumber(editedTotals.ttc) : (taxe + accessoire + cedeao + displayedPN);



    setPrimeAnnuelle(displayedPA);

    setPrimeNette(displayedPN);

    setCumulPrimeTTC(displayedTTC);

    dispatch(setEditingMode(false));

    dispatch(clearEditedPrimes());

    // Mettre à jour l'état des checkboxes pour correspondre aux nouvelles offres
    const newCheckedState = Array.from({ length: updatedOffres.length }, (_, i) => checkedState[i] ?? true);
    setCheckedState(newCheckedState);

    // Appliquer la correction côté backend et rafraîchir les CPs
    try {
      const resolvedId = getResolvedDevisId();
      if (!Number.isFinite(parseInt(resolvedId)) || parseInt(resolvedId) <= 0) {
        return;
      }
      const result = await applyCorrectionWithDevisId(parseInt(resolvedId));
      if (result?.success) {
        //toast.success("Modifications enregistrées et conditions particulières mises à jour");
        try {
          window.dispatchEvent(new CustomEvent('offres:updated', { detail: { id_devis: effectiveDevisId } }));
        } catch (_) { }
        // Une fois le backend synchronisé avec succès, on peut vider la liste locale
        setDeletedGaranties([]);
      } else {
        toast.error(toHumanMessage(result?.message) || "Échec de l'enregistrement des modifications");
      }
    } catch (e) {
      toast.error(toHumanMessage(e?.message) || "Erreur lors de l'application des corrections");
      console.error(e);
    }
    console.log("🔄 Primes mises à jour dans le state Redux:", {
      PrimeAnnuelle: newTotalPrimeAnnuelle,

      PrimeNette: newTotalPrimeNette,

      PrimeTTC: displayedTTC,

      modifiedOffres: Object.keys(editedPrimes).length,
      hasModifications: true
    });

  };



  const handleCheckboxChange = (index) => {

    const newCheckedState = [...checkedState];

    newCheckedState[index] = !newCheckedState[index];

    setCheckedState(newCheckedState);

  };

  // Supprimer une garantie de la liste
  const handleDeleteGarantie = (index) => {
    const garantie = offres[index];
    if (!garantie || garantie.IdGarantie === 0) return; // Ne pas supprimer la ligne agrégée

    // Demander confirmation à l'utilisateur
    const confirmMessage = `Êtes-vous sûr de vouloir supprimer la garantie "${garantie.LibelleSousGarantie}" ?\n\nCette garantie sera supprimée définitivement de la liste.`;

    if (window.confirm(confirmMessage)) {
      const garantieId = parseInt(garantie.IdSousGarantie || garantie.IdGarantie);

      // Ajouter l'ID à la liste des garanties supprimées
      setDeletedGaranties(prev => [...prev, garantieId]);

      // Supprimer immédiatement de la liste d'offres
      const filteredOffres = offres.filter((_, i) => i !== index);
      dispatch(updateOffres({ devisId: effectiveDevisId, offres: filteredOffres }));
      // Forcer le recalcul des totaux du récapitulatif
      hasInitializedTotals.current = false;

      // Recalculer immédiatement la Prime Nette et la Prime TTC après suppression
      try {
        const newPrimeNette = calculatePrimeNette(filteredOffres);
        setPrimeNette(newPrimeNette);
        if (isEditing) {
          setEditedTotals((prev) => ({
            ...prev,
            pn: String(newPrimeNette),
          }));
        }

        const ligne0 = (filteredOffres || []).find((x) => x.IdGarantie === 0 || x.IdSousGarantie === 0) || {};
        const taxe = toNumber(ligne0.Taxe || 0);
        const accessoire = toNumber(ligne0.MontantAccessoire || 0);
        const cedeao = ensureCedeaoMin(ligne0.CEDEAO || 0);
        const fga = fgaAmount || 0;
        const newTTC = newPrimeNette + taxe + accessoire + cedeao + fga;
        setCumulPrimeTTC(newTTC);
        if (isEditing) {
          setEditedTotals((prev) => ({
            ...prev,
            ttc: String(newTTC),
          }));
        }
      } catch (_) {}

      // Réindexer editedPrimes pour éviter les décalages de valeurs après suppression
      try {
        const newEditedPrimes = {};
        Object.keys(editedPrimes || {}).forEach((k) => {
          const oldIdx = parseInt(k, 10);
          if (Number.isNaN(oldIdx)) return;
          if (oldIdx === index) return; // on supprime l'entrée correspondante
          const newIdx = oldIdx > index ? oldIdx - 1 : oldIdx; // compacter les indices au-delà
          newEditedPrimes[newIdx] = editedPrimes[oldIdx];
        });
        dispatch(updateEditedPrimes(newEditedPrimes));
      } catch (_) { }

      // Mettre à jour l'état des checkboxes
      const newCheckedState = checkedState.filter((_, i) => i !== index);
      setCheckedState(newCheckedState);

      // Marquer qu'il y a des modifications
      dispatch(setHasModifications({ devisId: effectiveDevisId, value: true }));

      // Persister immédiatement dans le localStorage pour éviter la perte de données
      try {
        const updatedDeletedGaranties = [...deletedGaranties, garantieId];
        localStorage.setItem(
          `offres_${effectiveDevisId}`,
          JSON.stringify({ offres: filteredOffres, deletedGaranties: updatedDeletedGaranties, hasModifications: true })
        );
        // Notifier les autres composants de la mise à jour
        window.dispatchEvent(new CustomEvent('offres:updated', { detail: { id_devis: effectiveDevisId } }));
      } catch (_) { }

      toast.success(`Garantie "${garantie.LibelleSousGarantie}" supprimée de la liste`);
    }
  };






  const handleNext = async () => {

    nextStep();

  };
  // console.log("FgaAmount:", fgaAmount);



  const getCorrectionData = () => {

    console.log("🔍 getCorrectionData - Données disponibles:", {

      offres: offres?.length || 0,

      editedPrimes: editedPrimes?.length || 0,

      hasModifications: hasModifications,
      source: "Redux state"
    });

    // Log des premières garanties pour debug
    if (offres && offres.length > 0) {
      console.log("🔍 Premières garanties Redux:", offres.slice(0, 3).map(o => ({
        libelle: o.LibelleSousGarantie,
        pa: o.PrimeAnnuelle,
        pn: o.PrimeNette
      })));
    }


    // Vérifier si on a des données d'offres ou des primes modifiées

    if ((!offres || offres.length === 0) && (!editedPrimes || editedPrimes.length === 0)) {

      console.log("ℹ️ Aucune donnée d'offres ou de primes modifiées disponible");

      return null;

    }



    let totalPrimeAnnuelle = 0;
    // total incluant toutes les garanties (y compris FGA) pour persistance backend
    let totalPrimeNetteAll = 0;
    // total éventuellement excluant FGA pour des affichages internes si nécessaire
    let totalPrimeNetteExclFGA = 0;



    // Conserver les indices d'origine pour rester aligné avec editedPrimes/checkedState
    const garantiesExistantes = (offres || [])
      .map((o, originalIndex) => ({ o, originalIndex }))
      .filter(({ o }) => {
        if (o.IdGarantie === 0 || !o.LibelleSousGarantie) return false;

        // Filtrer les garanties qui ne doivent jamais s'afficher
        if (estGarantieExclue(o)) return false;

        return true;
      })
      .map(({ o, originalIndex }) => {

        // Utiliser directement les valeurs mises à jour dans Redux
        // Si editedPrimes existe, l'utiliser, sinon utiliser les valeurs Redux mises à jour
        const pa = editedPrimes[originalIndex]?.PrimeAnnuelle !== undefined
          ? toNumber(editedPrimes[originalIndex].PrimeAnnuelle)
          : toNumber(o.PrimeAnnuelle);

        const pn = editedPrimes[originalIndex]?.PrimeNette !== undefined
          ? toNumber(editedPrimes[originalIndex].PrimeNette)
          : toNumber(o.PrimeNette);



        // Log pour debug - afficher les valeurs utilisées
        if (originalIndex < 3) { // Log seulement les 3 premières pour éviter le spam
          console.log(`🔍 Garantie ${originalIndex} (${o.LibelleSousGarantie}):`, {
            editedPrimes: editedPrimes[originalIndex],
            reduxPA: o.PrimeAnnuelle,
            reduxPN: o.PrimeNette,
            finalPA: pa,
            finalPN: pn
          });
        }

        totalPrimeAnnuelle += pa;

        // Toujours compter pour la persistance
        totalPrimeNetteAll += pn;
        // Exclure FGA uniquement pour les calculs d'affichage internes éventuels
        if (!isFGA(o)) {
          totalPrimeNetteExclFGA += pn;
        }



        return {

          // Utiliser l'identifiant le plus spécifique attendu par l'API
          id_garantie: parseInt(o.IdSousGarantie || o.IdGarantie),
          id_devis_detail: o.IdDevisDetail ? parseInt(o.IdDevisDetail) : null,

          // Etat d'acquisition: si décoché dans l'UI, doit apparaître NON dans les CP
          acquise: Boolean(editedPrimes[originalIndex]?.Acquise ?? checkedState[originalIndex] ?? true),
          // Alias commun côté API (certains endpoints attendent 'souscrite')
          souscrite: Boolean(editedPrimes[originalIndex]?.Acquise ?? checkedState[originalIndex] ?? true),

          capital: toNumber(o.Capital || 0),

          prime_annuelle: parseFloat(pa.toFixed(2)),

          prime_nette: parseFloat(pn.toFixed(2)),

          montant_franchise: toNumber(o.Franchise || 0),

          taux_franchise: toNumber(o.TauxFranchise || 0),

          franchise_minimum: toNumber(o.FranchiseMin || 0),

          franchise_maximum: toNumber(o.FranchiseMax || 0),

          capital_deces: toNumber(o.CapitalDeces || 0),

          capital_ipp: toNumber(o.CapitalIPP || 0),

          capital_ft: toNumber(o.CapitalFT || 0),

          // Réductions prises depuis la ligne si présentes (ou 0 par défaut)
          reduction_commerciale: toNumber(o.ReductionCommerciale || 0),
          reduction_bns: toNumber(o.ReductionBns || 0),
          is_new_garantie: !!o.is_new_garantie, // Indiquer explicitement si c'est une nouvelle garantie
        };

      });



    console.log("🔍 Garanties pour correction:", {

      garantiesExistantes: garantiesExistantes.length,

      totalOffres: offres?.length || 0,
      garantiesIncluses: garantiesExistantes.map(g => ({
        libelle: g.id_garantie === 0 ? "LIGNE TOTALE" : g.id_garantie,
        acquise: g.acquise,
        pa: g.prime_annuelle
      }))
    });

    const liste_garantie = garantiesExistantes;

    // Version "toutes garanties" pour la PERSISTENCE (n'exclut pas estGarantieExclue, mais EXCLUT FGA et CEDEAO pour sync PDF)
    let totalPrimeNettePersistAll = 0;
    (offres || []).forEach((o, originalIndex) => {
      if (o.IdGarantie === 0 || !o.LibelleSousGarantie) return;
      if (isFGA(o)) return; // EXCLURE FGA du total Prime Nette stocké
      if (isCEDEAO(o)) return; // EXCLURE CEDEAO du total Prime Nette (ajouté séparément dans le TTC)

      const pn = editedPrimes[originalIndex]?.PrimeNette !== undefined
        ? toNumber(editedPrimes[originalIndex].PrimeNette)
        : toNumber(o.PrimeNette);
      totalPrimeNettePersistAll += pn;
    });


    const ligne0 = (offres || []).find((o) => o.IdGarantie === 0) || {};

    const taxe = parseFloat(ligne0.Taxe || 0);

    const accessoire = parseFloat(ligne0.MontantAccessoire || 0);

    // Utiliser la valeur modifiée de CEDEAO si disponible, sinon celle de ligne0, avec valeur par défaut 1000
    const cedeaoVal = ensureCedeaoMin(
      editedExtras.cedeao !== "" ? editedExtras.cedeao : ligne0.CEDEAO || 0
    );

    // Calcul du FGA: somme des primes nettes des lignes identifiées comme FGA (modifiable par saisie)
    let fgaVal = 0;
    try {
      const sourceGaranties = (authoritativeGarantiesRef.current && authoritativeGarantiesRef.current.length > 0)
        ? authoritativeGarantiesRef.current
        : (offres || []);
      fgaVal = (sourceGaranties || []).reduce((acc, o, originalIndex) => {
        // Identifier la ligne FGA
        const id = parseInt(o?.IdSousGarantie || o?.IdGarantie);
        const lib = String(o?.LibelleSousGarantie || o?.LibelleGarantie || '').toLowerCase();
        const isFga = id === 169 || lib.includes('fga');
        if (!isFga) return acc;
        // Prendre en compte les éventuelles modifications saisies
        const pn = editedPrimes[originalIndex]?.PrimeNette !== undefined
          ? toNumber(editedPrimes[originalIndex].PrimeNette)
          : toNumber(o.PrimeNette || 0);
        return acc + pn;
      }, 0);
    } catch (_) { fgaVal = 0; }
    // Override par la saisie utilisateur si fournie
    try {
      if (editedExtras && editedExtras.fga !== "") {
        fgaVal = toNumber(editedExtras.fga);
      }
    } catch (_) { }

    // Si disponibles, utiliser les garanties restaurées "autoritatives" (garanties corrigées) pour les totaux
    // NOTE: On NE SURCHARGE PLUS si on a des modifications locales (nouvelles garanties) pour éviter les décalages
    let totalPNPersist = totalPrimeNettePersistAll;
    let totalPAPersist = totalPrimeAnnuelle;

    // On ne fallback vers authoritative que si on n'a aucune modification et aucune offre chargée (peu probable ici)
    // ou si on veut vraiment la cohérence stricte avec l'API au détriment de l'affichage courant.
    // L'utilisateur veut la cohérence avec l'écran -> on garde totalPrimeNettePersistAll.

    // Préférer les valeurs imposées saisies par l'utilisateur si disponibles
    try {
      if (editedTotals && editedTotals.pn !== "") totalPNPersist = toNumber(editedTotals.pn);
      if (editedTotals && editedTotals.pa !== "") totalPAPersist = toNumber(editedTotals.pa);
    } catch (_) { }

    // Total TTC PERSISTÉ en incluant CEDEAO et FGA, et en priorisant TTC imposé si fourni
    // Le backend attend un TTC cohérent = PN + taxe + accessoire + cedeao + FGA
    // Si l'utilisateur a imposé une valeur TTC, on l'utilise, sinon on calcule
    let totalPrimeTTCPersistAll = taxe + accessoire + totalPNPersist + fgaVal;
    try {
      if (editedTotals && editedTotals.ttc !== "") {
        totalPrimeTTCPersistAll = toNumber(editedTotals.ttc);
      }
    } catch (_) { }



    // Récupération de l'ID devis depuis différents états possibles

    // Fallback plus robuste pour l'ID devis
    let idDevisFromState = devisSaved?.IdDevis || devisSaved?.id_devis || devisSaved?.id;
    if (!idDevisFromState) {
      // Essayer avec l'ID extrait de l'URL si disponible
      try {
        const path = window?.location?.pathname || '';
        const matchEdition = path.match(/edition-devis\/(?:\d+)\/(\d+)/);
        const matchDetails = path.match(/details-devis\/(\d+)/);
        const id = matchEdition ? parseInt(matchEdition[1], 10) : (matchDetails ? parseInt(matchDetails[1], 10) : null);
        if (Number.isFinite(id)) idDevisFromState = id;
      } catch (_) { }
    }
    if (!idDevisFromState && Number.isFinite(parseInt(effectiveDevisId))) {
      idDevisFromState = parseInt(effectiveDevisId);
    }



    console.log("🔍 ID devis récupéré:", {
      devisSaved,
      IdDevis: devisSaved?.IdDevis,
      id_devis: devisSaved?.id_devis,
      id: devisSaved?.id,
      finalId: idDevisFromState
    });

    // Fallback plus robuste pour l'ID devis
    let idDevisFromStateFallback = idDevisFromState;
    if (!idDevisFromStateFallback) {
      // Essayer avec l'ID extrait de l'URL si disponible
      try {
        const path = window?.location?.pathname || '';
        const matchEdition = path.match(/edition-devis\/(?:\d+)\/(\d+)/);
        const matchDetails = path.match(/details-devis\/(\d+)/);
        const id = matchEdition ? parseInt(matchEdition[1], 10) : (matchDetails ? parseInt(matchDetails[1], 10) : null);
        if (Number.isFinite(id)) idDevisFromStateFallback = id;
      } catch (_) { }
    }
    if (!idDevisFromStateFallback && Number.isFinite(parseInt(effectiveDevisId))) {
      idDevisFromStateFallback = parseInt(effectiveDevisId);
    }

    console.log("🔍 ID devis récupéré (fallback):", idDevisFromStateFallback);



    // Validation des données avant envoi

    // Détection renouvellement robuste pour id_avenant
    const detectRenewal = () => {
      try {
        if (typeof isEditPolice !== 'undefined' && isEditPolice) return true;
        if (sessionStorage.getItem(`forceRenewalRestore_${effectiveDevisId}`)) return true;
        // Sticky flag set earlier in the flow to survive route changes (edition -> details)
        if (sessionStorage.getItem(`renewalDetected_${effectiveDevisId}`) === '1') return true;
        const path = window?.location?.pathname?.toLowerCase?.() || '';
        // Considérer toute route d'édition de devis comme un flux de renouvellement/édition
        if (path.includes('/edition-devis/')) return true;
        // Et considérer également la page détails-devis comme faisant partie du flux de renouvellement
        if (path.includes('/details-devis/')) return true;
        if (path.includes('mouvement') || path.includes('renouvel')) return true;
      } catch (_) { }
      return false;
    };
    const isRenewalDetected = detectRenewal();
    try { if (isRenewalDetected) sessionStorage.setItem(`renewalDetected_${effectiveDevisId}`, '1'); } catch (_) { }
    const currentPathForLog = (() => { try { return window?.location?.pathname || ''; } catch { return ''; } })();
    console.log('🔎 Détection id_avenant (renouvellement):', { isEditPolice, isRenewalDetected, id_avenant: isRenewalDetected ? 2 : undefined, path: currentPathForLog });

    const correctionData = {

      id_devis: parseInt(idDevisFromState || 0),

      prime_annuelle: parseFloat(totalPAPersist.toFixed(2)),

      // Persister la prime nette basée sur TOUTES les garanties (pas d'exclusion visuelle)
      prime_nette: parseFloat(totalPNPersist.toFixed(2)),

      taxe: parseFloat(taxe.toFixed(2)),

      accessoire: parseFloat(accessoire.toFixed(2)),

      // CEDEAO doit être envoyé en minuscule côté backend
      cedeao: parseFloat(cedeaoVal.toFixed(2)),
      // Nouveau champ attendu par l'API: FGA (somme des lignes FGA)
      fga: parseFloat((fgaVal || 0).toFixed(2)),

      prime_ttc: parseFloat(totalPrimeTTCPersistAll.toFixed(2)),

      date_emission: handleDate(dateEmission),

      date_effet: handleDate(dateEffet),

      date_expiration: dateExpiration,

      numero_police: `POL-${Date.now()}`,

      // Réductions globales à 0 (les réductions par garantie sont envoyées dans chaque ligne)
      reduction_commerciale: 0,
      reduction_bns: 0,
      reduction_flotte: 0.00,

      liste_garantie,

      // Supprimer côté backend les garanties absentes: on force le backend à refléter strictement liste_garantie
      supprimer_garanties_manquantes: true,
      // Fournir explicitement la liste des IDs supprimés pour suppression côté API
      garanties_supprimees: (deletedGaranties || []).map((id) => parseInt(id, 10)).filter((n) => Number.isFinite(n)),
      // Avenant 2 = Renouvellement (détection élargie)
      id_avenant: isRenewalDetected ? 2 : undefined,
    };



    // Validation finale des données

    if (!correctionData.id_devis || correctionData.id_devis <= 0) {

      console.warn("ℹ️ ID devis manquant dans le state; il sera injecté lors de l'appel avec applyCorrectionWithDevisId.");

      // Ne pas retourner ici: l'ID sera fourni par applyCorrectionWithDevisId

    }



    if (!correctionData.liste_garantie || correctionData.liste_garantie.length === 0) {

      console.error("❌ Aucune garantie dans la liste");

      return null;

    }



    // Vérifier que toutes les garanties ont des données valides

    const invalidGaranties = correctionData.liste_garantie.filter(g =>

      // Pour les garanties existantes, id_garantie est requis. Pour les nouvelles (is_new_garantie), il peut être null

      (!g.is_new_garantie && (g.id_garantie === null || g.id_garantie === undefined)) ||

      typeof g.acquise !== 'boolean' ||

      Number.isNaN(g.capital) ||

      Number.isNaN(g.prime_annuelle) ||

      Number.isNaN(g.prime_nette)

    );



    if (invalidGaranties.length > 0) {

      console.error("❌ Garanties invalides détectées:", invalidGaranties);

      return null;

    }



    console.log("🔍 Données de correction validées:", correctionData);

    return correctionData;

  };



  const applyCorrection = async () => {

    const correctionData = getCorrectionData();

    if (!correctionData) {

      console.log("ℹ️ Aucune modification de primes à appliquer");

      return { success: true, message: "Aucune modification à appliquer" };

    }



    try {

      console.log("🚀 Application de la correction (Redux):", correctionData);

      const action = await dispatch(correctionDevis(correctionData));

      if (action.type === 'corrections/create/fulfilled') {

        console.log("✅ Correction appliquée (Redux):", action.payload);

        // Laisser le recalcul local des totaux (sum des garanties) mettre à jour PrimeNette/Annuelle/TTC

        // Écraser les offres locales avec les valeurs corrigées
        try {
          const byId = new Map(
            correctionData.liste_garantie.map(g => [parseInt(g.id_garantie), g])
          );
          let nextOffres = (offres || []).map(o => {
            if (o.IdGarantie === 0) return o; // garder la ligne agrégée telle quelle
            const key = parseInt(o.IdSousGarantie || o.IdGarantie);
            const corrected = byId.get(key);
            if (!corrected) return o;
            return {
              ...o,
              PrimeAnnuelle: corrected.prime_annuelle,
              PrimeNette: corrected.prime_nette,
            };
          });
          // Appliquer/Préserver les valeurs imposées sur la ligne agrégée
          const idx0 = nextOffres.findIndex(o => o?.IdGarantie === 0 || o?.IdSousGarantie === 0);
          if (idx0 !== -1) {
            const l0 = nextOffres[idx0] || {};
            nextOffres[idx0] = {
              ...l0,
              Taxe: toNumber(correctionData.taxe ?? l0.Taxe ?? 0),
              MontantAccessoire: toNumber(correctionData.accessoire ?? l0.MontantAccessoire ?? 0),
              CEDEAO: ensureCedeaoMin(correctionData.cedeao ?? l0.CEDEAO ?? 0),
              TotalPrimeAnnuelleImposee: editedTotals?.pa !== '' ? toNumber(editedTotals.pa) : l0.TotalPrimeAnnuelleImposee,
              TotalPrimeNetteImposee: editedTotals?.pn !== '' ? toNumber(editedTotals.pn) : l0.TotalPrimeNetteImposee,
              TotalTTCImpose: editedTotals?.ttc !== '' ? toNumber(editedTotals.ttc) : l0.TotalTTCImpose,
            };
          }
          dispatch(updateOffres({ devisId: effectiveDevisId, offres: nextOffres }));
          try {
            localStorage.setItem(
              `offres_${effectiveDevisId}`,
              JSON.stringify({ offres: nextOffres, deletedGaranties })
            );
          } catch (_) { }
        } catch { }
        dispatch(setEditingMode(false));

        dispatch(clearEditedPrimes());
        // Vider deletedGaranties seulement après succès côté backend (géré plus haut)

        dispatch(clearModifications(effectiveDevisId));

        // Persister dans recap_correction pour synchronisation immédiate avec le PDF
        try {
          const ids = new Set([
            String(devisSaved?.IdDevis || ''),
            String(devisSaved?.id_devis || ''),
            String(routeDevisId || ''),
            String(effectiveDevisId || ''),
            String(devisSaved?.numerodevis || '')
          ].filter(Boolean));
          ids.forEach(id => {
            localStorage.setItem(`recap_correction_${id}`, JSON.stringify(correctionData));
          });
        } catch (_) { }

        return { success: true, message: "Correction des primes appliquée avec succès", data: action.payload };

      }

      console.warn("❌ Correction échouée (Redux):", action);

      return { success: false, message: action.payload || 'Échec de la correction' };

    } catch (error) {

      console.error("❌ Erreur (Redux):", error);

      return { success: false, message: `Erreur: ${error.message}` };

    }

  };



  const applyCorrectionWithDevisId = async (devisId) => {

    console.log("🔍 ID devis reçu en paramètre:", devisId);

    console.log("🔍 État des données avant getCorrectionData:", {

      offres: offres?.length || 0,

      editedPrimes: editedPrimes?.length || 0,

      devisSaved: devisSaved

    });



    const correctionData = getCorrectionData();

    if (!correctionData) {

      console.log("ℹ️ Aucune modification de primes à appliquer");

      return { success: true, message: "Aucune modification à appliquer" };
    }

    // Normaliser et valider l'ID devis (paramètre -> helper -> payload)
    let finalDevisId = parseInt(devisId);
    if (!Number.isFinite(finalDevisId) || finalDevisId <= 0) {
      const helperId = parseInt(getResolvedDevisId());
      if (Number.isFinite(helperId) && helperId > 0) finalDevisId = helperId;
    }
    if (!Number.isFinite(finalDevisId) || finalDevisId <= 0) {
      const payloadId = parseInt(correctionData.id_devis);
      if (Number.isFinite(payloadId) && payloadId > 0) finalDevisId = payloadId;
    }
    if (!Number.isFinite(finalDevisId) || finalDevisId <= 0) {
      console.error("❌ Aucun ID devis valide trouvé:", { devisId, helper: getResolvedDevisId(), payload: correctionData.id_devis });
      return { success: false, message: "ID devis manquant ou invalide" };
    }

    const updatedCorrectionData = {

      ...correctionData,

      id_devis: parseInt(finalDevisId),

    };



    try {

      console.log("🚀 Application de la correction avec ID devis:", updatedCorrectionData);

      const action = await dispatch(correctionDevis(updatedCorrectionData));

      if (action.type === 'corrections/create/fulfilled') {

        console.log("✅ Correction appliquée avec ID devis:", action.payload);

        // Laisser le recalcul local des totaux (sum des garanties) mettre à jour PrimeNette/Annuelle/TTC

        // Écraser les offres locales avec les valeurs corrigées
        try {
          const byId = new Map(
            updatedCorrectionData.liste_garantie.map(g => [parseInt(g.id_garantie), g])
          );
          const nextOffres = (offres || []).map(o => {
            if (o.IdGarantie === 0) return o;
            const key = parseInt(o.IdSousGarantie || o.IdGarantie);
            const corrected = byId.get(key);
            if (!corrected) return o;
            return {
              ...o,
              PrimeAnnuelle: corrected.prime_annuelle,
              PrimeNette: corrected.prime_nette,
            };
          });
          dispatch(updateOffres({ devisId: effectiveDevisId, offres: nextOffres }));
        } catch { }
        dispatch(setEditingMode(false));

        dispatch(clearEditedPrimes());
        setDeletedGaranties([]);

        // Rafraîchir immédiatement depuis le backend pour refléter les CPs sans rechargement manuel
        try {
          const corrected = await loadCorrectedGuaranteesFromDevis(parseInt(finalDevisId));
          if (corrected && corrected.length > 0) {
            const merged = await mergeWithBaselineTaxes(corrected);
            // Appliquer/Préserver les valeurs imposées sur la ligne agrégée du résultat fusionné
            let mergedWithTotals = merged;
            try {
              const idx0 = mergedWithTotals.findIndex(o => o?.IdGarantie === 0 || o?.IdSousGarantie === 0);
              if (idx0 !== -1) {
                const l0 = mergedWithTotals[idx0] || {};
                mergedWithTotals = [...mergedWithTotals];
                mergedWithTotals[idx0] = {
                  ...l0,
                  Taxe: toNumber(updatedCorrectionData.taxe ?? l0.Taxe ?? 0),
                  MontantAccessoire: toNumber(updatedCorrectionData.accessoire ?? l0.MontantAccessoire ?? 0),
                  CEDEAO: ensureCedeaoMin(updatedCorrectionData.cedeao ?? l0.CEDEAO ?? 0),
                  TotalPrimeAnnuelleImposee: editedTotals?.pa !== '' ? toNumber(editedTotals.pa) : l0.TotalPrimeAnnuelleImposee,
                  TotalPrimeNetteImposee: editedTotals?.pn !== '' ? toNumber(editedTotals.pn) : l0.TotalPrimeNetteImposee,
                  TotalTTCImpose: editedTotals?.ttc !== '' ? toNumber(editedTotals.ttc) : l0.TotalTTCImpose,
                  FGAImpose: editedExtras?.fga !== '' ? toNumber(editedExtras.fga) : l0.FGAImpose,
                };
              }
            } catch (_) { }
            dispatch(updateOffres({ devisId: effectiveDevisId, offres: mergedWithTotals }));
            dispatch(setHasModifications({ devisId: effectiveDevisId, value: true }));
            try { sessionStorage.setItem(`finalizedCorrection_${effectiveDevisId}`, '1'); } catch (_) { }
            try { window.dispatchEvent(new CustomEvent('offres:updated', { detail: { id_devis: effectiveDevisId } })); } catch (_) { }
          }
        } catch (e) {
          console.warn('⚠️ Rafraîchissement post-correction non disponible, les valeurs locales restent affichées', e);
        }

        dispatch(clearModifications(effectiveDevisId));

        // Persister dans recap_correction pour synchronisation immédiate avec le PDF
        try {
          const ids = new Set([
            String(devisSaved?.IdDevis || ''),
            String(devisSaved?.id_devis || ''),
            String(routeDevisId || ''),
            String(effectiveDevisId || ''),
            String(finalDevisId || ''),
            String(devisSaved?.numerodevis || '')
          ].filter(Boolean));
          ids.forEach(id => {
            localStorage.setItem(`recap_correction_${id}`, JSON.stringify(updatedCorrectionData));
          });
        } catch (_) { }

        return { success: true, message: "Correction des primes appliquée avec succès", data: action.payload };

      }



      // Gestion détaillée des erreurs

      if (action.type === 'corrections/create/rejected') {

        console.error("❌ Correction échouée avec ID devis:", action);

        console.error("❌ Détails de l'erreur:", action.payload);

        console.error("❌ Meta de l'erreur:", action.meta);



        // Essayer de récupérer les détails de l'erreur depuis la réponse

        let errorMessage = action.payload || 'Échec de la correction';

        if (action.meta?.arg) {

          console.error("❌ Données envoyées qui ont causé l'erreur:", action.meta.arg);

        }



        return { success: false, message: errorMessage, details: action.meta };

      }



      return { success: false, message: action.payload || 'Échec de la correction' };

    } catch (error) {

      console.error("❌ Erreur avec ID devis:", error);

      return { success: false, message: `Erreur: ${error.message}` };

    }

  };



  return (

    <div className="p-4 mb-6 col-span-full xl:col-span-6 bg-white rounded-md border-2 border-gray-200">

      {typeContrat === 0 && (

        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <ButtonNext
              handleClick={handleEditPrimes}
              buttonClassname={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${isEditPolice
                ? "text-white bg-orange-600 hover:bg-orange-700 shadow-lg"
                : "text-white bg-bleu-600 hover:bg-bleu-700"
                }`}
              content={isEditing ? "Annuler" : isEditPolice ? "Imposer la prime (Renouvellement)" : "Imposer la prime"}
            />

            {isEditPolice && restorationSource && (
              <div className="text-xs text-orange-600 font-medium bg-orange-50 px-3 py-1 rounded-full">
                Mode Renouvellement - Données corrigées restaurées depuis {restorationSource === 'localStorage' ? 'les données sauvegardées' : 'les conditions particulières'}
              </div>
            )}
          </div>
          <div className="ml-auto relative flex items-center space-x-4">
            {/* Bouton "Ajouter une garantie" qui s'affiche après avoir cliqué sur "Imposer la prime" */}
            {isEditing && (
              <ButtonNext
                handleClick={() => {
                  setShowAddDropdown((v) => !v);
                  if (!showAddDropdown) {
                    fetchSousGaranties();
                  }
                }}
                buttonClassname="px-4 py-2 rounded-md text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 active:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-400 transition-transform duration-150 ease-out transform hover:-translate-y-0.5 shadow-sm hover:shadow"
                content="Ajouter une garantie"
              />
            )}

            {showAddDropdown && (
              <div className="relative inline-block">
                <div className="absolute z-20 mt-2 right-0 w-[20rem] bg-white border border-gray-200 rounded-lg shadow-xl p-4">

                  <div className="grid grid-cols-1 gap-2 mb-2">
                    <div className="flex items-center w-full">
                      <div className="relative flex-1">
                        <select
                          value={selectedGarantieId}
                          onChange={(e) => setSelectedGarantieId(e.target.value)}
                          className="w-full appearance-none border border-gray-300 rounded-xl py-2.5 px-4 text-sm font-medium text-gray-700 bg-white shadow-sm transition duration-200 ease-in-out 
                 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 hover:border-blue-400"
                        >
                          <option value="" disabled className="text-gray-400 italic">
                            — Choisir une sous-garantie —
                          </option>

                          {sousGarantiesAll?.length > 0 ? (
                            (() => {
                              const filteredGaranties = sousGarantiesAll.filter((sg) => {
                                console.log('🔍 Garantie:', sg.LibelleSousGarantie, 'SaisieAuto:', sg.SaisieAuto, 'type:', typeof sg.SaisieAuto);
                                return sg.SaisieAuto === true || sg.SaisieAuto === 1 || sg.SaisieAuto === 'true';
                              });
                              console.log('📊 Garanties filtrées:', filteredGaranties.length, 'sur', sousGarantiesAll.length);
                              return filteredGaranties.map((sg) => (
                                <option
                                  key={String(sg.IdSousGarantie || sg.IdGarantie)}
                                  value={String(sg.IdSousGarantie || sg.IdGarantie)}
                                  className="text-gray-700"
                                >
                                  {sg.LibelleSousGarantie}
                                </option>
                              ));
                            })()
                          ) : (
                            <option disabled className="text-gray-400 italic">
                              Chargement des sous-garanties...
                            </option>
                          )}
                        </select>

                        {/* Petite flèche custom */}
                        <svg
                          className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none"
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                        >
                          <path
                            fillRule="evenodd"
                            d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.21 8.27a.75.75 0 01.02-1.06z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                    </div>

                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm text-gray-700">
                    <div>
                      <label className="flex items-center space-x-2 mb-2">
                        <input
                          type="checkbox"
                          checked={newGarantieForm.acquise}
                          onChange={(e) => setNewGarantieForm({ ...newGarantieForm, acquise: e.target.checked })}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="font-medium text-gray-600 text-xs">Acquise</span>
                      </label>
                      <label className="block mb-1 font-medium text-gray-600 text-xs">Capital</label>
                      <input
                        value={newGarantieForm.capital}
                        onChange={(e) => setNewGarantieForm({ ...newGarantieForm, capital: e.target.value })}
                        className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500 mb-2"
                      />
                      <label className="block mb-1 font-medium text-gray-600 text-xs">Prime annuelle</label>
                      <input
                        value={newGarantieForm.prime_annuelle}
                        onChange={(e) => setNewGarantieForm({ ...newGarantieForm, prime_annuelle: e.target.value })}
                        className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500 mb-2"
                      />
                      <label className="block mb-1 font-medium text-gray-600 text-xs">Prime nette</label>
                      <input
                        value={newGarantieForm.prime_nette}
                        onChange={(e) => setNewGarantieForm({ ...newGarantieForm, prime_nette: e.target.value })}
                        className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block mb-1 font-medium text-gray-600 text-xs">Montant franchise</label>
                      <input
                        value={newGarantieForm.montant_franchise}
                        onChange={(e) => setNewGarantieForm({ ...newGarantieForm, montant_franchise: e.target.value })}
                        className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500 mb-2"
                      />
                      <label className="block mb-1 font-medium text-gray-600 text-xs">Taux franchise</label>
                      <input
                        value={newGarantieForm.taux_franchise}
                        onChange={(e) => setNewGarantieForm({ ...newGarantieForm, taux_franchise: e.target.value })}
                        className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500 mb-2"
                      />
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block mb-1 font-medium text-gray-600 text-xs">Franchise min</label>
                          <input
                            value={newGarantieForm.franchise_minimum}
                            onChange={(e) => setNewGarantieForm({ ...newGarantieForm, franchise_minimum: e.target.value })}
                            className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block mb-1 font-medium text-gray-600 text-xs">Franchise max</label>
                          <input
                            value={newGarantieForm.franchise_maximum}
                            onChange={(e) => setNewGarantieForm({ ...newGarantieForm, franchise_maximum: e.target.value })}
                            className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-sm text-gray-700 mt-3">
                    <div>
                      <label className="block mb-1 font-medium text-gray-600 text-xs">Capital décès</label>
                      <input
                        value={newGarantieForm.capital_deces}
                        onChange={(e) => setNewGarantieForm({ ...newGarantieForm, capital_deces: e.target.value })}
                        className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block mb-1 font-medium text-gray-600 text-xs">Capital IPP</label>
                      <input
                        value={newGarantieForm.capital_ipp}
                        onChange={(e) => setNewGarantieForm({ ...newGarantieForm, capital_ipp: e.target.value })}
                        className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block mb-1 font-medium text-gray-600 text-xs">Capital FT</label>
                      <input
                        value={newGarantieForm.capital_ft}
                        onChange={(e) => setNewGarantieForm({ ...newGarantieForm, capital_ft: e.target.value })}
                        className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm text-gray-700 mt-3">
                    <div>
                      <label className="block mb-1 font-medium text-gray-600 text-xs">Réduction commerciale</label>
                      <input
                        value={newGarantieForm.reduction_commerciale}
                        onChange={(e) => setNewGarantieForm({ ...newGarantieForm, reduction_commerciale: e.target.value })}
                        className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block mb-1 font-medium text-gray-600 text-xs">Réduction BNS</label>
                      <input
                        value={newGarantieForm.reduction_bns}
                        onChange={(e) => setNewGarantieForm({ ...newGarantieForm, reduction_bns: e.target.value })}
                        className="w-full border border-gray-300 rounded-md py-1.5 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-200 focus:border-blue-500"
                      />
                    </div>
                  </div>
                  <div className="flex items-center justify-end mt-4 space-x-2">
                    <button
                      onClick={() => setShowAddDropdown(false)}
                      className="px-3 py-1.5 rounded-md bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-medium transition-colors"
                    >
                      Annuler
                    </button>
                    <button
                      onClick={handleAddGarantie}
                      className="px-3 py-1.5 rounded-md bg-orange-500 hover:bg-orange-600 text-white text-xs font-medium transition-colors"
                    >
                      Ajouter
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
          {isEditing && (

            <ButtonNext

              handleClick={handleSavePrimes}

              buttonClassname="text-white bg-blue-500 hover:bg-blue-600 px-4 py-2 rounded-md text-sm font-medium ml-2"

              content="Sauvegarder"

            />

          )}
        </div>

      )}

      <div className="flex space-x-6 p-2">

        <div>

          <label htmlFor="offre" className="font-bold mb-4 text-sm uppercase text-blue-500">

            Offre

          </label>

          <select

            name="offre"

            value={offre}

            disabled={offreState}

            onChange={(e) => handleChangeOffre(e.target.value)}
            className="bg-gray-50 mt-1 block w-96 rounded-md border-2 border-gray-300 py-1 px-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"

          >

            {offresList.map((offre) => (

              <option value={offre.IdOffre} key={offre.IdOffre}>

                {offre.LibelleOffre}

              </option>

            ))}

          </select>

        </div>

      </div>

      <div className="flex flex-col">

        <div className="-m-1.5 overflow-x-auto">

          <div className="p-1.5 min-w-full inline-block align-middle">

            <div className="border-2 border-gray-200 rounded-xl divide-y divide-gray-200 overflow-hidden">

              <div className="overflow-auto max-h-[28rem]">

                <table className="min-w-full table-auto divide-y divide-gray-200">

                  <thead className="bg-gray-50 sticky top-0 z-10 shadow-sm">

                    <tr>

                      <th scope="col" className="px-6 py-3 text-left text-[11px] tracking-wide font-medium text-gray-600 uppercase">Garantie</th>

                      <th scope="col" className="px-6 py-3 text-left text-[11px] tracking-wide font-medium text-gray-600 uppercase">Acquise</th>

                      <th scope="col" className="px-6 py-3 text-left text-[11px] tracking-wide font-medium text-gray-600 uppercase">Capital</th>

                      <th scope="col" className="px-6 py-3 text-left text-[11px] tracking-wide font-medium text-gray-600 uppercase">Franchise</th>

                      <th scope="col" className="px-6 py-3 text-left text-[11px] tracking-wide font-medium text-gray-600 uppercase">Formule</th>

                      <th scope="col" className="px-6 py-3 text-left text-[11px] tracking-wide font-medium text-gray-600 uppercase">Place</th>

                      <th scope="col" className="px-6 py-3 text-right text-[11px] tracking-wide font-medium text-gray-600 uppercase">Prime Annuelle</th>

                      <th scope="col" className="px-6 py-3 text-right text-[11px] tracking-wide font-medium text-gray-600 uppercase">Prime Nette</th>

                      {isEditing && typeContrat === 0 && (
                        <th scope="col" className="px-6 py-3 text-center text-xs font-normal text-gray-500 uppercase">Actions</th>
                      )}
                    </tr>

                  </thead>

                  <tbody className="divide-y divide-gray-200">

                    {offres.flatMap((offreSousgarantie, index) => {
                      // Filtrer les garanties qui ne doivent jamais s'afficher
                      if (estGarantieExclue(offreSousgarantie)) {
                        return []; // Ne pas afficher cette garantie
                      }

                      return offreSousgarantie.IdGarantie !== 0 && offreSousgarantie.IdSousGarantie !== 0 ? (

                        <tr key={index} className="odd:bg-white even:bg-gray-50 hover:bg-indigo-50/40 transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-normal">
                            <span>{offreSousgarantie.LibelleSousGarantie}</span>
                          </td>

                          <td className="py-3 pl-4">
                            <div className="flex items-center h-5">
                              {isEditing && typeContrat === 0 ? (
                                <input
                                  id={`custom-checkbox-${index}`}
                                  type="checkbox"
                                  checked={Boolean(editedPrimes[index]?.Acquise ?? checkedState[index])}
                                  onChange={(e) => handlePrimeChange(index, 'Acquise', e.target.checked)}
                                  className="border-gray-200 rounded text-blue-600 focus:ring-blue-500 cursor-pointer"
                                />
                              ) : (
                                <input
                                  id={`custom-checkbox-${index}`}
                                  type="checkbox"
                                  checked={Boolean(checkedState[index])}
                                  onChange={() => handleCheckboxChange(index)}
                                  className="border-gray-200 rounded text-blue-600 focus:ring-blue-500 cursor-pointer"
                                />
                              )}
                              <label htmlFor={`custom-checkbox-${index}`} className="sr-only">Checkbox</label>
                            </div>
                          </td>

                          <td className="px-6 py-4 whitespace-nowrap w-32 text-sm">
                            {isEditing && typeContrat === 0 ? (
                              <input
                                type="text"
                                inputMode="numeric"
                                placeholder="0"
                                value={(editedPrimes[index]?.Capital === '-')
                                  ? ''
                                  : formatFr((editedPrimes[index]?.Capital ?? offreSousgarantie.Capital ?? ''))
                                }
                                onChange={(e) => handlePrimeChange(index, 'Capital', unformat(e.target.value))}
                                className="w-28 px-3 py-1.5 text-xs border border-gray-300 rounded-md bg-white text-right focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                              />
                            ) : (
                              Intl.NumberFormat().format(parseInt(offreSousgarantie.Capital || 0))
                            )}
                          </td>

                          <td className="px-6 py-4 whitespace-nowrap w-32 text-sm">
                            {isEditing && typeContrat === 0 ? (
                              <input
                                type="text"
                                inputMode="numeric"
                                placeholder="0"
                                value={(editedPrimes[index]?.Franchise === '-')
                                  ? ''
                                  : formatFr((editedPrimes[index]?.Franchise ?? offreSousgarantie.Franchise ?? ''))
                                }
                                onChange={(e) => handlePrimeChange(index, 'Franchise', unformat(e.target.value))}
                                className="w-28 px-3 py-1.5 text-xs border border-gray-300 rounded-md bg-white text-right focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                              />
                            ) : (
                              offreSousgarantie.TexteFranchise
                            )}
                          </td>

                          <td className="px-6 py-4 whitespace-nowrap w-32 text-sm"></td>

                          <td className="px-6 py-4 whitespace-nowrap w-32 text-sm"></td>

                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-right text-indigo-500">

                            {isEditing && typeContrat === 0 ? (
                              <div className="relative inline-flex">
                                <input
                                  type="text"
                                  inputMode="numeric"
                                  placeholder="0"
                                  value={(editedPrimes[index]?.PrimeAnnuelle === '-')
                                    ? ''
                                    : formatFr((editedPrimes[index]?.PrimeAnnuelle ?? offreSousgarantie.PrimeAnnuelle ?? ''))
                                  }
                                  onChange={(e) => handlePrimeChange(index, 'PrimeAnnuelle', unformat(e.target.value))}
                                  className="w-32 pr-10 pl-3 py-1.5 text-xs border border-gray-300 rounded-md bg-white text-right focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                />
                                <span className="absolute inset-y-0 right-2 flex items-center text-[10px] font-semibold text-gray-500">FCFA</span>
                              </div>
                            ) : (

                              <span className="font-semibold text-indigo-600">{formatCurrency(offreSousgarantie.PrimeAnnuelle || 0)}</span>

                            )}

                          </td>

                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-right text-indigo-500">

                            {isEditing && typeContrat === 0 ? (
                              <div className="relative inline-flex">
                                <input
                                  type="text"
                                  inputMode="numeric"
                                  placeholder="0"
                                  value={(editedPrimes[index]?.PrimeNette === '-')
                                    ? ''
                                    : formatFr((editedPrimes[index]?.PrimeNette ?? offreSousgarantie.PrimeNette ?? ''))
                                  }
                                  onChange={(e) => handlePrimeChange(index, 'PrimeNette', unformat(e.target.value))}
                                  className="w-32 pr-10 pl-3 py-1.5 text-xs border border-gray-300 rounded-md bg-white text-right focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                />
                                <span className="absolute inset-y-0 right-2 flex items-center text-[10px] font-semibold text-gray-500">FCFA</span>
                              </div>
                            ) : (

                              <span className="font-semibold text-indigo-600">{formatCurrency(offreSousgarantie.PrimeNette || 0)}</span>

                            )}

                          </td>

                          <td className="px-6 py-4 whitespace-nowrap text-sm font-normal text-blue-500">

                          </td>

                          {isEditing && typeContrat === 0 && (
                            <td className="px-6 py-4 whitespace-nowrap text-center">
                              <button
                                onClick={() => handleDeleteGarantie(index)}
                                className="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                title="Supprimer cette garantie"
                              >
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            </td>
                          )}

                        </tr>

                      ) : (

                        []

                      )

                    })}

                  </tbody>

                </table>
              </div>

            </div>

            <div className="py-1 px-0">
              {/* Extras: Taxe, Accessoire, CEDEAO, FGA */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                {/* Taxe */}
                <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-200 p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
                        {/* icon receipt */}
                        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M8 7h8M8 11h8M8 15h5" /><path d="M6 3h12a1 1 0 0 1 1 1v16l-3-2-3 2-3-2-3 2V4a1 1 0 0 1 1-1z" /></svg>
                      </span>
                      <p className="text-[11px] tracking-wide font-medium text-gray-500 uppercase">Taxe d'enregistrement</p>
                    </div>
                  </div>
                  {isEditing ? (
                    <div className="mt-2 relative">
                      <input
                        type="text"
                        inputMode="numeric"
                        value={formatFr(editedExtras.taxe)}
                        onChange={(e) => handleExtrasChange('taxe', unformat(e.target.value))}
                        placeholder="0"
                        className="mt-1 w-full rounded-md border-gray-300 pr-14 pl-3 py-2 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-right font-medium"
                      />
                      <span className="absolute inset-y-0 right-3 flex items-center text-xs font-semibold text-gray-500">FCFA</span>
                      <p className="mt-1 text-xs text-gray-400">Saisissez le montant de la taxe.</p>
                    </div>
                  ) : (
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{formatCurrency(editedExtras.taxe ||detailsBeforeEdit?.taxe || 0)}</p>
                  )}
                </div>

                {/* FGA (issu des conditions particulières) */}
                <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-200 p-4">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-yellow-50 text-yellow-700">
                      {/* icon shield */}
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 3l7 4v5c0 5-3.5 9-7 9s-7-4-7-9V7l7-4z" /></svg>
                    </span>
                    <p className="text-[11px] tracking-wide font-medium text-gray-500 uppercase">FGA</p>
                  </div>
                  {isEditing ? (
                    <div className="mt-2 relative">
                      <input
                        type="text"
                        inputMode="numeric"
                        value={editedExtras.fga}
                        onChange={(e) => handleExtrasChange('fga', e.target.value)}
                        placeholder="0"
                        className="mt-1 w-full rounded-md border-gray-300 pr-14 pl-3 py-2 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-right font-medium"
                      />
                      <span className="absolute inset-y-0 right-3 flex items-center text-xs font-semibold text-gray-500">FCFA</span>
                      <p className="mt-1 text-xs text-gray-400">Montant FGA appliqué au devis.</p>
                    </div>
                  ) : (
                      <p className="mt-2 text-2xl font-semibold text-gray-900">{formatCurrency(editedExtras.fga ||detailsBeforeEdit?.fga || 0)}</p>
                  )}
                </div>

                {/* Accessoire */}
                <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-200 p-4">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
                      {/* icon toolbox */}
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M3 7h18v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" /><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" /><path d="M3 11h18" /></svg>
                    </span>
                    <p className="text-[11px] tracking-wide font-medium text-gray-500 uppercase">Accessoire</p>
                  </div>
                  {isEditing ? (
                    <div className="mt-2 relative">
                      <input
                        type="text"
                        inputMode="numeric"
                        value={formatFr(editedExtras.accessoire)}
                        onChange={(e) => handleExtrasChange('accessoire', unformat(e.target.value))}
                        placeholder="0"
                        className="mt-1 w-full rounded-md border-gray-300 pr-14 pl-3 py-2 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-right font-medium"
                      />
                      <span className="absolute inset-y-0 right-3 flex items-center text-xs font-semibold text-gray-500">FCFA</span>
                      <p className="mt-1 text-xs text-gray-400">Montant de l'accessoire appliqué au devis.</p>
                    </div>
                  ) : (
                      <p className="mt-2 text-2xl font-semibold text-gray-900">{formatCurrency(editedExtras.accessoire || detailsBeforeEdit?.accessoire || 0)}</p>
                  )}
                </div>

                {/* CEDEAO */}
                <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-200 p-4 hidden">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-yellow-50 text-yellow-600">
                      {/* icon globe */}
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="9" /><path d="M2 12h20" /><path d="M12 3a12 12 0 0 1 0 18a12 12 0 0 1 0-18z" /></svg>
                    </span>
                    <p className="text:[11px] tracking-wide font-medium text-gray-500 uppercase">CEDEAO</p>
                  </div>
                  {isEditing ? (
                    <div className="mt-2 relative">
                      <input
                        type="number"
                        step="1000"
                        min="0"
                        value={editedExtras.cedeao !== "" && editedExtras.cedeao !== undefined ? editedExtras.cedeao : 1000}
                        onChange={(e) => handleExtrasChange('cedeao', e.target.value)}
                        placeholder="1000"
                        className="mt-1 w-full rounded-md border-gray-300 pr-14 pl-3 py-2 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-right font-medium"
                      />
                      <span className="absolute inset-y-0 right-3 flex items-center text-xs font-semibold text-gray-500">FCFA</span>
                      <p className="mt-1 text-xs text-gray-400">Montant CEDEAO appliqué au devis (multiple de 1000).</p>
                    </div>
                  ) : (
                      <p className="mt-2 text-2xl font-semibold text-gray-900 d-none">{formatCurrency(detailsBeforeEdit?.cedeao || 0)}</p>
                  )}
                </div>
              </div>

              {/* Totaux */}
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Total Prime Annuelle */}
                <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-200 p-4">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-gray-50 text-gray-500">
                      <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
                    </span>
                    <p className="text-[11px] tracking-wide font-medium text-gray-500 uppercase">Total Prime Annuelle</p>
                  </div>
                  {isEditing ? (
                    <div className="mt-2 relative">
                      <input
                        type="text"
                        inputMode="numeric"
                        value={formatFr(editedTotals.pa)}
                        onChange={(e) => handleTotalsChange('pa', unformat(e.target.value))}
                        placeholder="0"
                        className="mt-1 w-full rounded-md border-gray-300 pr-14 pl-3 py-2 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-right font-medium"
                      />
                      <span className="absolute inset-y-0 right-3 flex items-center text-xs font-semibold text-gray-500">FCFA</span>
                    </div>
                  ) : (
                      <p className="mt-2 text-xl font-semibold text-gray-900">{formatCurrency(editedTotals.pa || detailsBeforeEdit?.primeannuelle || 0)}</p>
                  )}
                </div>
                {/* Total Prime Nette */}
                <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-200 p-4">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-gray-50 text-gray-500">
                      <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 3v18M3 12h18" /></svg>
                    </span>
                    <p className="text-[11px] tracking-wide font-medium text-gray-500 uppercase">Total Prime Nette</p>
                  </div>
                  {isEditing ? (
                    <div className="mt-2 relative">
                      <input
                        type="text"
                        inputMode="numeric"
                        value={formatFr(editedTotals.pn)}
                        onChange={(e) => handleTotalsChange('pn', unformat(e.target.value))}
                        placeholder="0"
                        className="mt-1 w-full rounded-md border-gray-300 pr-14 pl-3 py-2 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-right font-medium"
                      />
                      <span className="absolute inset-y-0 right-3 flex items-center text-xs font-semibold text-gray-500">FCFA</span>
                    </div>
                  ) : (
                      <p className="mt-2 text-xl font-semibold text-gray-900">{formatCurrency(editedTotals.pn || (detailsBeforeEdit?.primenette - detailsBeforeEdit?.fga) || 0)}</p>
                  )}
                </div>
                {/* Prime TTC */}
                <div className="rounded-xl bg-gradient-to-br from-indigo-50 to-white ring-1 ring-indigo-200 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-[11px] tracking-wide font-semibold text-indigo-700 uppercase">Prime TTC</p>
                    {!isEditing && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">Calculé</span>
                    )}
                  </div>
                  {isEditing ? (
                    <div className="mt-2 relative">
                      <input
                        type="text"
                        inputMode="numeric"
                        value={formatFr(editedTotals.ttc)}
                        onChange={(e) => handleTotalsChange('ttc', unformat(e.target.value))}
                        placeholder="0"
                        className="mt-1 w-full rounded-md border-gray-300 pr-14 pl-3 py-2 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-right font-semibold text-indigo-700"
                      />
                      <span className="absolute inset-y-0 right-3 flex items-center text-xs font-semibold text-indigo-600">FCFA</span>
                    </div>
                  ) : (
                      <p className="mt-2 text-2xl font-extrabold text-indigo-700">{formatCurrency(editedTotals.ttc || detailsBeforeEdit?.primettc || 0)}</p>
                  )}
                </div>
              </div>
            </div>

            <div>

              <p>

                <OutlineButton

                  handleClick={prevStep}

                  buttonClassname="before:bg-red-600 text-red-600 text-xs"

                  content="Précédent"

                />

                <ButtonNext

                  handleClick={handleNext}

                  buttonClassname="text-white bg-blue-500 hover:bg-blue-800 mt-8 ml-4"

                  content="Suivant"

                />

              </p>

            </div>

          </div>

        </div>

      </div>

    </div>

  );

}







export default OffreSection;