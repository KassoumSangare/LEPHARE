import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { dataStore } from '../../../api/dataStore';
import { quoteApi, customerApi, settingsApi, contractApi, iaApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import {
  UserPlus,
  ArrowLeft,
  ArrowRight,
  Check,
  Plus,
  Trash2,
  Edit3,
  AlertTriangle,
  Calculator,
} from 'lucide-react';
import { ViewQuoteModal } from './ViewQuoteModal';
import { QuickAddClientModal } from '../clients/QuickAddClientModal';
import { sortUniqueBy, trierParLibelle } from '../../../utils/sortUtils';
import { AmountInput } from '../../../components/common/AmountInput';

// Durées du contrat (mêmes identifiants que la base : stddevis.idduree)
const DUREES = [
  { id: 1, duree: '1 Mois' },
  { id: 2, duree: '3 Mois' },
  { id: 3, duree: '6 Mois' },
  { id: 4, duree: '12 Mois (Annuel)' },
  { id: 5, duree: 'Divers / Période Spécifique' },
];
// Catégorie IA MINENE : exige le n° de police Santé connexe
const ID_TARIF_MINENE = 103;

const fcfa = (v) => Math.round(Number(v) || 0).toLocaleString('fr-FR');
const aujourdhui = () => new Date().toISOString().split('T')[0];
const jour = (v) => (v ? String(v).slice(0, 10) : '');

// Message lisible d'une erreur renvoyée par l'API ({error}, {erreur}, {message} ou erreurs par champ)
const messageErreurApi = (err) => {
  const data = err?.response?.data;
  if (!data) return err?.message || 'serveur injoignable';
  if (typeof data === 'string') return data.slice(0, 200);
  const direct = data.message || data.error || data.erreur || data.detail;
  if (direct) return typeof direct === 'string' ? direct : JSON.stringify(direct);
  return Object.entries(data)
    .map(([champ, v]) => `${champ} : ${Array.isArray(v) ? v.join(' ') : typeof v === 'object' ? JSON.stringify(v) : v}`)
    .join(' ; ');
};

// Date d'expiration : date d'effet + durée - 1 jour (même règle que la base)
const expirationPour = (dateEffet, dureeId, personnalisee) => {
  if (!dateEffet) return '';
  if (Number(dureeId) === 5) return personnalisee || '';
  const mois = { 1: 1, 2: 3, 3: 6, 4: 12 }[Number(dureeId)] || 12;
  const d = new Date(dateEffet);
  d.setMonth(d.getMonth() + mois);
  d.setDate(d.getDate() - 1);
  return d.toISOString().split('T')[0];
};

const assureVide = () => ({
  cle: `n${Date.now()}${Math.random()}`,
  IdDevisDetail: 0,
  IdAssure: 0,
  Nom: '',
  Prenoms: '',
  DateNaissance: '',
  IdProfession: 0,
  AdresseGeographique: '',
  CapitalDeces: 0,
  CapitalIpp: 0,
  FraisTraitement: 0,
  AyantsDroit: [],
  ayantsOrigine: '[]',
  prime: null,
});

// Empreintes : une ligne n'est renvoyée au calcul que si elle a changé (primes imposées conservées)
const empreinteLigne = (a) => JSON.stringify([
  Number(a.IdAssure) || 0,
  (a.Nom || '').trim().toUpperCase(),
  (a.Prenoms || '').trim().toUpperCase(),
  jour(a.DateNaissance),
  Number(a.IdProfession) || 0,
  (a.AdresseGeographique || '').trim(),
  Number(a.CapitalDeces) || 0,
  Number(a.CapitalIpp) || 0,
  Number(a.FraisTraitement) || 0,
]);
const empreinteAyants = (liste) => JSON.stringify((liste || []).map((d) => [
  Number(d.IdQualiteAyantDroit) || 0,
  (d.Nom || '').trim().toUpperCase(),
  (d.Prenoms || '').trim().toUpperCase(),
  Number(d.Part) || 0,
]));
const ayantsDepuisApi = (liste) => (liste || []).map((d) => ({
  IdQualiteAyantDroit: Number(d.qualite_ayant_droit) || 0,
  Nom: d.nom_ayant_droit || '',
  Prenoms: (d.prenoms_ayant_droit || '').trim(),
  Part: Number(d.part) || 0,
}));

export const NewIaQuotePage = () => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  // « Modifier » depuis le registre des devis : /user/quotes/ia?edit=<iddevis>
  const [searchParams] = useSearchParams();
  const editIddevisParam = searchParams.get('edit');
  const [isLoadingEdit, setIsLoadingEdit] = useState(Boolean(editIddevisParam));
  const [idDevisEdite, setIdDevisEdite] = useState(null);
  const [numeroDevisEdite, setNumeroDevisEdite] = useState('');
  const [primeImposee, setPrimeImposee] = useState(false);
  const [enteteOrigine, setEnteteOrigine] = useState(null);
  const [totauxEnregistres, setTotauxEnregistres] = useState(null);

  const [step, setStep] = useState(1);
  const [createdQuote, setCreatedQuote] = useState(null);
  const [isQuickAddClientOpen, setIsQuickAddClientOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [calculEnCours, setCalculEnCours] = useState(false);

  // -------------------------------------------------------------
  // RÉFÉRENTIELS
  // -------------------------------------------------------------
  const [clients, setClients] = useState([]);
  const [companies, setCompanies] = useState(() => dataStore.getActiveCompanies('IA'));
  const [tarifs, setTarifs] = useState([]);
  const [offres, setOffres] = useState([]);
  const [professions, setProfessions] = useState([]);
  const [qualites, setQualites] = useState([]);

  // -------------------------------------------------------------
  // ÉTAPE 1 : CONTRAT
  // -------------------------------------------------------------
  const [compagnieId, setCompagnieId] = useState(1);
  const [idTarif, setIdTarif] = useState(77);
  const [idOffre, setIdOffre] = useState(0);
  const [flotte, setFlotte] = useState(false);
  const [dureeId, setDureeId] = useState(4);
  const [dateEmission, setDateEmission] = useState(aujourdhui);
  const [dateEffet, setDateEffet] = useState(aujourdhui);
  const [expirationPersonnalisee, setExpirationPersonnalisee] = useState('');
  const [reduction, setReduction] = useState(0);
  const [numeroPoliceCompagnie, setNumeroPoliceCompagnie] = useState('');
  const [numeroPoliceConnexe, setNumeroPoliceConnexe] = useState('');
  const dateExpiration = useMemo(
    () => expirationPour(dateEffet, dureeId, expirationPersonnalisee),
    [dateEffet, dureeId, expirationPersonnalisee]
  );

  // -------------------------------------------------------------
  // ÉTAPE 2 : SOUSCRIPTEUR, ASSURÉ(S) ET AYANTS DROIT
  // -------------------------------------------------------------
  const [souscripteurId, setSouscripteurId] = useState(0);
  const [rechercheSouscripteur, setRechercheSouscripteur] = useState('');
  const [listeSouscripteurOuverte, setListeSouscripteurOuverte] = useState(false);

  const [assures, setAssures] = useState([]);
  const [assureEnCours, setAssureEnCours] = useState(assureVide);
  const [cleEnEdition, setCleEnEdition] = useState(null);
  const [modeAssure, setModeAssure] = useState('nouveau'); // 'nouveau' (saisi par son nom) | 'existant' (fiche client)
  const [rechercheAssure, setRechercheAssure] = useState('');
  const [listeAssureOuverte, setListeAssureOuverte] = useState(false);
  const [ayantEnCours, setAyantEnCours] = useState({ IdQualiteAyantDroit: 1, Nom: '', Prenoms: '', Part: '' });

  const professionsTriees = useMemo(() => trierParLibelle(professions, (p) => p.libelle_profession), [professions]);
  const qualitesTriees = useMemo(() => trierParLibelle(qualites, (q) => q.libelle_qualite_ayant_droit), [qualites]);
  const codeActivite = (idProfession) => professions.find((p) => Number(p.id) === Number(idProfession))?.code_classe_assure || '01';
  const libelleProfession = (idProfession) => professions.find((p) => Number(p.id) === Number(idProfession))?.libelle_profession || 'AUTRE';
  const libelleQualite = (id) => qualites.find((q) => Number(q.id_qualite) === Number(id))?.libelle_qualite_ayant_droit || '';

  // En-tête : si elle change, toutes les lignes sont recalculées
  const enteteActuelle = JSON.stringify([
    Number(compagnieId), Number(idTarif), Number(idOffre), Number(dureeId), dateEmission, dateEffet,
    dateExpiration, Number(reduction) || 0, numeroPoliceCompagnie || '', numeroPoliceConnexe || '', Number(souscripteurId),
  ]);
  const enteteModifiee = Boolean(enteteOrigine) && enteteOrigine !== enteteActuelle;
  const ligneAChanger = (a) => !a.IdDevisDetail || enteteModifiee || empreinteLigne(a) !== a.origine;

  // -------------------------------------------------------------
  // CHARGEMENT DES RÉFÉRENTIELS
  // -------------------------------------------------------------
  useEffect(() => {
    let actif = true;
    (async () => {
      const [cls, cies, trfs, profs, quals] = await Promise.all([
        customerApi.getClients().catch(() => []),
        settingsApi.getCompanies().catch(() => []),
        iaApi.getTarifs().catch(() => []),
        iaApi.getProfessions().catch(() => []),
        iaApi.getQualites().catch(() => []),
      ]);
      if (!actif) return;
      if (cls && cls.length) {
        setClients((prev) => [...prev.filter((p) => !cls.some((c) => String(c.id) === String(p.id))), ...cls]);
      }
      if (cies && cies.length) {
        setCompanies(cies.map((c) => ({ id: c.IdCompagnie || c.id, nom: c.RaisonSociale || c.nom })));
      }
      setTarifs(trfs || []);
      setProfessions(profs || []);
      setQualites(quals || []);
    })();
    return () => { actif = false; };
  }, []);

  // Offres et nature (individuelle / groupe) de la catégorie choisie
  useEffect(() => {
    let actif = true;
    if (!idTarif) return undefined;
    Promise.all([
      iaApi.getOffres(idTarif).catch(() => []),
      iaApi.estTarifGroupe(idTarif).catch(() => false),
    ]).then(([liste, groupe]) => {
      if (!actif) return;
      setOffres(liste || []);
      setFlotte(Boolean(groupe));
      setIdOffre((courant) => ((liste || []).some((o) => Number(o.IdOffre) === Number(courant))
        ? courant
        : Number(liste?.[0]?.IdOffre) || 0));
    });
    return () => { actif = false; };
  }, [idTarif]);

  // -------------------------------------------------------------
  // « MODIFIER » : REPRISE DE TOUT CE QUI A ÉTÉ SAISI À LA CRÉATION
  // -------------------------------------------------------------
  useEffect(() => {
    if (!editIddevisParam) return undefined;
    let actif = true;
    (async () => {
      setIsLoadingEdit(true);
      try {
        const [devis, lignes, details] = await Promise.all([
          quoteApi.getQuote(editIddevisParam),
          iaApi.getAssuresDevis(editIddevisParam),
          iaApi.getDetailsDevis(editIddevisParam).catch(() => []),
        ]);
        if (!actif) return;
        const raw = devis?.raw || {};
        if (raw.confirme) {
          toastError('Ce devis est confirmé (déjà en contrat) : il ne peut plus être modifié.');
          navigate('/user/quotes');
          return;
        }
        const detail = (details || [])[0] || {};
        const entete = {
          compagnieId: Number(raw.compagnie?.IdCompagnie ?? raw.compagnie) || 1,
          idTarif: Number(detail.idtarif?.IdTarif ?? detail.idtarif) || 77,
          idOffre: Number(detail.idoffre?.IdOffre ?? detail.idoffre) || 0,
          dureeId: Number(raw.idduree) || 4,
          dateEmission: jour(raw.dateemission) || aujourdhui(),
          dateEffet: jour(raw.dateeffet) || aujourdhui(),
          dateExpiration: jour(raw.dateexpiration),
          reduction: Number(detail.taux_reduction) || 0,
          numeroPoliceCompagnie: raw.numero_police_compagnie || '',
          numeroPoliceConnexe: raw.numero_police_connexe || raw.numeropoliceconnexe || '',
          souscripteurId: Number(raw.client?.IdClient ?? raw.client) || 0,
        };
        setIdDevisEdite(Number(editIddevisParam));
        setNumeroDevisEdite(raw.numerodevis || '');
        setPrimeImposee(Boolean(raw.prime_imposee));
        setTotauxEnregistres({
          primeNette: Number(raw.primenette) || 0,
          taxe: Number(raw.taxe) || 0,
          accessoire: Number(raw.accessoire) || 0,
          primeTtc: Number(raw.primettc) || 0,
        });
        setCompagnieId(entete.compagnieId);
        setIdTarif(entete.idTarif);
        setIdOffre(entete.idOffre);
        setDureeId(entete.dureeId);
        setDateEmission(entete.dateEmission);
        setDateEffet(entete.dateEffet);
        setExpirationPersonnalisee(entete.dateExpiration);
        setReduction(entete.reduction);
        setNumeroPoliceCompagnie(entete.numeroPoliceCompagnie);
        setNumeroPoliceConnexe(entete.numeroPoliceConnexe);
        setSouscripteurId(entete.souscripteurId);
        const expirationChargee = expirationPour(entete.dateEffet, entete.dureeId, entete.dateExpiration);
        setEnteteOrigine(JSON.stringify([
          entete.compagnieId, entete.idTarif, entete.idOffre, entete.dureeId, entete.dateEmission, entete.dateEffet,
          expirationChargee, entete.reduction, entete.numeroPoliceCompagnie, entete.numeroPoliceConnexe, entete.souscripteurId,
        ]));

        // Souscripteur
        const souscripteur = entete.souscripteurId
          ? await customerApi.getClientDetail(entete.souscripteurId).catch(() => null)
          : null;
        if (!actif) return;
        if (souscripteur) {
          setClients((prev) => (prev.some((p) => String(p.id) === String(souscripteur.id)) ? prev : [souscripteur, ...prev]));
        }
        setRechercheSouscripteur(souscripteur?.nomcomplet || (entete.souscripteurId ? `Client n° ${entete.souscripteurId}` : ''));

        // Assurés (une ligne de devis chacun) avec leurs ayants droit
        const chargees = await Promise.all((lignes || []).map(async (l) => {
          const ayants = ayantsDepuisApi(await iaApi.getAyantsDroit(l.id_assure).catch(() => []));
          const assure = {
            cle: `l${l.id_devis_detail}`,
            IdDevisDetail: Number(l.id_devis_detail),
            IdAssure: Number(l.id_assure),
            Nom: l.nom || '',
            Prenoms: l.prenoms || '',
            DateNaissance: jour(l.date_naissance),
            IdProfession: Number(l.id_profession) || 0,
            AdresseGeographique: l.adresse_geographique || '',
            CapitalDeces: Math.round(Number(l.capital_deces) || 0),
            CapitalIpp: Math.round(Number(l.capital_infirmite) || 0),
            FraisTraitement: Math.round(Number(l.capital_frais_traitement) || 0),
            AyantsDroit: ayants,
            ayantsOrigine: empreinteAyants(ayants),
            prime: {
              primeNette: Math.round(Number(l.prime_nette) || 0),
              taxe: Math.round(Number(l.taxe) || 0),
              accessoire: Math.round(Number(l.accessoire) || 0),
              enregistree: true,
            },
          };
          assure.origine = empreinteLigne(assure);
          return assure;
        }));
        if (!actif) return;
        setAssures(chargees);
      } catch (err) {
        if (actif) toastError(`Impossible de charger le devis à modifier : ${messageErreurApi(err)}`);
      } finally {
        if (actif) setIsLoadingEdit(false);
      }
    })();
    return () => { actif = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editIddevisParam]);

  // -------------------------------------------------------------
  // PRIMES CALCULÉES PAR LE SERVEUR (même moteur que l'enregistrement)
  // -------------------------------------------------------------
  const calculerPrime = (a) => iaApi.calculerPrimes({
    idCompagnie: compagnieId,
    idOffre,
    capitalDeces: a.CapitalDeces,
    capitalIpp: a.CapitalIpp,
    fraisTraitement: a.FraisTraitement,
    tauxReduction: reduction,
    dateEffet,
    dateExpiration,
    dateNaissance: a.DateNaissance,
    codeActivite: codeActivite(a.IdProfession),
  });

  // Récapitulatif : lignes à recalculer mises à jour (les lignes inchangées gardent leurs primes enregistrées)
  const rafraichirPrimes = async () => {
    const aCalculer = assures.filter((a) => ligneAChanger(a) || !a.prime);
    if (!aCalculer.length || !idOffre) return;
    setCalculEnCours(true);
    try {
      const resultats = await Promise.all(aCalculer.map((a) => calculerPrime(a).then((p) => [a.cle, p]).catch(() => [a.cle, null])));
      const parCle = Object.fromEntries(resultats);
      setAssures((prev) => prev.map((a) => (a.cle in parCle ? { ...a, prime: parCle[a.cle] } : a)));
      if (resultats.some(([, p]) => !p)) toastError('Certaines primes n\'ont pas pu être calculées : vérifiez les dates et les capitaux.');
    } finally {
      setCalculEnCours(false);
    }
  };

  useEffect(() => {
    if (step === 3) rafraichirPrimes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  const totaux = useMemo(() => {
    const primeNette = assures.reduce((s, a) => s + (a.prime?.primeNette || 0), 0);
    const taxeLignes = assures.reduce((s, a) => s + (a.prime?.taxe || 0), 0);
    // Individuel : accessoire (et sa taxe) de la ligne calculée ; groupe : fixés par la base à l'enregistrement
    const calcule = !flotte && assures[0]?.prime && !assures[0].prime.enregistree ? assures[0].prime : null;
    if (!calcule) return { primeNette, taxe: taxeLignes, accessoire: null, primeTtc: null };
    const taxe = taxeLignes + (calcule.taxeAccessoire || 0);
    return { primeNette, taxe, accessoire: calcule.accessoire, primeTtc: primeNette + taxe + calcule.accessoire };
  }, [assures, flotte]);
  const rienAModifier = Boolean(idDevisEdite) && !enteteModifiee
    && assures.every((a) => a.IdDevisDetail && empreinteLigne(a) === a.origine);

  // -------------------------------------------------------------
  // ÉDITION D'UN ASSURÉ
  // -------------------------------------------------------------
  const reinitialiserEditeur = () => {
    setAssureEnCours(assureVide());
    setCleEnEdition(null);
    setModeAssure('nouveau');
    setRechercheAssure('');
    setAyantEnCours({ IdQualiteAyantDroit: 1, Nom: '', Prenoms: '', Part: '' });
  };

  const choisirClientAssure = async (c) => {
    setListeAssureOuverte(false);
    setRechercheAssure(c.nomcomplet || `${c.nom || ''} ${c.prenom || ''}`.trim());
    const brut = c.raw || c;
    // Ses ayants droit déjà enregistrés sont repris (ils lui sont rattachés, pas au devis)
    const ayants = ayantsDepuisApi(await iaApi.getAyantsDroit(c.id).catch(() => []));
    setAssureEnCours((p) => ({
      ...p,
      IdAssure: Number(c.id),
      Nom: c.nom || c.Nom || c.nomcomplet || '',
      Prenoms: c.prenom || c.Prenoms || '',
      DateNaissance: p.DateNaissance || jour(brut.DateNaissance),
      AdresseGeographique: p.AdresseGeographique || brut.Adresse2 || '',
      AyantsDroit: ayants,
      ayantsOrigine: empreinteAyants(ayants),
    }));
  };

  const editerAssure = (a) => {
    setAssureEnCours({ ...a, AyantsDroit: [...a.AyantsDroit] });
    setCleEnEdition(a.cle);
    setModeAssure(a.IdAssure ? 'existant' : 'nouveau');
    setRechercheAssure(`${a.Nom} ${a.Prenoms}`.trim());
    window.scrollTo({ top: 300, behavior: 'smooth' });
  };

  const retirerAssure = (cle) => {
    setAssures((prev) => prev.filter((a) => a.cle !== cle));
    if (cleEnEdition === cle) reinitialiserEditeur();
  };

  const ajouterAyant = () => {
    const part = Number(ayantEnCours.Part) || 0;
    if (!ayantEnCours.Nom.trim()) { toastError('Saisissez le nom de l\'ayant droit.'); return; }
    if (part <= 0) { toastError('La part de l\'ayant droit doit être supérieure à 0 %.'); return; }
    const total = assureEnCours.AyantsDroit.reduce((s, d) => s + (Number(d.Part) || 0), 0) + part;
    if (total > 100) { toastError(`Le total des parts dépasserait 100 % (${total} %).`); return; }
    setAssureEnCours((p) => ({
      ...p,
      AyantsDroit: [...p.AyantsDroit, { ...ayantEnCours, Nom: ayantEnCours.Nom.trim().toUpperCase(), Prenoms: ayantEnCours.Prenoms.trim().toUpperCase(), Part: part }],
    }));
    setAyantEnCours({ IdQualiteAyantDroit: ayantEnCours.IdQualiteAyantDroit, Nom: '', Prenoms: '', Part: '' });
  };

  const validerAssure = async () => {
    const a = assureEnCours;
    if (modeAssure === 'existant' && !a.IdAssure) { toastError('Choisissez le client assuré.'); return; }
    if (modeAssure === 'nouveau' && !a.Nom.trim()) { toastError('Saisissez le nom de l\'assuré.'); return; }
    if (!a.DateNaissance) { toastError('Saisissez la date de naissance de l\'assuré.'); return; }
    if (!(Number(a.CapitalDeces) > 0 || Number(a.CapitalIpp) > 0 || Number(a.FraisTraitement) > 0)) {
      toastError('Saisissez au moins un capital (décès, infirmité ou frais de traitement).');
      return;
    }
    if (!flotte && !cleEnEdition && assures.length >= 1) {
      toastError('Cette catégorie est individuelle : un seul assuré. Choisissez une catégorie « groupe » pour en ajouter.');
      return;
    }
    const assure = {
      ...a,
      IdAssure: modeAssure === 'existant' ? a.IdAssure : 0,
      Nom: a.Nom.trim().toUpperCase(),
      Prenoms: a.Prenoms.trim().toUpperCase(),
    };
    if (modeAssure === 'nouveau' && a.IdAssure) assure.ayantsOrigine = '[]';
    // Ligne enregistrée et inchangée : le serveur n'y touchera pas, sa prime enregistrée reste affichée
    if (assure.IdDevisDetail && !ligneAChanger(assure) && a.prime?.enregistree) {
      setAssures((prev) => prev.map((x) => (x.cle === cleEnEdition ? assure : x)));
      success('Assuré modifié.');
      reinitialiserEditeur();
      return;
    }
    let prime = null;
    if (idOffre) {
      try {
        prime = await calculerPrime(assure);
      } catch (err) {
        toastError(`Calcul de la prime impossible : ${messageErreurApi(err)}`);
        return;
      }
    }
    assure.prime = prime;
    setAssures((prev) => (cleEnEdition ? prev.map((x) => (x.cle === cleEnEdition ? assure : x)) : [...prev, assure]));
    success(cleEnEdition ? 'Assuré modifié.' : 'Assuré ajouté au devis.');
    reinitialiserEditeur();
  };

  // -------------------------------------------------------------
  // ENREGISTREMENT (création ou modification, une seule transaction côté serveur)
  // -------------------------------------------------------------
  const handleSave = async () => {
    if (!souscripteurId) { toastError('Choisissez le souscripteur.'); setStep(2); return; }
    if (!assures.length) { toastError('Ajoutez au moins un assuré.'); setStep(2); return; }
    if (!idOffre) { toastError('Aucune offre pour cette catégorie : choisissez une autre catégorie.'); setStep(1); return; }
    if (!dateExpiration) { toastError('Saisissez la date d\'expiration.'); setStep(1); return; }
    if (!flotte && assures.length > 1) {
      toastError('Cette catégorie est individuelle : un seul assuré. Choisissez une catégorie « groupe ».');
      setStep(1);
      return;
    }
    if (Number(idTarif) === ID_TARIF_MINENE && !numeroPoliceConnexe.trim()) {
      toastError('Catégorie MINENE : saisissez le n° de police Santé connexe.');
      setStep(1);
      return;
    }

    const payload = {
      IdDevis: idDevisEdite || 0,
      IdCompagnie: Number(compagnieId),
      IdTarif: Number(idTarif),
      IdOffre: Number(idOffre),
      Flotte: flotte,
      IdClient: Number(souscripteurId),
      DateEffet: dateEffet,
      DateExpiration: dateExpiration,
      DateEmission: dateEmission,
      IdDuree: Number(dureeId),
      TauxReduction: Number(reduction) || 0,
      NumeroPoliceCompagnie: numeroPoliceCompagnie || '',
      NumeroPoliceConnexe: numeroPoliceConnexe || '',
      Assures: assures.map((a) => ({
        IdDevisDetail: a.IdDevisDetail || 0,
        IdAssure: a.IdAssure || 0,
        Nom: a.Nom,
        Prenoms: a.Prenoms,
        DateNaissance: a.DateNaissance,
        IdProfession: Number(a.IdProfession) || 0,
        AdresseGeographique: a.AdresseGeographique || '',
        CapitalDeces: Number(a.CapitalDeces) || 0,
        CapitalIpp: Number(a.CapitalIpp) || 0,
        FraisTraitement: Number(a.FraisTraitement) || 0,
        Recalculer: ligneAChanger(a),
        AyantsDroitModifies: empreinteAyants(a.AyantsDroit) !== (a.ayantsOrigine || '[]'),
        AyantsDroit: a.AyantsDroit.map((d) => ({
          IdQualiteAyantDroit: Number(d.IdQualiteAyantDroit) || 0,
          Nom: d.Nom,
          Prenoms: d.Prenoms,
          Part: Number(d.Part) || 0,
        })),
      })),
    };

    setIsSubmitting(true);
    try {
      let res;
      try {
        res = await iaApi.enregistrerDevis(payload);
      } catch (errApi) {
        toastError(`Devis IA non enregistré : ${messageErreurApi(errApi)}`);
        return;
      }
      const devisId = res?.devis_id;
      if (!devisId) {
        toastError('Devis IA non enregistré : le serveur n\'a pas renvoyé de numéro de devis.');
        return;
      }
      const souscripteur = clients.find((c) => String(c.id) === String(souscripteurId));
      const compagnie = companies.find((c) => String(c.id) === String(compagnieId));
      const saved = dataStore.saveQuote({
        id: devisId,
        iddevis: devisId,
        numerodevis: res.numero_devis,
        client_nom: souscripteur?.nomcomplet || rechercheSouscripteur,
        client_id: Number(souscripteurId),
        produit: `Individuelle Accidents (${assures.length} assuré${assures.length > 1 ? 's' : ''})`,
        branche: 'IA',
        compagnie: compagnie?.nom || '',
        prime_nette: res.totaux?.prime_nette,
        taxes: res.totaux?.taxe,
        accessoires: res.totaux?.accessoire,
        prime_totale: res.totaux?.prime_ttc,
        date_emission: dateEmission,
        date_effet: dateEffet,
        date_expiration: dateExpiration,
      });
      let devisEnregistre = null;
      try {
        devisEnregistre = await quoteApi.getQuote(devisId);
      } catch {
        // l'aperçu utilisera la copie locale ci-dessus
      }
      success(
        idDevisEdite
          ? `Devis Individuelle Accidents N° ${res.numero_devis} modifié.`
          : `Devis Individuelle Accidents N° ${res.numero_devis} enregistré.`
      );
      setCreatedQuote(devisEnregistre || saved);
    } catch (err) {
      toastError(`Erreur lors de l'enregistrement du devis IA : ${messageErreurApi(err)}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConvertToContract = async (quoteToConvert) => {
    try {
      await contractApi.createContractFromQuote(quoteToConvert.id);
    } catch (e) {
      console.warn('Fallback contract creation');
    }
    const newContract = dataStore.convertQuoteToContract(quoteToConvert);
    success(`Devis ${quoteToConvert.numerodevis} transformé en police d'assurance avec succès !`);
    setCreatedQuote(null);
    navigate(`/user/contracts/${newContract.id || newContract.numeropolice}`);
  };

  // -------------------------------------------------------------
  // AFFICHAGE
  // -------------------------------------------------------------
  const clientsFiltres = (texte) => {
    const t = (texte || '').toLowerCase();
    return clients.filter((c) => (c.nomcomplet || '').toLowerCase().includes(t)).slice(0, 40);
  };
  const totalParts = assureEnCours.AyantsDroit.reduce((s, d) => s + (Number(d.Part) || 0), 0);
  const listeDeroulante = {
    position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50, background: '#1e293b',
    border: '1px solid var(--border-subtle)', borderRadius: '6px', maxHeight: '220px', overflowY: 'auto',
    marginTop: '4px', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.5)',
  };
  const elementListe = { padding: '0.6rem 1rem', cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.85rem' };
  const titreSection = { color: '#8b5cf6', fontWeight: 800, textTransform: 'uppercase', fontSize: '1.05rem', margin: '0 0 1.25rem' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '1240px', margin: '0 auto', paddingBottom: '3rem' }}>
      {/* EN-TÊTE ET ÉTAPES */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <button className="btn btn-secondary" onClick={() => navigate('/user/quotes')} style={{ padding: '0.35rem 0.75rem', marginBottom: '0.5rem' }}>
            <ArrowLeft size={16} /> Retour aux devis
          </button>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <UserPlus size={26} color="#8b5cf6" />
            {editIddevisParam
              ? `Modifier le Devis Individuelle Accident${numeroDevisEdite ? ` [${numeroDevisEdite}]` : ''}`
              : 'Nouveau Devis Individuelle Accident (IA)'}
          </h1>
          {isLoadingEdit ? (
            <p style={{ color: '#a78bfa', fontSize: '0.875rem', fontWeight: 600 }}>Chargement du devis à modifier…</p>
          ) : (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
              Garanties Décès accidentel, Infirmité permanente et Frais de traitement — {flotte ? 'contrat groupe (plusieurs assurés)' : 'contrat individuel (un assuré)'}.
            </p>
          )}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {[
            { n: 1, label: '1. CONTRAT' },
            { n: 2, label: '2. SOUSCRIPTEUR & ASSURÉS' },
            { n: 3, label: '3. RÉCAPITULATIF' },
          ].map((e) => (
            <button
              key={e.n}
              type="button"
              onClick={() => setStep(e.n)}
              style={{
                padding: '0.5rem 0.95rem', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer',
                border: step === e.n ? '2px solid #8b5cf6' : '1px solid var(--border-subtle)',
                background: step === e.n ? 'rgba(139, 92, 246, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                color: step === e.n ? '#c4b5fd' : 'var(--text-muted)',
              }}
            >
              {e.label}
            </button>
          ))}
        </div>
      </div>

      {primeImposee && (
        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'flex-start', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid #f59e0b', background: 'rgba(245, 158, 11, 0.08)', color: '#fcd34d', fontSize: '0.85rem' }}>
          <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: 2 }} />
          <span>
            Ce devis comporte des <strong>primes imposées</strong>. Les assurés que vous ne modifiez pas gardent leurs primes ;
            un assuré modifié ou ajouté, ou un changement du contrat (dates, catégorie, réduction…), est recalculé au tarif,
            ainsi que les totaux du devis.
          </span>
        </div>
      )}

      {/* ÉTAPE 1 : CONTRAT */}
      {step === 1 && (
        <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
          <h3 style={titreSection}>Informations générales du contrat</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.25rem' }}>
            <div className="form-group">
              <label className="form-label">Compagnie d'assurance (* requis)</label>
              <select className="form-control" value={compagnieId} onChange={(e) => setCompagnieId(Number(e.target.value))}>
                {sortUniqueBy(companies, (c) => c.nom).map((c) => (
                  <option key={c.id} value={c.id}>{c.nom}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Catégorie (* requis)</label>
              <select className="form-control" value={idTarif} onChange={(e) => setIdTarif(Number(e.target.value))}>
                {trierParLibelle(tarifs, (t) => t.LibelleTarif).map((t) => (
                  <option key={t.IdTarif} value={t.IdTarif}>{t.LibelleTarif}</option>
                ))}
              </select>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{flotte ? 'Groupe : plusieurs assurés' : 'Individuel : un seul assuré'}</span>
            </div>
            <div className="form-group">
              <label className="form-label">Offre (* requis)</label>
              <select className="form-control" value={idOffre} onChange={(e) => setIdOffre(Number(e.target.value))}>
                {offres.length === 0 && <option value={0}>Aucune offre pour cette catégorie</option>}
                {trierParLibelle(offres, (o) => o.LibelleOffre).map((o) => (
                  <option key={o.IdOffre} value={o.IdOffre}>{o.LibelleOffre}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Durée du contrat</label>
              <select className="form-control" value={dureeId} onChange={(e) => setDureeId(Number(e.target.value))}>
                {DUREES.map((d) => (<option key={d.id} value={d.id}>{d.duree}</option>))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Date d'émission</label>
              <input type="date" className="form-control" value={dateEmission} onChange={(e) => setDateEmission(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Date d'effet (* requis)</label>
              <input type="date" className="form-control" value={dateEffet} onChange={(e) => setDateEffet(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Date d'expiration {Number(dureeId) === 5 ? '(* requis)' : '(calculée)'}</label>
              {Number(dureeId) === 5 ? (
                <input type="date" className="form-control" value={expirationPersonnalisee} onChange={(e) => setExpirationPersonnalisee(e.target.value)} />
              ) : (
                <input type="date" className="form-control" value={dateExpiration} readOnly style={{ background: 'rgba(255,255,255,0.05)', color: '#a78bfa', fontWeight: 700 }} />
              )}
            </div>
            <div className="form-group">
              <label className="form-label">Réduction commerciale (%)</label>
              <input type="number" min="0" max="100" className="form-control" value={reduction} onChange={(e) => setReduction(Math.max(0, Math.min(100, Number(e.target.value) || 0)))} />
            </div>
            <div className="form-group">
              <label className="form-label">N° de police compagnie (optionnel)</label>
              <input type="text" className="form-control" value={numeroPoliceCompagnie} onChange={(e) => setNumeroPoliceCompagnie(e.target.value)} />
            </div>
            {Number(idTarif) === ID_TARIF_MINENE && (
              <div className="form-group">
                <label className="form-label">N° de police Santé connexe (* requis)</label>
                <input type="text" className="form-control" value={numeroPoliceConnexe} onChange={(e) => setNumeroPoliceConnexe(e.target.value)} placeholder="Ex: SANTE-MINENE-2024-001" />
              </div>
            )}
          </div>
          <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-primary" onClick={() => setStep(2)} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#7c3aed' }}>
              Suivant : Souscripteur & assurés <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* ÉTAPE 2 : SOUSCRIPTEUR, ASSURÉS ET AYANTS DROIT */}
      {step === 2 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
            <h3 style={titreSection}>Souscripteur</h3>
            <div className="form-group" style={{ position: 'relative', maxWidth: '560px' }}>
              <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Nom du souscripteur (* requis)</span>
                <button type="button" onClick={() => setIsQuickAddClientOpen(true)} style={{ background: 'transparent', border: 'none', color: '#a78bfa', cursor: 'pointer', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                  <Plus size={14} /> Nouveau client
                </button>
              </label>
              <input
                type="text"
                className="form-control"
                placeholder="Rechercher un client..."
                value={rechercheSouscripteur}
                onChange={(e) => { setRechercheSouscripteur(e.target.value); setListeSouscripteurOuverte(true); }}
                onFocus={() => setListeSouscripteurOuverte(true)}
              />
              {listeSouscripteurOuverte && (
                <div style={listeDeroulante}>
                  {clientsFiltres(rechercheSouscripteur).map((c) => (
                    <div
                      key={c.id}
                      style={elementListe}
                      onClick={() => { setSouscripteurId(Number(c.id)); setRechercheSouscripteur(c.nomcomplet); setListeSouscripteurOuverte(false); }}
                    >
                      <div style={{ fontWeight: 700, color: '#fff' }}>{c.nomcomplet}</div>
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{c.codeclient} • {c.telephone}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1.25rem' }}>
              <h3 style={{ ...titreSection, margin: 0 }}>{cleEnEdition ? 'Modifier l\'assuré' : 'Ajouter un assuré'}</h3>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {[{ v: 'nouveau', l: 'Nouvel assuré (saisi par son nom)' }, { v: 'existant', l: 'Client existant' }].map((m) => (
                  <button
                    key={m.v}
                    type="button"
                    className={modeAssure === m.v ? 'btn btn-primary' : 'btn btn-secondary'}
                    style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', background: modeAssure === m.v ? '#7c3aed' : undefined }}
                    onClick={() => {
                      setModeAssure(m.v);
                      setAssureEnCours((p) => ({ ...p, IdAssure: 0, AyantsDroit: m.v === 'nouveau' ? [] : p.AyantsDroit, ayantsOrigine: '[]' }));
                      setRechercheAssure('');
                    }}
                  >
                    {m.l}
                  </button>
                ))}
                {souscripteurId > 0 && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                    onClick={() => {
                      const c = clients.find((x) => String(x.id) === String(souscripteurId));
                      if (c) { setModeAssure('existant'); choisirClientAssure(c); }
                    }}
                  >
                    Assuré = souscripteur
                  </button>
                )}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
              {modeAssure === 'existant' ? (
                <div className="form-group" style={{ position: 'relative' }}>
                  <label className="form-label">Client assuré (* requis)</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Rechercher un assuré..."
                    value={rechercheAssure}
                    onChange={(e) => { setRechercheAssure(e.target.value); setListeAssureOuverte(true); }}
                    onFocus={() => setListeAssureOuverte(true)}
                  />
                  {listeAssureOuverte && (
                    <div style={listeDeroulante}>
                      {clientsFiltres(rechercheAssure).map((c) => (
                        <div key={c.id} style={elementListe} onClick={() => choisirClientAssure(c)}>
                          <div style={{ fontWeight: 700, color: '#fff' }}>{c.nomcomplet}</div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{c.codeclient} • {c.telephone}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <>
                  <div className="form-group">
                    <label className="form-label">Nom (* requis)</label>
                    <input type="text" className="form-control" value={assureEnCours.Nom} onChange={(e) => setAssureEnCours((p) => ({ ...p, Nom: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Prénoms</label>
                    <input type="text" className="form-control" value={assureEnCours.Prenoms} onChange={(e) => setAssureEnCours((p) => ({ ...p, Prenoms: e.target.value }))} />
                  </div>
                </>
              )}
              <div className="form-group">
                <label className="form-label">Date de naissance (* requis)</label>
                <input type="date" className="form-control" value={assureEnCours.DateNaissance} onChange={(e) => setAssureEnCours((p) => ({ ...p, DateNaissance: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Profession</label>
                <select className="form-control" value={assureEnCours.IdProfession} onChange={(e) => setAssureEnCours((p) => ({ ...p, IdProfession: Number(e.target.value) }))}>
                  <option value={0}>AUTRE</option>
                  {professionsTriees.map((p) => (
                    <option key={p.id} value={p.id}>{p.libelle_profession} (classe {p.code_classe_assure})</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Adresse géographique</label>
                <input type="text" className="form-control" value={assureEnCours.AdresseGeographique} onChange={(e) => setAssureEnCours((p) => ({ ...p, AdresseGeographique: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Capital décès</label>
                <AmountInput value={assureEnCours.CapitalDeces} onChange={(v) => setAssureEnCours((p) => ({ ...p, CapitalDeces: v }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Capital infirmité permanente</label>
                <AmountInput value={assureEnCours.CapitalIpp} onChange={(v) => setAssureEnCours((p) => ({ ...p, CapitalIpp: v }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Capital frais de traitement</label>
                <AmountInput value={assureEnCours.FraisTraitement} onChange={(v) => setAssureEnCours((p) => ({ ...p, FraisTraitement: v }))} />
              </div>
            </div>

            {/* Ayants droit de l'assuré */}
            <div style={{ marginTop: '1.5rem', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', background: 'rgba(255,255,255,0.02)' }}>
              <h4 style={{ fontSize: '0.9rem', color: '#e2e8f0', fontWeight: 700, margin: '0 0 0.75rem' }}>
                Ayants droit (bénéficiaires en cas de décès) — total {totalParts} %
              </h4>
              {assureEnCours.AyantsDroit.length > 0 && (
                <table className="table" style={{ width: '100%', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ color: '#94a3b8', fontSize: '0.75rem' }}>
                      <th style={{ textAlign: 'left', padding: '0.4rem' }}>QUALITÉ</th>
                      <th style={{ textAlign: 'left', padding: '0.4rem' }}>NOM</th>
                      <th style={{ textAlign: 'left', padding: '0.4rem' }}>PRÉNOMS</th>
                      <th style={{ textAlign: 'right', padding: '0.4rem' }}>PART</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {assureEnCours.AyantsDroit.map((d, i) => (
                      <tr key={`${d.Nom}-${i}`}>
                        <td style={{ padding: '0.4rem' }}>{libelleQualite(d.IdQualiteAyantDroit)}</td>
                        <td style={{ padding: '0.4rem' }}>{d.Nom}</td>
                        <td style={{ padding: '0.4rem' }}>{d.Prenoms}</td>
                        <td style={{ padding: '0.4rem', textAlign: 'right' }}>{d.Part} %</td>
                        <td style={{ padding: '0.4rem', textAlign: 'right' }}>
                          <button type="button" className="btn btn-secondary" title="Retirer" style={{ padding: '0.25rem 0.45rem', color: '#ef4444' }}
                            onClick={() => setAssureEnCours((p) => ({ ...p, AyantsDroit: p.AyantsDroit.filter((_, j) => j !== i) }))}
                          >
                            <Trash2 size={13} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(180px, 1.2fr) 1fr 1fr 110px auto', gap: '0.6rem', alignItems: 'end' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Qualité</label>
                  <select className="form-control" value={ayantEnCours.IdQualiteAyantDroit} onChange={(e) => setAyantEnCours((p) => ({ ...p, IdQualiteAyantDroit: Number(e.target.value) }))}>
                    {qualitesTriees.map((q) => (<option key={q.id_qualite} value={q.id_qualite}>{q.libelle_qualite_ayant_droit}</option>))}
                  </select>
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Nom</label>
                  <input type="text" className="form-control" value={ayantEnCours.Nom} onChange={(e) => setAyantEnCours((p) => ({ ...p, Nom: e.target.value }))} />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Prénoms</label>
                  <input type="text" className="form-control" value={ayantEnCours.Prenoms} onChange={(e) => setAyantEnCours((p) => ({ ...p, Prenoms: e.target.value }))} />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Part (%)</label>
                  <input type="number" min="0" max="100" className="form-control" value={ayantEnCours.Part} onChange={(e) => setAyantEnCours((p) => ({ ...p, Part: e.target.value }))} />
                </div>
                <button type="button" className="btn btn-secondary" onClick={ajouterAyant} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }} disabled={totalParts >= 100}>
                  <Plus size={14} /> Ajouter
                </button>
              </div>
            </div>

            <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              {cleEnEdition && (
                <button type="button" className="btn btn-secondary" onClick={reinitialiserEditeur}>Annuler la modification</button>
              )}
              <button type="button" className="btn btn-primary" onClick={validerAssure} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#10b981' }}>
                <Check size={16} /> {cleEnEdition ? 'Enregistrer les modifications de l\'assuré' : 'Ajouter cet assuré au devis'}
              </button>
            </div>
          </div>

          {/* Liste des assurés du devis */}
          <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
            <h3 style={titreSection}>Assurés du devis ({assures.length})</h3>
            <div style={{ overflowX: 'auto' }}>
              <table className="table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: '#94a3b8', fontSize: '0.75rem' }}>
                    <th style={{ padding: '0.6rem', textAlign: 'left' }}>ASSURÉ</th>
                    <th style={{ padding: '0.6rem', textAlign: 'left' }}>NÉ(E) LE</th>
                    <th style={{ padding: '0.6rem', textAlign: 'left' }}>PROFESSION</th>
                    <th style={{ padding: '0.6rem', textAlign: 'right' }}>DÉCÈS</th>
                    <th style={{ padding: '0.6rem', textAlign: 'right' }}>INFIRMITÉ</th>
                    <th style={{ padding: '0.6rem', textAlign: 'right' }}>FRAIS TRAIT.</th>
                    <th style={{ padding: '0.6rem', textAlign: 'center' }}>AYANTS DROIT</th>
                    <th style={{ padding: '0.6rem', textAlign: 'right' }}>PRIME NETTE</th>
                    <th style={{ padding: '0.6rem', textAlign: 'center' }}>ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {assures.length === 0 && (
                    <tr><td colSpan={9} style={{ padding: '1rem', textAlign: 'center', color: '#94a3b8' }}>Aucun assuré pour l'instant.</td></tr>
                  )}
                  {assures.map((a) => (
                    <tr key={a.cle} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', background: cleEnEdition === a.cle ? 'rgba(139, 92, 246, 0.08)' : undefined }}>
                      <td style={{ padding: '0.6rem', fontWeight: 600 }}>
                        {a.Nom} {a.Prenoms}
                        {!a.IdAssure && <span style={{ marginLeft: '0.4rem', fontSize: '0.7rem', color: '#a78bfa' }}>(nouvelle fiche)</span>}
                      </td>
                      <td style={{ padding: '0.6rem' }}>{a.DateNaissance ? a.DateNaissance.split('-').reverse().join('/') : ''}</td>
                      <td style={{ padding: '0.6rem' }}>{libelleProfession(a.IdProfession)}</td>
                      <td style={{ padding: '0.6rem', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{fcfa(a.CapitalDeces)}</td>
                      <td style={{ padding: '0.6rem', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{fcfa(a.CapitalIpp)}</td>
                      <td style={{ padding: '0.6rem', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{fcfa(a.FraisTraitement)}</td>
                      <td style={{ padding: '0.6rem', textAlign: 'center' }}>{a.AyantsDroit.length}</td>
                      <td style={{ padding: '0.6rem', textAlign: 'right', fontFamily: 'var(--font-mono)', color: '#c4b5fd', fontWeight: 700 }}>
                        {a.prime ? `${fcfa(a.prime.primeNette)} FCFA` : '—'}
                      </td>
                      <td style={{ padding: '0.6rem', textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'center' }}>
                          <button type="button" className="btn btn-secondary" title="Modifier" style={{ padding: '0.35rem 0.5rem' }} onClick={() => editerAssure(a)}>
                            <Edit3 size={14} />
                          </button>
                          <button type="button" className="btn btn-secondary" title="Retirer du devis" style={{ padding: '0.35rem 0.5rem', color: '#ef4444' }} onClick={() => retirerAssure(a.cle)}>
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'space-between' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setStep(1)} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ArrowLeft size={16} /> Précédent
              </button>
              <button type="button" className="btn btn-primary" onClick={() => setStep(3)} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#7c3aed' }}>
                Suivant : Récapitulatif <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ÉTAPE 3 : RÉCAPITULATIF */}
      {step === 3 && (
        <div className="glass-panel" style={{ padding: '2rem', borderRadius: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
            <h3 style={{ ...titreSection, margin: 0 }}>Récapitulatif des primes</h3>
            {calculEnCours && <span style={{ color: '#a78bfa', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}><Calculator size={15} /> Calcul des primes…</span>}
          </div>
          <table className="table" style={{ width: '100%', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
            <thead>
              <tr style={{ color: '#94a3b8', fontSize: '0.75rem', borderBottom: '1px solid var(--border-subtle)' }}>
                <th style={{ padding: '0.6rem', textAlign: 'left' }}>ASSURÉ</th>
                <th style={{ padding: '0.6rem', textAlign: 'right' }}>PRIME NETTE</th>
                <th style={{ padding: '0.6rem', textAlign: 'right' }}>TAXES</th>
                <th style={{ padding: '0.6rem', textAlign: 'left' }}>ÉTAT</th>
              </tr>
            </thead>
            <tbody>
              {assures.map((a) => (
                <tr key={a.cle} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <td style={{ padding: '0.6rem', fontWeight: 600 }}>{a.Nom} {a.Prenoms}</td>
                  <td style={{ padding: '0.6rem', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{a.prime ? fcfa(a.prime.primeNette) : '—'}</td>
                  <td style={{ padding: '0.6rem', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{a.prime ? fcfa(a.prime.taxe) : '—'}</td>
                  <td style={{ padding: '0.6rem', color: '#94a3b8' }}>
                    {!idDevisEdite ? 'Nouveau' : !a.IdDevisDetail ? 'Ajouté' : ligneAChanger(a) ? 'Recalculé' : 'Inchangé (prime enregistrée)'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            {(rienAModifier && totauxEnregistres
              ? [
                ['Prime nette', totauxEnregistres.primeNette],
                ['Taxes', totauxEnregistres.taxe],
                ['Accessoires', totauxEnregistres.accessoire],
                ['Prime TTC', totauxEnregistres.primeTtc],
              ]
              : [
                ['Prime nette', totaux.primeNette],
                [flotte ? 'Taxes (hors accessoire)' : 'Taxes', totaux.taxe],
                ['Accessoires', totaux.accessoire],
                ['Prime TTC', totaux.primeTtc],
              ]).map(([libelle, valeur]) => (
                <div key={libelle} style={{ background: libelle === 'Prime TTC' ? 'rgba(139, 92, 246, 0.12)' : 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px', border: libelle === 'Prime TTC' ? '2px solid #8b5cf6' : '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>{libelle}</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#fff' }}>
                    {valeur === null || valeur === undefined ? 'à l\'enregistrement' : `${fcfa(valeur)} FCFA`}
                  </div>
                </div>
              ))}
          </div>
          {flotte && !rienAModifier && (
            <p style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: '#94a3b8' }}>
              Contrat groupe : l'accessoire et la taxe sur accessoire sont fixés par la base à l'enregistrement (barème de la compagnie) ;
              le montant définitif s'affiche ensuite dans l'aperçu du devis.
            </p>
          )}

          <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'space-between' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setStep(2)} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ArrowLeft size={16} /> Précédent
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSave}
              disabled={isSubmitting || isLoadingEdit || calculEnCours}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#7c3aed', padding: '0.75rem 1.5rem', fontWeight: 800 }}
            >
              <Check size={18} />
              {isSubmitting ? 'Enregistrement en cours...' : idDevisEdite ? 'Enregistrer les modifications' : 'Enregistrer le Devis IA'}
            </button>
          </div>
        </div>
      )}

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

      <QuickAddClientModal
        isOpen={isQuickAddClientOpen}
        onClose={() => setIsQuickAddClientOpen(false)}
        onClientCreated={(newClient) => {
          setClients((prev) => [newClient, ...prev]);
          setSouscripteurId(Number(newClient.id || newClient.IdClient));
          setRechercheSouscripteur(newClient.nomcomplet || newClient.Nom);
        }}
      />
    </div>
  );
};

export default NewIaQuotePage;
