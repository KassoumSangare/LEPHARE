import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertTriangle, CheckCircle2, ChevronDown, History, ListChecks, Loader2, PencilLine, RefreshCw, ScrollText, Wrench,
} from 'lucide-react';
import { correctionsApi } from '../../../api/endpoints';
import { CorrectionEncaissement } from '../../../components/cash/CorrectionEncaissement';
import { useToast } from '../../../context/ToastContext';
import { aLeDroit } from '../../../utils/droits';
import { saisirTexte } from '../../../utils/dialogue';
import { messageErreurApi } from '../../../utils/financeUtils';
import { CATALOGUE } from '../../../utils/corrections';

/* =========================================================================
   CENTRE DES CORRECTIONS (Administration > Corrections, production/corrections.py)
   - À corriger : erreurs de saisie probables trouvées dans les données, chacune avec son bouton de correction ;
   - Erreurs et outils : pour chaque erreur qu'un utilisateur peut commettre, l'écran qui la corrige ;
   - Journal : corrections faites, avec leur auteur et leur motif (droit « Consulter le journal d'audit »).
   ========================================================================= */

const dateHeure = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '');

const LigneAnomalie = ({ anomalie, ligne, onAction, enCours }) => {
  const permis = aLeDroit(anomalie.Droit);
  const actions = {
    clients_doublons: [{ libelle: 'Comparer et fusionner', action: 'fusion' }],
    clients_homonymes: [{ libelle: 'Comparer', action: 'fusion' }],
    encaissements_doublons: [{ libelle: 'Corriger', action: 'encaissement' }],
    reglements_sans_reference: [{ libelle: 'Corriger', action: 'encaissement' }],
    quittances_trop_percues: [{ libelle: 'Voir les règlements', action: 'reglements' }],
    cheques_a_rapprocher: [{ libelle: 'Recalculer le solde', action: 'solde' }],
    cheques_doublons: [{ libelle: 'Portefeuille', action: 'portefeuille' }],
    contrats_desaccord: [{ libelle: 'Réaligner', action: 'realigner' }, { libelle: 'Ouvrir', action: 'contrat', secondaire: true }],
    contrats_periode: [{ libelle: 'Corriger', action: 'contrat' }],
  }[anomalie.Code] || [];
  return (
    <li className="corr-ligne">
      <div>
        <strong>{ligne.Libelle}</strong>
        <span>{ligne.Detail}</span>
      </div>
      <div className="corr-ligne-actions">
        {permis ? actions.map((a) => (
          <button key={a.action} type="button" className={`btn ${a.secondaire ? 'btn-secondary' : 'btn-primary'}`} disabled={enCours}
            onClick={() => onAction(a.action, anomalie, ligne)}>
            {a.libelle}
          </button>
        )) : <span className="corr-muet">Droit requis : {anomalie.Droit}</span>}
      </div>
    </li>
  );
};

export const CentreCorrectionsPage = () => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();
  const [onglet, setOnglet] = useState('anomalies');
  const [anomalies, setAnomalies] = useState(null);
  const [erreur, setErreur] = useState('');
  const [ouvertes, setOuvertes] = useState({});
  const [aCorriger, setACorriger] = useState(null);
  const [enCours, setEnCours] = useState(false);
  const [journal, setJournal] = useState(null);
  const [pageJournal, setPageJournal] = useState(1);
  const voirJournal = aLeDroit('audit.view');

  const charger = () => {
    setErreur('');
    correctionsApi.anomalies()
      .then((r) => {
        setAnomalies(r.Anomalies || []);
        setOuvertes((o) => (Object.keys(o).length ? o : Object.fromEntries((r.Anomalies || []).filter((a) => a.Nombre).slice(0, 1).map((a) => [a.Code, true]))));
      })
      .catch((e) => setErreur(messageErreurApi(e)));
  };
  useEffect(charger, []);
  useEffect(() => {
    if (onglet !== 'journal' || !voirJournal) return;
    setJournal(null);
    correctionsApi.journal(pageJournal).then(setJournal).catch((e) => toastError(messageErreurApi(e)));
  }, [onglet, pageJournal]); // eslint-disable-line react-hooks/exhaustive-deps

  const total = useMemo(() => (anomalies || []).reduce((t, a) => t + (Number(a.Nombre) || 0), 0), [anomalies]);

  const avecMotif = async (titre, message, appel) => {
    const motif = await saisirTexte({ titre, message, placeholder: 'Motif de la correction', minimum: 5, confirmer: 'Corriger', ton: 'attention' });
    if (!motif) return;
    setEnCours(true);
    try {
      const r = await appel(motif.trim());
      success(r?.Message || 'Correction enregistrée.');
      charger();
    } catch (e) {
      toastError(messageErreurApi(e));
    } finally {
      setEnCours(false);
    }
  };

  const agir = (action, anomalie, ligne) => {
    if (action === 'fusion') navigate(`/admin/corrections/clients?garder=${ligne.Garder}&fusionner=${ligne.Fusionner}`);
    else if (action === 'encaissement') setACorriger(ligne.IdEncaissement);
    else if (action === 'reglements') navigate(`/admin/corrections/encaissements?q=${encodeURIComponent(ligne.Quittance)}`);
    else if (action === 'portefeuille') navigate('/user/cheques');
    else if (action === 'contrat') navigate(`/admin/contracts/edit?contrat=${ligne.IdContrat}`);
    else if (action === 'solde') {
      avecMotif('Recalculer le solde du chèque', `${ligne.Libelle} : ${ligne.Detail}.`, (motif) => correctionsApi.recalculerSoldeCheque(ligne.IdCheque, motif));
    } else if (action === 'realigner') {
      avecMotif('Réaligner la quittance et le devis', `${ligne.Libelle} : la quittance et le devis reprennent le souscripteur, la compagnie et le n° de police du contrat.`,
        (motif) => correctionsApi.realignerContrat(ligne.IdContrat, motif));
    }
  };

  return (
    <div className="corr-page">
      <header className="corr-entete">
        <span className="corr-entete-icone" aria-hidden="true"><Wrench size={22} /></span>
        <div>
          <h1 className="title-xl">Centre des corrections</h1>
          <p>Les erreurs de saisie repérées dans les données et l’outil qui corrige chacune, avec motif et trace au journal.</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={charger} disabled={enCours}><RefreshCw size={15} /> Actualiser</button>
      </header>

      <div className="cs-onglets-boutons" role="tablist" aria-label="Centre des corrections" style={{ alignSelf: 'flex-start' }}>
        <button type="button" role="tab" aria-selected={onglet === 'anomalies'} className={`cs-onglet${onglet === 'anomalies' ? ' actif' : ''}`} onClick={() => setOnglet('anomalies')}>
          <AlertTriangle size={15} aria-hidden="true" /> À corriger{anomalies ? ` (${total})` : ''}
        </button>
        <button type="button" role="tab" aria-selected={onglet === 'catalogue'} className={`cs-onglet${onglet === 'catalogue' ? ' actif' : ''}`} onClick={() => setOnglet('catalogue')}>
          <ListChecks size={15} aria-hidden="true" /> Erreurs et outils
        </button>
        {voirJournal && (
          <button type="button" role="tab" aria-selected={onglet === 'journal'} className={`cs-onglet${onglet === 'journal' ? ' actif' : ''}`} onClick={() => setOnglet('journal')}>
            <History size={15} aria-hidden="true" /> Journal
          </button>
        )}
      </div>

      {onglet === 'anomalies' && (
        <section className="cs-contenu corr-anomalies" aria-label="Erreurs à corriger">
          {erreur && <p className="corr-erreur"><AlertTriangle size={15} /> {erreur}</p>}
          {!anomalies && !erreur && <p className="corr-muet"><Loader2 className="spin" size={15} /> Recherche des erreurs…</p>}
          {anomalies && !anomalies.length && <p className="corr-muet">Aucun contrôle n’est accessible avec vos droits.</p>}
          {(anomalies || []).map((a) => {
            const ouverte = ouvertes[a.Code] && a.Nombre > 0;
            return (
              <article key={a.Code} className={`corr-carte${a.Nombre ? ' a-corriger' : ' juste'}`}>
                <button type="button" className="corr-carte-tete" aria-expanded={Boolean(ouverte)} disabled={!a.Nombre}
                  onClick={() => setOuvertes((o) => ({ ...o, [a.Code]: !o[a.Code] }))}>
                  <span className="corr-domaine">{a.Domaine}</span>
                  <span className="corr-carte-titre">
                    <strong>{a.Titre}</strong>
                    <span>{a.Texte}</span>
                  </span>
                  {a.Nombre === null ? <span className="corr-compte erreur">?</span>
                    : a.Nombre ? <span className="corr-compte">{a.Nombre}</span>
                      : <span className="corr-compte juste"><CheckCircle2 size={16} /> Rien à corriger</span>}
                  {a.Nombre > 0 && <ChevronDown size={16} className="corr-chevron" aria-hidden="true" />}
                </button>
                {ouverte && (
                  <ul className="corr-lignes">
                    {a.Lignes.map((l, i) => <LigneAnomalie key={`${a.Code}-${i}`} anomalie={a} ligne={l} onAction={agir} enCours={enCours} />)}
                    {a.Nombre > a.Lignes.length && <li className="corr-muet">Les {a.Lignes.length} premiers sur {a.Nombre}.</li>}
                  </ul>
                )}
              </article>
            );
          })}
        </section>
      )}

      {onglet === 'catalogue' && (
        <section className="cs-contenu corr-catalogue" aria-label="Erreurs et outils">
          {CATALOGUE.map((d) => (
            <div key={d.domaine} className="corr-groupe">
              <h2>{d.domaine}</h2>
              <ul>
                {d.cas.map((c) => (
                  <li key={c.erreur} className="corr-cas">
                    <div>
                      <strong>{c.erreur}</strong>
                      <span>{c.correction}</span>
                    </div>
                    {aLeDroit(c.droit)
                      ? (c.onglet
                        ? <button type="button" className="btn btn-secondary" onClick={() => setOnglet(c.onglet)}><PencilLine size={14} /> {c.outil}</button>
                        : <Link to={c.lien} className="btn btn-secondary"><PencilLine size={14} /> {c.outil}</Link>)
                      : <span className="corr-muet">Droit requis : {c.droit}</span>}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}

      {onglet === 'journal' && voirJournal && (
        <section className="cs-contenu glass-panel corr-journal" aria-label="Journal des corrections">
          {!journal ? <p className="corr-muet"><Loader2 className="spin" size={15} /> Chargement…</p> : (
            <>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>Date</th><th>Correction</th><th>Par</th><th>Objet</th><th>Motif</th></tr></thead>
                  <tbody>
                    {journal.Lignes.map((l) => (
                      <tr key={l.Id}>
                        <td style={{ whiteSpace: 'nowrap' }}>{dateHeure(l.Date)}</td>
                        <td><strong>{l.Action}</strong><div className="corr-muet">{l.Description}</div></td>
                        <td>{l.Auteur}</td>
                        <td>{l.Objet}</td>
                        <td>{l.Motif || '-'}</td>
                      </tr>
                    ))}
                    {!journal.Lignes.length && <tr><td colSpan={5} className="corr-muet">Aucune correction enregistrée.</td></tr>}
                  </tbody>
                </table>
              </div>
              <div className="corr-pagination">
                <span className="corr-muet"><ScrollText size={14} /> {journal.Total} correction{journal.Total > 1 ? 's' : ''}</span>
                <button type="button" className="btn btn-secondary" disabled={pageJournal <= 1} onClick={() => setPageJournal((p) => p - 1)}>Précédentes</button>
                <button type="button" className="btn btn-secondary" disabled={pageJournal * journal.Taille >= journal.Total} onClick={() => setPageJournal((p) => p + 1)}>Suivantes</button>
              </div>
            </>
          )}
        </section>
      )}

      {aCorriger && (
        <CorrectionEncaissement idEncaissement={aCorriger} onClose={() => setACorriger(null)} onCorrige={charger} />
      )}
    </div>
  );
};

export default CentreCorrectionsPage;
