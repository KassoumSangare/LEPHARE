import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { dataStore } from '../../../api/dataStore';
import { quoteApi, customerApi, settingsApi, contractApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import {
  HeartPulse,
  ArrowRight,
  ArrowLeft,
  Plus,
  Trash2,
  Edit3,
  UserPlus,
  Save,
  Percent,
  CheckCircle2,
  Users,
  Shield,
  Building,
  UserCheck,
} from 'lucide-react';
import { ViewQuoteModal } from './ViewQuoteModal';
import { QuickAddClientModal } from '../clients/QuickAddClientModal';

const formatFcfa = (val) => {
  const num = typeof val === 'string' ? parseFloat(val.replace(/\s/g, '')) || 0 : Number(val) || 0;
  return new Intl.NumberFormat('fr-FR').format(Math.round(num));
};

const cleanNum = (str) => {
  if (typeof str === 'number') return str;
  return parseFloat(String(str || '0').replace(/\s/g, '')) || 0;
};

// Durées standards CIMA / OREOLE
const DEFAULT_DUREES = [
  { id: 1, duree: '1 Mois' },
  { id: 2, duree: '3 Mois' },
  { id: 3, duree: '6 Mois' },
  { id: 4, duree: '12 Mois (Annuel)' },
  { id: 5, duree: 'Divers' },
];

export const NewSanteQuotePage = () => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  // Étape courante (1: Contrat & Formule, 2: Collèges & Filiales, 3: Souscripteur, Adhérents & Décompte)
  const [step, setStep] = useState(1);

  // Modales
  const [createdQuote, setCreatedQuote] = useState(null);
  const [isQuickAddClientOpen, setIsQuickAddClientOpen] = useState(false);

  // Référentiels
  const [clients, setClients] = useState([]);
  const [companies, setCompanies] = useState(() => dataStore.getActiveCompanies('Santé'));

  // -------------------------------------------------------------
  // ÉTAPE 1 : CONTRAT SANTÉ (kX OREOLE)
  // -------------------------------------------------------------
  const [typeContrat, setTypeContrat] = useState('GROUPE'); // 'GROUPE' | 'INDIVIDUEL' | 'FAMILLE'
  const [numeroPoliceCompagnie, setNumeroPoliceCompagnie] = useState('');
  const [compagnieId, setCompagnieId] = useState(1);
  const [compagnieNom, setCompagnieNom] = useState('NSIA ASSURANCES CI');
  const [offreCommerciale, setOffreCommerciale] = useState('SANTE CONFORT PLUS');
  const [gestionnaireSante, setGestionnaireSante] = useState('ASCOMA / OLEAPHARMA');
  const [dureeId, setDureeId] = useState(4); // Annuel
  const todayStr = useMemo(() => new Date().toISOString().split('T')[0], []);
  const [dateEmission, setDateEmission] = useState(todayStr);
  const [dateEffet, setDateEffet] = useState(todayStr);
  const [reductionCommerciale, setReductionCommerciale] = useState(0);
  const [ajustement, setAjustement] = useState(0);

  // Date d'expiration calculée
  const calculatedDateExpiration = useMemo(() => {
    if (!dateEffet) return '';
    const d = new Date(dateEffet);
    let months = 12;
    if (Number(dureeId) === 1) months = 1;
    else if (Number(dureeId) === 2) months = 3;
    else if (Number(dureeId) === 3) months = 6;
    else if (Number(dureeId) === 4) months = 12;
    d.setMonth(d.getMonth() + months);
    d.setDate(d.getDate() - 1);
    return d.toISOString().split('T')[0];
  }, [dateEffet, dureeId]);

  // -------------------------------------------------------------
  // ÉTAPE 2 : FILIALES, COLLÈGES & COUVERTURE (JX OREOLE)
  // -------------------------------------------------------------
  const [zoneCouverture, setZoneCouverture] = useState('COTE D\'IVOIRE & ZONE CIMA');
  const [formuleCouverture, setFormuleCouverture] = useState('100% FRAIS REELS / TIERS PAYANT');

  const [colleges, setColleges] = useState([
    {
      id: 1,
      code: 'CADRES',
      nom: 'Collège Cadres & Direction',
      taux_couverture: '100%',
      plafond_annuel: 15000000,
      effectif: 15,
      prime_par_tete: 450000,
      zone: 'Monde Entier (hors USA)',
    },
    {
      id: 2,
      code: 'EMPLOYES',
      nom: 'Collège Employés & Ouvriers',
      taux_couverture: '80%',
      plafond_annuel: 8000000,
      effectif: 50,
      prime_par_tete: 220000,
      zone: 'Côte d\'Ivoire & Zone CIMA',
    },
  ]);

  // Saisie nouveau collège
  const [editingCollegeId, setEditingCollegeId] = useState(null);
  const [currCollegeNom, setCurrCollegeNom] = useState('');
  const [currTauxCouverture, setCurrTauxCouverture] = useState('80%');
  const [currPlafondAnnuel, setCurrPlafondAnnuel] = useState('10 000 000');
  const [currEffectif, setCurrEffectif] = useState('');
  const [currPrimeParTete, setCurrPrimeParTete] = useState('250 000');

  // -------------------------------------------------------------
  // ÉTAPE 3 : SOUSCRIPTEUR, ADHÉRENTS & DÉCOMPTE FINAL (KX OREOLE)
  // -------------------------------------------------------------
  const [souscripteurId, setSouscripteurId] = useState(1);
  const [searchSouscripteur, setSearchSouscripteur] = useState('');
  const [isSearchSouscripteurOpen, setIsSearchSouscripteurOpen] = useState(false);
  const [telephoneSouscripteur, setTelephoneSouscripteur] = useState('+225 ');
  const [adresseSouscripteur, setAdresseSouscripteur] = useState('');
  const [montantAccessoireManuel, setMontantAccessoireManuel] = useState('5000');
  const [surprimeAffection, setSurprimeAffection] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // -------------------------------------------------------------
  // CHARGEMENT INITIAL DES RÉFÉRENTIELS
  // -------------------------------------------------------------
  useEffect(() => {
    let isMounted = true;
    const loadRefs = async () => {
      try {
        const [cls, cies] = await Promise.all([
          customerApi.getClients().catch(() => []),
          settingsApi.getCompanies().catch(() => []),
        ]);
        if (!isMounted) return;
        if (cls && cls.length > 0) {
          setClients(cls);
          setSouscripteurId(cls[0].id);
          setSearchSouscripteur(cls[0].nomcomplet || '');
          setTelephoneSouscripteur(cls[0].telephone || cls[0].mobile || '+225 ');
          setAdresseSouscripteur(cls[0].adresse || '');
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
      } catch (err) {
        console.error('Erreur chargement références Santé:', err);
      }
    };
    loadRefs();
    return () => { isMounted = false; };
  }, []);

  // Totaux financiers calculés
  const totalsFinanciers = useMemo(() => {
    const totalEffectif = colleges.reduce((sum, c) => sum + (Number(c.effectif) || 0), 0);
    const primeNetteBase = colleges.reduce((sum, c) => sum + ((Number(c.effectif) || 0) * (Number(c.prime_par_tete) || 0)), 0);

    const redRate = Math.min(Math.max(Number(reductionCommerciale) || 0, 0), 35) / 100;
    const montantReduction = Math.round(primeNetteBase * redRate);
    const primeNetteApresReduction = primeNetteBase - montantReduction + (Number(surprimeAffection) || 0);

    // En Côte d'Ivoire / CIMA, les contrats d'assurance maladie sont généralement exonérés de taxe ou au taux réduit
    const taxes = Math.round(primeNetteApresReduction * 0.05); // Taxe spécifique santé 5%
    const accessoires = cleanNum(montantAccessoireManuel) || 5000;
    const primeTtc = primeNetteApresReduction + taxes + accessoires;

    return {
      totalEffectif,
      primeNetteBase,
      montantReduction,
      primeNetteApresReduction,
      taxes,
      accessoires,
      primeTtc,
    };
  }, [colleges, reductionCommerciale, surprimeAffection, montantAccessoireManuel]);

  // Actions Collèges
  const handleSaveCollege = () => {
    const eff = cleanNum(currEffectif);
    const ppt = cleanNum(currPrimeParTete);
    const plafond = cleanNum(currPlafondAnnuel);

    if (!currCollegeNom.trim()) {
      toastError('Veuillez renseigner le libellé du collège.');
      return;
    }
    if (eff <= 0) {
      toastError('L\'effectif doit être supérieur à 0.');
      return;
    }

    if (editingCollegeId) {
      setColleges((prev) =>
        prev.map((c) =>
          c.id === editingCollegeId
            ? {
                ...c,
                nom: currCollegeNom,
                taux_couverture: currTauxCouverture,
                plafond_annuel: plafond,
                effectif: eff,
                prime_par_tete: ppt,
              }
            : c
        )
      );
      success('Collège mis à jour !');
      setEditingCollegeId(null);
    } else {
      const newColl = {
        id: Date.now(),
        code: `COL_${colleges.length + 1}`,
        nom: currCollegeNom,
        taux_couverture: currTauxCouverture,
        plafond_annuel: plafond,
        effectif: eff,
        prime_par_tete: ppt,
        zone: zoneCouverture,
      };
      setColleges((prev) => [...prev, newColl]);
      success('Nouveau collège ajouté avec succès !');
    }

    setCurrCollegeNom('');
    setCurrEffectif('');
    setCurrPrimeParTete('250 000');
  };

  const handleEditCollege = (c) => {
    setEditingCollegeId(c.id);
    setCurrCollegeNom(c.nom);
    setCurrTauxCouverture(c.taux_couverture || '80%');
    setCurrPlafondAnnuel(c.plafond_annuel ? String(c.plafond_annuel) : '10 000 000');
    setCurrEffectif(String(c.effectif));
    setCurrPrimeParTete(String(c.prime_par_tete));
  };

  const handleRemoveCollege = (id) => {
    if (colleges.length <= 1) {
      toastError('Le contrat santé doit comporter au moins un collège d\'adhérents.');
      return;
    }
    setColleges((prev) => prev.filter((c) => c.id !== id));
    success('Collège retiré.');
  };

  // Enregistrement final du devis Santé
  const handleFinalSubmit = async () => {
    if (colleges.length === 0) {
      toastError('Veuillez ajouter au moins un collège de bénéficiaires.');
      setStep(2);
      return;
    }

    const selectedClient = clients.find((c) => String(c.id) === String(souscripteurId)) || clients[0];
    setIsSubmitting(true);

    try {
      const quotePayload = {
        client_nom: selectedClient?.nomcomplet || 'Souscripteur Santé Uranus',
        client_id: selectedClient?.id,
        telephone_assure: telephoneSouscripteur,
        adresse_geographique: adresseSouscripteur || selectedClient?.adresse || 'Abidjan',
        produit: `Assurance Santé (${typeContrat} - ${totalsFinanciers.totalEffectif} Bénéficiaires)`,
        branche: 'Santé',
        compagnie: compagnieNom,
        id_compagnie: Number(compagnieId),
        numero_police_compagnie: numeroPoliceCompagnie,
        categorie: typeContrat === 'GROUPE' ? 'SANTE ENTREPRISE GROUPE' : 'SANTE INDIVIDUELLE FAMILLE',
        offre_commerciale: offreCommerciale,
        gestionnaire_sante: gestionnaireSante,
        date_emission: dateEmission,
        date_effet: dateEffet,
        date_expiration: calculatedDateExpiration,
        taux_reduction: Number(reductionCommerciale) || 0,
        prime_nette: totalsFinanciers.primeNetteApresReduction,
        taxe: totalsFinanciers.taxes,
        accessoire: totalsFinanciers.accessoires,
        prime_ttc: totalsFinanciers.primeTtc,
        details: {
          typeContrat,
          zoneCouverture,
          formuleCouverture,
          totalEffectif: totalsFinanciers.totalEffectif,
          colleges,
        },
      };

      // 1. Sauvegarde locale dataStore
      const saved = dataStore.saveQuote(quotePayload);

      // 2. Appel API Django POST /api/enregistrementdevissante
      try {
        await quoteApi.createSanteQuote({
          IdCompagnie: Number(compagnieId),
          IdClient: Number(selectedClient?.id || 1),
          NumeroPoliceCompagnie: numeroPoliceCompagnie || '',
          TypeContrat: typeContrat,
          Offre: offreCommerciale,
          DateEffet: dateEffet,
          DateExpiration: calculatedDateExpiration,
          DateEmission: dateEmission,
          TauxReduction: Number(reductionCommerciale) || 0,
          PrimeNette: totalsFinanciers.primeNetteApresReduction,
          Taxe: totalsFinanciers.taxes,
          Accessoire: totalsFinanciers.accessoires,
          PrimeTTC: totalsFinanciers.primeTtc,
          TotalEffectif: totalsFinanciers.totalEffectif,
          Colleges: colleges,
        });
      } catch (errApi) {
        console.warn('API Sante fallback local:', errApi);
      }

      success(`Devis Assurance Santé N° ${saved.numerodevis} créé avec succès !`);
      setCreatedQuote(saved);
    } catch (err) {
      toastError('Erreur lors de la création du devis Santé.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConvertToContract = (q) => {
    const newContract = dataStore.convertQuoteToContract(q);
    success(`Devis converti en Police Santé N° ${newContract.numeropolice} !`);
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
            <HeartPulse size={28} color="#ec4899" />
            Production de Contrat Santé & Assurance Maladie
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Gestion des collèges de bénéficiaires, tiers payant pharmacie, hospitalisation & gestionnaires délégués.
          </p>
        </div>

        {/* STEPPER OREOLE 3 ONGLETS */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {[
            { stepNum: 1, label: '1. CONTRAT & FORMULE' },
            { stepNum: 2, label: '2. COLLÈGES & COUVERTURE' },
            { stepNum: 3, label: '3. SOUSCRIPTEUR & DÉCOMPTE' },
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
                border: step === item.stepNum ? '2px solid #ec4899' : '1px solid var(--border-subtle)',
                background: step === item.stepNum ? 'rgba(236, 72, 153, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                color: step === item.stepNum ? '#f472b6' : 'var(--text-muted)',
                transition: 'all 0.15s ease',
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* =========================================================================
          ÉTAPE 1 : CONTRAT SANTÉ (kX OREOLE)
          ========================================================================= */}
      {step === 1 && (
        <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
          <h3 style={{ color: '#ec4899', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1.5rem', fontSize: '1.05rem' }}>
            Paramètres du Contrat Santé
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
            {/* Type de contrat santé */}
            <div className="form-group">
              <label className="form-label">Type de Contrat Santé (* requis)</label>
              <select
                className="form-control"
                value={typeContrat}
                onChange={(e) => setTypeContrat(e.target.value)}
              >
                <option value="GROUPE">Santé Entreprise / Groupe d'Affiliés</option>
                <option value="FAMILLE">Santé Familiale / Particulier</option>
                <option value="INDIVIDUEL">Individuel Mono-Bénéficiaire</option>
              </select>
            </div>

            {/* Numéro police compagnie */}
            <div className="form-group">
              <label className="form-label">Numéro de police compagnie (Optionnel)</label>
              <input
                type="text"
                className="form-control"
                placeholder="Ex: POL-SANTE-2026-88"
                value={numeroPoliceCompagnie}
                onChange={(e) => setNumeroPoliceCompagnie(e.target.value)}
              />
            </div>

            {/* Compagnie d'Assurance */}
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

            {/* Offre Commerciale */}
            <div className="form-group">
              <label className="form-label">Offre Commerciale Santé</label>
              <select
                className="form-control"
                value={offreCommerciale}
                onChange={(e) => setOffreCommerciale(e.target.value)}
              >
                <option value="SANTE CONFORT PLUS">SANTE CONFORT PLUS (100% Réseau Premium)</option>
                <option value="SANTE ESSENTIEL">SANTE ESSENTIEL (80% Hospitalisation & Consultations)</option>
                <option value="SANTE ELITE MONDE">SANTE ELITE MONDE (Évacuation sanitaire incluse)</option>
              </select>
            </div>

            {/* Gestionnaire Tiers Payant */}
            <div className="form-group">
              <label className="form-label">Gestionnaire Délégué Tiers Payant</label>
              <select
                className="form-control"
                value={gestionnaireSante}
                onChange={(e) => setGestionnaireSante(e.target.value)}
              >
                <option value="ASCOMA / OLEAPHARMA">ASCOMA / OLEAPHARMA</option>
                <option value="GRAS SAVOYE CI">GRAS SAVOYE CI</option>
                <option value="SUNU SANTE">SUNU GESTION SANTE</option>
                <option value="NSIA HEALTH">NSIA ASSISTANCE SANTE</option>
              </select>
            </div>

            {/* Réduction commerciale */}
            <div className="form-group">
              <label className="form-label">Réduction Commerciale (%)</label>
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

            <div className="form-group">
              <label className="form-label">Date d'expiration (* calculée)</label>
              <input
                type="date"
                className="form-control"
                value={calculatedDateExpiration}
                readOnly
                style={{ background: 'rgba(255,255,255,0.05)', color: '#f472b6', fontWeight: 700 }}
              />
            </div>
          </div>

          <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setStep(2)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#ec4899' }}
            >
              Suivant : Collèges & Couverture <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          ÉTAPE 2 : COLLÈGES & COUVERTURE (JX OREOLE)
          ========================================================================= */}
      {step === 2 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
            <h3 style={{ color: '#ec4899', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1.5rem', fontSize: '1.05rem' }}>
              Zone Géographique & Options de Prise en Charge
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
              <div className="form-group">
                <label className="form-label">Zone de Couverture Géographique</label>
                <select
                  className="form-control"
                  value={zoneCouverture}
                  onChange={(e) => setZoneCouverture(e.target.value)}
                >
                  <option value="COTE D'IVOIRE">Côte d'Ivoire (Réseau National)</option>
                  <option value="COTE D'IVOIRE & ZONE CIMA">Côte d'Ivoire & Zone CIMA (UEMOA / CEMAC)</option>
                  <option value="MONDE ENTIER">Monde Entier (Incluant Évacuation Sanitaire)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Formule de Remboursement / Base</label>
                <select
                  className="form-control"
                  value={formuleCouverture}
                  onChange={(e) => setFormuleCouverture(e.target.value)}
                >
                  <option value="100% FRAIS REELS / TIERS PAYANT">100% Frais Réels / Tiers Payant Intégral</option>
                  <option value="80% TICKET MODERATEUR 20%">80% Remboursement (Ticket modérateur 20%)</option>
                  <option value="100% PLAFONNE BAREME CONVENTIONNE">100% Plafonné au Barème Conventionné</option>
                </select>
              </div>
            </div>

            {/* Formulaire Ajout de Collège */}
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '1.5rem', marginBottom: '1.5rem' }}>
              <h4 style={{ color: '#f472b6', fontWeight: 700, fontSize: '0.95rem', marginBottom: '1rem' }}>
                {editingCollegeId ? 'Modifier le Collège' : 'Ajouter un Collège d\'Affiliés'}
              </h4>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Libellé du Collège</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Ex: Cadres Supérieurs & Familles"
                    value={currCollegeNom}
                    onChange={(e) => setCurrCollegeNom(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Taux de Couverture</label>
                  <select
                    className="form-control"
                    value={currTauxCouverture}
                    onChange={(e) => setCurrTauxCouverture(e.target.value)}
                  >
                    <option value="100%">100%</option>
                    <option value="90%">90%</option>
                    <option value="80%">80%</option>
                    <option value="70%">70%</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Effectif Prévu (Têtes)</label>
                  <input
                    type="number"
                    min="1"
                    className="form-control"
                    placeholder="Ex: 25"
                    value={currEffectif}
                    onChange={(e) => setCurrEffectif(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Prime Nette / Tête / An (FCFA)</label>
                  <input
                    type="text"
                    className="form-control"
                    value={currPrimeParTete ? formatFcfa(currPrimeParTete) : ''}
                    onChange={(e) => setCurrPrimeParTete(e.target.value.replace(/[^0-9]/g, ''))}
                  />
                </div>
              </div>

              <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                {editingCollegeId && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setEditingCollegeId(null);
                      setCurrCollegeNom('');
                      setCurrEffectif('');
                    }}
                  >
                    Annuler
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleSaveCollege}
                  style={{ background: '#10b981' }}
                >
                  <Plus size={16} /> {editingCollegeId ? 'Enregistrer Collège' : 'Ajouter Collège'}
                </button>
              </div>
            </div>

            {/* Tableau des collèges */}
            <h4 style={{ color: '#fff', fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem' }}>
              Collèges Actifs ({colleges.length})
            </h4>

            <div style={{ overflowX: 'auto' }}>
              <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: '#94a3b8', fontSize: '0.8rem' }}>
                    <th style={{ padding: '0.75rem' }}>COLLÈGE</th>
                    <th style={{ padding: '0.75rem', textAlign: 'center' }}>TAUX</th>
                    <th style={{ padding: '0.75rem', textAlign: 'center' }}>EFFECTIF</th>
                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>PRIME / TÊTE</th>
                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>SOUS-TOTAL</th>
                    <th style={{ padding: '0.75rem', textAlign: 'center' }}>ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {colleges.map((c) => (
                    <tr key={c.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                      <td style={{ padding: '0.75rem', fontWeight: 700, color: '#f472b6' }}>{c.nom}</td>
                      <td style={{ padding: '0.75rem', textAlign: 'center' }}>{c.taux_couverture}</td>
                      <td style={{ padding: '0.75rem', textAlign: 'center', fontWeight: 700 }}>{c.effectif}</td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                        {formatFcfa(c.prime_par_tete)} FCFA
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'var(--font-mono)', color: '#38bdf8', fontWeight: 700 }}>
                        {formatFcfa(c.effectif * c.prime_par_tete)} FCFA
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => handleEditCollege(c)}
                            style={{ padding: '0.35rem 0.5rem' }}
                          >
                            <Edit3 size={14} />
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => handleRemoveCollege(c.id)}
                            style={{ padding: '0.35rem 0.5rem', color: '#ef4444' }}
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
                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#ec4899' }}
              >
                Suivant : Souscripteur & Décompte <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          ÉTAPE 3 : SOUSCRIPTEUR, ADHÉRENTS & DÉCOMPTE FINAL (KX OREOLE)
          ========================================================================= */}
      {step === 3 && (
        <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
          <h3 style={{ color: '#ec4899', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1.5rem', fontSize: '1.05rem' }}>
            Souscripteur / Entreprise & Décompte Financier
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
            {/* Recherche Client Souscripteur */}
            <div className="form-group" style={{ position: 'relative' }}>
              <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Souscripteur / Entreprise Contractante (* requis)</span>
                <button
                  type="button"
                  onClick={() => setIsQuickAddClientOpen(true)}
                  style={{ background: 'transparent', border: 'none', color: '#f472b6', cursor: 'pointer', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.2rem' }}
                >
                  <UserPlus size={14} /> + Nouveau client
                </button>
              </label>
              <input
                type="text"
                className="form-control"
                placeholder="Rechercher une entreprise ou un client..."
                value={searchSouscripteur}
                onChange={(e) => {
                  setSearchSouscripteur(e.target.value);
                  setIsSearchSouscripteurOpen(true);
                }}
                onFocus={() => setIsSearchSouscripteurOpen(true)}
              />

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
                          setTelephoneSouscripteur(c.telephone || c.mobile || '+225 ');
                          setAdresseSouscripteur(c.adresse || '');
                        }}
                        style={{ padding: '0.65rem 1rem', cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.85rem' }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(236, 72, 153, 0.2)')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                      >
                        <div style={{ fontWeight: 700, color: '#fff' }}>{c.nomcomplet}</div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{c.codeclient} • {c.telephone || c.mobile}</div>
                      </div>
                    ))}
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">Téléphone Contact</label>
              <input
                type="tel"
                className="form-control"
                value={telephoneSouscripteur}
                onChange={(e) => setTelephoneSouscripteur(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Adresse Géographique</label>
              <input
                type="text"
                className="form-control"
                value={adresseSouscripteur}
                onChange={(e) => setAdresseSouscripteur(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Frais d'Adhésion / Accessoires</label>
              <input
                type="text"
                className="form-control"
                value={formatFcfa(montantAccessoireManuel)}
                onChange={(e) => setMontantAccessoireManuel(e.target.value.replace(/[^0-9]/g, ''))}
              />
            </div>
          </div>

          {/* Synthèse financière finale */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Bénéficiaires Totaux</div>
              <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#fff' }}>
                {totalsFinanciers.totalEffectif} Assurés
              </div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Prime Nette Totale</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                {formatFcfa(totalsFinanciers.primeNetteApresReduction)} FCFA
              </div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Taxes Spécifiques (5%)</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#cbd5e1', fontFamily: 'var(--font-mono)' }}>
                {formatFcfa(totalsFinanciers.taxes)} FCFA
              </div>
            </div>

            <div style={{ background: 'rgba(236, 72, 153, 0.1)', padding: '1rem', borderRadius: '8px', border: '2px solid #ec4899' }}>
              <div style={{ fontSize: '0.75rem', color: '#f472b6', textTransform: 'uppercase', fontWeight: 700 }}>Prime TTC Annuelle</div>
              <div style={{ fontSize: '1.35rem', fontWeight: 900, color: '#fff', fontFamily: 'var(--font-mono)' }}>
                {formatFcfa(totalsFinanciers.primeTtc)} FCFA
              </div>
            </div>
          </div>

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
              disabled={isSubmitting}
              onClick={handleFinalSubmit}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#ec4899', padding: '0.75rem 1.75rem', fontWeight: 800 }}
            >
              <Save size={18} />
              {isSubmitting ? 'Enregistrement en cours...' : 'Enregistrer le Devis Santé'}
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
          setTelephoneSouscripteur(newClient.telephone || newClient.mobile || '+225 ');
        }}
      />
    </div>
  );
};

export default NewSanteQuotePage;
