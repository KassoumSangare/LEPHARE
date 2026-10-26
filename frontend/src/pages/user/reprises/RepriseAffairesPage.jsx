import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  History, Plus, Upload, Download, Search, Trash2, Loader2, CheckCircle2, AlertTriangle, X, Save, FileSpreadsheet, RotateCcw,
} from 'lucide-react';
import { Modal } from '../../../components/common/Modal';
import { AmountInput } from '../../../components/common/AmountInput';
import { customerApi, repriseApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { useAuth } from '../../../context/AuthContext';
import { messageErreurApi } from '../../../utils/financeUtils';
import { confirmer } from '../../../utils/dialogue';
import { downloadBlob } from '../../../utils/exportUtils';
import { QuickAddClientModal } from '../clients/QuickAddClientModal';

// Reprise des affaires antérieures (demande du 2026-10-26) : contrats et quittances des années passées absents de
// LE PHARE, saisis un à un ou importés d'un fichier Excel, tels qu'ils ont été émis (production/reprise.py). Ils
// comptent dans les états de leur année, jamais dans ceux de l'année en cours ; le reste dû s'encaisse en caisse.

const ID_AUTO = 1;
const fcfa = (v) => `${Math.round(Number(v) || 0).toLocaleString('fr-FR').replace(/[  ]/g, ' ')} F`;
const dateFr = (v) => (v ? String(v).slice(0, 10).split('-').reverse().join('/') : '');
const PAIEMENTS = [['PAYEE', 'Payée'], ['PARTIELLE', 'Partiellement payée'], ['IMPAYEE', 'Impayée']];
const COULEURS_PAIEMENT = { PAYEE: 'badge-emerald', PARTIELLE: 'badge-amber', IMPAYEE: 'badge-rose' };
const nomClient = (c) => [c.Nom, c.Prenoms].filter(Boolean).join(' ').trim();

const AFFAIRE_VIDE = {
  IdClient: 0, Client: '', IdCompagnie: '', IdProduit: '', IdTarif: '', NumeroPoliceCompagnie: '', DateEmission: '', DateEffet: '',
  DateExpiration: '', PrimeNette: 0, Accessoire: 0, Taxe: 0, Fga: 0, Cedeao: 0, PrimeTtc: 0, TauxCommission: '', CommissionPercue: false,
  StatutPaiement: 'PAYEE', MontantEncaisse: 0, Immatriculation: '', IdMarque: '', Modele: '', Puissance: '', Places: '', IdEnergie: '',
  ValeurNeuve: 0, ValeurVenale: 0, DateMec: '', Risque: '', Observation: '',
};

// Échéance par défaut : un an moins un jour après l'effet
const echeanceAnnuelle = (effet) => {
  if (!effet) return '';
  const d = new Date(`${effet}T00:00:00`);
  d.setFullYear(d.getFullYear() + 1);
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
};

const Champ = ({ libelle, aide, children, requis }) => (
  <div className="form-group" style={{ margin: 0 }}>
    <label className="form-label">{libelle}{requis ? ' *' : ''}</label>
    {children}
    {aide && <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{aide}</span>}
  </div>
);

const grille = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.9rem', alignItems: 'start' };
const sousTitre = { fontSize: '0.78rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--primary-500)', margin: '1.1rem 0 0.6rem' };

// ------------------------------------------------------------------ saisie d'une affaire
const FormulaireAffaire = ({ ref_, onEnregistre, onFermer }) => {
  const { success, error: toastError } = useToast();
  const [a, setA] = useState(AFFAIRE_VIDE);
  const [recherche, setRecherche] = useState('');
  const [resultats, setResultats] = useState([]);
  const [listeOuverte, setListeOuverte] = useState(false);
  const [nouveauClient, setNouveauClient] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState('');
  const changer = (champ, valeur) => setA((x) => ({ ...x, [champ]: valeur }));
  const produit = ref_.Produits.find((p) => String(p.id) === String(a.IdProduit));
  const auto = Number(a.IdProduit) === ID_AUTO;
  const somme = (Number(a.PrimeNette) || 0) + (Number(a.Accessoire) || 0) + (Number(a.Taxe) || 0);
  const ttc = Number(a.PrimeTtc) || somme;
  const commission = a.TauxCommission !== '' ? Math.round((Number(a.PrimeNette) || 0) * Number(a.TauxCommission) / 100) : null;

  useEffect(() => {
    const terme = recherche.trim();
    if (terme.length < 2 || a.IdClient) { setResultats([]); return undefined; }
    let actif = true;
    const minuterie = setTimeout(() => {
      customerApi.searchClient(encodeURIComponent(terme)).then((l) => { if (actif) setResultats((l || []).slice(0, 30)); }).catch(() => {});
    }, 300);
    return () => { actif = false; clearTimeout(minuterie); };
  }, [recherche, a.IdClient]);

  const choisirClient = (c) => {
    setA((x) => ({ ...x, IdClient: c.IdClient, Client: nomClient(c) }));
    setRecherche(nomClient(c));
    setListeOuverte(false);
  };

  const enregistrer = async (puisNouvelle) => {
    setErreur('');
    if (!a.IdClient) { setErreur('Choisissez le client dans la liste (ou créez-le).'); return; }
    setEnvoi(true);
    try {
      const res = await repriseApi.creer({ ...a, PrimeTtc: ttc });
      success(res.message);
      onEnregistre();
      if (puisNouvelle) {
        // Même client, même compagnie et même branche : la suivante se saisit plus vite
        setA((x) => ({ ...AFFAIRE_VIDE, IdClient: x.IdClient, Client: x.Client, IdCompagnie: x.IdCompagnie, IdProduit: x.IdProduit, IdTarif: x.IdTarif }));
      } else {
        onFermer();
      }
    } catch (err) {
      setErreur(messageErreurApi(err));
      toastError(`Affaire non reprise : ${messageErreurApi(err)}`);
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div>
      <div style={sousTitre}>Client et contrat</div>
      <div style={grille}>
        <Champ libelle="Client" requis aide={a.IdClient ? `Client n° ${a.IdClient}` : 'Tapez au moins 2 lettres du nom.'}>
          <div style={{ position: 'relative' }}>
            <div style={{ display: 'flex', gap: '0.35rem' }}>
              <input className="form-control" value={recherche} placeholder="Rechercher un client…"
                onChange={(e) => { setRecherche(e.target.value); setListeOuverte(true); if (a.IdClient) setA((x) => ({ ...x, IdClient: 0, Client: '' })); }}
                onFocus={() => setListeOuverte(true)} />
              <button type="button" className="btn btn-secondary" title="Nouveau client" onClick={() => setNouveauClient(true)}><Plus size={14} /></button>
            </div>
            {listeOuverte && resultats.length > 0 && (
              <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 30, maxHeight: 220, overflowY: 'auto', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-medium)', borderRadius: 6, boxShadow: 'var(--shadow-lg)' }}>
                {resultats.map((c) => (
                  <div key={c.IdClient} role="option" aria-selected="false" tabIndex={0} onClick={() => choisirClient(c)} onKeyDown={(e) => e.key === 'Enter' && choisirClient(c)}
                    style={{ padding: '0.5rem 0.8rem', cursor: 'pointer', borderBottom: '1px solid var(--border-subtle)', fontSize: '0.84rem' }}>
                    <strong>{nomClient(c)}</strong> <span style={{ color: 'var(--text-muted)' }}>— n° {c.IdClient}{c.Mobile || c.Telephone ? ` — ${c.Mobile || c.Telephone}` : ''}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Champ>
        <Champ libelle="Compagnie" requis>
          <select className="form-control" value={a.IdCompagnie} onChange={(e) => changer('IdCompagnie', e.target.value)}>
            <option value="">— Choisir —</option>
            {ref_.Compagnies.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </Champ>
        <Champ libelle="Branche" requis>
          <select className="form-control" value={a.IdProduit} onChange={(e) => setA((x) => ({ ...x, IdProduit: e.target.value, IdTarif: '' }))}>
            <option value="">— Choisir —</option>
            {ref_.Produits.map((p) => <option key={p.id} value={p.id}>{p.libelle}</option>)}
          </select>
        </Champ>
        <Champ libelle="Catégorie" aide="La première de la branche à défaut.">
          <select className="form-control" value={a.IdTarif} onChange={(e) => changer('IdTarif', e.target.value)} disabled={!produit}>
            <option value="">— Par défaut —</option>
            {(produit?.categories || []).map((t) => <option key={t.id} value={t.id}>{t.libelle}</option>)}
          </select>
        </Champ>
        <Champ libelle="N° police de la compagnie" requis>
          <input className="form-control" value={a.NumeroPoliceCompagnie} onChange={(e) => changer('NumeroPoliceCompagnie', e.target.value)} />
        </Champ>
        <Champ libelle="Date d'émission" requis aide={`Avant le 01/01/${ref_.AnneeLimite}.`}>
          <input type="date" className="form-control" value={a.DateEmission} max={`${ref_.AnneeLimite - 1}-12-31`} onChange={(e) => changer('DateEmission', e.target.value)} />
        </Champ>
        <Champ libelle="Date d'effet" requis>
          <input type="date" className="form-control" value={a.DateEffet} max={`${ref_.AnneeLimite - 1}-12-31`}
            onChange={(e) => setA((x) => ({ ...x, DateEffet: e.target.value, DateEmission: x.DateEmission || e.target.value, DateExpiration: x.DateExpiration || echeanceAnnuelle(e.target.value) }))} />
        </Champ>
        <Champ libelle="Date d'échéance" requis>
          <input type="date" className="form-control" value={a.DateExpiration} onChange={(e) => changer('DateExpiration', e.target.value)} />
        </Champ>
      </div>

      <div style={sousTitre}>Primes de la quittance</div>
      <div style={grille}>
        <Champ libelle="Prime nette" requis aide={auto ? 'FGA et CEDEAO compris, comme sur la quittance.' : undefined}>
          <AmountInput value={a.PrimeNette} onChange={(v) => changer('PrimeNette', v)} suffix="F" />
        </Champ>
        <Champ libelle="Accessoires"><AmountInput value={a.Accessoire} onChange={(v) => changer('Accessoire', v)} suffix="F" /></Champ>
        <Champ libelle="Taxes"><AmountInput value={a.Taxe} onChange={(v) => changer('Taxe', v)} suffix="F" /></Champ>
        {auto && <Champ libelle="dont FGA"><AmountInput value={a.Fga} onChange={(v) => changer('Fga', v)} suffix="F" /></Champ>}
        {auto && <Champ libelle="dont CEDEAO"><AmountInput value={a.Cedeao} onChange={(v) => changer('Cedeao', v)} suffix="F" /></Champ>}
        <Champ libelle="Prime TTC" aide={a.PrimeTtc && Math.abs(Number(a.PrimeTtc) - somme) > 2 ? `Somme des primes : ${fcfa(somme)}` : 'Somme calculée si laissée à 0.'}>
          <AmountInput value={a.PrimeTtc || somme} onChange={(v) => changer('PrimeTtc', v)} suffix="F" />
        </Champ>
      </div>

      <div style={sousTitre}>Paiement et commission</div>
      <div style={grille}>
        <Champ libelle="Paiement du client" requis>
          <select className="form-control" value={a.StatutPaiement} onChange={(e) => changer('StatutPaiement', e.target.value)}>
            {PAIEMENTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </Champ>
        {a.StatutPaiement === 'PARTIELLE' && (
          <Champ libelle="Montant déjà encaissé" requis aide={`Reste à encaisser : ${fcfa(ttc - (Number(a.MontantEncaisse) || 0))}`}>
            <AmountInput value={a.MontantEncaisse} onChange={(v) => changer('MontantEncaisse', v)} suffix="F" />
          </Champ>
        )}
        <Champ libelle="Taux de commission (%)" aide={commission !== null ? `Commission : ${fcfa(commission)}` : 'Taux de la compagnie et de la branche à défaut.'}>
          <input type="number" min="0" max="100" step="0.01" className="form-control" value={a.TauxCommission} onChange={(e) => changer('TauxCommission', e.target.value)} />
        </Champ>
        <Champ libelle="Commission">
          <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.85rem', marginTop: '0.45rem', cursor: 'pointer' }}>
            <input type="checkbox" checked={a.CommissionPercue} onChange={(e) => changer('CommissionPercue', e.target.checked)} /> Déjà perçue
          </label>
        </Champ>
      </div>
      {a.StatutPaiement !== 'PAYEE' && (
        <p style={{ fontSize: '0.78rem', color: 'var(--accent-amber)', margin: '0.5rem 0 0' }}>
          Le reste dû apparaîtra en caisse comme toute quittance à encaisser.
        </p>
      )}

      <div style={sousTitre}>{auto ? 'Véhicule' : 'Risque assuré'}</div>
      {auto ? (
        <div style={grille}>
          <Champ libelle="Immatriculation" requis><input className="form-control" value={a.Immatriculation} onChange={(e) => changer('Immatriculation', e.target.value.toUpperCase())} /></Champ>
          <Champ libelle="Marque">
            <select className="form-control" value={a.IdMarque} onChange={(e) => changer('IdMarque', e.target.value)}>
              <option value="">—</option>
              {ref_.Marques.map((m) => <option key={m.id} value={m.id}>{m.libelle}</option>)}
            </select>
          </Champ>
          <Champ libelle="Modèle"><input className="form-control" value={a.Modele} maxLength={30} onChange={(e) => changer('Modele', e.target.value)} /></Champ>
          <Champ libelle="Puissance (CV)"><input type="number" min="0" className="form-control" value={a.Puissance} onChange={(e) => changer('Puissance', e.target.value)} /></Champ>
          <Champ libelle="Places"><input type="number" min="0" className="form-control" value={a.Places} onChange={(e) => changer('Places', e.target.value)} /></Champ>
          <Champ libelle="Énergie">
            <select className="form-control" value={a.IdEnergie} onChange={(e) => changer('IdEnergie', e.target.value)}>
              <option value="">—</option>
              {ref_.Energies.map((x) => <option key={x.id} value={x.id}>{x.libelle}</option>)}
            </select>
          </Champ>
          <Champ libelle="Valeur neuve"><AmountInput value={a.ValeurNeuve} onChange={(v) => changer('ValeurNeuve', v)} suffix="F" /></Champ>
          <Champ libelle="Valeur vénale"><AmountInput value={a.ValeurVenale} onChange={(v) => changer('ValeurVenale', v)} suffix="F" /></Champ>
          <Champ libelle="Mise en circulation"><input type="date" className="form-control" value={a.DateMec} onChange={(e) => changer('DateMec', e.target.value)} /></Champ>
        </div>
      ) : (
        <Champ libelle="Description du risque" aide="Objet assuré, lieu, personnes, capitaux…">
          <textarea className="form-control" rows={2} maxLength={500} value={a.Risque} onChange={(e) => changer('Risque', e.target.value)} />
        </Champ>
      )}
      <div style={{ marginTop: '0.9rem' }}>
        <Champ libelle="Observation">
          <input className="form-control" maxLength={500} value={a.Observation} onChange={(e) => changer('Observation', e.target.value)} />
        </Champ>
      </div>

      {erreur && (
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', padding: '0.6rem 0.8rem', borderRadius: 8, background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.3)', color: 'var(--accent-rose)', fontSize: '0.84rem', marginTop: '1rem' }}>
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }} /> {erreur}
        </div>
      )}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.2rem', flexWrap: 'wrap' }}>
        <button type="button" className="btn btn-secondary" onClick={onFermer} disabled={envoi}>Fermer</button>
        <button type="button" className="btn btn-secondary" onClick={() => enregistrer(true)} disabled={envoi} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <Plus size={14} /> Enregistrer et saisir la suivante
        </button>
        <button type="button" className="btn btn-primary" onClick={() => enregistrer(false)} disabled={envoi} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          {envoi ? <Loader2 size={14} className="spin" /> : <Save size={14} />} Enregistrer
        </button>
      </div>

      <QuickAddClientModal isOpen={nouveauClient} onClose={() => setNouveauClient(false)}
        onClientCreated={(c) => {
          const id = Number(c.id || c.IdClient);
          const nom = c.nomcomplet || [c.Nom, c.Prenoms].filter(Boolean).join(' ');
          setA((x) => ({ ...x, IdClient: id, Client: nom }));
          setRecherche(nom);
        }} />
    </div>
  );
};

// ------------------------------------------------------------------ import Excel
const ImportAffaires = ({ onImporte }) => {
  const { success, error: toastError } = useToast();
  const [fichier, setFichier] = useState(null);
  const [analyse, setAnalyse] = useState(null);
  const [resultat, setResultat] = useState(null);
  const [envoi, setEnvoi] = useState('');
  const lancer = async (importer) => {
    if (!fichier) { toastError('Choisissez le fichier Excel.'); return; }
    setEnvoi(importer ? 'import' : 'analyse');
    try {
      const r = importer ? await repriseApi.importer(fichier) : await repriseApi.analyser(fichier);
      if (importer) {
        setResultat(r);
        setAnalyse(null);
        success(`${r.Correctes} affaire${r.Correctes > 1 ? 's' : ''} reprise${r.Correctes > 1 ? 's' : ''}${r.Erreurs ? `, ${r.Erreurs} ligne${r.Erreurs > 1 ? 's' : ''} refusée${r.Erreurs > 1 ? 's' : ''}` : ''}.`);
        onImporte();
      } else {
        setAnalyse(r);
        setResultat(null);
      }
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi('');
    }
  };
  const telechargerModele = async () => {
    try {
      downloadBlob(await repriseApi.modele(), 'modele_reprise_affaires_anterieures.xlsx');
    } catch (err) {
      toastError(messageErreurApi(err));
    }
  };
  const compteRendu = resultat || analyse;
  return (
    <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div style={{ flex: 1, minWidth: 260 }}>
          <div style={{ fontWeight: 700, marginBottom: '0.3rem' }}>Importer un fichier Excel</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Une ligne par quittance, colonnes du modèle (aide dans sa deuxième feuille). L'analyse contrôle chaque ligne sans rien enregistrer ;
            l'import reprend les lignes correctes et signale les autres. Les clients absents sont créés.
          </div>
        </div>
        <button type="button" className="btn btn-secondary" onClick={telechargerModele} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <Download size={14} /> Modèle Excel
        </button>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.9rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <input type="file" accept=".xlsx,.xlsm" className="form-control" style={{ maxWidth: 380 }}
          onChange={(e) => { setFichier(e.target.files?.[0] || null); setAnalyse(null); setResultat(null); }} />
        <button type="button" className="btn btn-secondary" onClick={() => lancer(false)} disabled={!fichier || !!envoi} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          {envoi === 'analyse' ? <Loader2 size={14} className="spin" /> : <Search size={14} />} Analyser
        </button>
        <button type="button" className="btn btn-primary" onClick={() => lancer(true)} disabled={!fichier || !!envoi || (analyse && !analyse.Correctes)}
          style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          {envoi === 'import' ? <Loader2 size={14} className="spin" /> : <Upload size={14} />}
          {analyse ? `Importer les ${analyse.Correctes} ligne${analyse.Correctes > 1 ? 's' : ''} correcte${analyse.Correctes > 1 ? 's' : ''}` : 'Importer'}
        </button>
      </div>
      {compteRendu && (
        <div style={{ marginTop: '1rem' }}>
          <div style={{ fontSize: '0.84rem', marginBottom: '0.5rem' }}>
            <strong>{resultat ? 'Import terminé' : 'Analyse'}</strong> : {compteRendu.Correctes} ligne{compteRendu.Correctes > 1 ? 's' : ''} correcte{compteRendu.Correctes > 1 ? 's' : ''}
            {' '}({fcfa(compteRendu.PrimeTtc)}), {compteRendu.Erreurs} refusée{compteRendu.Erreurs > 1 ? 's' : ''}
            {compteRendu.NouveauxClients ? `, ${compteRendu.NouveauxClients} nouveau${compteRendu.NouveauxClients > 1 ? 'x' : ''} client${compteRendu.NouveauxClients > 1 ? 's' : ''}` : ''}
            {resultat ? '.' : ' — rien n\'est encore enregistré.'}
          </div>
          <div className="table-wrapper" style={{ maxHeight: 340, overflowY: 'auto' }}>
            <table className="data-table">
              <thead><tr><th>Ligne</th><th>État</th><th>Client</th><th>Police compagnie</th><th>Prime TTC</th><th>{resultat ? 'Police / quittance' : 'Police / quittance prévues'}</th><th>Motif</th></tr></thead>
              <tbody>
                {compteRendu.Lignes.map((l) => (
                  <tr key={l.Ligne}>
                    <td>{l.Ligne}</td>
                    <td>{l.Statut === 'OK'
                      ? <span className="badge badge-emerald"><CheckCircle2 size={12} /> {resultat ? 'Reprise' : 'Correcte'}</span>
                      : <span className="badge badge-rose"><X size={12} /> Refusée</span>}</td>
                    <td>{l.Client}{l.NouveauClient ? <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}> (nouveau)</span> : ''}</td>
                    <td>{l.NumeroPoliceCompagnie}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{l.PrimeTtc !== null && l.PrimeTtc !== undefined ? fcfa(l.PrimeTtc) : ''}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>{l.NumeroPolice ? `${l.NumeroPolice} / ${l.NumeroQuittance}` : ''}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--accent-rose)' }}>{l.Message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

// ------------------------------------------------------------------ page
export const RepriseAffairesPage = () => {
  const { success, error: toastError } = useToast();
  const { peut } = useAuth();
  const [ref_, setRef] = useState(null);
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [filtres, setFiltres] = useState({ annee: '', compagnie: '', produit: '', paiement: '', commission: '', q: '', page: 1 });
  const [saisieOuverte, setSaisieOuverte] = useState(false);
  const [importOuvert, setImportOuvert] = useState(false);
  const peutSaisir = peut('contrats.reprise');

  useEffect(() => {
    repriseApi.referentiels().then(setRef).catch((err) => toastError(`Listes non chargées : ${messageErreurApi(err)}`));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const charger = () => {
    setChargement(true);
    const params = Object.fromEntries(Object.entries(filtres).filter(([, v]) => v !== ''));
    repriseApi.lister(params).then(setDonnees).catch((err) => toastError(messageErreurApi(err))).finally(() => setChargement(false));
  };
  useEffect(() => {
    const minuterie = setTimeout(charger, filtres.q ? 350 : 0);
    return () => clearTimeout(minuterie);
  }, [filtres]); // eslint-disable-line react-hooks/exhaustive-deps

  const filtrer = (cle, valeur) => setFiltres((f) => ({ ...f, [cle]: valeur, page: 1 }));
  const basculerCommission = async (l) => {
    try {
      await repriseApi.commission(l.Id, !l.CommissionPercue);
      success(`Commission ${!l.CommissionPercue ? 'notée perçue' : 'remise à percevoir'} : police ${l.NumeroPolice}.`);
      charger();
    } catch (err) {
      toastError(messageErreurApi(err));
    }
  };
  const supprimerReprise = async (l) => {
    if (!(await confirmer({
      ton: 'danger', titre: `Supprimer la reprise ${l.NumeroPolice} ?`, confirmer: 'Supprimer',
      message: `Le contrat, sa quittance ${l.NumeroQuittance} et le devis créés par la reprise seront supprimés. Possible tant qu'aucun encaissement, avenant ou sinistre n'existe sur ce contrat.`,
    }))) return;
    try {
      const r = await repriseApi.supprimer(l.Id);
      success(r.message);
      charger();
    } catch (err) {
      toastError(messageErreurApi(err));
    }
  };
  const totaux = donnees?.Totaux;
  const tuiles = useMemo(() => (totaux ? [
    ['Affaires reprises', String(totaux.Nombre)], ['Primes TTC', fcfa(totaux.PrimeTtc)], ['Encaissé', fcfa(totaux.Encaisse)],
    ['Reste à encaisser', fcfa(totaux.Reste)], ['Commissions à percevoir', fcfa(totaux.CommissionAPercevoir)],
  ] : []), [totaux]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', paddingBottom: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}><History size={26} /> Affaires antérieures</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', maxWidth: 900, margin: '0.3rem 0 0' }}>
            Contrats des années passées absents de LE PHARE, repris tels qu'ils ont été émis : toute compagnie, toute branche, avant le 01/01/{ref_?.AnneeLimite || ''}.
            Ils comptent dans les états de leur année (jamais dans ceux de l'année en cours), apparaissent au portefeuille, sur la fiche du client
            et aux renouvellements ; le reste dû s'encaisse en caisse.
          </p>
        </div>
        {peutSaisir && (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setImportOuvert((v) => !v)} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <FileSpreadsheet size={15} /> Importer (Excel)
            </button>
            <button type="button" className="btn btn-primary" onClick={() => setSaisieOuverte(true)} disabled={!ref_} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Plus size={15} /> Nouvelle affaire antérieure
            </button>
          </div>
        )}
      </div>

      {importOuvert && peutSaisir && <ImportAffaires onImporte={charger} />}

      {tuiles.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.7rem' }}>
          {tuiles.map(([libelle, valeur]) => (
            <div key={libelle} className="glass-panel" style={{ padding: '0.8rem 1rem' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{libelle}</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>{valeur}</div>
            </div>
          ))}
        </div>
      )}

      <div className="glass-panel" style={{ padding: '1rem 1.1rem' }}>
        <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: '0.8rem' }}>
          <div style={{ flex: 1, minWidth: 220, position: 'relative' }}>
            <label className="form-label" htmlFor="reprise-recherche">Rechercher</label>
            <Search size={14} style={{ position: 'absolute', left: 10, bottom: 11, color: 'var(--text-muted)' }} />
            <input id="reprise-recherche" className="form-control" style={{ paddingLeft: '1.9rem' }} placeholder="Police, client, quittance…"
              value={filtres.q} onChange={(e) => filtrer('q', e.target.value)} />
          </div>
          <div><label className="form-label" htmlFor="reprise-annee">Année d'effet</label>
            <select id="reprise-annee" className="form-control" value={filtres.annee} onChange={(e) => filtrer('annee', e.target.value)}>
              <option value="">Toutes</option>{(donnees?.Annees || []).map((a) => <option key={a} value={a}>{a}</option>)}
            </select></div>
          <div><label className="form-label" htmlFor="reprise-compagnie">Compagnie</label>
            <select id="reprise-compagnie" className="form-control" value={filtres.compagnie} onChange={(e) => filtrer('compagnie', e.target.value)}>
              <option value="">Toutes</option>{(ref_?.Compagnies || []).map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
            </select></div>
          <div><label className="form-label" htmlFor="reprise-produit">Branche</label>
            <select id="reprise-produit" className="form-control" value={filtres.produit} onChange={(e) => filtrer('produit', e.target.value)}>
              <option value="">Toutes</option>{(ref_?.Produits || []).map((p) => <option key={p.id} value={p.id}>{p.libelle}</option>)}
            </select></div>
          <div><label className="form-label" htmlFor="reprise-paiement">Paiement</label>
            <select id="reprise-paiement" className="form-control" value={filtres.paiement} onChange={(e) => filtrer('paiement', e.target.value)}>
              <option value="">Tous</option>{PAIEMENTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select></div>
          <div><label className="form-label" htmlFor="reprise-commission">Commission</label>
            <select id="reprise-commission" className="form-control" value={filtres.commission} onChange={(e) => filtrer('commission', e.target.value)}>
              <option value="">Toutes</option><option value="A_PERCEVOIR">À percevoir</option>
            </select></div>
          {Object.entries(filtres).some(([k, v]) => k !== 'page' && v !== '') && (
            <button type="button" className="btn btn-secondary" title="Retirer les filtres"
              onClick={() => setFiltres({ annee: '', compagnie: '', produit: '', paiement: '', commission: '', q: '', page: 1 })}><RotateCcw size={14} /></button>
          )}
        </div>

        {chargement && !donnees ? (
          <div style={{ color: 'var(--text-muted)' }}><Loader2 size={15} className="spin" /> Chargement…</div>
        ) : !donnees?.Lignes.length ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.88rem', padding: '1rem 0' }}>
            Aucune affaire antérieure reprise{Object.entries(filtres).some(([k, v]) => k !== 'page' && v !== '') ? ' pour ces filtres' : ''}.
          </div>
        ) : (
          <>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr><th>Police OREOLE</th><th>Police compagnie</th><th>Client</th><th>Compagnie / branche</th><th>Effet → échéance</th>
                    <th>Prime TTC</th><th>Paiement</th><th>Commission</th><th>Saisie</th><th /></tr>
                </thead>
                <tbody>
                  {donnees.Lignes.map((l) => (
                    <tr key={l.Id}>
                      <td><Link to={`/user/contracts/${l.IdContrat}`} style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{l.NumeroPolice}</Link>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{l.NumeroQuittance}</div></td>
                      <td>{l.NumeroPoliceCompagnie}</td>
                      <td>{l.Client}</td>
                      <td>{l.Compagnie}<div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{l.Branche}</div></td>
                      <td style={{ whiteSpace: 'nowrap' }}>{dateFr(l.DateEffet)} → {dateFr(l.DateExpiration)}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>{fcfa(l.PrimeTtc)}</td>
                      <td><span className={`badge ${COULEURS_PAIEMENT[l.Paiement]}`}>{l.PaiementLibelle}</span>
                        {l.Reste > 0 && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>reste {fcfa(l.Reste)}</div>}</td>
                      <td style={{ whiteSpace: 'nowrap' }}>{fcfa(l.Commission)}
                        <div>{peutSaisir ? (
                          <button type="button" className="btn-link" onClick={() => basculerCommission(l)}
                            style={{ fontSize: '0.72rem', background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: l.CommissionPercue ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
                            {l.CommissionPercue ? 'perçue' : 'à percevoir'}
                          </button>
                        ) : <span style={{ fontSize: '0.72rem' }}>{l.CommissionPercue ? 'perçue' : 'à percevoir'}</span>}</div></td>
                      <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{l.Mode === 'import' ? 'Import' : 'Saisie'}<div>{l.CreePar}</div></td>
                      <td>{peutSaisir && (l.Auteur || donnees.PeutToutSupprimer) && (
                        <button type="button" className="btn btn-secondary" title="Supprimer cette reprise" onClick={() => supprimerReprise(l)}
                          style={{ padding: '0.25rem 0.5rem', color: 'var(--accent-rose)' }}><Trash2 size={14} /></button>
                      )}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {donnees.Pages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.4rem', alignItems: 'center', marginTop: '0.7rem', fontSize: '0.82rem' }}>
                <button type="button" className="btn btn-secondary" disabled={donnees.Page <= 1} onClick={() => setFiltres((f) => ({ ...f, page: f.page - 1 }))}>Précédente</button>
                <span>Page {donnees.Page} / {donnees.Pages}</span>
                <button type="button" className="btn btn-secondary" disabled={donnees.Page >= donnees.Pages} onClick={() => setFiltres((f) => ({ ...f, page: f.page + 1 }))}>Suivante</button>
              </div>
            )}
          </>
        )}
      </div>

      <Modal isOpen={saisieOuverte} onClose={() => setSaisieOuverte(false)} title="Nouvelle affaire antérieure"
        subtitle="Saisissez la quittance telle qu'elle a été émise : primes, dates et état du paiement." size="large" maxWidth="980px">
        {saisieOuverte && ref_ && <FormulaireAffaire ref_={ref_} onEnregistre={charger} onFermer={() => setSaisieOuverte(false)} />}
      </Modal>
    </div>
  );
};

export default RepriseAffairesPage;
