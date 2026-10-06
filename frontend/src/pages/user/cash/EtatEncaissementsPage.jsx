import React, { useEffect, useMemo, useState } from 'react';
import { FileSpreadsheet, FileText, ListChecks, Loader2, RefreshCw } from 'lucide-react';
import { financeApi, settingsApi } from '../../../api/endpoints';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { useToast } from '../../../context/ToastContext';
import { aujourdhui, dateFr, exporterEtatEncaissements, fcfa, messageErreurApi } from '../../../utils/financeUtils';
import { trierParLibelle } from '../../../utils/sortUtils';

// État récapitulatif des encaissements : montant, mode, référence et statut de chaque quittance
// encaissée, par compagnie (GET /api/finance/encaissements/). Statut : à reverser, reversé
// (partiellement ou en entier) à la compagnie, annulé, chèque impayé, repris d'URANUS. Un
// décaissement (prime mal affectée) est compté en négatif et déduit du reste à reverser de sa quittance.
const COULEURS = { A_REVERSER: 'amber', PARTIEL: 'amber', REVERSE: 'emerald', ANNULE: 'rose', IMPAYE: 'rose', DECAISSEMENT: 'rose', DEDUIT: 'slate', REPRIS: 'slate' };
const STATUTS = [
  ['', 'Tous les statuts'], ['A_REVERSER', 'À reverser'], ['PARTIEL', 'Partiellement reversé'], ['REVERSE', 'Reversé à la compagnie'],
  ['DECAISSEMENT', 'Décaissement (déduit)'], ['DEDUIT', 'Couvert par un décaissement'],
  ['ANNULE', 'Annulé'], ['IMPAYE', 'Chèque impayé'], ['REPRIS', "Repris d'URANUS"],
];

const Carte = ({ libelle, valeur, detail, couleur = 'var(--text-primary)' }) => (
  <div className="glass-panel" style={{ padding: '1rem 1.1rem' }}>
    <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>{libelle}</div>
    <div style={{ fontSize: '1.3rem', fontWeight: 900, color: couleur, marginTop: '0.2rem' }}>{valeur}</div>
    {detail && <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>{detail}</div>}
  </div>
);

export const EtatEncaissementsPage = () => {
  const { error: toastError } = useToast();
  const [compagnies, setCompagnies] = useState([]);
  const [modes, setModes] = useState([]);
  const [filtres, setFiltres] = useState({ du: `${new Date().getFullYear()}-01-01`, au: aujourdhui(), compagnie: '', mode: '', statut: '' });
  const [etat, setEtat] = useState(null);
  const [chargement, setChargement] = useState(false);

  useEffect(() => {
    settingsApi.getCompanies().then((l) => setCompagnies(Array.isArray(l) ? l : [])).catch(() => {});
    settingsApi.getModesEncaissement().then((l) => setModes(Array.isArray(l) ? l : [])).catch(() => {});
  }, []);

  const charger = () => {
    setChargement(true);
    const params = Object.fromEntries(Object.entries(filtres).filter(([, v]) => v !== ''));
    financeApi.etatEncaissements(params)
      .then(setEtat)
      .catch((err) => toastError(`État des encaissements indisponible : ${messageErreurApi(err)}`))
      .finally(() => setChargement(false));
  };
  useEffect(charger, []); // eslint-disable-line react-hooks/exhaustive-deps

  const libelleCompagnie = useMemo(
    () => compagnies.find((c) => String(c.IdCompagnie ?? c.id) === String(filtres.compagnie))?.RaisonSociale || '',
    [compagnies, filtres.compagnie],
  );
  const champ = (cle) => (e) => setFiltres((f) => ({ ...f, [cle]: e.target.value }));
  const exporter = (format) => etat && exporterEtatEncaissements(etat, { libelleCompagnie }, format);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', paddingBottom: '2rem' }}>
      <div>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', margin: 0 }}>
          <ListChecks size={26} style={{ color: 'var(--primary-500)' }} /> État des encaissements
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0.3rem 0 0' }}>
          Chaque quittance encaissée avec son montant, son mode de règlement, sa référence et son statut, par compagnie.
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '1rem 1.25rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 170px), 1fr))', gap: '0.75rem', alignItems: 'end' }}>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label" htmlFor="ee-du">Du</label>
          <input id="ee-du" type="date" className="form-control" value={filtres.du} onChange={champ('du')} />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label" htmlFor="ee-au">Au</label>
          <input id="ee-au" type="date" className="form-control" value={filtres.au} onChange={champ('au')} />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label" htmlFor="ee-cie">Compagnie</label>
          <select id="ee-cie" className="form-control" value={filtres.compagnie} onChange={champ('compagnie')}>
            <option value="">Toutes les compagnies</option>
            {trierParLibelle(compagnies, (c) => c.RaisonSociale).map((c) => (
              <option key={c.IdCompagnie ?? c.id} value={c.IdCompagnie ?? c.id}>{c.RaisonSociale}</option>
            ))}
          </select>
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label" htmlFor="ee-mode">Mode</label>
          <select id="ee-mode" className="form-control" value={filtres.mode} onChange={champ('mode')}>
            <option value="">Tous les modes</option>
            {modes.map((m) => <option key={m.idmodeencaissement} value={m.idmodeencaissement}>{m.libellemodepaiement}</option>)}
          </select>
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label" htmlFor="ee-statut">Statut</label>
          <select id="ee-statut" className="form-control" value={filtres.statut} onChange={champ('statut')}>
            {STATUTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-primary" onClick={charger} disabled={chargement} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {chargement ? <Loader2 size={15} className="spin" /> : <RefreshCw size={15} />} Afficher
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => exporter('excel')} disabled={!etat} title="Exporter en Excel"><FileSpreadsheet size={15} /></button>
          <button type="button" className="btn btn-secondary" onClick={() => exporter('pdf')} disabled={!etat} title="Imprimer / PDF"><FileText size={15} /></button>
        </div>
      </div>

      {etat && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', gap: '0.75rem' }}>
            <Carte libelle="Montant encaissé net" valeur={`${fcfa(etat.Total.Montant)} F`} detail={`${etat.Total.Nombre} ligne(s), décaissements déduits, hors annulés et impayés`} />
            <Carte libelle="Reversé aux compagnies" valeur={`${fcfa(etat.Total.Reverse)} F`} couleur="var(--accent-emerald)" />
            <Carte libelle="Reste à reverser" valeur={`${fcfa(etat.Total.ResteAReverser)} F`} couleur="var(--accent-amber)" detail={`Encaissements depuis le ${dateFr(etat.DebutReversements)}`} />
            {(etat.ParStatut || []).filter((s) => ['DECAISSEMENT', 'ANNULE', 'IMPAYE'].includes(s.Statut)).map((s) => (
              <Carte key={s.Statut} libelle={s.Libelle} valeur={`${fcfa(s.Montant)} F`} couleur="var(--accent-rose)" detail={`${s.Nombre} ligne(s)`} />
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', gap: '0.75rem' }}>
            {[['Par mode de règlement', etat.ParMode], ['Par compagnie', etat.ParCompagnie]].map(([titre, groupes]) => (
              <div key={titre} className="glass-panel" style={{ padding: '1rem 1.1rem' }}>
                <div style={{ fontWeight: 800, marginBottom: '0.5rem' }}>{titre}</div>
                <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>{titre === 'Par compagnie' ? 'Compagnie' : 'Mode'}</th><th style={{ textAlign: 'right' }}>Lignes</th><th style={{ textAlign: 'right' }}>Encaissé</th><th style={{ textAlign: 'right' }}>Reversé</th></tr></thead>
                  <tbody>
                    {groupes.map((g) => (
                      <tr key={g.Libelle}><td>{g.Libelle}</td><td style={{ textAlign: 'right' }}>{g.Nombre}</td><td style={{ textAlign: 'right', fontWeight: 700 }}>{fcfa(g.Montant)}</td><td style={{ textAlign: 'right' }}>{fcfa(g.Reverse)}</td></tr>
                    ))}
                    {!groupes.length && <tr><td colSpan={4} style={{ color: 'var(--text-muted)' }}>Aucun encaissement.</td></tr>}
                  </tbody>
                </table>
                </div>
              </div>
            ))}
          </div>

          <div className="glass-panel" style={{ padding: '1rem 1.1rem' }}>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th><th>N° pièce</th><th>Compagnie</th><th>Client</th><th>Branche</th><th>Quittance</th>
                    <th>Mode</th><th>Référence</th><th style={{ textAlign: 'right' }}>Montant</th><th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {etat.Lignes.map((l) => (
                    <tr key={l.IdDetailEncaissement}>
                      <td>{dateFr(l.DateEncaissement)}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{l.NumeroPiece}</td>
                      <td>{l.Compagnie}</td>
                      <td>{l.Client}</td>
                      <td>{l.Branche}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{l.NumeroQuittance}</td>
                      <td>{l.Mode}</td>
                      <td>{[l.Reference, l.Banque].filter(Boolean).join(' — ') || '—'}</td>
                      <td style={{ textAlign: 'right', fontWeight: 700, color: l.Montant < 0 ? 'var(--accent-rose)' : undefined }}>{fcfa(l.Montant)}</td>
                      <td title={l.MotifAnnulation || undefined} style={{ whiteSpace: 'nowrap' }}><StatusBadge label={l.LibelleStatut} color={COULEURS[l.Statut]} /></td>
                    </tr>
                  ))}
                  {!etat.Lignes.length && (
                    <tr><td colSpan={10} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>Aucun encaissement pour ces critères.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default EtatEncaissementsPage;
