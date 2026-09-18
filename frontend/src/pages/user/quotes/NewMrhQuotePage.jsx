import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { dataStore } from '../../../api/dataStore';
import { quoteApi, mrhApi, customerApi, settingsApi, contractApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import {
  Home,
  ArrowRight,
  ArrowLeft,
  Calculator,
  Plus,
  Trash2,
  Edit3,
  Search,
  UserPlus,
  Save,
  CheckCircle2,
  ShieldAlert,
  Building,
  DollarSign,
  FileText,
  Percent,
} from 'lucide-react';
import { ViewQuoteModal } from './ViewQuoteModal';
import { QuickAddClientModal } from '../clients/QuickAddClientModal';

// Formattage monétaire FCFA
const formatFcfa = (val) => {
  const num = typeof val === 'string' ? parseFloat(val.replace(/\s/g, '')) || 0 : Number(val) || 0;
  return new Intl.NumberFormat('fr-FR').format(Math.round(num));
};

const cleanNum = (str) => {
  if (typeof str === 'number') return str;
  return parseFloat(String(str || '0').replace(/\s/g, '')) || 0;
};

// Durées standards OREOLE
const DEFAULT_DUREES = [
  { id: 1, duree: '1 Mois' },
  { id: 2, duree: '3 Mois' },
  { id: 3, duree: '6 Mois' },
  { id: 4, duree: '12 Mois (Annuel)' },
  { id: 5, duree: 'Divers / Période Spécifique' },
];

export const NewMrhQuotePage = () => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  // Étape du formulaire (1: Contrat, 2: Habitations, 3: Récapitulatif/Imposition, 4: Souscripteur/Assuré)
  const [step, setStep] = useState(1);

  // Modales
  const [createdQuote, setCreatedQuote] = useState(null);
  const [isQuickAddClientOpen, setIsQuickAddClientOpen] = useState(false);

  // -------------------------------------------------------------
  // RÉFÉRENTIELS OREOLE / DJANGO
  // -------------------------------------------------------------
  const [clients, setClients] = useState([]);
  const [companies, setCompanies] = useState(() => dataStore.getActiveCompanies('MRH'));
  const [tarifs, setTarifs] = useState([
    { IdTarif: 401, LibelleTarif: 'MULTIRISQUES HABITATION STANDARD', Libelle: 'MULTIRISQUES HABITATION STANDARD' }
  ]);
  const [termes, setTermes] = useState([
    { IdTerme: 1, Libelle: 'Tacite reconduction' },
    { IdTerme: 2, Libelle: 'Ferme' }
  ]);
  const [usages, setUsages] = useState([]);
  const [isLoadingUsages, setIsLoadingUsages] = useState(false);

  // ID du devis actif côté Backend MRH s'il est initialisé
  const [idDevisActuel, setIdDevisActuel] = useState(null);

  // -------------------------------------------------------------
  // ÉTAPE 1 : CONTRAT (_2 dans OREOLE)
  // -------------------------------------------------------------
  const [numeroPoliceCompagnie, setNumeroPoliceCompagnie] = useState('');
  const [compagnieId, setCompagnieId] = useState(1);
  const [compagnieNom, setCompagnieNom] = useState('NSIA ASSURANCES CI');
  const [categorieId, setCategorieId] = useState(401);
  const [reductionCommerciale, setReductionCommerciale] = useState(0);
  const [termeId, setTermeId] = useState(1);
  const [dureeId, setDureeId] = useState(4); // 4 = 12 Mois
  const todayStr = useMemo(() => new Date().toISOString().split('T')[0], []);
  const [dateEmission, setDateEmission] = useState(todayStr);
  const [dateEffet, setDateEffet] = useState(todayStr);
  const [customExpiration, setCustomExpiration] = useState('');

  // Calcul automatique de la date d'expiration
  const calculatedDateExpiration = useMemo(() => {
    if (!dateEffet) return '';
    if (Number(dureeId) === 5) {
      return customExpiration || '';
    }
    const d = new Date(dateEffet);
    let months = 12;
    if (Number(dureeId) === 1) months = 1;
    else if (Number(dureeId) === 2) months = 3;
    else if (Number(dureeId) === 3) months = 6;
    else if (Number(dureeId) === 4) months = 12;
    d.setMonth(d.getMonth() + months);
    d.setDate(d.getDate() - 1);
    return d.toISOString().split('T')[0];
  }, [dateEffet, dureeId, customExpiration]);

  // -------------------------------------------------------------
  // ÉTAPE 2 : HABITATIONS & MAISONS ASSURÉES (B2 dans OREOLE)
  // -------------------------------------------------------------
  const [maisons, setMaisons] = useState([
    {
      id: 1,
      maison_id: 1,
      code_usage: 'proprietaire_occupant_total',
      usage_libelle: 'Propriétaire occupant total',
      adresse: 'Cocody Riviera 3, Abidjan',
      valeur_batiment: 45000000,
      valeur_contenu: 15000000,
      loyer_mensuel: 0,
      capital_rvt: 0,
      options: ['rc_chef_famille', 'degats_eaux'],
      sous_garanties_optionnelles: ['vol_effraction'],
      prime_nette: 85000,
      taxe: 12325,
      accessoire: 5000,
      prime_ttc: 102325,
    }
  ]);

  // Formulaire courant pour ajouter / modifier une maison
  const [editingMaisonId, setEditingMaisonId] = useState(null);
  const [currentUsageCode, setCurrentUsageCode] = useState('proprietaire_occupant_total');
  const [currentAdresse, setCurrentAdresse] = useState('');
  const [currentValBatiment, setCurrentValBatiment] = useState('');
  const [currentValContenu, setCurrentValContenu] = useState('');
  const [currentLoyerMensuel, setCurrentLoyerMensuel] = useState('');
  const [currentCapitalRvt, setCurrentCapitalRvt] = useState('');
  const [availableOptions, setAvailableOptions] = useState([]);
  const [selectedOptions, setSelectedOptions] = useState([]);
  const [availableGaranties, setAvailableGaranties] = useState([]);
  const [selectedGaranties, setSelectedGaranties] = useState([]);

  // Détails de l'usage courant sélectionné
  const currentUsageDetails = useMemo(() => {
    return usages.find((u) => u.code === currentUsageCode) || null;
  }, [usages, currentUsageCode]);

  // -------------------------------------------------------------
  // ÉTAPE 3 : RÉCAPITULATIF FINANCIER & IMPOSITION (L2 dans OREOLE)
  // -------------------------------------------------------------
  const [isImpositionActive, setIsImpositionActive] = useState(false);
  const [imposedPrimesParMaison, setImposedPrimesParMaison] = useState({});
  const [imposedTaxe, setImposedTaxe] = useState('0');
  const [imposedAccessoire, setImposedAccessoire] = useState('5000');
  const [impositionMotif, setImpositionMotif] = useState('');

  // -------------------------------------------------------------
  // ÉTAPE 4 : SOUSCRIPTEUR / ASSURÉ (R2 dans OREOLE)
  // -------------------------------------------------------------
  const [souscripteurId, setSouscripteurId] = useState(1);
  const [assureId, setAssureId] = useState(1);
  const [searchSouscripteur, setSearchSouscripteur] = useState('');
  const [searchAssure, setSearchAssure] = useState('');
  const [isSearchSouscripteurOpen, setIsSearchSouscripteurOpen] = useState(false);
  const [isSearchAssureOpen, setIsSearchAssureOpen] = useState(false);
  const [telephoneAssure, setTelephoneAssure] = useState('+225 ');
  const [adresseGeo, setAdresseGeo] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // -------------------------------------------------------------
  // CHARGEMENT INITIAL DES RÉFÉRENTIELS DEPUIS L'API
  // -------------------------------------------------------------
  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      try {
        const [cls, cies, usgList, termList] = await Promise.all([
          customerApi.getClients().catch(() => []),
          settingsApi.getCompanies().catch(() => []),
          mrhApi.getUsages().catch(() => []),
          mrhApi.getTermes().catch(() => []),
        ]);

        if (!isMounted) return;

        if (cls && cls.length > 0) {
          setClients(cls);
          setSouscripteurId(cls[0].id);
          setAssureId(cls[0].id);
          setTelephoneAssure(cls[0].telephone || cls[0].mobile || '+225 ');
          setSearchSouscripteur(cls[0].nomcomplet || '');
          setSearchAssure(cls[0].nomcomplet || '');
        }

        if (cies && cies.length > 0) {
          const mapped = cies.map((c) => ({
            id: c.IdCompagnie || c.id,
            nom: c.RaisonSociale || c.nom,
          }));
          setCompanies(mapped);
          setCompagnieId(mapped[0].id);
          setCompagnieNom(mapped[0].nom);
        }

        if (usgList && usgList.length > 0) {
          setUsages(usgList);
          setCurrentUsageCode(usgList[0].code);
        }

        if (termList && termList.length > 0) {
          setTermes(termList);
          setTermeId(termList[0].IdTerme || 1);
        }
      } catch (err) {
        console.error('Erreur chargement référentiels MRH:', err);
      }
    };
    loadData();
    return () => { isMounted = false; };
  }, []);

  // Chargement dynamique des options et garanties de l'usage sélectionné
  useEffect(() => {
    let isMounted = true;
    if (!currentUsageCode) return;
    const fetchUsageAddons = async () => {
      try {
        const [opts, gars] = await Promise.all([
          mrhApi.getOptionsByUsage(currentUsageCode).catch(() => []),
          mrhApi.getGarantiesByUsage(currentUsageCode).catch(() => []),
        ]);
        if (isMounted) {
          setAvailableOptions(opts || []);
          setAvailableGaranties(gars || []);
        }
      } catch (e) {
        console.warn('Fallback options/garanties usage:', e);
      }
    };
    fetchUsageAddons();
    return () => { isMounted = false; };
  }, [currentUsageCode]);

  // Synchronisation des totaux financiers calculés
  const totalsFinanciers = useMemo(() => {
    let primeNette = 0;
    let taxes = 0;
    let accessoires = 0;

    maisons.forEach((m) => {
      const pNetteMaison = isImpositionActive && imposedPrimesParMaison[m.id] !== undefined
        ? cleanNum(imposedPrimesParMaison[m.id])
        : Number(m.prime_nette) || 0;
      primeNette += pNetteMaison;
      taxes += Number(m.taxe) || Math.round(pNetteMaison * 0.145);
      accessoires += Number(m.accessoire) || 5000;
    });

    if (isImpositionActive) {
      if (cleanNum(imposedTaxe) > 0) taxes = cleanNum(imposedTaxe);
      if (cleanNum(imposedAccessoire) > 0) accessoires = cleanNum(imposedAccessoire);
    }

    // Réduction commerciale
    const redRate = Math.min(Math.max(Number(reductionCommerciale) || 0, 0), 35) / 100;
    const primeNetteApresReduction = Math.round(primeNette * (1 - redRate));
    const primeTtc = primeNetteApresReduction + taxes + accessoires;

    return {
      primeNette,
      reductionMontant: Math.round(primeNette * redRate),
      primeNetteApresReduction,
      taxes,
      accessoires,
      primeTtc,
    };
  }, [maisons, isImpositionActive, imposedPrimesParMaison, imposedTaxe, imposedAccessoire, reductionCommerciale]);

  // -------------------------------------------------------------
  // ACTIONS : GESTION DES MAISONS
  // -------------------------------------------------------------
  const handleSaveMaison = async () => {
    const valBat = cleanNum(currentValBatiment);
    const valCont = cleanNum(currentValContenu);
    const loyer = cleanNum(currentLoyerMensuel);
    const rvt = cleanNum(currentCapitalRvt);

    if (valBat === 0 && valCont === 0 && loyer === 0 && rvt === 0) {
      toastError('Veuillez saisir au moins une valeur de capital (Bâtiment, Contenu, Loyer ou RVT).');
      return;
    }

    const usageObj = usages.find((u) => u.code === currentUsageCode);
    const libelleUsage = usageObj?.libelle || currentUsageCode;

    // Calcul de simulation de prime (ou via API /api/mrh/calcul/maison/)
    let primeNetteCalc = 0;
    try {
      const calcRes = await mrhApi.calculerPrimeMaison({
        code_usage: currentUsageCode,
        valeur_batiment: valBat,
        valeur_contenu: valCont,
        loyer_mensuel: loyer,
        capital_rvt: rvt,
        options: selectedOptions.map((o) => ({ code_option: o })),
        sous_garanties_optionnelles: selectedGaranties.map((g) => ({ code_sous_garantie: g })),
      });
      if (calcRes && (calcRes.prime_nette || calcRes.prime_nette_totale)) {
        primeNetteCalc = Number(calcRes.prime_nette || calcRes.prime_nette_totale);
      }
    } catch (_) {
      // Fallback formule standard OREOLE CIMA
      const batPrime = valBat * 0.0018;
      const contPrime = valCont * 0.0032;
      const loyerPrime = loyer * 12 * 0.0025;
      const rvtPrime = rvt * 0.0015;
      const optsPrime = selectedOptions.length * 8000;
      const garsPrime = selectedGaranties.length * 12000;
      primeNetteCalc = Math.max(Math.round(batPrime + contPrime + loyerPrime + rvtPrime + optsPrime + garsPrime), 25000);
    }

    const taxeCalc = Math.round(primeNetteCalc * 0.145);
    const accessoireCalc = 5000;
    const ttcCalc = primeNetteCalc + taxeCalc + accessoireCalc;

    if (editingMaisonId) {
      // Modification maison existante
      setMaisons((prev) =>
        prev.map((m) =>
          m.id === editingMaisonId
            ? {
                ...m,
                code_usage: currentUsageCode,
                usage_libelle: libelleUsage,
                adresse: currentAdresse || m.adresse,
                valeur_batiment: valBat,
                valeur_contenu: valCont,
                loyer_mensuel: loyer,
                capital_rvt: rvt,
                options: selectedOptions,
                sous_garanties_optionnelles: selectedGaranties,
                prime_nette: primeNetteCalc,
                taxe: taxeCalc,
                accessoire: accessoireCalc,
                prime_ttc: ttcCalc,
              }
            : m
        )
      );
      success('Logement modifié avec succès !');
      setEditingMaisonId(null);
    } else {
      // Ajout nouvelle maison
      const newMaison = {
        id: Date.now(),
        maison_id: Date.now(),
        code_usage: currentUsageCode,
        usage_libelle: libelleUsage,
        adresse: currentAdresse || `Logement ${maisons.length + 1}, Abidjan`,
        valeur_batiment: valBat,
        valeur_contenu: valCont,
        loyer_mensuel: loyer,
        capital_rvt: rvt,
        options: selectedOptions,
        sous_garanties_optionnelles: selectedGaranties,
        prime_nette: primeNetteCalc,
        taxe: taxeCalc,
        accessoire: accessoireCalc,
        prime_ttc: ttcCalc,
      };
      setMaisons((prev) => [...prev, newMaison]);
      success('Nouveau logement ajouté avec succès !');
    }

    // Reset du formulaire logement
    setCurrentAdresse('');
    setCurrentValBatiment('');
    setCurrentValContenu('');
    setCurrentLoyerMensuel('');
    setCurrentCapitalRvt('');
    setSelectedOptions([]);
    setSelectedGaranties([]);
  };

  const handleEditMaison = (m) => {
    setEditingMaisonId(m.id);
    setCurrentUsageCode(m.code_usage);
    setCurrentAdresse(m.adresse || '');
    setCurrentValBatiment(m.valeur_batiment ? String(m.valeur_batiment) : '');
    setCurrentValContenu(m.valeur_contenu ? String(m.valeur_contenu) : '');
    setCurrentLoyerMensuel(m.loyer_mensuel ? String(m.loyer_mensuel) : '');
    setCurrentCapitalRvt(m.capital_rvt ? String(m.capital_rvt) : '');
    setSelectedOptions(m.options || []);
    setSelectedGaranties(m.sous_garanties_optionnelles || []);
    window.scrollTo({ top: 350, behavior: 'smooth' });
  };

  const handleRemoveMaison = (id) => {
    if (maisons.length <= 1) {
      toastError('Un devis MRH doit comporter au moins une maison assurée.');
      return;
    }
    setMaisons((prev) => prev.filter((m) => m.id !== id));
    success('Maison retirée du devis.');
  };

  // -------------------------------------------------------------
  // VALIDATION & ENREGISTREMENT DU DEVIS MRH
  // -------------------------------------------------------------
  const handleFinalSubmit = async () => {
    if (maisons.length === 0) {
      toastError('Veuillez ajouter au moins une maison à assurer.');
      setStep(2);
      return;
    }

    const selectedClient = clients.find((c) => String(c.id) === String(souscripteurId)) || clients[0];
    const selectedAssure = clients.find((c) => String(c.id) === String(assureId)) || selectedClient;

    setIsSubmitting(true);
    try {
      const quotePayload = {
        client_nom: selectedClient?.nomcomplet || 'Souscripteur Uranus',
        client_id: selectedClient?.id,
        assure_nom: selectedAssure?.nomcomplet || selectedClient?.nomcomplet,
        assure_id: selectedAssure?.id,
        telephone_assure: telephoneAssure,
        adresse_geographique: adresseGeo || selectedClient?.adresse || 'Abidjan',
        produit: `Multirisques Habitation (${maisons.length} Logement${maisons.length > 1 ? 's' : ''})`,
        branche: 'MRH',
        compagnie: compagnieNom,
        id_compagnie: Number(compagnieId),
        numero_police_compagnie: numeroPoliceCompagnie,
        categorie: 'MULTIRISQUES HABITATION STANDARD',
        id_tarif: Number(categorieId),
        id_terme: Number(termeId),
        id_duree: Number(dureeId),
        date_emission: dateEmission,
        date_effet: dateEffet,
        date_expiration: calculatedDateExpiration,
        taux_reduction: Number(reductionCommerciale) || 0,
        is_prime_imposee: isImpositionActive,
        motif_imposition: impositionMotif,
        prime_nette: totalsFinanciers.primeNetteApresReduction,
        taxe: totalsFinanciers.taxes,
        accessoire: totalsFinanciers.accessoires,
        prime_ttc: totalsFinanciers.primeTtc,
        maisons: maisons.map((m) => ({
          code_usage: m.code_usage,
          adresse: m.adresse,
          valeur_batiment: m.valeur_batiment,
          valeur_contenu: m.valeur_contenu,
          loyer_mensuel: m.loyer_mensuel,
          capital_rvt: m.capital_rvt,
          options: m.options,
          sous_garanties: m.sous_garanties_optionnelles,
          prime_nette: isImpositionActive && imposedPrimesParMaison[m.id] !== undefined
            ? cleanNum(imposedPrimesParMaison[m.id])
            : m.prime_nette,
        })),
      };

      // 1. Sauvegarde locale dataStore pour consultation immédiate et hors ligne
      const savedLocal = dataStore.saveQuote(quotePayload);

      // 2. Appel au backend Django OREOLE (/api/mrh/devis/ ou /api/enregistrementdevismrh)
      let backendId = savedLocal.id;
      try {
        const res = await mrhApi.creerDevis({
          idintermediaire: 1,
          idcompagnie: Number(compagnieId),
          idproduit: 4, // 4 = MRH
          idtarif: Number(categorieId),
          idoffre: 10,
          idclient: Number(selectedClient?.id || 1),
          idassure: Number(selectedAssure?.id || selectedClient?.id || 1),
          dateeffet: `${dateEffet}T00:00:00Z`,
          dateemission: `${dateEmission}T00:00:00Z`,
          dateexpiration: `${calculatedDateExpiration}T23:59:59Z`,
          numeropoliciecompagnie: numeroPoliceCompagnie ? Number(numeroPoliceCompagnie) : 0,
          idterme: Number(termeId),
          idduree: Number(dureeId),
          reductioncommerciale: Number(reductionCommerciale) || 0,
        });
        if (res && (res.id || res.iddevis || res.ObjectId)) {
          backendId = res.id || res.iddevis || res.ObjectId;
          // Ajout des maisons au devis backend
          for (const m of maisons) {
            await mrhApi.ajouterMaison(backendId, {
              code_usage: m.code_usage,
              adresse: m.adresse,
              valeur_batiment: m.valeur_batiment,
              valeur_contenu: m.valeur_contenu,
              loyer_mensuel: m.loyer_mensuel,
              capital_rvt: m.capital_rvt,
              id_tarif: Number(categorieId),
              options: (m.options || []).map((o) => ({ code_option: o })),
              sous_garanties_optionnelles: (m.sous_garanties_optionnelles || []).map((g) => ({ code_sous_garantie: g })),
            });
          }
        }
      } catch (errApi) {
        console.warn('Appel API mrh fallback local:', errApi);
      }

      success(`Devis Multirisques Habitation N° ${savedLocal.numerodevis} créé avec succès !`);
      setCreatedQuote(savedLocal);
    } catch (err) {
      toastError('Erreur lors de la création du devis MRH.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConvertToContract = (q) => {
    const newContract = dataStore.convertQuoteToContract(q);
    success(`Devis converti en Contrat N° ${newContract.numeropolice} !`);
    setCreatedQuote(null);
    navigate(`/user/contracts/${newContract.id || newContract.numeropolice}`);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '1240px', margin: '0 auto', paddingBottom: '3rem' }}>
      {/* HEADER & BOUTON RETOUR */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <button
            type="button"
            className="btn btn-link"
            onClick={() => navigate('/user/quotes')}
            style={{ color: '#ef4444', fontWeight: 600, padding: 0, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          >
            ← Annuler
          </button>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Home size={28} color="#0ea5e9" />
            Production de Contrat Multirisques Habitation (MRH)
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Couverture complète CIMA : Incendie, Dégâts des eaux, Vol & Vandalisme, RC Chef de famille.
          </p>
        </div>

        {/* STEPPER OREOLE 4 ONGLETS */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {[
            { stepNum: 1, label: '1. CONTRAT' },
            { stepNum: 2, label: '2. HABITATION & BIENS' },
            { stepNum: 3, label: '3. RÉCAPITULATIF FINANCIER' },
            { stepNum: 4, label: '4. SOUSCRIPTEUR / ASSURÉ' },
          ].map((item) => (
            <button
              key={item.stepNum}
              type="button"
              onClick={() => setStep(item.stepNum)}
              style={{
                padding: '0.5rem 0.95rem',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: 'pointer',
                border: step === item.stepNum ? '2px solid #0ea5e9' : '1px solid var(--border-subtle)',
                background: step === item.stepNum ? 'rgba(14, 165, 233, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                color: step === item.stepNum ? '#38bdf8' : 'var(--text-muted)',
                transition: 'all 0.15s ease',
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* =========================================================================
          ÉTAPE 1 : CONTRAT (_2 OREOLE)
          ========================================================================= */}
      {step === 1 && (
        <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
          <h3 style={{ color: '#0ea5e9', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1.5rem', fontSize: '1.05rem' }}>
            Informations Générales du Contrat
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
            {/* Numéro police compagnie */}
            <div className="form-group">
              <label className="form-label">Numéro de police compagnie (Optionnel)</label>
              <input
                type="text"
                className="form-control"
                placeholder="Ex: POL-MRH-2026-001"
                value={numeroPoliceCompagnie}
                onChange={(e) => setNumeroPoliceCompagnie(e.target.value)}
              />
            </div>

            {/* Compagnie d'assurance */}
            <div className="form-group">
              <label className="form-label">Compagnie d'Assurance (* requis)</label>
              <select
                className="form-control"
                value={compagnieId}
                onChange={(e) => {
                  setCompagnieId(Number(e.target.value));
                  const c = companies.find((x) => String(x.id) === String(e.target.value));
                  if (c) setCompagnieNom(c.nom);
                }}
              >
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nom}
                  </option>
                ))}
              </select>
            </div>

            {/* Catégorie / Tarif MRH */}
            <div className="form-group">
              <label className="form-label">Catégorie / Formule (* requis)</label>
              <select
                className="form-control"
                value={categorieId}
                onChange={(e) => setCategorieId(Number(e.target.value))}
              >
                {tarifs.map((t) => (
                  <option key={t.IdTarif} value={t.IdTarif}>
                    {t.LibelleTarif || t.Libelle}
                  </option>
                ))}
              </select>
            </div>

            {/* Terme du contrat */}
            <div className="form-group">
              <label className="form-label">Terme du contrat</label>
              <select
                className="form-control"
                value={termeId}
                onChange={(e) => setTermeId(Number(e.target.value))}
              >
                {termes.map((t) => (
                  <option key={t.IdTerme} value={t.IdTerme}>
                    {t.Libelle}
                  </option>
                ))}
              </select>
            </div>

            {/* Réduction commerciale */}
            <div className="form-group">
              <label className="form-label">Réduction commerciale (%)</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="number"
                  min="0"
                  max="35"
                  className="form-control"
                  value={reductionCommerciale}
                  onChange={(e) => setReductionCommerciale(Math.max(0, Math.min(35, Number(e.target.value) || 0)))}
                />
                <Percent size={16} style={{ position: 'absolute', right: '12px', top: '12px', color: '#94a3b8' }} />
              </div>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Max. 35% sans dérogation</span>
            </div>

            {/* Durée du contrat */}
            <div className="form-group">
              <label className="form-label">Durée du contrat</label>
              <select
                className="form-control"
                value={dureeId}
                onChange={(e) => setDureeId(Number(e.target.value))}
              >
                {DEFAULT_DUREES.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.duree}
                  </option>
                ))}
              </select>
            </div>

            {/* Dates Émission & Effet */}
            <div className="form-group">
              <label className="form-label">Date d'émission</label>
              <input
                type="date"
                className="form-control"
                value={dateEmission}
                onChange={(e) => setDateEmission(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Date d'effet (* requis)</label>
              <input
                type="date"
                className="form-control"
                value={dateEffet}
                onChange={(e) => setDateEffet(e.target.value)}
              />
            </div>

            {/* Date Expiration */}
            <div className="form-group">
              <label className="form-label">Date d'expiration (* calculée)</label>
              {Number(dureeId) === 5 ? (
                <input
                  type="date"
                  className="form-control"
                  value={customExpiration}
                  onChange={(e) => setCustomExpiration(e.target.value)}
                />
              ) : (
                <input
                  type="date"
                  className="form-control"
                  value={calculatedDateExpiration}
                  readOnly
                  style={{ background: 'rgba(255,255,255,0.05)', color: '#60a5fa', fontWeight: 700 }}
                />
              )}
            </div>
          </div>

          <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setStep(2)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#0ea5e9' }}
            >
              Suivant : Habitation & Biens <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          ÉTAPE 2 : HABITATION & BIENS ASSURÉS (B2 OREOLE)
          ========================================================================= */}
      {step === 2 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Bloc Formulaire Ajout / Édition Maison */}
          <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ color: '#0ea5e9', fontWeight: 800, textTransform: 'uppercase', fontSize: '1.05rem', margin: 0 }}>
                {editingMaisonId ? 'Modifier la maison assurée' : 'Ajouter une maison assurée'}
              </h3>
              {editingMaisonId && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    setEditingMaisonId(null);
                    setCurrentValBatiment('');
                    setCurrentValContenu('');
                    setCurrentLoyerMensuel('');
                    setCurrentCapitalRvt('');
                    setSelectedOptions([]);
                    setSelectedGaranties([]);
                  }}
                  style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                >
                  Annuler modification
                </button>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
              {/* Usage Habitation */}
              <div className="form-group">
                <label className="form-label">Usage / Statut d'occupation (* requis)</label>
                <select
                  className="form-control"
                  value={currentUsageCode}
                  onChange={(e) => setCurrentUsageCode(e.target.value)}
                >
                  {usages.length > 0 ? (
                    usages.map((u) => (
                      <option key={u.code} value={u.code}>
                        {u.libelle}
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="proprietaire_occupant_total">Propriétaire occupant total</option>
                      <option value="proprietaire_occupant_partiel">Propriétaire occupant partiel</option>
                      <option value="proprietaire_non_occupant">Propriétaire non occupant</option>
                      <option value="locataire">Locataire (Logement entier)</option>
                      <option value="locataire_meuble">Locataire en meublé</option>
                      <option value="locataire_partiel">Locataire partiel</option>
                    </>
                  )}
                </select>
              </div>

              {/* Adresse complète */}
              <div className="form-group">
                <label className="form-label">Adresse / Localisation du bien</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Ex: Riviera Palmeraie, Rue Ministre, Villa 42"
                  value={currentAdresse}
                  onChange={(e) => setCurrentAdresse(e.target.value)}
                />
              </div>

              {/* Valeur Bâtiment */}
              <div className="form-group">
                <label className="form-label">Valeur Bâtiment (FCFA)</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Ex: 50 000 000"
                  value={currentValBatiment ? formatFcfa(currentValBatiment) : ''}
                  onChange={(e) => setCurrentValBatiment(e.target.value.replace(/[^0-9]/g, ''))}
                />
              </div>

              {/* Valeur Contenu */}
              <div className="form-group">
                <label className="form-label">Valeur Contenu & Mobilier (FCFA)</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Ex: 15 000 000"
                  value={currentValContenu ? formatFcfa(currentValContenu) : ''}
                  onChange={(e) => setCurrentValContenu(e.target.value.replace(/[^0-9]/g, ''))}
                />
              </div>

              {/* Loyer Mensuel */}
              <div className="form-group">
                <label className="form-label">Loyer Mensuel (Si locataire - FCFA)</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Ex: 350 000"
                  value={currentLoyerMensuel ? formatFcfa(currentLoyerMensuel) : ''}
                  onChange={(e) => setCurrentLoyerMensuel(e.target.value.replace(/[^0-9]/g, ''))}
                />
              </div>

              {/* Capital RVT */}
              <div className="form-group">
                <label className="form-label">Recours des Voisins et des Tiers - RVT (FCFA)</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Ex: 10 000 000"
                  value={currentCapitalRvt ? formatFcfa(currentCapitalRvt) : ''}
                  onChange={(e) => setCurrentCapitalRvt(e.target.value.replace(/[^0-9]/g, ''))}
                />
              </div>
            </div>

            {/* Options disponibles */}
            {availableOptions.length > 0 && (
              <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <h4 style={{ fontSize: '0.9rem', color: '#e2e8f0', fontWeight: 700, marginBottom: '0.75rem' }}>
                  Options Spécifiques d'Usage
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.75rem' }}>
                  {availableOptions.map((opt) => {
                    const code = opt.code_option || opt.code;
                    const isChecked = selectedOptions.includes(code);
                    return (
                      <label
                        key={code}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          fontSize: '0.85rem',
                          color: isChecked ? '#38bdf8' : '#cbd5e1',
                          cursor: 'pointer',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {
                            setSelectedOptions((prev) =>
                              prev.includes(code) ? prev.filter((x) => x !== code) : [...prev, code]
                            );
                          }}
                        />
                        <span>{opt.libelle || code}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Garanties Optionnelles */}
            {availableGaranties.length > 0 && (
              <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <h4 style={{ fontSize: '0.9rem', color: '#e2e8f0', fontWeight: 700, marginBottom: '0.75rem' }}>
                  Sous-Garanties Complémentaires
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.75rem' }}>
                  {availableGaranties.map((gar) => {
                    const code = gar.code_sous_garantie || gar.code;
                    const isChecked = selectedGaranties.includes(code);
                    return (
                      <label
                        key={code}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          fontSize: '0.85rem',
                          color: isChecked ? '#38bdf8' : '#cbd5e1',
                          cursor: 'pointer',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {
                            setSelectedGaranties((prev) =>
                              prev.includes(code) ? prev.filter((x) => x !== code) : [...prev, code]
                            );
                          }}
                        />
                        <span>{gar.libelle || code}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            )}

            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleSaveMaison}
                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#10b981' }}
              >
                <Plus size={16} />
                {editingMaisonId ? 'Enregistrer les modifications' : 'Ajouter cette maison au devis'}
              </button>
            </div>
          </div>

          {/* Liste des maisons ajoutées */}
          <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
            <h3 style={{ color: '#0ea5e9', fontWeight: 800, textTransform: 'uppercase', fontSize: '1.05rem', marginBottom: '1rem' }}>
              Maisons Assurées dans le Devis ({maisons.length})
            </h3>

            <div style={{ overflowX: 'auto' }}>
              <table className="table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: '#94a3b8', fontSize: '0.8rem' }}>
                    <th style={{ padding: '0.75rem' }}>#</th>
                    <th style={{ padding: '0.75rem' }}>USAGE</th>
                    <th style={{ padding: '0.75rem' }}>LOCALISATION</th>
                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>VALEUR BÂTIMENT</th>
                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>VALEUR CONTENU</th>
                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>PRIME NETTE</th>
                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>PRIME TTC</th>
                    <th style={{ padding: '0.75rem', textAlign: 'center' }}>ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {maisons.map((m, idx) => (
                    <tr key={m.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', fontSize: '0.85rem' }}>
                      <td style={{ padding: '0.75rem', fontWeight: 700, color: '#60a5fa' }}>{idx + 1}</td>
                      <td style={{ padding: '0.75rem', fontWeight: 600 }}>{m.usage_libelle || m.code_usage}</td>
                      <td style={{ padding: '0.75rem', color: '#cbd5e1' }}>{m.adresse || 'Abidjan'}</td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                        {formatFcfa(m.valeur_batiment)} FCFA
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                        {formatFcfa(m.valeur_contenu)} FCFA
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'var(--font-mono)', color: '#38bdf8', fontWeight: 700 }}>
                        {formatFcfa(m.prime_nette)} FCFA
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'var(--font-mono)', color: '#10b981', fontWeight: 700 }}>
                        {formatFcfa(m.prime_ttc)} FCFA
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => handleEditMaison(m)}
                            style={{ padding: '0.35rem 0.5rem' }}
                            title="Modifier"
                          >
                            <Edit3 size={14} />
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => handleRemoveMaison(m.id)}
                            style={{ padding: '0.35rem 0.5rem', color: '#ef4444' }}
                            title="Supprimer"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'space-between' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setStep(1)}
                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
              >
                <ArrowLeft size={16} /> Précédent
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setStep(3)}
                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#0ea5e9' }}
              >
                Suivant : Récapitulatif Financier <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          ÉTAPE 3 : RÉCAPITULATIF FINANCIER & IMPOSITION (L2 OREOLE)
          ========================================================================= */}
      {step === 3 && (
        <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
            <h3 style={{ color: '#0ea5e9', fontWeight: 800, textTransform: 'uppercase', fontSize: '1.05rem', margin: 0 }}>
              Décompte Financier & Imposition de Primes
            </h3>

            {isImpositionActive ? (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setIsImpositionActive(false);
                  setImposedPrimesParMaison({});
                  setImpositionMotif('');
                }}
                style={{ color: '#ef4444', borderColor: '#ef4444', fontSize: '0.8rem', padding: '0.4rem 0.85rem' }}
              >
                Annuler l'imposition manuelle
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setIsImpositionActive(true)}
                style={{ background: '#10b981', fontSize: '0.8rem', padding: '0.4rem 0.85rem' }}
              >
                Imposer Prime Globale / Par Maison
              </button>
            )}
          </div>

          {/* Cartes récapitulatives */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.75rem' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Prime Nette Totale</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                {formatFcfa(totalsFinanciers.primeNette)} FCFA
              </div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Réduction ({reductionCommerciale}%)</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f59e0b', fontFamily: 'var(--font-mono)' }}>
                - {formatFcfa(totalsFinanciers.reductionMontant)} FCFA
              </div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Taxes d'Enregistrement</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#cbd5e1', fontFamily: 'var(--font-mono)' }}>
                {formatFcfa(totalsFinanciers.taxes)} FCFA
              </div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Accessoires & Frais</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#cbd5e1', fontFamily: 'var(--font-mono)' }}>
                {formatFcfa(totalsFinanciers.accessoires)} FCFA
              </div>
            </div>

            <div style={{ background: 'rgba(14, 165, 233, 0.1)', padding: '1rem', borderRadius: '8px', border: '2px solid #0ea5e9' }}>
              <div style={{ fontSize: '0.75rem', color: '#38bdf8', textTransform: 'uppercase', fontWeight: 700 }}>Prime Globale TTC</div>
              <div style={{ fontSize: '1.35rem', fontWeight: 900, color: '#fff', fontFamily: 'var(--font-mono)' }}>
                {formatFcfa(totalsFinanciers.primeTtc)} FCFA
              </div>
            </div>
          </div>

          {/* Tableau d'imposition si activé */}
          {isImpositionActive && (
            <div style={{ background: 'rgba(16, 185, 129, 0.05)', border: '2px solid #10b981', padding: '1.5rem', borderRadius: '8px', marginBottom: '1.5rem' }}>
              <h4 style={{ color: '#10b981', fontWeight: 700, fontSize: '0.95rem', marginBottom: '1rem' }}>
                Mode Imposition Manuelle des Primes
              </h4>

              <div style={{ overflowX: 'auto', marginBottom: '1rem' }}>
                <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #10b981', fontSize: '0.8rem', color: '#a7f3d0' }}>
                      <th style={{ padding: '0.65rem' }}>MAISON</th>
                      <th style={{ padding: '0.65rem', textAlign: 'right' }}>PRIME CALCULÉE</th>
                      <th style={{ padding: '0.65rem', textAlign: 'right', width: '220px' }}>PRIME NETTE IMPOSÉE (FCFA)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {maisons.map((m, idx) => {
                      const val = imposedPrimesParMaison[m.id] !== undefined
                        ? imposedPrimesParMaison[m.id]
                        : String(m.prime_nette);
                      return (
                        <tr key={m.id} style={{ borderBottom: '1px solid rgba(16, 185, 129, 0.2)' }}>
                          <td style={{ padding: '0.65rem', fontWeight: 600 }}>Logement #{idx + 1} - {m.usage_libelle}</td>
                          <td style={{ padding: '0.65rem', textAlign: 'right', color: '#94a3b8' }}>
                            {formatFcfa(m.prime_nette)} FCFA
                          </td>
                          <td style={{ padding: '0.65rem', textAlign: 'right' }}>
                            <input
                              type="text"
                              className="form-control"
                              style={{ textAlign: 'right', fontWeight: 700, color: '#10b981', borderColor: '#10b981' }}
                              value={formatFcfa(val)}
                              onChange={(e) => {
                                const digits = e.target.value.replace(/[^0-9]/g, '');
                                setImposedPrimesParMaison((prev) => ({ ...prev, [m.id]: digits }));
                              }}
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Taxe Imposée (FCFA)</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Auto si 0"
                    value={imposedTaxe ? formatFcfa(imposedTaxe) : ''}
                    onChange={(e) => setImposedTaxe(e.target.value.replace(/[^0-9]/g, ''))}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Accessoire Imposé (FCFA)</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="5000 par défaut"
                    value={imposedAccessoire ? formatFcfa(imposedAccessoire) : ''}
                    onChange={(e) => setImposedAccessoire(e.target.value.replace(/[^0-9]/g, ''))}
                  />
                </div>
                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                  <label className="form-label">Motif de l'imposition</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Ex: Négociation commerciale grand compte / Tarif dérogatoire"
                    value={impositionMotif}
                    onChange={(e) => setImpositionMotif(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'space-between' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setStep(2)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <ArrowLeft size={16} /> Précédent
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setStep(4)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#0ea5e9' }}
            >
              Suivant : Souscripteur & Assuré <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          ÉTAPE 4 : SOUSCRIPTEUR / ASSURÉ & FINALISATION (R2 OREOLE)
          ========================================================================= */}
      {step === 4 && (
        <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
          <h3 style={{ color: '#0ea5e9', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1.5rem', fontSize: '1.05rem' }}>
            Souscripteur / Assuré
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
            {/* Nom du Client / Souscripteur avec autocomplétion OREOLE */}
            <div className="form-group" style={{ position: 'relative' }}>
              <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Nom du Client / Souscripteur (* requis)</span>
                <button
                  type="button"
                  onClick={() => setIsQuickAddClientOpen(true)}
                  style={{ background: 'transparent', border: 'none', color: '#38bdf8', cursor: 'pointer', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.2rem' }}
                >
                  <UserPlus size={14} /> + Nouveau client
                </button>
              </label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Rechercher un client..."
                  value={searchSouscripteur}
                  onChange={(e) => {
                    setSearchSouscripteur(e.target.value);
                    setIsSearchSouscripteurOpen(true);
                  }}
                  onFocus={() => setIsSearchSouscripteurOpen(true)}
                />
              </div>

              {isSearchSouscripteurOpen && (
                <div
                  style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    zIndex: 50,
                    background: '#1e293b',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    maxHeight: '220px',
                    overflowY: 'auto',
                    marginTop: '4px',
                    boxShadow: '0 10px 15px -3px rgba(0,0,0,0.5)',
                  }}
                >
                  {clients
                    .filter((c) => (c.nomcomplet || '').toLowerCase().includes((searchSouscripteur || '').toLowerCase()))
                    .map((c) => (
                      <div
                        key={c.id}
                        onClick={() => {
                          setSouscripteurId(c.id);
                          setSearchSouscripteur(c.nomcomplet);
                          setIsSearchSouscripteurOpen(false);
                          if (!searchAssure) {
                            setAssureId(c.id);
                            setSearchAssure(c.nomcomplet);
                          }
                          setTelephoneAssure(c.telephone || c.mobile || '+225 ');
                          setAdresseGeo(c.adresse || '');
                        }}
                        style={{ padding: '0.65rem 1rem', cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.85rem' }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(14, 165, 233, 0.2)')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                      >
                        <div style={{ fontWeight: 700, color: '#fff' }}>{c.nomcomplet}</div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{c.codeclient} • {c.telephone || c.mobile}</div>
                      </div>
                    ))}
                </div>
              )}
            </div>

            {/* Nom de l'Assuré */}
            <div className="form-group" style={{ position: 'relative' }}>
              <label className="form-label">Nom de l'Assuré (* requis)</label>
              <input
                type="text"
                className="form-control"
                placeholder="Rechercher un assuré..."
                value={searchAssure}
                onChange={(e) => {
                  setSearchAssure(e.target.value);
                  setIsSearchAssureOpen(true);
                }}
                onFocus={() => setIsSearchAssureOpen(true)}
              />

              {isSearchAssureOpen && (
                <div
                  style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    zIndex: 50,
                    background: '#1e293b',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    maxHeight: '220px',
                    overflowY: 'auto',
                    marginTop: '4px',
                    boxShadow: '0 10px 15px -3px rgba(0,0,0,0.5)',
                  }}
                >
                  {clients
                    .filter((c) => (c.nomcomplet || '').toLowerCase().includes((searchAssure || '').toLowerCase()))
                    .map((c) => (
                      <div
                        key={c.id}
                        onClick={() => {
                          setAssureId(c.id);
                          setSearchAssure(c.nomcomplet);
                          setIsSearchAssureOpen(false);
                          setTelephoneAssure(c.telephone || c.mobile || '+225 ');
                        }}
                        style={{ padding: '0.65rem 1rem', cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.85rem' }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(14, 165, 233, 0.2)')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                      >
                        <div style={{ fontWeight: 700, color: '#fff' }}>{c.nomcomplet}</div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{c.codeclient} • {c.telephone || c.mobile}</div>
                      </div>
                    ))}
                </div>
              )}
            </div>

            {/* Téléphone de l'assuré */}
            <div className="form-group">
              <label className="form-label">Numéro de Téléphone Assuré</label>
              <input
                type="tel"
                className="form-control"
                placeholder="+225 0700000000"
                value={telephoneAssure}
                onChange={(e) => setTelephoneAssure(e.target.value)}
              />
            </div>

            {/* Adresse Géographique */}
            <div className="form-group">
              <label className="form-label">Adresse Géographique</label>
              <input
                type="text"
                className="form-control"
                placeholder="Ex: Abidjan, Cocody Riviera"
                value={adresseGeo}
                onChange={(e) => setAdresseGeo(e.target.value)}
              />
            </div>
          </div>

          <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'space-between' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setStep(3)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <ArrowLeft size={16} /> Précédent
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={isSubmitting}
              onClick={handleFinalSubmit}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#0ea5e9', padding: '0.75rem 1.75rem', fontWeight: 800 }}
            >
              <Save size={18} />
              {isSubmitting ? 'Enregistrement en cours...' : 'Enregistrer le Devis MRH'}
            </button>
          </div>
        </div>
      )}

      {/* Modal d'affichage du devis créé */}
      {createdQuote && (
        <ViewQuoteModal
          isOpen={Boolean(createdQuote)}
          quote={createdQuote}
          onClose={() => {
            setCreatedQuote(null);
            navigate('/user/quotes');
          }}
          onConvertToContract={handleConvertToContract}
        />
      )}

      {/* Modal d'ajout rapide client */}
      <QuickAddClientModal
        isOpen={isQuickAddClientOpen}
        onClose={() => setIsQuickAddClientOpen(false)}
        onClientCreated={(newClient) => {
          setClients((prev) => [newClient, ...prev]);
          setSouscripteurId(newClient.id || newClient.IdClient);
          setSearchSouscripteur(newClient.nomcomplet || newClient.Nom);
          setTelephoneAssure(newClient.telephone || newClient.mobile || '+225 ');
        }}
      />
    </div>
  );
};

export default NewMrhQuotePage;
