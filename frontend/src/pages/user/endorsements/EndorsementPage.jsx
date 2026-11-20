import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ChevronLeft, ChevronRight, ClipboardList, Eye, FilePen, Layers, Loader2, Plus, Printer, RefreshCw, Search, Undo2, Wallet,
} from 'lucide-react';
import { contractApi } from '../../../api/endpoints';
import apiClient from '../../../api/apiClient';
import { cheminDevis, francs, pluriel, Tuile } from '../../../components/common/Cockpit';
import { Modal } from '../../../components/common/Modal';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { useToast } from '../../../context/ToastContext';
import { libelleAvenant } from '../../../utils/avenants';
import { aLeDroit } from '../../../utils/droits';
import { dateFr, messageErreurApi } from '../../../utils/financeUtils';
import { estAvenantPolice, imprimerAvenantPolice } from '../../../utils/impressionsAvenants';

/* =========================================================================
   Registre des avenants (serveur : production/registre_avenants.py). Un avenant est un contrat de la police : code de
   mouvement, numéro d'avenant, période et quittance. Deux vues :
   - émis : renouvellements, incorporations, modifications (Santé), retraits, résiliations, changements d'immatriculation,
     annulations et autres actes, par date d'émission ;
   - en préparation : devis d'avenant non confirmés (renouvellement, incorporation, modification Santé), à continuer dans
     leur écran de saisie puis à confirmer.
   Un nouvel avenant part de la fiche de la police : elle propose les actes possibles selon la branche et le contrat.
   ========================================================================= */
const TYPES = [
  ['', 'Tous'], ['REN', 'Renouvellements'], ['INC', 'Incorporations'], ['MOD', 'Modifications'], ['RET', 'Retraits'],
  ['RES', 'Résiliations'], ['CHI', "Changements d'immatriculation"], ['ANL', 'Annulations'], ['AUTRES', 'Autres actes'],
];
const COULEURS = { REN: 'emerald', INC: 'blue', MOD: 'purple', RET: 'amber', RES: 'rose', CHI: 'blue', ANL: 'rose', AUTRES: 'blue' };
const TAILLE = 50;
const STATUTS_POLICE = { en_cours: 'En cours', a_renouveler: 'À renouveler', echu: 'Échue', renouvele: 'Renouvelée', resilie: 'Résiliée', annule: 'Annulée' };
const PETIT = { padding: '0.3rem 0.55rem', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' };
const DROITE = { textAlign: 'right', whiteSpace: 'nowrap' };
const SECONDAIRE = { fontSize: '0.72rem', color: 'var(--text-muted)' };

const iso = (d) => {
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};
const PERIODES = {
  exercice: () => { const j = new Date(); return { du: `${j.getFullYear()}-01-01`, au: iso(j) }; },
  douze: () => { const j = new Date(); const d = new Date(j); d.setFullYear(j.getFullYear() - 1); d.setDate(d.getDate() + 1); return { du: iso(d), au: iso(j) }; },
  tout: () => ({ du: '2000-01-01', au: iso(new Date()) }),
};
const numeroAvenant = (n) => (n ? `n° ${Number(n) || n}` : '');

const Acte = ({ ligne }) => (
  <div>
    <StatusBadge label={libelleAvenant(ligne.Code, ligne.Libelle)} color={COULEURS[ligne.Type] || 'blue'} />
    <div style={{ ...SECONDAIRE, marginTop: 3 }}>{[numeroAvenant(ligne.NumeroAvenant), ligne.Objets > 1 ? pluriel(ligne.Objets, 'objet', 'objets') : '']
      .filter(Boolean).join(' - ')}</div>
  </div>
);

// Quittance de l'acte : soldée, reste à encaisser, ou ristourne à rembourser (Caisse > Ristournes à régler)
const EtatQuittance = ({ ligne }) => {
  if (!ligne.Quittance) return <span style={SECONDAIRE}>Sans quittance</span>;
  const reste = ligne.ResteQuittance || 0;
  let etat;
  if (Math.abs(reste) < 5) etat = <span style={{ color: 'var(--accent-emerald)' }}>{ligne.PrimeTtc < 0 ? 'Ristourne réglée' : 'Soldée'}</span>;
  else if (reste < 0) etat = <Link to={`/user/cash/ristournes?quittance=${encodeURIComponent(ligne.Quittance)}`}>À rembourser {francs(-reste)}</Link>;
  else etat = <span style={{ color: 'var(--accent-amber)' }}>Reste {francs(reste)}</span>;
  return <div>{ligne.Quittance}<div style={{ fontSize: '0.72rem' }}>{etat}</div></div>;
};

// Nouvel avenant : choisir la police ; sa fiche propose les actes possibles (renouveler, incorporer, retirer, résilier…)
const ChoixPolice = ({ onClose }) => {
  const navigate = useNavigate();
  const [recherche, setRecherche] = useState('');
  const [resultats, setResultats] = useState(null);
  const [chargement, setChargement] = useState(false);
  useEffect(() => {
    const texte = recherche.trim();
    if (texte.length < 3) { setResultats(null); return undefined; }
    const minuterie = setTimeout(async () => {
      setChargement(true);
      try {
        const { contrats } = await contractApi.getPortefeuille({ recherche: texte, page: 1, page_size: 12 });
        setResultats(contrats);
      } catch {
        setResultats([]);
      } finally {
        setChargement(false);
      }
    }, 350);
    return () => clearTimeout(minuterie);
  }, [recherche]);

  return (
    <Modal isOpen onClose={onClose} size="large" title="Nouvel avenant" subtitle="Choisissez la police : sa fiche propose les actes possibles">
      <div style={{ position: 'relative' }}>
        <Search size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
        <input className="form-control" style={{ paddingLeft: 32 }} autoFocus value={recherche} onChange={(e) => setRecherche(e.target.value)}
          placeholder="N° de police, client, immatriculation" aria-label="Rechercher une police" />
      </div>
      <div style={{ marginTop: '0.9rem', minHeight: 120 }}>
        {chargement && <div style={{ color: 'var(--text-muted)' }}><Loader2 size={16} className="spin" /> Recherche…</div>}
        {!chargement && resultats === null && <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Saisissez au moins 3 caractères.</div>}
        {!chargement && resultats && !resultats.length && <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Aucune police trouvée.</div>}
        {!chargement && resultats && resultats.length > 0 && (
          <div className="table-wrapper" style={{ maxHeight: '50vh', overflow: 'auto' }}>
            <table className="data-table" style={{ fontSize: '0.82rem' }}>
              <thead><tr><th>Police / client</th><th>Compagnie / branche</th><th>Période</th><th>Statut</th><th aria-label="Ouvrir" /></tr></thead>
              <tbody>
                {resultats.map((c) => (
                  <tr key={c.id}>
                    <td>{c.numeropolice}<div style={SECONDAIRE}>{c.client_nom}</div></td>
                    <td>{c.compagnie}<div style={SECONDAIRE}>{c.produit}</div></td>
                    <td style={{ whiteSpace: 'nowrap' }}>{dateFr(c.date_effet)}<div style={SECONDAIRE}>au {dateFr(c.date_expiration)}</div></td>
                    <td>{STATUTS_POLICE[c.statut_portefeuille] || c.statut_contrat || '-'}</td>
                    <td><button type="button" className="btn btn-primary" style={PETIT} onClick={() => navigate(`/user/contracts/${c.id}`)}>Ouvrir la fiche</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Modal>
  );
};

export const EndorsementPage = () => {
  const navigate = useNavigate();
  const { error: toastError } = useToast();
  const [parametres, setParametres] = useSearchParams();
  const etat = parametres.get('etat') === 'preparation' ? 'preparation' : 'emis';
  const type = parametres.get('type') || '';
  const [periode, setPeriode] = useState(() => ({ ...PERIODES.exercice(), du: parametres.get('du') || PERIODES.exercice().du, au: parametres.get('au') || PERIODES.exercice().au }));
  const [saisie, setSaisie] = useState(parametres.get('q') || '');
  const [recherche, setRecherche] = useState(saisie);
  const [page, setPage] = useState(1);
  const [donnees, setDonnees] = useState(null);
  // Synthèse affichée quel que soit l'onglet : actes émis de la période (tous types) et avenants en préparation
  const [synthese, setSynthese] = useState(null);
  const [enPreparation, setEnPreparation] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [choix, setChoix] = useState(false);
  const requete = useRef(0);
  const peutAvenant = aLeDroit('contrats.avenant') || aLeDroit('contrats.cancel');

  // Recherche saisie : envoyée au serveur après une courte pause
  useEffect(() => {
    const minuterie = setTimeout(() => setRecherche(saisie.trim()), 350);
    return () => clearTimeout(minuterie);
  }, [saisie]);
  useEffect(() => { setPage(1); }, [etat, type, periode, recherche]);

  const changer = (cle, valeur) => setParametres((p) => {
    const n = new URLSearchParams(p);
    if (valeur) n.set(cle, valeur); else n.delete(cle);
    if (cle === 'etat') n.delete('type');
    return n;
  }, { replace: true });

  const charger = useCallback(async () => {
    const numero = ++requete.current;
    setChargement(true);
    const base = { du: periode.du, au: periode.au, q: recherche || undefined };
    try {
      // L'onglet affiché, et l'autre état réduit à une ligne pour sa synthèse
      const autre = etat === 'emis' ? 'preparation' : 'emis';
      const [registre, complement] = await Promise.all([
        apiClient.get('/avenants/registre/', { params: { ...base, etat, type: type || undefined, page, taille: TAILLE } }).then((r) => r.data),
        apiClient.get('/avenants/registre/', { params: { ...base, etat: autre, taille: 1 } }).then((r) => r.data).catch(() => null),
      ]);
      if (numero !== requete.current) return;
      setDonnees(registre);
      const emis = etat === 'emis' ? registre : complement;
      const preparation = etat === 'emis' ? complement : registre;
      setSynthese(emis ? { Compteurs: emis.Compteurs, Totaux: emis.Totaux } : null);
      setEnPreparation(preparation ? Object.values(preparation.Compteurs || {}).reduce((s, n) => s + n, 0) : null);
    } catch (err) {
      if (numero === requete.current) toastError(`Registre des avenants indisponible : ${messageErreurApi(err)}`);
    } finally {
      if (numero === requete.current) setChargement(false);
    }
  }, [etat, type, page, periode, recherche, toastError]);
  useEffect(() => { charger(); }, [charger]);

  const compteurs = donnees?.Compteurs || {};
  const tousTypes = Object.values(compteurs).reduce((s, n) => s + n, 0);
  const onglets = TYPES.filter(([cle]) => !cle || cle === type || compteurs[cle] > 0);
  const pages = donnees ? Math.max(1, Math.ceil(donnees.Total / TAILLE)) : 1;
  const totaux = synthese?.Totaux;
  const renouvellements = synthese?.Compteurs?.REN || 0;
  const periodeActive = useMemo(() => Object.keys(PERIODES).find((k) => {
    const p = PERIODES[k]();
    return p.du === periode.du && p.au === periode.au;
  }) || '', [periode]);

  const imprimer = async (ligne) => {
    try {
      await imprimerAvenantPolice(ligne.IdContrat);
    } catch (err) {
      toastError(`Avenant non imprimé : ${messageErreurApi(err)}`);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', paddingBottom: '2rem' }}>
      <div className="responsive-header">
        <div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', margin: 0 }}>
            <ClipboardList size={26} style={{ color: 'var(--primary-500)' }} /> Registre des avenants
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0.3rem 0 0', maxWidth: 900 }}>
            Renouvellements, incorporations, modifications, retraits, résiliations et changements d'immatriculation de toutes les polices.
          </p>
        </div>
        {peutAvenant && (
          <button type="button" className="btn btn-primary" onClick={() => setChoix(true)} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Plus size={16} /> Nouvel avenant
          </button>
        )}
      </div>

      <div className="cockpit-tuiles">
        <Tuile titre={`Actes émis du ${dateFr(periode.du)} au ${dateFr(periode.au)}`} icone={Layers} couleur="blue"
          valeur={totaux ? pluriel(totaux.Actes, 'acte', 'actes') : '-'}
          lignes={totaux ? [
            `${pluriel(renouvellements, 'renouvellement', 'renouvellements')}, ${pluriel(totaux.Actes - renouvellements, 'autre avenant', 'autres avenants')}`,
            totaux.Annules > 0 && `dont ${pluriel(totaux.Annules, 'acte annulé', 'actes annulés')}`,
          ] : []} />
        <Tuile titre="Primes des avenants" icone={Wallet} couleur="emerald" valeur={totaux ? francs(totaux.Primes) : '-'}
          lignes={['Prime TTC des actes non annulés']} />
        <Tuile titre="Ristournes" icone={Undo2} couleur="rose" valeur={totaux ? francs(totaux.Ristournes) : '-'}
          vers="/user/cash/ristournes" lignes={['Retraits et résiliations : à régler en caisse']} />
        <Tuile titre="En préparation" icone={FilePen} couleur="amber" valeur={enPreparation === null ? '-' : pluriel(enPreparation, 'avenant', 'avenants')}
          lignes={['Devis de renouvellement, incorporation ou modification à confirmer']} />
      </div>

      <div className="glass-panel" style={{ padding: '1rem 1.1rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div role="tablist" aria-label="Avenants émis ou en préparation" style={{ display: 'flex', gap: '0.4rem' }}>
            <button type="button" role="tab" aria-selected={etat === 'emis'} className={`btn ${etat === 'emis' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => changer('etat', '')}>
              Émis
            </button>
            <button type="button" role="tab" aria-selected={etat === 'preparation'} className={`btn ${etat === 'preparation' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => changer('etat', 'preparation')}>
              En préparation{enPreparation !== null ? ` (${enPreparation})` : ''}
            </button>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" htmlFor="reg-du">{etat === 'emis' ? 'Émis du' : 'Créés du'}</label>
            <input id="reg-du" type="date" className="form-control" value={periode.du} max={periode.au} onChange={(e) => e.target.value && setPeriode((p) => ({ ...p, du: e.target.value }))} />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" htmlFor="reg-au">au</label>
            <input id="reg-au" type="date" className="form-control" value={periode.au} min={periode.du} onChange={(e) => e.target.value && setPeriode((p) => ({ ...p, au: e.target.value }))} />
          </div>
          <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
            {[['exercice', 'Exercice'], ['douze', '12 mois'], ['tout', 'Tout']].map(([cle, libelle]) => (
              <button key={cle} type="button" className={`btn ${periodeActive === cle ? 'btn-primary' : 'btn-secondary'}`} style={{ padding: '0.4rem 0.7rem' }}
                onClick={() => setPeriode(PERIODES[cle]())}>{libelle}</button>
            ))}
          </div>
          <div style={{ position: 'relative', flex: '1 1 220px', maxWidth: 380, marginLeft: 'auto' }}>
            <Search size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input className="form-control" style={{ paddingLeft: 32 }} value={saisie} onChange={(e) => setSaisie(e.target.value)}
              placeholder="Police, client, compagnie, quittance" aria-label="Rechercher dans le registre" />
          </div>
        </div>

        <div role="tablist" aria-label="Type d'acte" style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
          {onglets.map(([cle, libelle]) => (
            <button key={cle || 'tous'} type="button" role="tab" aria-selected={type === cle} className={`btn ${type === cle ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '0.35rem 0.7rem', fontSize: '0.8rem' }} onClick={() => changer('type', cle)}>
              {libelle} ({cle ? compteurs[cle] || 0 : tousTypes})
            </button>
          ))}
        </div>

        <div className="table-wrapper" style={{ maxHeight: '62vh', overflow: 'auto', position: 'relative' }}>
          {etat === 'emis' ? (
            <table className="data-table" style={{ fontSize: '0.82rem' }}>
              <thead>
                <tr><th>Émis le</th><th>Acte</th><th>Police / client</th><th>Compagnie / branche</th><th>Période</th>
                  <th style={DROITE}>Prime TTC</th><th>Quittance</th><th aria-label="Actions" /></tr>
              </thead>
              <tbody>
                {(donnees?.Lignes || []).map((l) => (
                  <tr key={l.IdContrat} style={l.Annule ? { opacity: 0.6 } : undefined}>
                    <td style={{ whiteSpace: 'nowrap' }}>{dateFr(l.DateEmission)}<div style={SECONDAIRE}>{l.Operateur}</div></td>
                    <td>
                      <Acte ligne={l} />
                      {l.Annule && <div style={{ marginTop: 3 }}><StatusBadge label="Annulé" color="rose" /></div>}
                      {l.Motif && <div style={{ ...SECONDAIRE, maxWidth: 240 }} title={l.Motif}>{l.Motif}</div>}
                    </td>
                    <td>{l.NumeroPolice}<div style={SECONDAIRE}>{l.Client}</div></td>
                    <td>{l.Compagnie}<div style={SECONDAIRE}>{l.Branche}{l.Flotte && l.IdProduit === 1 ? ' - flotte' : ''}</div></td>
                    <td style={{ whiteSpace: 'nowrap' }}>{dateFr(l.DateEffet)}<div style={SECONDAIRE}>au {dateFr(l.DateExpiration)}</div></td>
                    <td style={{ ...DROITE, fontWeight: 700, color: l.PrimeTtc < 0 ? 'var(--accent-rose)' : undefined }}>
                      {l.PrimeTtc < 0 ? `- ${francs(-l.PrimeTtc)}` : francs(l.PrimeTtc)}
                    </td>
                    <td><EtatQuittance ligne={l} /></td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <button type="button" className="btn btn-secondary" style={PETIT} onClick={() => navigate(`/user/contracts/${l.IdContrat}`)} title="Fiche de l'acte : documents, quittance, historique de la police">
                        <Eye size={13} /> Fiche
                      </button>{' '}
                      {estAvenantPolice(l.Code) && (
                        <button type="button" className="btn btn-secondary" style={PETIT} onClick={() => imprimer(l)} title="Avenant imprimé">
                          <Printer size={13} /> Avenant
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <table className="data-table" style={{ fontSize: '0.82rem' }}>
              <thead>
                <tr><th>Créé le</th><th>Acte</th><th>Devis</th><th>Police / client</th><th>Compagnie / branche</th><th>Période</th>
                  <th style={DROITE}>Prime TTC</th><th aria-label="Actions" /></tr>
              </thead>
              <tbody>
                {(donnees?.Lignes || []).map((l) => (
                  <tr key={l.IdDevis}>
                    <td style={{ whiteSpace: 'nowrap' }}>{dateFr(l.DateEmission)}<div style={SECONDAIRE}>{l.Operateur}</div></td>
                    <td><StatusBadge label={libelleAvenant(l.Code, l.Libelle)} color={COULEURS[l.Type] || 'blue'} /></td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{l.NumeroDevis}</td>
                    <td>{l.NumeroPolice || '-'}<div style={SECONDAIRE}>{l.Client}</div></td>
                    <td>{l.Compagnie}<div style={SECONDAIRE}>{l.Branche}</div></td>
                    <td style={{ whiteSpace: 'nowrap' }}>{dateFr(l.DateEffet)}<div style={SECONDAIRE}>au {dateFr(l.DateExpiration)}</div></td>
                    <td style={{ ...DROITE, fontWeight: 700 }}>{francs(l.PrimeTtc)}</td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <button type="button" className="btn btn-primary" style={PETIT} onClick={() => navigate(cheminDevis(l.IdProduit, l.IdDevis))} title="Continuer la saisie puis confirmer l'avenant">
                        <RefreshCw size={13} /> Continuer
                      </button>{' '}
                      {l.IdContratBase && (
                        <button type="button" className="btn btn-secondary" style={PETIT} onClick={() => navigate(`/user/contracts/${l.IdContratBase}`)} title="Fiche de la police">
                          <Eye size={13} /> Police
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {!chargement && donnees && !donnees.Lignes.length && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>
              {etat === 'emis' ? 'Aucun avenant émis sur la période.' : 'Aucun avenant en préparation sur la période.'}
            </div>
          )}
          {chargement && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1rem' }}><Loader2 size={16} className="spin" /> Chargement…</div>
          )}
        </div>

        {donnees && donnees.Total > TAILLE && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem' }}>
            <span>{pluriel(donnees.Total, 'ligne', 'lignes')} - page {page} sur {pages}</span>
            <button type="button" className="btn btn-secondary" style={PETIT} disabled={page <= 1 || chargement} onClick={() => setPage((p) => p - 1)} aria-label="Page précédente">
              <ChevronLeft size={14} />
            </button>
            <button type="button" className="btn btn-secondary" style={PETIT} disabled={page >= pages || chargement} onClick={() => setPage((p) => p + 1)} aria-label="Page suivante">
              <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>

      {choix && <ChoixPolice onClose={() => setChoix(false)} />}
    </div>
  );
};

export default EndorsementPage;
