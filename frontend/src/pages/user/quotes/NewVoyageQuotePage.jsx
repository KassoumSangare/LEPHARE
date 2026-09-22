import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { dataStore } from '../../../api/dataStore';
import { customerApi, settingsApi, contractApi, voyageApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { ViewQuoteModal } from './ViewQuoteModal';
import { QuickAddClientModal } from '../clients/QuickAddClientModal';
import { sortUniqueBy } from '../../../utils/sortUtils';
import {
  Plane,
  Shield,
  ShieldCheck,
  Globe,
  Plus,
  FileCheck,
  CheckCircle2,
  DollarSign,
  Search,
  ChevronRight,
  ChevronLeft,
  Users
} from 'lucide-react';

const OREOLE_PAYS_FALLBACK = [
  { id_pays: 1, libelle_pays: "Côte d'Ivoire", nationalite: "IVOIRIENNE", id_zone: 1 },
  { id_pays: 2, libelle_pays: "France (Espace Schengen)", nationalite: "FRANÇAISE", id_zone: 2 },
  { id_pays: 8, libelle_pays: "Allemagne (Espace Schengen)", nationalite: "ALLEMANDE", id_zone: 2 },
  { id_pays: 22, libelle_pays: "Belgique (Espace Schengen)", nationalite: "BELGE", id_zone: 2 },
  { id_pays: 39, libelle_pays: "Canada", nationalite: "CANADIENNE", id_zone: 3 },
  { id_pays: 42, libelle_pays: "Chine", nationalite: "CHINOISE", id_zone: 3 },
  { id_pays: 60, libelle_pays: "Émirats Arabes Unis", nationalite: "EMIRIENNE", id_zone: 3 },
  { id_pays: 70, libelle_pays: "États-Unis d'Amérique", nationalite: "AMÉRICAINE", id_zone: 3 },
  { id_pays: 10, libelle_pays: "Angleterre / Royaume-Uni", nationalite: "BRITANNIQUE", id_zone: 3 },
  { id_pays: 191, libelle_pays: "Sénégal", nationalite: "SÉNÉGALAISE", id_zone: 1 },
  { id_pays: 137, libelle_pays: "Maroc", nationalite: "MAROCAINE", id_zone: 1 },
  { id_pays: 222, libelle_pays: "Turquie", nationalite: "TURQUE", id_zone: 3 },
];

const OREOLE_OFFRES_DEFAULT = [
  {
    IdOffre: 1,
    LibelleOffre: "Voyage Schengen Standard (Conforme Visa)",
    garanties: [
      { id: 23, LibelleSousGarantie: "Frais Médicaux & Hospitalisation d'urgence", Capital: 19679000, Franchise: "0 FCFA", PrimeAnnuelle: 35000, PrimeNette: 28000 },
      { id: 28, LibelleSousGarantie: "Rapatriement sanitaire corps & blessé", Capital: 50000000, Franchise: "Sans", PrimeAnnuelle: 12000, PrimeNette: 9500 },
      { id: 29, LibelleSousGarantie: "Assistance Juridique à l'étranger", Capital: 3000000, Franchise: "32 800 FCFA", PrimeAnnuelle: 8000, PrimeNette: 6500 },
      { id: 30, LibelleSousGarantie: "Perte ou vol de bagages enregistrés", Capital: 1000000, Franchise: "25 000 FCFA", PrimeAnnuelle: 5000, PrimeNette: 4000 },
      { id: 31, LibelleSousGarantie: "Responsabilité Civile Vie Privée à l'Étranger", Capital: 10000000, Franchise: "50 000 FCFA", PrimeAnnuelle: 7000, PrimeNette: 5500 },
    ]
  },
  {
    IdOffre: 2,
    LibelleOffre: "Voyage Schengen Confort & Famille",
    garanties: [
      { id: 23, LibelleSousGarantie: "Frais Médicaux d'urgence plafonné à 50 000 €", Capital: 32798000, Franchise: "0 FCFA", PrimeAnnuelle: 48000, PrimeNette: 39000 },
      { id: 28, LibelleSousGarantie: "Rapatriement médicalisé et retour des accompagnants", Capital: 100000000, Franchise: "Sans", PrimeAnnuelle: 18000, PrimeNette: 14500 },
      { id: 29, LibelleSousGarantie: "Assistance Juridique et Caution Pénale", Capital: 6000000, Franchise: "32 800 FCFA", PrimeAnnuelle: 10000, PrimeNette: 8000 },
      { id: 30, LibelleSousGarantie: "Bagages, retards de vol et correspondances manquées", Capital: 2000000, Franchise: "Sans", PrimeAnnuelle: 9000, PrimeNette: 7500 },
      { id: 31, LibelleSousGarantie: "Frais d'hébergement d'un proche accompagnant", Capital: 1500000, Franchise: "Sans", PrimeAnnuelle: 6000, PrimeNette: 5000 },
    ]
  },
  {
    IdOffre: 3,
    LibelleOffre: "Voyage Monde Entier & Business Premium",
    garanties: [
      { id: 23, LibelleSousGarantie: "Frais Médicaux Monde Illimités / 100 000 USD", Capital: 65000000, Franchise: "0 FCFA", PrimeAnnuelle: 75000, PrimeNette: 62000 },
      { id: 28, LibelleSousGarantie: "Évacuation sanitaire d'extrême urgence", Capital: 150000000, Franchise: "Sans", PrimeAnnuelle: 25000, PrimeNette: 20000 },
      { id: 29, LibelleSousGarantie: "Assistance Rapatriement, Annulation ou Interruption", Capital: 15000000, Franchise: "Sans", PrimeAnnuelle: 15000, PrimeNette: 12000 },
      { id: 30, LibelleSousGarantie: "Perte matériel professionnel / Ordinateur", Capital: 3000000, Franchise: "30 000 FCFA", PrimeAnnuelle: 12000, PrimeNette: 10000 },
    ]
  }
];

export const NewVoyageQuotePage = () => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const [step, setStep] = useState(1);
  const [createdQuote, setCreatedQuote] = useState(null);
  const [isQuickAddClientOpen, setIsQuickAddClientOpen] = useState(false);

  // References
  const [clients, setClients] = useState([]);
  const [companies, setCompanies] = useState(() => dataStore.getActiveCompanies('Voyage'));
  const [paysList, setPaysList] = useState(OREOLE_PAYS_FALLBACK);
  const [tarifsVoyage, setTarifsVoyage] = useState([]);

  // Step 1: Contrat parameters
  const [numeroPoliceCompagnie, setNumeroPoliceCompagnie] = useState('POL-VOY-2026-001');
  const [compagnieId, setCompagnieId] = useState(21);
  const [compagnieNom, setCompagnieNom] = useState('AMSA ASSURANCES CI');
  const [categorieTarif, setCategorieTarif] = useState(108);
  const [nationaliteId, setNationaliteId] = useState(1);
  const [paysDestinationId, setPaysDestinationId] = useState(2);
  const [reduction, setReduction] = useState(0);
  const [referenceContrat, setReferenceContrat] = useState('REF-VOY-CI-998');
  const [numeroAttestation, setNumeroAttestation] = useState('ATT-SCH-2026-CI');
  const [dateNaissance, setDateNaissance] = useState('1990-05-15');
  const [isSchengen, setIsSchengen] = useState(true);
  const [dateEmission, setDateEmission] = useState(() => new Date().toISOString().split('T')[0]);

  const todayPlus7 = new Date();
  todayPlus7.setDate(todayPlus7.getDate() + 7);
  const [dateEffet, setDateEffet] = useState(() => todayPlus7.toISOString().split('T')[0]);

  const todayPlus37 = new Date();
  todayPlus37.setDate(todayPlus37.getDate() + 37);
  const [dateExpiration, setDateExpiration] = useState(() => todayPlus37.toISOString().split('T')[0]);

  const [numeroPassport, setNumeroPassport] = useState('24CI88992');
  const [dureeJours, setDureeJours] = useState(30);

  // Step 2: Offres & Garanties
  // Catalogue d'offres et garanties réellement paramétré en base (StdOffre / StdOffreGarantie / StdSousGarantie),
  // interrogé via fn_liste_offre_voyage et fn_garantie_offre_voyage. OREOLE_OFFRES_DEFAULT ne sert plus que de
  // secours hors-ligne si l'API est indisponible.
  const [selectedOffreId, setSelectedOffreId] = useState(1);
  const [offresList, setOffresList] = useState(OREOLE_OFFRES_DEFAULT);
  const [usingCatalogueReel, setUsingCatalogueReel] = useState(false);
  const currentOffre = useMemo(() => {
    return offresList.find(o => o.IdOffre === parseInt(selectedOffreId)) || offresList[0];
  }, [offresList, selectedOffreId]);

  const [offreGaranties, setOffreGaranties] = useState(OREOLE_OFFRES_DEFAULT[0].garanties);
  const [checkedGaranties, setCheckedGaranties] = useState(() => {
    const init = {};
    OREOLE_OFFRES_DEFAULT[0].garanties.forEach(g => { init[g.id] = true; });
    return init;
  });

  // Step 3: Souscripteur & Assuré
  const [clientId, setClientId] = useState(1);
  const [clientSearchTerm, setClientSearchTerm] = useState('');
  const [filteredClients, setFilteredClients] = useState([]);
  const [isClientDropdownOpen, setIsClientDropdownOpen] = useState(false);

  const [assureNom, setAssureNom] = useState('KOUAME Jean-Yves');
  const [telephoneAssure, setTelephoneAssure] = useState('0708091011');
  const [adresseAssure, setAdresseAssure] = useState('Abidjan Cocody Angré 8ème Tranche');
  const [adresseGeo, setAdresseGeo] = useState('Immeuble Les Oliviers, 3ème étage');

  // Load real backend references
  useEffect(() => {
    let isMounted = true;
    const loadRealRefs = async () => {
      try {
        const [cls, cies, paysRes, tarifsRes] = await Promise.all([
          customerApi.getClients().catch(() => []),
          settingsApi.getCompanies().catch(() => []),
          voyageApi.getPaysZone(21).catch(() => []),
          voyageApi.getTarifsVoyage(21).catch(() => []),
        ]);
        if (isMounted) {
          if (cls && cls.length > 0) {
            setClients(cls);
            setClientId(cls[0].id || cls[0].IdClient || 1);
            setClientSearchTerm(cls[0].nomcomplet || cls[0].Nom || '');
            setAssureNom(cls[0].nomcomplet || cls[0].Nom || 'KOUAME Jean-Yves');
            if (cls[0].telephone) setTelephoneAssure(cls[0].telephone);
            if (cls[0].adresse) setAdresseAssure(cls[0].adresse);
          }
          if (cies && cies.length > 0) {
            const mappedCies = cies.map((c) => ({
              id: c.id || c.IdCompagnie,
              nom: c.RaisonSociale || c.nom
            }));
            setCompanies(mappedCies);
            const foundAmsa = mappedCies.find(c => c.id === 21) || mappedCies[0];
            setCompagnieNom(foundAmsa.nom);
            setCompagnieId(foundAmsa.id);
          }
          if (paysRes && paysRes.length > 0) {
            setPaysList(paysRes);
            const defPays = paysRes.find(p => p.id_pays === 2) || paysRes[0];
            setPaysDestinationId(defPays.id_pays);
          }
          if (tarifsRes && tarifsRes.length > 0) {
            setTarifsVoyage(tarifsRes);
            if (tarifsRes[0]?.IdTarif) setCategorieTarif(tarifsRes[0].IdTarif);
          }
        }
      } catch (err) {
        console.warn('Utilisation données locales Voyage:', err);
      }
    };
    loadRealRefs();
    return () => { isMounted = false; };
  }, []);

  const toDmy = (isoDate) => {
    if (!isoDate) return '01-01-2026';
    const parts = isoDate.split('-');
    return parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : isoDate;
  };

  // Offres réellement paramétrées pour cette compagnie / ce tarif / cette zone de destination
  // (fn_liste_offre_voyage). Remplace le catalogue par défaut dès que l'API répond.
  useEffect(() => {
    if (!compagnieId || !categorieTarif) return;
    let isMounted = true;
    const destObj = paysList.find(p => p.id_pays === parseInt(paysDestinationId));
    const idZone = destObj?.id_zone || 1;
    voyageApi.getOffresVoyage(compagnieId, categorieTarif, idZone).then((res) => {
      if (!isMounted || !Array.isArray(res) || res.length === 0) return;
      const mapped = res.map((o) => ({
        IdOffre: Number(o.IdOffre ?? o.id_offre),
        LibelleOffre: o.LibelleOffre ?? o.libelle_offre ?? 'Offre Voyage',
      }));
      setOffresList(mapped);
      setUsingCatalogueReel(true);
      setSelectedOffreId(mapped[0].IdOffre);
    }).catch(() => {});
    return () => { isMounted = false; };
  }, [compagnieId, categorieTarif, paysDestinationId, paysList]);

  // Garanties réellement rattachées à l'offre sélectionnée, avec capitaux et primes calculés par le
  // moteur de tarification (fn_garantie_offre_voyage), selon la zone, la réduction et les dates saisies.
  useEffect(() => {
    if (!currentOffre) return;
    if (!usingCatalogueReel) {
      // Catalogue de secours (hors-ligne) : garanties déjà embarquées dans l'offre.
      setOffreGaranties(currentOffre.garanties || []);
      const init = {};
      (currentOffre.garanties || []).forEach((g) => { init[g.id] = true; });
      setCheckedGaranties(init);
      return;
    }
    let isMounted = true;
    const destObj = paysList.find(p => p.id_pays === parseInt(paysDestinationId));
    const idZone = destObj?.id_zone || 1;
    voyageApi.getGarantiesVoyage({
      IdCompagnie: compagnieId,
      IdTarif: categorieTarif,
      IdOffre: currentOffre.IdOffre,
      IdZoneVoyage: idZone,
      TauxReduction: Number(reduction) || 0,
      DateEffet: toDmy(dateEffet),
      DateExpiration: toDmy(dateExpiration),
      DateNaissance: toDmy(dateNaissance),
    }).then((res) => {
      if (!isMounted || !Array.isArray(res)) return;
      const mapped = res.map((r) => ({
        id: r.IdSousGarantie,
        LibelleSousGarantie: r.LibelleSousGarantie,
        Capital: Number(r.Capital || 0),
        Franchise: r.MontantAccessoire ? `${Number(r.MontantAccessoire).toLocaleString('fr-FR')} FCFA` : 'Selon Conditions Générales',
        PrimeAnnuelle: Number(r.PrimeAnnuelle || 0),
        PrimeNette: Number(r.PrimeNette || 0),
        acquiseParDefaut: !!r.Acquise,
      }));
      setOffreGaranties(mapped);
      const init = {};
      mapped.forEach((g) => { init[g.id] = g.acquiseParDefaut; });
      setCheckedGaranties(init);
    }).catch(() => {});
    return () => { isMounted = false; };
  }, [currentOffre, usingCatalogueReel, compagnieId, categorieTarif, paysDestinationId, paysList, reduction, dateEffet, dateExpiration, dateNaissance]);

  // Update duration
  useEffect(() => {
    if (dateEffet && dateExpiration) {
      const d1 = new Date(dateEffet);
      const d2 = new Date(dateExpiration);
      const diffTime = d2.getTime() - d1.getTime();
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      setDureeJours(diffDays > 0 ? diffDays : 1);
    }
  }, [dateEffet, dateExpiration]);

  // Financial calculations conforming to OREOLE
  const financialTotals = useMemo(() => {
    if (!offreGaranties || offreGaranties.length === 0) {
      return { totalPAnnuelle: 0, totalPNette: 0, primeTtc: 0, accessoires: 2500, taxe: 0 };
    }

    let sumPAnnuelle = 0;
    let sumPNette = 0;

    offreGaranties.forEach(g => {
      if (checkedGaranties[g.id]) {
        sumPAnnuelle += Number(g.PrimeAnnuelle || 0);
        sumPNette += Number(g.PrimeNette || 0);
      }
    });

    const factorDuree = Math.min(Math.max(dureeJours / 365, 0.15), 1.0);
    let primeNetteAjustee = Math.round(sumPNette * factorDuree);

    if (reduction > 0) {
      const discount = (primeNetteAjustee * reduction) / 100;
      primeNetteAjustee = Math.max(Math.round(primeNetteAjustee - discount), 15000);
    }

    const accessoires = 2500;
    const taxe = Math.round(primeNetteAjustee * 0.145);
    const primeTtc = primeNetteAjustee + accessoires + taxe;

    return {
      totalPAnnuelle: Math.round(sumPAnnuelle * factorDuree),
      totalPNette: primeNetteAjustee,
      accessoires,
      taxe,
      primeTtc
    };
  }, [offreGaranties, checkedGaranties, dureeJours, reduction]);

  // Search client handler
  const handleClientSearch = (val) => {
    setClientSearchTerm(val);
    if (!val || val.trim().length === 0) {
      setFilteredClients([]);
      setIsClientDropdownOpen(false);
      return;
    }
    const filtered = clients.filter(c => {
      const n = (c.nomcomplet || c.Nom || '').toLowerCase();
      return n.includes(val.toLowerCase());
    });
    setFilteredClients(filtered);
    setIsClientDropdownOpen(filtered.length > 0);
  };

  const handleSelectClient = (c) => {
    setClientId(c.id || c.IdClient);
    setClientSearchTerm(c.nomcomplet || c.Nom || '');
    if (c.telephone) setTelephoneAssure(c.telephone);
    if (c.adresse) setAdresseAssure(c.adresse);
    setIsClientDropdownOpen(false);
  };

  // Step 1 -> Step 2 validation
  const handleNextToStep2 = () => {
    if (!dateEffet || !dateExpiration) {
      toastError("Veuillez renseigner les dates d'effet et d'expiration.");
      return;
    }
    if (new Date(dateExpiration) <= new Date(dateEffet)) {
      toastError("La date d'expiration doit être postérieure à la date d'effet.");
      return;
    }
    if (!numeroPassport) {
      toastError("Le numéro de passeport est requis.");
      return;
    }
    setStep(2);
  };

  // Step 2 -> Step 3 validation
  const handleNextToStep3 = () => {
    const hasAnyChecked = Object.values(checkedGaranties).some(v => v === true);
    if (!hasAnyChecked) {
      toastError("Veuillez sélectionner au moins une garantie acquise.");
      return;
    }
    setStep(3);
  };

  // Final Quote Submission
  const handleSaveDevisVoyage = async () => {
    if (!clientSearchTerm) {
      toastError("Veuillez renseigner le nom du souscripteur.");
      return;
    }

    const destObj = paysList.find(p => p.id_pays === parseInt(paysDestinationId)) || OREOLE_PAYS_FALLBACK[1];
    const natObj = paysList.find(p => p.id_pays === parseInt(nationaliteId)) || OREOLE_PAYS_FALLBACK[0];

    const formatDateOREOLE = (d) => {
      if (!d) return '01-01-2026';
      const parts = d.split('-');
      if (parts.length === 3) return `${parts[2]}-${parts[1]}-${parts[0]}`;
      return d;
    };

    const newQuoteData = {
      client_nom: clientSearchTerm,
      client_id: clientId,
      produit: `Assurance Voyage - ${currentOffre.LibelleOffre}`,
      branche: 'Voyage',
      compagnie: compagnieNom,
      prime_nette: financialTotals.totalPNette,
      accessoires: financialTotals.accessoires,
      taxes: financialTotals.taxe,
      prime_totale: financialTotals.primeTtc,
      date_emission: dateEmission,
      statut: 'En attente',
      statut_badge: 'amber',
      details: {
        policeCompagnie: numeroPoliceCompagnie,
        referenceContrat,
        numeroAttestation,
        numeroPassport,
        isSchengen,
        paysDestination: destObj.libelle_pays,
        nationalite: natObj.nationalite,
        dateNaissance,
        dateEffet,
        dateExpiration,
        dureeJours,
        offre: currentOffre.LibelleOffre,
        reduction: `${reduction}%`,
        assure: {
          nom: assureNom,
          telephone: telephoneAssure,
          adresse: adresseAssure,
          adresseGeo
        },
        garantiesAcquises: offreGaranties.filter(g => checkedGaranties[g.id])
      }
    };

    const saved = dataStore.saveQuote(newQuoteData);

    try {
      const backendPayload = {
        IdIntermediaire: 1,
        IdCompagnie: Number(compagnieId) || 21,
        IdProduit: 3,
        IdOffre: Number(selectedOffreId) || 1,
        IdAvenant: 1,
        IdClient: Number(clientId) || 1,
        IdAssure: Number(clientId) || 1,
        Flotte: false,
        Coassurance: false,
        DateEffet: formatDateOREOLE(dateEffet),
        DateExpiration: formatDateOREOLE(dateExpiration),
        DateEmission: formatDateOREOLE(dateEmission),
        IdTarif: Number(categorieTarif) || 1,
        TauxReduction: Number(reduction) || 0,
        DateNaissance: formatDateOREOLE(dateNaissance),
        IdPaysDestination: Number(paysDestinationId) || 2,
        IdPaysVoyageur: Number(nationaliteId) || 1,
        ReferenceContrat: referenceContrat || 'REF-VOY-2026',
        NumeroAttestation: numeroAttestation || 'ATT-VOY-2026',
        Schengen: Boolean(isSchengen),
        NumeroPasseport: numeroPassport || 'CI123456',
        NumeroPoliceCompagnie: numeroPoliceCompagnie || 'RAS',
        IdDevis: 0,
        IdDuree: Number(dureeJours) || 30
      };
      const apiRes = await voyageApi.enregistrerDevisVoyage(backendPayload);
      if (apiRes?.data?.[0]?.ObjectId) {
        saved.numerodevis = `DEV-VOY-2026-${String(apiRes.data[0].ObjectId).padStart(4, '0')}`;
      }
    } catch (e) {
      console.warn('Enregistrement Voyage fallback local dataStore:', e);
    }

    success(`Devis Voyage ${saved.numerodevis} généré et synchronisé avec succès !`);
    setCreatedQuote(saved);
  };

  const handleConvertToContract = async (quoteToConvert) => {
    try {
      await contractApi.createContractFromQuote(quoteToConvert.id);
    } catch (e) {
      console.warn('Fallback contract creation');
    }
    const newContract = dataStore.convertQuoteToContract(quoteToConvert);
    success(`Devis ${quoteToConvert.numerodevis} transformé en contrat d'assurance !`);
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
            <Plane size={28} color="#3b82f6" />
            Production de Contrat Assurance Voyage & Schengen
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Architecture fidèle à OREOLE Production : saisie paramétrique, garanties d'assistance internationale et tarification certifiée.
          </p>
        </div>

        {/* STEPPER OREOLE 3 ONGLETS EXACTS */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {[
            { stepNum: 1, label: '1. CONTRAT & DATES' },
            { stepNum: 2, label: '2. OFFRES & DÉCOMPTE' },
            { stepNum: 3, label: '3. SOUSCRIPTEUR & ASSURÉ' },
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
                border: step === item.stepNum ? '2px solid #2563eb' : '1px solid var(--border-subtle)',
                background: step === item.stepNum ? 'rgba(37, 99, 235, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                color: step === item.stepNum ? '#60a5fa' : 'var(--text-muted)',
                transition: 'all 0.15s ease',
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* =========================================================================
          ÉTAPE 1 : CONTRAT & DATES (K$ OREOLE)
          ========================================================================= */}
      {step === 1 && (
        <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
          <h3 style={{ color: '#3b82f6', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1.5rem', fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Globe size={18} /> Informations Générales du Contrat & Dates
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
            {/* Numéro Police Compagnie */}
            <div className="form-group">
              <label className="form-label">Numéro de Police Compagnie</label>
              <input
                type="text"
                className="form-control"
                value={numeroPoliceCompagnie}
                onChange={(e) => setNumeroPoliceCompagnie(e.target.value)}
                placeholder="Ex: POL-VOY-2026-001"
              />
            </div>

            {/* Compagnie d'assurance */}
            <div className="form-group">
              <label className="form-label">Compagnie d'Assurance (* requis)</label>
              <select
                className="form-control"
                value={compagnieId}
                onChange={(e) => {
                  const selId = parseInt(e.target.value);
                  setCompagnieId(selId);
                  const found = companies.find(c => c.id === selId);
                  if (found) setCompagnieNom(found.nom);
                }}
              >
                {sortUniqueBy(companies, (c) => c.nom).map((c) => (
                  <option key={c.id} value={c.id}>{c.nom}</option>
                ))}
              </select>
            </div>

            {/* Formule / Catégorie */}
            <div className="form-group">
              <label className="form-label">Formule / Catégorie Tarifaire</label>
              <select
                className="form-control"
                value={categorieTarif}
                onChange={(e) => setCategorieTarif(parseInt(e.target.value))}
              >
                {tarifsVoyage && tarifsVoyage.length > 0 ? (
                  tarifsVoyage.map((t) => (
                    <option key={t.IdTarif} value={t.IdTarif}>{t.LibelleTarif || t.libelle}</option>
                  ))
                ) : (
                  <>
                    <option value={108}>Voyage Tourisme & Loisirs Standard</option>
                    <option value={109}>Voyage Affaires & Missions Internationales</option>
                    <option value={110}>Voyage Études & Long Séjour</option>
                  </>
                )}
              </select>
            </div>

            {/* Nationalité */}
            <div className="form-group">
              <label className="form-label">Nationalité de l'Assuré</label>
              <select
                className="form-control"
                value={nationaliteId}
                onChange={(e) => setNationaliteId(parseInt(e.target.value))}
              >
                {sortUniqueBy(paysList, (p) => p.nationalite || p.libelle_pays).map((p) => (
                  <option key={p.id_pays} value={p.id_pays}>{p.nationalite || p.libelle_pays}</option>
                ))}
              </select>
            </div>

            {/* Pays de Destination */}
            <div className="form-group">
              <label className="form-label">Pays de Destination (* requis)</label>
              <select
                className="form-control"
                value={paysDestinationId}
                onChange={(e) => {
                  const pid = parseInt(e.target.value);
                  setPaysDestinationId(pid);
                  const selP = paysList.find(p => p.id_pays === pid);
                  if (selP && (selP.id_zone === 2 || (selP.libelle_pays && selP.libelle_pays.toLowerCase().includes('schengen')))) {
                    setIsSchengen(true);
                  }
                }}
              >
                {sortUniqueBy(paysList, (p) => p.libelle_pays).map((p) => (
                  <option key={p.id_pays} value={p.id_pays}>{p.libelle_pays}</option>
                ))}
              </select>
            </div>

            {/* Taux de Réduction */}
            <div className="form-group">
              <label className="form-label">Taux de Réduction (%)</label>
              <input
                type="number"
                min="0"
                max="35"
                className="form-control"
                value={reduction}
                onChange={(e) => setReduction(Math.max(0, Math.min(35, Number(e.target.value))))}
              />
            </div>

            {/* Référence Contrat */}
            <div className="form-group">
              <label className="form-label">Référence Contrat</label>
              <input
                type="text"
                className="form-control"
                value={referenceContrat}
                onChange={(e) => setReferenceContrat(e.target.value)}
              />
            </div>

            {/* Numéro Attestation */}
            <div className="form-group">
              <label className="form-label">Numéro d'Attestation</label>
              <input
                type="text"
                className="form-control"
                value={numeroAttestation}
                onChange={(e) => setNumeroAttestation(e.target.value)}
              />
            </div>

            {/* Date de Naissance */}
            <div className="form-group">
              <label className="form-label">Date de Naissance de l'Assuré</label>
              <input
                type="date"
                className="form-control"
                value={dateNaissance}
                onChange={(e) => setDateNaissance(e.target.value)}
              />
            </div>

            {/* Option Visa Schengen */}
            <div className="form-group" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <label className="form-label">Option Visa Schengen</label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', cursor: 'pointer', marginTop: '0.25rem' }}>
                <input
                  type="checkbox"
                  checked={isSchengen}
                  onChange={(e) => setIsSchengen(e.target.checked)}
                  style={{ width: '18px', height: '18px', accentColor: '#2563eb' }}
                />
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: isSchengen ? '#60a5fa' : 'var(--text-secondary)' }}>
                  {isSchengen ? 'Attestation Schengen Conforme (30k €)' : 'Non Schengen'}
                </span>
              </label>
            </div>

            {/* Date d'Émission */}
            <div className="form-group">
              <label className="form-label">Date d'Émission</label>
              <input
                type="date"
                className="form-control"
                value={dateEmission}
                onChange={(e) => setDateEmission(e.target.value)}
              />
            </div>

            {/* Date d'Effet */}
            <div className="form-group">
              <label className="form-label">Date d'Effet (* requis)</label>
              <input
                type="date"
                className="form-control"
                value={dateEffet}
                onChange={(e) => setDateEffet(e.target.value)}
              />
            </div>

            {/* Date d'Expiration */}
            <div className="form-group">
              <label className="form-label">Date d'Expiration (* requis)</label>
              <input
                type="date"
                className="form-control"
                value={dateExpiration}
                onChange={(e) => setDateExpiration(e.target.value)}
              />
            </div>

            {/* Numéro Passeport */}
            <div className="form-group">
              <label className="form-label">Numéro de Passeport (* requis)</label>
              <input
                type="text"
                className="form-control"
                value={numeroPassport}
                onChange={(e) => setNumeroPassport(e.target.value.toUpperCase())}
                placeholder="Ex: 24CI99881"
              />
            </div>

            {/* Durée Calculée */}
            <div className="form-group" style={{ background: 'rgba(37, 99, 235, 0.08)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid rgba(37, 99, 235, 0.25)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#60a5fa', fontWeight: 700 }}>Durée du Séjour</span>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)' }}>{dureeJours} Jours</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Zone Tarifaire</span>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#38bdf8' }}>Zone {isSchengen ? '2 (Schengen)' : '3 (Monde)'}</div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleNextToStep2}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem 1.25rem' }}
            >
              <span>Passer aux Offres & Garanties</span>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          ÉTAPE 2 : OFFRES & DÉCOMPTE (Z$ OREOLE)
          ========================================================================= */}
      {step === 2 && (
        <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
          <h3 style={{ color: '#3b82f6', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1.5rem', fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldCheck size={18} /> Sélection de l'Offre & Tableau des Garanties Acquises
          </h3>

          {/* Formule selector */}
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-subtle)', padding: '1.25rem', borderRadius: '10px', display: 'flex', gap: '1.5rem', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
            <div style={{ minWidth: '320px', flex: 1 }}>
              <label className="form-label" style={{ fontWeight: 700, color: '#60a5fa' }}>Offre Voyage Disponible</label>
              <select
                className="form-control"
                value={selectedOffreId}
                onChange={(e) => setSelectedOffreId(parseInt(e.target.value))}
                style={{ fontWeight: 700 }}
              >
                {sortUniqueBy(offresList, (o) => o.LibelleOffre).map((o) => (
                  <option key={o.IdOffre} value={o.IdOffre}>{o.LibelleOffre}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 2, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--text-primary)' }}>{currentOffre.LibelleOffre}</strong>
              <p style={{ margin: '0.25rem 0 0 0' }}>Couvre l'intégralité des exigences consulaires pour visas (Frais médicaux, rapatriement d'urgence, assistance juridique).</p>
            </div>
          </div>

          {/* Warranties Table */}
          <div className="table-container" style={{ maxHeight: '420px', overflowY: 'auto', marginBottom: '1.5rem' }}>
            <table className="table">
              <thead>
                <tr>
                  <th style={{ textAlign: 'left' }}>Garantie</th>
                  <th style={{ textAlign: 'center' }}>Acquise</th>
                  <th style={{ textAlign: 'right' }}>Capital Garanti</th>
                  <th style={{ textAlign: 'center' }}>Franchise</th>
                  <th style={{ textAlign: 'right' }}>Prime Annuelle</th>
                  <th style={{ textAlign: 'right' }}>Prime Nette</th>
                </tr>
              </thead>
              <tbody>
                {offreGaranties.map((g) => {
                  const isAcquise = !!checkedGaranties[g.id];
                  return (
                    <tr key={g.id} style={{ opacity: isAcquise ? 1 : 0.5 }}>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{g.LibelleSousGarantie}</td>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={isAcquise}
                          onChange={(e) => {
                            setCheckedGaranties(prev => ({
                              ...prev,
                              [g.id]: e.target.checked
                            }));
                          }}
                          style={{ width: '16px', height: '16px', accentColor: '#2563eb', cursor: 'pointer' }}
                        />
                      </td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{Number(g.Capital).toLocaleString('fr-FR')} FCFA</td>
                      <td style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>{g.Franchise}</td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{Number(g.PrimeAnnuelle).toLocaleString('fr-FR')} FCFA</td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#38bdf8' }}>{Number(g.PrimeNette).toLocaleString('fr-FR')} FCFA</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Financial Summary Tile Bar */}
          <div style={{ background: 'rgba(15, 23, 42, 0.9)', border: '1px solid var(--border-medium)', padding: '1.25rem 1.5rem', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ padding: '0.5rem', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa' }}>
                <DollarSign size={22} />
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Décompte de la Cotisation</span>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Durée de séjour : {dureeJours} jours {reduction > 0 && `(Réduction : -${reduction}%)`}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block' }}>Prime Nette</span>
                <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>{financialTotals.totalPNette.toLocaleString('fr-FR')} FCFA</strong>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block' }}>Accessoires</span>
                <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>{financialTotals.accessoires.toLocaleString('fr-FR')} FCFA</strong>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block' }}>Taxes CIMA</span>
                <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>{financialTotals.taxe.toLocaleString('fr-FR')} FCFA</strong>
              </div>
              <div style={{ paddingLeft: '1.25rem', borderLeft: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <span style={{ fontSize: '0.75rem', color: '#60a5fa', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Prime Totale TTC</span>
                <strong style={{ fontSize: '1.35rem', color: '#38bdf8' }}>{financialTotals.primeTtc.toLocaleString('fr-FR')} FCFA</strong>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1.5rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setStep(1)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <ChevronLeft size={16} />
              <span>Précédent</span>
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleNextToStep3}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem 1.25rem' }}
            >
              <span>Passer au Souscripteur & Assuré</span>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          ÉTAPE 3 : SOUSCRIPTEUR & ASSURÉ (J$ OREOLE)
          ========================================================================= */}
      {step === 3 && (
        <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
          <h3 style={{ color: '#3b82f6', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1.5rem', fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Users size={18} /> Identification du Souscripteur & de l'Assuré Voyageur
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
            {/* Nom Souscripteur with Search Dropdown */}
            <div className="form-group" style={{ position: 'relative' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                <label className="form-label" style={{ margin: 0 }}>Nom du Souscripteur (* requis)</label>
                <button
                  type="button"
                  onClick={() => setIsQuickAddClientOpen(true)}
                  style={{ background: 'none', border: 'none', color: '#60a5fa', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                >
                  <Plus size={12} /> Nouveau Client
                </button>
              </div>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  className="form-control"
                  value={clientSearchTerm}
                  onChange={(e) => handleClientSearch(e.target.value)}
                  placeholder="Rechercher ou saisir un souscripteur..."
                />
                <Search size={16} style={{ position: 'absolute', right: '12px', top: '12px', color: 'var(--text-muted)', pointerEvents: 'none' }} />
              </div>

              {isClientDropdownOpen && (
                <div style={{ position: 'absolute', left: 0, right: 0, top: '100%', zIndex: 50, marginTop: '4px', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-medium)', borderRadius: '8px', boxShadow: 'var(--shadow-lg)', maxHeight: '180px', overflowY: 'auto' }}>
                  {filteredClients.map((c) => (
                    <div
                      key={c.id}
                      onClick={() => handleSelectClient(c)}
                      style={{ padding: '0.5rem 0.85rem', fontSize: '0.8rem', cursor: 'pointer', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between' }}
                    >
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.nomcomplet || c.Nom}</span>
                      <span style={{ color: 'var(--text-muted)' }}>{c.telephone}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Nom de l'Assuré */}
            <div className="form-group">
              <label className="form-label">Nom de l'Assuré (Titulaire du Passeport)</label>
              <input
                type="text"
                className="form-control"
                value={assureNom}
                onChange={(e) => setAssureNom(e.target.value)}
                placeholder="Nom & Prénoms figurant sur le passeport"
              />
            </div>

            {/* Téléphone Assuré */}
            <div className="form-group">
              <label className="form-label">Numéro de Téléphone Assuré</label>
              <div style={{ display: 'flex' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', padding: '0 0.75rem', background: 'var(--bg-surface-hover)', border: '1px solid var(--border-medium)', borderRight: 'none', borderRadius: '8px 0 0 8px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                  +225
                </span>
                <input
                  type="tel"
                  className="form-control"
                  style={{ borderRadius: '0 8px 8px 0' }}
                  value={telephoneAssure}
                  onChange={(e) => setTelephoneAssure(e.target.value)}
                  placeholder="0700000000"
                />
              </div>
            </div>

            {/* Adresse Assuré */}
            <div className="form-group">
              <label className="form-label">Adresse Postale Assuré</label>
              <input
                type="text"
                className="form-control"
                value={adresseAssure}
                onChange={(e) => setAdresseAssure(e.target.value)}
                placeholder="Ex: BP 123 Abidjan"
              />
            </div>

            {/* Adresse Géographique */}
            <div className="form-group" style={{ gridColumn: 'span 2' }}>
              <label className="form-label">Adresse Géographique de Résidence</label>
              <input
                type="text"
                className="form-control"
                value={adresseGeo}
                onChange={(e) => setAdresseGeo(e.target.value)}
                placeholder="Ex: Abidjan Cocody, Résidence les Palmiers"
              />
            </div>
          </div>

          {/* Recap Tile */}
          <div style={{ background: 'rgba(37, 99, 235, 0.08)', border: '1px solid rgba(37, 99, 235, 0.2)', padding: '1rem 1.25rem', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ padding: '0.5rem', borderRadius: '8px', background: 'rgba(37, 99, 235, 0.2)', color: '#60a5fa' }}>
                <FileCheck size={20} />
              </div>
              <div style={{ fontSize: '0.85rem' }}>
                <strong style={{ color: 'var(--text-primary)' }}>{currentOffre.LibelleOffre}</strong>
                <p style={{ margin: '0.2rem 0 0 0', color: 'var(--text-secondary)' }}>
                  Passeport : <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#38bdf8' }}>{numeroPassport}</span> | Durée : {dureeJours} jours
                </p>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Montant TTC à Régler</span>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#38bdf8' }}>{financialTotals.primeTtc.toLocaleString('fr-FR')} FCFA</div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1.5rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setStep(2)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <ChevronLeft size={16} />
              <span>Précédent</span>
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSaveDevisVoyage}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem 1.5rem', fontWeight: 800 }}
            >
              <CheckCircle2 size={16} />
              <span>Enregistrer le Devis Voyage</span>
            </button>
          </div>
        </div>
      )}

      {/* Modals */}
      <QuickAddClientModal
        isOpen={isQuickAddClientOpen}
        onClose={() => setIsQuickAddClientOpen(false)}
        onClientCreated={(newClient) => {
          setClients(prev => [newClient, ...prev]);
          handleSelectClient(newClient);
        }}
      />

      {createdQuote && (
        <ViewQuoteModal
          quote={createdQuote}
          isOpen={!!createdQuote}
          onClose={() => setCreatedQuote(null)}
          onConvertToContract={handleConvertToContract}
        />
      )}
    </div>
  );
};

export default NewVoyageQuotePage;
