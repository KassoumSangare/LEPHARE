import React, { useEffect, useMemo, useRef, useState } from 'react';
import { redirigerSiOreole } from './oreole/oreoleCommun';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle, Calculator, Check, Download, FileSpreadsheet, FileText, HeartHandshake, Loader2, Plus, Trash2, Upload,
  UserCheck, Users, X,
} from 'lucide-react';
import { afaApi, contractApi, quoteApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { Champ, FichePersonne, RechercheClient, personneDepuisClient } from '../../../components/common/RechercheClient';
import { EtapesDevis, ResumeDevis } from '../../../components/common/ParcoursDevis';
import { AmountInput } from '../../../components/common/AmountInput';
import { Modal } from '../../../components/common/Modal';
import { QuickAddClientModal } from '../clients/QuickAddClientModal';
import { ViewQuoteModal } from './ViewQuoteModal';
import { messageErreurApi } from '../../../utils/financeUtils';

/* =========================================================================
   DEVIS VIE - AFA (production/afa.py)
   Contrat de groupe : une ligne par assuré (nom, naissance, qualité, capital, bénéficiaires, prime). La liste vient
   d'un fichier Excel au modèle d'OREOLE ou se saisit à l'écran. Primes reprises telles quelles (affaire forfaitaire,
   aucun prorata), pas de taxe en Vie. Affaire nouvelle, ou renouvellement d'une police Vie du souscripteur chez la
   même compagnie (même numéro de police à la confirmation).
   ========================================================================= */

const COULEUR = '#7c3aed';
const ETAPES = [
  { num: 1, libelle: 'Contrat', icone: FileText },
  { num: 2, libelle: 'Assurés', icone: Users },
  { num: 3, libelle: 'Vérification', icone: Calculator },
];
const ACTES = ['Affaire nouvelle', 'Renouvellement', 'Incorporation'];
const fcfa = (v) => Math.round(Number(v) || 0).toLocaleString('fr-FR').replace(/ /g, ' ');
const dateFr = (iso) => (iso ? String(iso).slice(0, 10).split('-').reverse().join('/') : '-');
let compteurLignes = 0;
const nouvelleCle = () => { compteurLignes += 1; return `a${Date.now()}-${compteurLignes}`; };
const ligneVide = (base = {}) => ({
  cle: nouvelleCle(), IdClient: null, Nom: '', Prenoms: '', DateNaissance: '', Qualite: 'ASSURE PRINCIPAL', Capital: '',
  PrimeTtc: '', Beneficiaires: '', Acte: '', Proposition: null, ClientConnu: null, Avertissements: [], ...base,
});
const age = (naissance, jour) => {
  if (!naissance || !jour) return null;
  const n = new Date(`${naissance}T00:00:00`);
  const j = new Date(`${jour}T00:00:00`);
  return j.getFullYear() - n.getFullYear() - ((j.getMonth() < n.getMonth() || (j.getMonth() === n.getMonth() && j.getDate() < n.getDate())) ? 1 : 0);
};
const cleIdentite = (l) => `${String(`${l.Nom} ${l.Prenoms}`).trim().toUpperCase().replace(/\s+/g, ' ')}|${l.DateNaissance}`;

// Contrôles d'une ligne, les mêmes que le serveur (production/afa.py, _assures_saisis) : bloquants avant l'enregistrement
const erreursLigne = (l, dateEffet) => {
  const erreurs = [];
  if (!String(l.Nom || '').trim()) erreurs.push('nom absent');
  if (!l.DateNaissance) erreurs.push('date de naissance absente');
  else {
    const a = age(l.DateNaissance, dateEffet || new Date().toISOString().slice(0, 10));
    if (a === null || a < 0 || a > 100) erreurs.push('date de naissance invraisemblable');
  }
  if (!(Number(l.Capital) > 0)) erreurs.push('capital à saisir');
  if (!(Number(l.PrimeTtc) > 0)) erreurs.push('prime à saisir');
  return erreurs;
};

export const NewAfaQuotePage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const idDevisEdite = Number(searchParams.get('edit')) || 0;
  // Devis lié au package Oreole Santé : il s'ouvre dans la branche, qui garde les trois polices ensemble
  useEffect(() => redirigerSiOreole(idDevisEdite, navigate), [idDevisEdite]); // eslint-disable-line react-hooks/exhaustive-deps
  const { success, error: toastError, info } = useToast();

  const [etape, setEtape] = useState(1);
  const [compagnies, setCompagnies] = useState([]);
  const [idCompagnie, setIdCompagnie] = useState('');
  const [souscripteur, setSouscripteur] = useState(null);
  const [polices, setPolices] = useState([]);
  const [mouvement, setMouvement] = useState('AFN');
  const [idContratRenouvele, setIdContratRenouvele] = useState('');
  const [dateEffet, setDateEffet] = useState('');
  const [dateExpiration, setDateExpiration] = useState('');
  const [policeCompagnie, setPoliceCompagnie] = useState('');
  const [accessoire, setAccessoire] = useState(0);
  const [assures, setAssures] = useState([ligneVide()]);
  const [import_, setImport] = useState(null);
  const [analyse, setAnalyse] = useState(false);
  const [enregistrement, setEnregistrement] = useState(false);
  const [chargement, setChargement] = useState(Boolean(idDevisEdite));
  const [devisLu, setDevisLu] = useState(null);
  const [devisEnregistre, setDevisEnregistre] = useState(null);
  const [nouveauClient, setNouveauClient] = useState(false);
  const [capitalTous, setCapitalTous] = useState('');
  const [primeTous, setPrimeTous] = useState('');
  const fichierRef = useRef(null);

  // Compagnies rattachées au cabinet (celle proposée pour la Vie d'abord) et polices Vie du souscripteur
  useEffect(() => {
    let actif = true;
    afaApi.referentiels(souscripteur?.IdClient)
      .then((r) => {
        if (!actif) return;
        setCompagnies(r.Compagnies || []);
        setPolices(r.Polices || []);
        setIdCompagnie((courant) => courant || String(r.IdCompagnieDefaut || r.Compagnies?.[0]?.IdCompagnie || ''));
      })
      .catch((err) => { if (actif) toastError(`Listes non chargées : ${messageErreurApi(err)}`); });
    return () => { actif = false; };
  }, [souscripteur?.IdClient]); // eslint-disable-line react-hooks/exhaustive-deps

  // Devis rouvert (« Modifier » du registre)
  useEffect(() => {
    if (!idDevisEdite) return undefined;
    let actif = true;
    afaApi.lire(idDevisEdite)
      .then((d) => {
        if (!actif) return;
        setDevisLu(d);
        setIdCompagnie(String(d.IdCompagnie || ''));
        setSouscripteur(d.IdClient ? { IdClient: d.IdClient, Nom: d.Client || `Client n° ${d.IdClient}` } : null);
        setMouvement(d.Mouvement === 'REN' ? 'REN' : 'AFN');
        setIdContratRenouvele(d.IdContratRenouvele ? String(d.IdContratRenouvele) : '');
        setDateEffet(d.DateEffet || '');
        setDateExpiration(d.DateExpiration || '');
        setPoliceCompagnie(d.NumeroPoliceCompagnie || '');
        setAccessoire(Number(d.Accessoire) || 0);
        setAssures((d.Assures || []).map((a) => ligneVide({ ...a, Capital: a.Capital ?? '', PrimeTtc: a.PrimeTtc ?? '' })));
      })
      .catch((err) => { if (actif) toastError(`Devis AFA non chargé : ${messageErreurApi(err)}`); })
      .finally(() => { if (actif) setChargement(false); });
    return () => { actif = false; };
  }, [idDevisEdite]); // eslint-disable-line react-hooks/exhaustive-deps

  const policesCompagnie = polices.filter((p) => String(p.IdCompagnie) === String(idCompagnie));
  const policeRenouvelee = polices.find((p) => String(p.IdContrat) === String(idContratRenouvele));
  const enModification = Boolean(idDevisEdite);
  const lectureSeule = Boolean(devisLu?.Confirme);
  const compagnie = compagnies.find((c) => String(c.IdCompagnie) === String(idCompagnie));

  const lignesSaisies = assures.filter((l) => String(l.Nom || '').trim() || l.DateNaissance || Number(l.PrimeTtc) > 0);
  const doublons = useMemo(() => {
    const vus = new Map();
    const resultat = new Set();
    lignesSaisies.forEach((l) => {
      const cle = l.IdClient ? `id${l.IdClient}` : cleIdentite(l);
      if (vus.has(cle)) { resultat.add(l.cle); resultat.add(vus.get(cle)); } else vus.set(cle, l.cle);
    });
    return resultat;
  }, [lignesSaisies]);
  const erreurs = Object.fromEntries(lignesSaisies.map((l) => [l.cle, [
    ...erreursLigne(l, dateEffet), ...(doublons.has(l.cle) ? ['assuré en double'] : []),
  ]]));
  const lignesEnErreur = lignesSaisies.filter((l) => erreurs[l.cle]?.length);
  const totalPrimes = lignesSaisies.reduce((s, l) => s + (Number(l.PrimeTtc) || 0), 0);
  const totalCapitaux = lignesSaisies.reduce((s, l) => s + (Number(l.Capital) || 0), 0);
  const primeTtc = totalPrimes + (Number(accessoire) || 0);

  const changerLigne = (cle, champ, valeur) => setAssures((liste) => liste.map((l) => (l.cle === cle ? {
    ...l,
    [champ]: valeur,
    // Nom ou date changés : la fiche client reprise ne correspond plus forcément
    ...(['Nom', 'Prenoms', 'DateNaissance'].includes(champ) && l.ClientConnu ? { IdClient: null, ClientConnu: null } : {}),
  } : l)));
  const retirerLigne = (cle) => setAssures((liste) => (liste.length > 1 ? liste.filter((l) => l.cle !== cle) : [ligneVide()]));
  const reprendreFiche = (cle) => setAssures((liste) => liste.map((l) => (l.cle === cle && l.Proposition ? {
    ...l, IdClient: l.Proposition.IdClient, ClientConnu: l.Proposition, Proposition: null,
  } : l)));
  const appliquerATous = () => {
    if (!(Number(capitalTous) > 0) && !(Number(primeTous) > 0)) return;
    setAssures((liste) => liste.map((l) => ({
      ...l,
      ...(Number(capitalTous) > 0 ? { Capital: Number(capitalTous) } : {}),
      ...(Number(primeTous) > 0 ? { PrimeTtc: Number(primeTous) } : {}),
    })));
    info('Capital et prime appliqués à tous les assurés de la liste.');
  };

  const choisirSouscripteur = (personne) => {
    setSouscripteur(personne);
    setIdContratRenouvele('');
    setMouvement('AFN');
  };

  // ------------------------------------------------------------- import Excel
  const lireFichier = async (fichier) => {
    if (!fichier) return;
    setAnalyse(true);
    try {
      setImport(await afaApi.analyserImport(fichier));
    } catch (err) {
      toastError(`Fichier non analysé : ${messageErreurApi(err)}`);
    } finally {
      setAnalyse(false);
      if (fichierRef.current) fichierRef.current.value = '';
    }
  };
  const reprendreImport = (remplacer) => {
    if (!import_) return;
    const lignes = import_.Lignes.map((l) => ligneVide({
      IdClient: l.IdClient, Nom: l.Nom, Prenoms: l.Prenoms, DateNaissance: l.DateNaissance || '', Qualite: l.Qualite,
      Capital: l.Capital ?? '', PrimeTtc: l.PrimeTtc ?? '', Beneficiaires: l.Beneficiaires, Acte: l.Acte,
      ClientConnu: l.ClientConnu, Proposition: l.Proposition, Avertissements: [...(l.Erreurs || []), ...(l.Avertissements || [])],
    }));
    setAssures((liste) => (remplacer || !lignesSaisies.length ? lignes : [...liste.filter((l) => lignesSaisies.includes(l)), ...lignes]));
    if (import_.DateEffet && (!dateEffet || remplacer)) setDateEffet(import_.DateEffet);
    if (import_.DateExpiration && (!dateExpiration || remplacer)) setDateExpiration(import_.DateExpiration);
    if (import_.Souscripteur?.IdClient && !souscripteur) {
      setSouscripteur({ IdClient: import_.Souscripteur.IdClient, Nom: import_.Souscripteur.Nom });
    }
    setImport(null);
    setEtape(2);
    success(`${lignes.length} assuré${lignes.length > 1 ? 's' : ''} repris du fichier : vérifiez la liste puis enregistrez.`);
  };
  const telechargerModele = async () => {
    try {
      const blob = await afaApi.modele();
      const lien = document.createElement('a');
      lien.href = URL.createObjectURL(blob);
      lien.download = 'modele_liste_afa.xlsx';
      lien.click();
      setTimeout(() => URL.revokeObjectURL(lien.href), 2000);
    } catch (err) {
      toastError(`Modèle non téléchargé : ${messageErreurApi(err)}`);
    }
  };

  // ------------------------------------------------------------- navigation et enregistrement
  const controleContrat = () => {
    if (!idCompagnie) return 'Choisissez la compagnie.';
    if (!souscripteur?.IdClient) return 'Choisissez le souscripteur dans la liste des clients.';
    if (!dateEffet || !dateExpiration) return "Saisissez les dates d'effet et d'échéance.";
    if (dateExpiration < dateEffet) return "La date d'échéance précède la date d'effet.";
    if (mouvement === 'REN' && !enModification && !idContratRenouvele) return 'Choisissez la police à renouveler.';
    return '';
  };
  const allerA = (cible) => {
    if (cible > 1) {
      const message = controleContrat();
      if (message) { toastError(message); setEtape(1); return; }
    }
    if (cible > 2) {
      if (!lignesSaisies.length) { toastError('Ajoutez au moins un assuré, ou importez la liste Excel.'); setEtape(2); return; }
      if (lignesEnErreur.length) { toastError(`${lignesEnErreur.length} assuré(s) à corriger avant de continuer.`); setEtape(2); return; }
    }
    setEtape(cible);
  };

  const enregistrer = async () => {
    const message = controleContrat();
    if (message) { toastError(message); setEtape(1); return; }
    if (!lignesSaisies.length || lignesEnErreur.length) { allerA(3); return; }
    setEnregistrement(true);
    try {
      const devis = await afaApi.enregistrer({
        IdDevis: idDevisEdite || 0,
        IdCompagnie: Number(idCompagnie),
        IdClient: Number(souscripteur.IdClient),
        IdContratRenouvele: !enModification && mouvement === 'REN' ? Number(idContratRenouvele) : 0,
        DateEffet: dateEffet,
        DateExpiration: dateExpiration,
        NumeroPoliceCompagnie: policeCompagnie,
        Accessoire: Number(accessoire) || 0,
        Assures: lignesSaisies.map((l) => ({
          IdClient: l.IdClient || 0, Nom: l.Nom, Prenoms: l.Prenoms, DateNaissance: l.DateNaissance, Qualite: l.Qualite,
          Capital: Number(l.Capital), PrimeTtc: Number(l.PrimeTtc), Beneficiaires: l.Beneficiaires, Acte: l.Acte,
        })),
      });
      success(`Devis AFA N° ${devis.NumeroDevis} ${enModification ? 'modifié' : 'enregistré'} : ${devis.Assures.length} assurés, ${fcfa(devis.PrimeTtc)} F.`);
      let fiche = null;
      try { fiche = await quoteApi.getQuote(devis.IdDevis); } catch { /* fiche indisponible : retour au registre */ }
      if (fiche) setDevisEnregistre(fiche);
      else navigate('/user/quotes');
    } catch (err) {
      toastError(`Devis AFA non enregistré : ${messageErreurApi(err)}`);
    } finally {
      setEnregistrement(false);
    }
  };

  const confirmerEnContrat = async (devis) => {
    try {
      const res = await contractApi.createContractFromQuote(devis.iddevis || devis.id);
      success(`Devis ${devis.numerodevis} confirmé : le contrat a été créé.`);
      setDevisEnregistre(null);
      const idContrat = Number(res?.data?.[0]?.ObjectId);
      navigate(idContrat > 0 ? `/user/contracts/${idContrat}` : '/user/contracts');
    } catch (err) {
      toastError(`Le devis n'a pas pu être confirmé : ${messageErreurApi(err)}`);
    }
  };

  // ------------------------------------------------------------- affichage
  const carte = { padding: '1.5rem', borderRadius: '14px' };
  const titreCarte = { display: 'flex', alignItems: 'center', gap: '0.55rem', margin: '0 0 1.2rem', fontSize: '1rem', fontWeight: 800, color: 'var(--text-primary)' };
  const grille = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 230px), 1fr))', gap: '1rem 1.25rem', alignItems: 'start' };
  const pied = (...boutons) => <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1.5rem' }}>{boutons}</div>;

  if (chargement) {
    return (
      <div className="glass-panel" style={{ ...carte, maxWidth: 640, margin: '3rem auto', textAlign: 'center' }}>
        <Loader2 size={28} className="spin" style={{ color: COULEUR }} />
        <p style={{ marginTop: '0.75rem', color: 'var(--text-secondary)' }}>Chargement du devis AFA…</p>
      </div>
    );
  }

  return (
    <div className="page-container afa-page" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <header>
        <button type="button" className="btn btn-link" onClick={() => navigate('/user/quotes')}
          style={{ color: '#ef4444', fontWeight: 600, padding: 0, marginBottom: '0.5rem' }}>← Annuler</button>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <HeartHandshake size={26} color={COULEUR} />
          {enModification ? `Modifier le devis AFA ${devisLu?.NumeroDevis || ''}` : 'Nouveau devis Vie - AFA'}
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: 820, lineHeight: 1.6 }}>
          Contrat de groupe : un assuré par ligne, avec son capital, sa prime et ses bénéficiaires. Importez la liste Excel
          de la compagnie ou saisissez-la. Les primes sont reprises telles quelles, sans prorata ; la Vie ne porte pas de taxe.
        </p>
        {!lectureSeule && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', marginTop: '0.75rem' }}>
            <input ref={fichierRef} type="file" accept=".xlsx,.xlsm" hidden onChange={(e) => lireFichier(e.target.files?.[0])} />
            <button type="button" className="btn btn-primary" onClick={() => fichierRef.current?.click()} disabled={analyse}
              title="Liste de la compagnie au modèle AFA : souscripteur, période et assurés sont repris"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', background: COULEUR, borderColor: COULEUR }}>
              {analyse ? <Loader2 size={15} className="spin" /> : <Upload size={15} />} Importer la liste Excel
            </button>
            <button type="button" className="btn btn-secondary" onClick={telechargerModele} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
              <Download size={15} /> Modèle vierge
            </button>
          </div>
        )}
        {lectureSeule && (
          <p role="note" style={{ padding: '0.6rem 0.8rem', borderRadius: 8, background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.4)', color: '#b45309', fontSize: '0.85rem' }}>
            Devis déjà confirmé : il est affiché en lecture seule.
          </p>
        )}
      </header>

      <EtapesDevis etapes={ETAPES} etape={etape} onAller={allerA} couleur={COULEUR} />

      <div style={{ display: 'flex', gap: '1.25rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div style={{ flex: '999 1 620px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {etape === 1 && (
            <section className="glass-panel" style={carte}>
              <h2 style={titreCarte}><FileText size={18} color={COULEUR} /> Contrat</h2>
              <div style={grille}>
                <Champ label="Compagnie" requis aide="SANLAM gère la Vie : elle est proposée d'office.">
                  <select className="form-control" value={idCompagnie} disabled={lectureSeule || (enModification && devisLu?.Mouvement === 'REN')}
                    onChange={(e) => { setIdCompagnie(e.target.value); setIdContratRenouvele(''); setMouvement('AFN'); }}>
                    <option value="">Choisir…</option>
                    {compagnies.map((c) => <option key={c.IdCompagnie} value={c.IdCompagnie}>{c.Libelle}</option>)}
                  </select>
                </Champ>
                <div style={{ gridColumn: '1 / -1' }}>
                  <RechercheClient label="Souscripteur (client)" personne={souscripteur} onChoisir={choisirSouscripteur}
                    onNouveau={() => setNouveauClient(true)} />
                  {souscripteur && <div style={{ marginTop: '0.75rem' }}><FichePersonne personne={souscripteur} /></div>}
                </div>
                <Champ label="Mouvement" requis large>
                  {enModification ? (
                    <div className="form-control" aria-readonly="true">
                      {devisLu?.Mouvement === 'REN' ? `Renouvellement de la police ${devisLu.PoliceRenouvelee}` : devisLu?.LibelleMouvement || 'Affaire nouvelle'}
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <input type="radio" name="mouvement" checked={mouvement === 'AFN'} onChange={() => { setMouvement('AFN'); setIdContratRenouvele(''); }} />
                        Affaire nouvelle (nouvelle police)
                      </label>
                      <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', opacity: policesCompagnie.length ? 1 : 0.55 }}>
                        <input type="radio" name="mouvement" checked={mouvement === 'REN'} disabled={!policesCompagnie.length}
                          onChange={() => { setMouvement('REN'); setIdContratRenouvele(String(policesCompagnie[0]?.IdContrat || '')); }} />
                        Renouvellement d'une police Vie du souscripteur chez {compagnie?.Libelle || 'cette compagnie'}
                      </label>
                      {mouvement === 'REN' && (
                        <select className="form-control" value={idContratRenouvele} onChange={(e) => setIdContratRenouvele(e.target.value)}>
                          {policesCompagnie.map((p) => (
                            <option key={p.IdContrat} value={p.IdContrat}>{`${p.NumeroPolice} - du ${dateFr(p.DateEffet)} au ${dateFr(p.DateExpiration)} - ${fcfa(p.PrimeTtc)} F`}</option>
                          ))}
                        </select>
                      )}
                      {souscripteur && !policesCompagnie.length && polices.length > 0 && (
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          Polices Vie de ce souscripteur chez d'autres compagnies : {polices.map((p) => `${p.NumeroPolice} - ${p.Compagnie}`).join(' ; ')}.
                          Un renouvellement garde la compagnie de la police : chez {compagnie?.Libelle || 'cette compagnie'}, c'est une affaire nouvelle.
                        </span>
                      )}
                    </div>
                  )}
                </Champ>
                <Champ label="Date d'effet" requis>
                  <input type="date" className="form-control" value={dateEffet} disabled={lectureSeule} onChange={(e) => setDateEffet(e.target.value)} />
                </Champ>
                <Champ label="Date d'échéance" requis>
                  <input type="date" className="form-control" value={dateExpiration} min={dateEffet || undefined} disabled={lectureSeule}
                    onChange={(e) => setDateExpiration(e.target.value)} />
                </Champ>
                <Champ label="N° de police compagnie">
                  <input type="text" className="form-control" maxLength={50} value={policeCompagnie} disabled={lectureSeule}
                    onChange={(e) => setPoliceCompagnie(e.target.value)} placeholder="Facultatif" />
                </Champ>
                <Champ label="Accessoires du contrat" aide="Coût de police éventuel, ajouté aux primes des assurés.">
                  <AmountInput value={accessoire} onChange={(v) => setAccessoire(Number(v) || 0)} disabled={lectureSeule} />
                </Champ>
              </div>
              {pied(<span key="vide" />, <button key="suivant" type="button" className="btn btn-primary" onClick={() => allerA(2)} style={{ background: COULEUR, borderColor: COULEUR }}>Suivant : assurés</button>)}
            </section>
          )}

          {etape === 2 && (
            <section className="glass-panel" style={carte}>
              <h2 style={titreCarte}><Users size={18} color={COULEUR} /> Assurés · {lignesSaisies.length}</h2>
              {!lectureSeule && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '1rem' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setAssures((l) => [...l, ligneVide()])} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Plus size={15} /> Ajouter un assuré
                  </button>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginLeft: 'auto', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Pour tous :</span>
                    <input type="number" min="0" className="form-control" style={{ width: 130 }} placeholder="Capital" value={capitalTous} onChange={(e) => setCapitalTous(e.target.value)} aria-label="Capital pour tous les assurés" />
                    <input type="number" min="0" className="form-control" style={{ width: 110 }} placeholder="Prime" value={primeTous} onChange={(e) => setPrimeTous(e.target.value)} aria-label="Prime pour tous les assurés" />
                    <button type="button" className="btn btn-secondary" onClick={appliquerATous} disabled={!(Number(capitalTous) > 0) && !(Number(primeTous) > 0)}>Appliquer</button>
                  </div>
                </div>
              )}
              <div className="table-wrapper">
                <table className="data-table afa-table">
                  <thead>
                    <tr>
                      <th>N°</th><th>Nom</th><th>Prénoms</th><th>Naissance</th><th>Qualité</th><th className="droite">Capital</th>
                      <th className="droite">Prime TTC</th><th>Bénéficiaires</th><th>Acte</th><th>Fiche client</th><th aria-label="Retirer" />
                    </tr>
                  </thead>
                  <tbody>
                    {assures.map((l, index) => {
                      const problemes = erreurs[l.cle] || [];
                      const ageAssure = age(l.DateNaissance, dateEffet);
                      return (
                        <React.Fragment key={l.cle}>
                          <tr className={problemes.length ? 'afa-ligne-erreur' : ''}>
                            <td>{index + 1}</td>
                            <td><input className="form-control" value={l.Nom} disabled={lectureSeule} onChange={(e) => changerLigne(l.cle, 'Nom', e.target.value.toUpperCase())} aria-label={`Nom de l'assuré ${index + 1}`} /></td>
                            <td><input className="form-control" value={l.Prenoms} disabled={lectureSeule} onChange={(e) => changerLigne(l.cle, 'Prenoms', e.target.value.toUpperCase())} aria-label={`Prénoms de l'assuré ${index + 1}`} /></td>
                            <td>
                              <input type="date" className="form-control" value={l.DateNaissance || ''} disabled={lectureSeule} onChange={(e) => changerLigne(l.cle, 'DateNaissance', e.target.value)} aria-label={`Date de naissance de l'assuré ${index + 1}`} />
                              {ageAssure !== null && ageAssure >= 0 && <span className="afa-age">{ageAssure} ans à l'effet</span>}
                            </td>
                            <td><input className="form-control" value={l.Qualite} disabled={lectureSeule} onChange={(e) => changerLigne(l.cle, 'Qualite', e.target.value.toUpperCase())} aria-label={`Qualité de l'assuré ${index + 1}`} /></td>
                            <td><input type="number" min="0" className="form-control droite" value={l.Capital} disabled={lectureSeule} onChange={(e) => changerLigne(l.cle, 'Capital', e.target.value)} aria-label={`Capital de l'assuré ${index + 1}`} /></td>
                            <td><input type="number" min="0" className="form-control droite" value={l.PrimeTtc} disabled={lectureSeule} onChange={(e) => changerLigne(l.cle, 'PrimeTtc', e.target.value)} aria-label={`Prime de l'assuré ${index + 1}`} /></td>
                            <td><input className="form-control" value={l.Beneficiaires} disabled={lectureSeule} onChange={(e) => changerLigne(l.cle, 'Beneficiaires', e.target.value.toUpperCase())} aria-label={`Bénéficiaires de l'assuré ${index + 1}`} placeholder="NOM PRENOMS / NOM 50%" /></td>
                            <td>
                              <select className="form-control" value={l.Acte} disabled={lectureSeule} onChange={(e) => changerLigne(l.cle, 'Acte', e.target.value)} aria-label={`Acte de l'assuré ${index + 1}`}>
                                <option value="">-</option>
                                {ACTES.map((a) => <option key={a} value={a}>{a}</option>)}
                              </select>
                            </td>
                            <td className="afa-fiche">
                              {l.IdClient ? (
                                <span className="afa-statut connu" title={l.ClientConnu?.Nom || ''}><UserCheck size={13} /> N° {l.IdClient}</span>
                              ) : l.Proposition ? (
                                <button type="button" className="afa-statut proposition" disabled={lectureSeule} onClick={() => reprendreFiche(l.cle)}
                                  title={`${l.Proposition.Nom} - ${l.Proposition.Motif}`}>
                                  Reprendre la fiche n° {l.Proposition.IdClient} ?
                                </button>
                              ) : (
                                <span className="afa-statut nouveau">Nouvelle fiche</span>
                              )}
                            </td>
                            <td>
                              {!lectureSeule && (
                                <button type="button" className="admin-bouton-icone" onClick={() => retirerLigne(l.cle)} aria-label={`Retirer l'assuré ${index + 1}`} title="Retirer de la liste">
                                  <Trash2 size={14} />
                                </button>
                              )}
                            </td>
                          </tr>
                          {(problemes.length > 0 || l.Avertissements?.length > 0 || l.Proposition) && (
                            <tr className="afa-ligne-message">
                              <td />
                              <td colSpan={10}>
                                {problemes.length > 0 && <span className="afa-message erreur"><AlertTriangle size={12} /> À corriger : {problemes.join(', ')}.</span>}
                                {l.Proposition && <span className="afa-message">Fiche n° {l.Proposition.IdClient} : {l.Proposition.Nom}{l.Proposition.DateNaissance ? `, né(e) le ${dateFr(l.Proposition.DateNaissance)}` : ''} - {l.Proposition.Motif}. Sans réponse, une nouvelle fiche est créée.</span>}
                                {(l.Avertissements || []).filter((a) => !a.startsWith('Assuré peut-être')).map((a) => <span key={a} className="afa-message">{a}</span>)}
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={5}>{lignesSaisies.length} assuré{lignesSaisies.length > 1 ? 's' : ''}</td>
                      <td className="droite">{fcfa(totalCapitaux)} F</td>
                      <td className="droite">{fcfa(totalPrimes)} F</td>
                      <td colSpan={4} />
                    </tr>
                  </tfoot>
                </table>
              </div>
              {pied(
                <button key="prec" type="button" className="btn btn-secondary" onClick={() => setEtape(1)}>Précédent</button>,
                <button key="suiv" type="button" className="btn btn-primary" onClick={() => allerA(3)} style={{ background: COULEUR, borderColor: COULEUR }}>Suivant : vérification</button>,
              )}
            </section>
          )}

          {etape === 3 && (
            <section className="glass-panel" style={carte}>
              <h2 style={titreCarte}><Calculator size={18} color={COULEUR} /> Vérification</h2>
              <div style={grille}>
                {[
                  ['Compagnie', compagnie?.Libelle],
                  ['Souscripteur', souscripteur?.Nom],
                  ['Mouvement', enModification
                    ? (devisLu?.Mouvement === 'REN' ? `Renouvellement de ${devisLu.PoliceRenouvelee}` : 'Affaire nouvelle')
                    : (mouvement === 'REN' ? `Renouvellement de ${policeRenouvelee?.NumeroPolice || ''}` : 'Affaire nouvelle')],
                  ['Période', `du ${dateFr(dateEffet)} au ${dateFr(dateExpiration)}`],
                  ['Assurés', `${lignesSaisies.length} dont ${lignesSaisies.filter((l) => !l.IdClient).length} nouvelle(s) fiche(s) client`],
                  ['Capitaux assurés', `${fcfa(totalCapitaux)} F`],
                ].map(([libelle, valeur]) => (
                  <div key={libelle}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>{libelle}</div>
                    <div style={{ fontWeight: 700, marginTop: '0.2rem' }}>{valeur || '-'}</div>
                  </div>
                ))}
              </div>
              {lignesSaisies.some((l) => l.Proposition) && (
                <p className="afa-message" style={{ marginTop: '1rem' }}>
                  <AlertTriangle size={13} /> {lignesSaisies.filter((l) => l.Proposition).length} assuré(s) ressemblent à une fiche existante sans
                  y être rattachés : une nouvelle fiche sera créée pour chacun. Revenez à l'étape Assurés pour reprendre ces fiches.
                </p>
              )}
              {pied(
                <button key="prec" type="button" className="btn btn-secondary" onClick={() => setEtape(2)}>Précédent</button>,
                !lectureSeule && (
                  <button key="enr" type="button" className="btn btn-primary" onClick={enregistrer} disabled={enregistrement}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', background: COULEUR, borderColor: COULEUR }} aria-busy={enregistrement}>
                    {enregistrement ? <Loader2 size={15} className="spin" /> : <Check size={15} />}
                    {enModification ? 'Enregistrer les modifications' : 'Enregistrer le devis'}
                  </button>
                ),
              )}
            </section>
          )}
        </div>

        {/* Étape Assurés : toute la largeur pour le tableau (totaux en pied de tableau) */}
        {etape !== 2 && (
        <ResumeDevis titre="Votre devis AFA" icone={HeartHandshake} couleur={COULEUR}
          lignes={[
            ['Compagnie', compagnie?.Libelle],
            ['Souscripteur', souscripteur?.Nom],
            ['Assurés', lignesSaisies.length],
            ['Primes des assurés', `${fcfa(totalPrimes)} F`],
            ['Accessoires', `${fcfa(accessoire)} F`],
            ['Taxe', '0 F'],
          ]}
          montant={`${fcfa(primeTtc)} F`}
          detail={lignesEnErreur.length ? `${lignesEnErreur.length} assuré(s) à corriger` : undefined}
        />
        )}
      </div>

      <Modal isOpen={Boolean(import_)} onClose={() => setImport(null)} title="Liste AFA importée"
        subtitle={import_ ? `${import_.Titre || import_.Feuille} - rien n'est enregistré avant « Enregistrer le devis »` : ''} maxWidth="900px">
        {import_ && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.75rem' }}>
              {[
                ['Assurés', import_.Totaux.Assures],
                ['Fiches retrouvées', import_.Totaux.Connus],
                ['Fiches à vérifier', import_.Totaux.AVerifier],
                ['Primes', `${fcfa(import_.Totaux.PrimeTtc)} F`],
                ['Capitaux', `${fcfa(import_.Totaux.Capital)} F`],
                ['Période', import_.DateEffet ? `${dateFr(import_.DateEffet)} au ${dateFr(import_.DateExpiration)}` : '-'],
              ].map(([libelle, valeur]) => (
                <div key={libelle} style={{ padding: '0.65rem 0.8rem', border: '1px solid var(--border-subtle)', borderRadius: 10 }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{libelle}</div>
                  <div style={{ fontWeight: 800 }}>{valeur}</div>
                </div>
              ))}
            </div>
            <div style={{ fontSize: '0.84rem' }}>
              Souscripteur du fichier : <strong>{import_.Souscripteur?.Texte || '-'}</strong>
              {import_.Souscripteur?.IdClient ? ` - client n° ${import_.Souscripteur.IdClient} retrouvé` : import_.Souscripteur ? ' - aucun client à ce nom : choisissez-le ou créez-le' : ''}
              {import_.Polices?.length > 0 && <div style={{ color: 'var(--text-muted)', marginTop: '0.25rem' }}>Polices Vie existantes : {import_.Polices.map((p) => `${p.NumeroPolice} - ${p.Compagnie}`).join(' ; ')}.</div>}
            </div>
            {[...import_.Erreurs.map((m) => ['erreur', m]), ...import_.Avertissements.map((m) => ['', m])].map(([ton, m]) => (
              <p key={m} className={`afa-message ${ton}`} style={{ margin: 0 }}><AlertTriangle size={13} /> {m}</p>
            ))}
            {import_.Lignes.some((l) => l.Erreurs.length || l.Avertissements.length) && (
              <div className="table-wrapper" style={{ maxHeight: 260 }}>
                <table className="data-table">
                  <thead><tr><th>Ligne</th><th>Assuré</th><th>Contrôles</th></tr></thead>
                  <tbody>
                    {import_.Lignes.filter((l) => l.Erreurs.length || l.Avertissements.length).map((l) => (
                      <tr key={l.Ligne}>
                        <td>{l.Ligne}</td>
                        <td>{l.NomComplet}</td>
                        <td>
                          {l.Erreurs.map((m) => <div key={m} className="afa-message erreur">{m}</div>)}
                          {l.Avertissements.map((m) => <div key={m} className="afa-message">{m}</div>)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setImport(null)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}><X size={15} /> Fermer</button>
              {lignesSaisies.length > 0 && (
                <button type="button" className="btn btn-secondary" onClick={() => reprendreImport(false)}>Ajouter à la liste actuelle</button>
              )}
              <button type="button" className="btn btn-primary" onClick={() => reprendreImport(true)}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', background: COULEUR, borderColor: COULEUR }}>
                <FileSpreadsheet size={15} /> {lignesSaisies.length ? 'Remplacer la liste' : 'Reprendre la liste'}
              </button>
            </div>
          </div>
        )}
      </Modal>

      {devisEnregistre && (
        <ViewQuoteModal
          isOpen={Boolean(devisEnregistre)}
          quote={devisEnregistre}
          onClose={() => { setDevisEnregistre(null); navigate('/user/quotes'); }}
          onConvertToContract={confirmerEnContrat}
        />
      )}

      <QuickAddClientModal
        isOpen={nouveauClient}
        onClose={() => setNouveauClient(false)}
        valeursInitiales={import_?.Souscripteur && !import_.Souscripteur.IdClient ? { nom: import_.Souscripteur.Texte, typeclient: 'Entreprise' } : undefined}
        onClientCreated={(client) => {
          const personne = personneDepuisClient(client);
          if (personne?.IdClient) choisirSouscripteur(personne);
          setNouveauClient(false);
        }}
      />
    </div>
  );
};

export default NewAfaQuotePage;
