import React, { useEffect, useMemo, useState } from 'react';
import {
  Building2, CalendarCheck, CheckCircle2, FileSpreadsheet, FileText, Loader2, Mail, Pencil, RefreshCw, Search, Send, ShieldCheck,
  Table2, Wallet, X, XCircle,
} from 'lucide-react';
import { financeApi, settingsApi } from '../../../api/endpoints';
import { Modal } from '../../../components/common/Modal';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { useToast } from '../../../context/ToastContext';
import { confirmer, saisirTexte } from '../../../utils/dialogue';
import {
  aujourdhui, correspondRecherche as correspond, dateFr, fcfa, messageErreurApi, recentsDabord,
} from '../../../utils/financeUtils';
import { imprimerBordereau, imprimerCourrier } from '../../../utils/impressionsFinance';
import { nomCabinet } from '../../../utils/parametrage';
import { trierParLibelle } from '../../../utils/sortUtils';

// Reversements aux compagnies au modèle d'OREOLE (production/views_bordereaux.py) :
// - les primes encaissées sont transmises par bordereau numéroté dans la suite d'OREOLE ; le titre dépend de
//   l'ordre du règlement : à l'ordre de la compagnie, chèque du client transmis tel quel (BORDEREAU DE RECLAMATION
//   DE COMMISSION, « Direct ») ; encaissé par le cabinet, reversé par son chèque (BORDEREAU DE REVERSEMENT DE
//   PRIME, prime entière, Code CIMA) ; un bordereau porte un ou plusieurs clients ;
// - chaque bordereau a son courrier de règlement de prime ; la date de décharge (cachet de la compagnie) se saisit
//   au retour ;
// - tableau de reversement (COMMI-MOIS) par compagnie : à l'écran et en Excel, une feuille par état.
const ID_NSIA = 1;
const MODES_PAIEMENT_CABINET = ['CHQ', 'VIR', 'TRT', 'ESP'];
const NATURES = {
  RECLAMATION: { libelle: 'Réclamation de commission', court: 'Direct', couleur: 'purple' },
  REVERSEMENT: { libelle: 'Reversement de prime', court: 'Reversement', couleur: 'blue' },
};
const FEUILLES = [
  ['TOUT', 'Tableau complet'], ['SOLDEES', 'Primes soldées'], ['NON_SOLDEES', 'Primes non soldées (arriérés)'],
  ['COMMISSIONS_PERCUES', 'Commissions perçues'], ['COMMISSIONS_NON_PERCUES', 'Commissions non perçues'],
];
const moisFr = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

const Onglet = ({ actif, onClick, icone: Icone, children }) => (
  <button type="button" role="tab" aria-selected={actif} className={`btn ${actif ? 'btn-primary' : 'btn-secondary'}`}
    onClick={onClick} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
    <Icone size={15} /> {children}
  </button>
);

const BadgeNature = ({ nature }) => <StatusBadge label={NATURES[nature]?.libelle || nature} color={NATURES[nature]?.couleur} />;

// Numéros de la compagnie (colonnes « N°Police » et « Avt » du bordereau), complétés ici s'ils manquent au contrat
const PoliceCompagnie = ({ ligne, onEnregistre }) => {
  const { error: toastError } = useToast();
  const [edition, setEdition] = useState(false);
  const [police, setPolice] = useState(ligne.PoliceCompagnie);
  const [avenant, setAvenant] = useState(ligne.AvenantCompagnie);
  const [envoi, setEnvoi] = useState(false);
  if (!ligne.IdContrat) return <span>{ligne.NumeroPolice}</span>;
  if (!edition) {
    return (
      <button type="button" className="btn-lien" onClick={() => setEdition(true)} title="Police et avenant de la compagnie"
        style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: ligne.PoliceCompagnie ? 'inherit' : 'var(--accent-amber, #d97706)', textAlign: 'left', font: 'inherit' }}>
        {ligne.PoliceCompagnie ? `${ligne.PoliceCompagnie}${ligne.AvenantCompagnie ? ` / avt ${ligne.AvenantCompagnie}` : ''}` : 'Police compagnie à saisir'}
        <Pencil size={11} style={{ marginLeft: 4, verticalAlign: 'middle', opacity: 0.6 }} />
      </button>
    );
  }
  const enregistrer = async () => {
    setEnvoi(true);
    try {
      const r = await financeApi.policeCompagnie(ligne.IdContrat, { NumeroPoliceCompagnie: police, NumeroAvenantCompagnie: avenant });
      onEnregistre(ligne.IdContrat, r.PoliceCompagnie, r.AvenantCompagnie);
      setEdition(false);
    } catch (err) {
      toastError(`Police non enregistrée : ${messageErreurApi(err)}`);
    } finally {
      setEnvoi(false);
    }
  };
  return (
    <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
      <input className="form-control" style={{ padding: '0.2rem 0.35rem', width: 120 }} placeholder="N° police" value={police} maxLength={60} onChange={(e) => setPolice(e.target.value)} />
      <input className="form-control" style={{ padding: '0.2rem 0.35rem', width: 52 }} placeholder="Avt" value={avenant} maxLength={20} onChange={(e) => setAvenant(e.target.value)} />
      <button type="button" className="btn btn-primary" style={{ padding: '0.2rem 0.45rem' }} disabled={envoi} onClick={enregistrer} aria-label="Enregistrer la police">
        {envoi ? <Loader2 size={13} className="spin" /> : <CheckCircle2 size={13} />}
      </button>
    </span>
  );
};

const PaiementCabinet = ({ modes, banques, valeur, onChange }) => {
  const mode = modes.find((m) => String(m.idmodeencaissement) === String(valeur.IdMode));
  const abrege = String(mode?.abregereglement || '').trim().toUpperCase();
  const champ = (cle) => (e) => onChange({ ...valeur, [cle]: e.target.value });
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.7rem' }}>
      <div className="form-group" style={{ margin: 0 }}>
        <label className="form-label" htmlFor="pc-mode">Paiement du cabinet</label>
        <select id="pc-mode" className="form-control" value={valeur.IdMode} onChange={champ('IdMode')}>
          <option value="">Plus tard</option>
          {modes.map((m) => <option key={m.idmodeencaissement} value={m.idmodeencaissement}>{m.libellemodepaiement}</option>)}
        </select>
      </div>
      {mode?.banque && (
        <>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" htmlFor="pc-banque">Banque du cabinet</label>
            <select id="pc-banque" className="form-control" required value={valeur.IdBanque} onChange={champ('IdBanque')}>
              <option value="">— Choisir —</option>
              {banques.map((b) => <option key={b.idbanque} value={b.idbanque}>{b.libelle}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" htmlFor="pc-num">{abrege === 'VIR' ? 'N° de virement' : 'N° du chèque'}</label>
            <input id="pc-num" className="form-control" maxLength={20} required={abrege === 'CHQ'} value={valeur.NumeroCheque} onChange={champ('NumeroCheque')} />
          </div>
        </>
      )}
      {valeur.IdMode && (
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label" htmlFor="pc-date">Date du paiement</label>
          <input id="pc-date" type="date" className="form-control" value={valeur.DatePaiement} onChange={champ('DatePaiement')} />
        </div>
      )}
    </div>
  );
};

const paiementVide = () => ({ IdMode: '', IdBanque: '', NumeroCheque: '', DatePaiement: aujourdhui() });

const BordereauModal = ({ bordereau, modes, banques, onClose, onChange }) => {
  const { success, error: toastError, warning } = useToast();
  const [decharge, setDecharge] = useState('');
  const [paiement, setPaiement] = useState(paiementVide());
  const [envoi, setEnvoi] = useState(false);
  useEffect(() => {
    setDecharge(bordereau?.DateDecharge || '');
    setPaiement(paiementVide());
  }, [bordereau]);
  if (!bordereau) return null;
  const b = bordereau;
  const aPayer = !b.Direct && !b.Valide;

  const action = async (fn, message) => {
    setEnvoi(true);
    try {
      const resultat = await fn();
      if (message) success(message);
      onChange(resultat);
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };
  const payer = () => action(async () => {
    await financeApi.validerReversement(b.IdReversement, {
      IdMode: paiement.IdMode, IdBanque: paiement.IdBanque, NumeroCheque: paiement.NumeroCheque, DateReversement: paiement.DatePaiement,
    });
    return financeApi.bordereau(b.IdReversement);
  }, `Paiement du bordereau N° ${b.Numero} enregistré.`);
  const enregistrerDecharge = () => action(() => financeApi.dechargeBordereau(b.IdReversement, decharge || null), 'Date de décharge enregistrée.');
  const annuler = async () => {
    const motif = await saisirTexte({
      titre: `Annuler le bordereau N° ${b.Numero || b.NumeroReversement}`,
      message: 'Les primes redeviennent à transmettre. Indiquez le motif (au moins 5 caractères).',
      minimum: 5, maximum: 255, confirmer: 'Annuler le bordereau', ton: 'danger',
    });
    if (!motif) return;
    action(async () => { await financeApi.annulerBordereau(b.IdReversement, motif); return null; }, `Bordereau N° ${b.Numero || ''} annulé.`);
  };
  const courrier = () => {
    if (b.Courrier?.PaiementManquant) warning('Le paiement du cabinet n\'est pas encore saisi : le courrier ne cite pas de chèque.');
    imprimerCourrier(b);
  };

  return (
    <Modal isOpen onClose={onClose} size="large"
      title={`${b.Titre} N° ${b.Numero || b.NumeroReversement}`}
      subtitle={`${b.NomBordereau || b.Compagnie} — du ${dateFr(b.DateBordereau)} — ${b.LibelleStatut}`}>
      <div style={{ display: 'flex', gap: '1.25rem', flexWrap: 'wrap', fontSize: '0.88rem', marginBottom: '0.9rem' }}>
        <span>Montant à reverser : <strong>{fcfa(b.MontantAReverser)} F</strong></span>
        <span>Quittances : <strong>{b.Lignes.length}</strong></span>
        <span>Commission réclamée : <strong>{fcfa(b.Totaux.Commission + b.Totaux.AccCourtier)} F</strong> (dont acc. courtier {fcfa(b.Totaux.AccCourtier)} F)</span>
        {b.Cheques.map((c) => <span key={c.Texte}>{c.Texte}</span>)}
      </div>
      <div className="table-wrapper" style={{ maxHeight: '45vh', overflow: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Nom du client</th><th>Assurance</th><th>N° Police</th><th>Avt</th><th>Effet</th><th>Expiration</th>
              <th style={{ textAlign: 'right' }}>Prime HT</th><th style={{ textAlign: 'right' }}>Prime TTC</th><th style={{ textAlign: 'right' }}>Encaissement</th>
              <th style={{ textAlign: 'right' }}>Acc. Courtier</th><th style={{ textAlign: 'right' }}>Taux</th><th style={{ textAlign: 'right' }}>Commission</th>
              <th style={{ textAlign: 'right' }}>Montant reversé</th>
            </tr>
          </thead>
          <tbody>
            {b.Blocs.map((bloc) => (
              <React.Fragment key={bloc.Titre}>
                <tr><td colSpan={13} style={{ fontWeight: 700, background: 'var(--bg-surface-elevated)' }}>
                  {bloc.Titre}{!bloc.Soldees && ` — reste dû par les clients : ${fcfa(bloc.Totaux.ResteDu)} F`}
                </td></tr>
                {bloc.Lignes.map((l) => (
                  <tr key={l.NumeroQuittance}>
                    <td>{l.Client}<div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{l.LibelleStatutPaiement}{!l.Soldee && ` — reste dû ${fcfa(l.ResteDu)} F`}</div></td>
                    <td>{l.Assurance}</td><td>{l.PoliceCompagnie || <span style={{ color: 'var(--accent-amber, #d97706)' }}>{l.NumeroPolice}</span>}</td><td>{l.Avenant}</td>
                    <td>{dateFr(l.DateEffet)}</td><td>{dateFr(l.DateExpiration)}</td>
                    <td style={{ textAlign: 'right' }}>{fcfa(l.PrimeHT)}</td><td style={{ textAlign: 'right' }}>{fcfa(l.PrimeTtc)}</td>
                    <td style={{ textAlign: 'right' }}>{fcfa(l.Encaissement)}</td><td style={{ textAlign: 'right' }}>{fcfa(l.AccCourtier)}</td>
                    <td style={{ textAlign: 'right' }}>{l.Taux}%</td><td style={{ textAlign: 'right' }}>{fcfa(l.Commission)}</td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>{b.Direct ? 'Direct' : fcfa(l.MontantReverse)}</td>
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
      {b.Lignes.some((l) => !l.PoliceCompagnie) && (
        <p style={{ fontSize: '0.8rem', color: 'var(--accent-amber, #d97706)', margin: '0.5rem 0 0' }}>
          Police de la compagnie manquante : le numéro LE PHARE est imprimé à la place (complétez-la dans « Primes à transmettre » avant l'émission).
        </p>
      )}

      {aPayer && (
        <div className="glass-panel" style={{ padding: '0.8rem 1rem', marginTop: '1rem' }}>
          <PaiementCabinet modes={modes} banques={banques} valeur={paiement} onChange={setPaiement} />
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.6rem' }}>
            <button type="button" className="btn btn-primary" disabled={envoi || !paiement.IdMode} onClick={payer} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Wallet size={15} /> Enregistrer le paiement du cabinet
            </button>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end', flexWrap: 'wrap', marginTop: '1rem' }}>
        {b.IdBordereau && (
          <>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" htmlFor="bd-decharge">Date de décharge (cachet de la compagnie)</label>
              <input id="bd-decharge" type="date" className="form-control" value={decharge || ''} onChange={(e) => setDecharge(e.target.value)} />
            </div>
            <button type="button" className="btn btn-secondary" disabled={envoi || (decharge || '') === (b.DateDecharge || '')} onClick={enregistrerDecharge} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <CalendarCheck size={15} /> Enregistrer
            </button>
          </>
        )}
        <span style={{ flex: 1 }} />
        <button type="button" className="btn btn-secondary" onClick={annuler} disabled={envoi} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-rose)' }}>
          <XCircle size={15} /> Annuler le bordereau
        </button>
        <button type="button" className="btn btn-secondary" onClick={courrier} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Mail size={15} /> Courrier
        </button>
        <button type="button" className="btn btn-primary" onClick={() => imprimerBordereau(b)} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <FileText size={15} /> Bordereau
        </button>
      </div>
    </Modal>
  );
};

const TableauReversement = ({ compagnie, nomCompagnie, recherche }) => {
  const { error: toastError } = useToast();
  const annee = new Date().getFullYear();
  const [du, setDu] = useState(`${annee}-01-01`);
  const [au, setAu] = useState(`${annee}-12-31`);
  const [feuille, setFeuille] = useState('TOUT');
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(false);
  const [export_, setExport] = useState(false);

  const charger = () => {
    if (!compagnie) return;
    setChargement(true);
    financeApi.tableauReversement({ compagnie, du, au, feuille })
      .then(setDonnees)
      .catch((err) => toastError(`Tableau indisponible : ${messageErreurApi(err)}`))
      .finally(() => setChargement(false));
  };
  useEffect(charger, [compagnie, du, au, feuille]); // eslint-disable-line react-hooks/exhaustive-deps

  const telecharger = async () => {
    setExport(true);
    try {
      await financeApi.telechargerTableauReversement({ compagnie, du, au },
        `TABLEAU DE REVERSEMENT ${donnees?.Compagnie || nomCompagnie} ${dateFr(du).replace(/\//g, '-')} au ${dateFr(au).replace(/\//g, '-')}.xlsx`);
    } catch (err) {
      toastError(`Export impossible : ${messageErreurApi(err)}`);
    } finally {
      setExport(false);
    }
  };

  // À l'écran : mois et quittances du plus récent au plus ancien (l'Excel garde l'ordre chronologique des tableaux
  // d'OREOLE) ; les reversements d'une même quittance restent dans l'ordre (1er acompte puis solde)
  const dernierCourrier = (l) => l.Reversements[l.Reversements.length - 1]?.DateCourrier;
  const visibles = useMemo(() => (donnees?.Lignes || [])
    .filter((l) => correspond(recherche, [
      l.Client, l.Souscripteur, l.NumeroQuittance, l.NumeroPolice, l.PoliceCompagnie, l.Branche, l.Observation, l.ChequesCommission,
      l.PrimeTtc, l.Encaissement, l.CommissionAPercevoir, dateFr(l.DateEffet),
      ...l.Reversements.flatMap((rv) => [rv.Numero, rv.Nature, dateFr(rv.DateCourrier), dateFr(rv.DateDecharge), rv.Montant]),
    ]))
    .sort(recentsDabord(dernierCourrier, (l) => l.IdQuittance)), [donnees, recherche]);
  const parMois = useMemo(() => {
    const groupes = new Map();
    visibles.forEach((l) => {
      if (!groupes.has(l.Mois)) groupes.set(l.Mois, []);
      groupes.get(l.Mois).push(l);
    });
    return [...groupes.entries()].sort(([a], [b]) => b.localeCompare(a));
  }, [visibles]);
  const somme = (ls, cle) => ls.reduce((t, l) => t + (Number(l[cle]) || 0), 0);
  const d = { textAlign: 'right', whiteSpace: 'nowrap' };

  return (
    <div className="glass-panel" style={{ padding: '1rem 1.1rem' }}>
      <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: '0.9rem' }}>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label" htmlFor="tr-du">Du</label>
          <input id="tr-du" type="date" className="form-control" value={du} onChange={(e) => setDu(e.target.value)} />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label" htmlFor="tr-au">Au</label>
          <input id="tr-au" type="date" className="form-control" value={au} onChange={(e) => setAu(e.target.value)} />
        </div>
        <div className="form-group" style={{ margin: 0, minWidth: 230 }}>
          <label className="form-label" htmlFor="tr-feuille">État</label>
          <select id="tr-feuille" className="form-control" value={feuille} onChange={(e) => setFeuille(e.target.value)}>
            {FEUILLES.map(([code, libelle]) => <option key={code} value={code}>{libelle}</option>)}
          </select>
        </div>
        <span style={{ flex: 1 }} />
        <button type="button" className="btn btn-primary" onClick={telecharger} disabled={export_ || !compagnie} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          {export_ ? <Loader2 size={15} className="spin" /> : <FileSpreadsheet size={15} />} Excel (une feuille par état)
        </button>
      </div>
      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0 0 0.7rem' }}>
        Une ligne par quittance, au mois de son dernier bordereau ; commission à percevoir = Prime HT × taux + acc. courtier ;
        solde = à percevoir − perçue ; observation = reste à encaisser (émissions − encaissements).
      </p>
      <div className="table-wrapper" style={{ maxHeight: '62vh', overflow: 'auto' }}>
        <table className="data-table" style={{ fontSize: '0.78rem' }}>
          <thead>
            <tr>
              <th>Nom du client</th><th>Courrier</th><th>Décharge</th><th>N° bord.</th><th>Assurance</th><th>N° Police</th><th>Effet</th><th>Expiration</th>
              <th style={d}>Prime HT</th><th style={d}>Prime TTC</th><th style={d}>Encaissement</th><th style={d}>Montant reversé</th><th>Nature du reversement</th>
              <th style={d}>Acc. courtier</th><th style={d}>Taux</th><th style={d}>Comm. à percevoir</th><th style={d}>Perçue</th><th style={d}>Solde</th>
              <th>Chèque de commission</th><th>Observation</th>
            </tr>
          </thead>
          <tbody>
            {parMois.map(([mois, ls]) => (
              <React.Fragment key={mois}>
                <tr><td colSpan={20} style={{ fontWeight: 700, textTransform: 'capitalize', background: 'var(--bg-surface-elevated)' }}>{moisFr(mois)}</td></tr>
                {ls.map((l) => l.Reversements.map((rv, i) => (
                  <tr key={`${l.NumeroQuittance}-${rv.IdReversement}`}>
                    {i === 0 && <td rowSpan={l.Reversements.length}>{l.Client}</td>}
                    <td>{dateFr(rv.DateCourrier)}</td><td>{dateFr(rv.DateDecharge) || '—'}</td><td>{rv.Numero || '—'}</td>
                    {i === 0 && (
                      <>
                        <td rowSpan={l.Reversements.length}>{l.Branche}</td>
                        <td rowSpan={l.Reversements.length}>{l.PoliceCompagnie || l.NumeroPolice}</td>
                        <td rowSpan={l.Reversements.length}>{dateFr(l.DateEffet)}</td>
                        <td rowSpan={l.Reversements.length}>{dateFr(l.DateExpiration)}</td>
                        <td rowSpan={l.Reversements.length} style={d}>{fcfa(l.PrimeHT)}</td>
                        <td rowSpan={l.Reversements.length} style={d}>{fcfa(l.PrimeTtc)}</td>
                        <td rowSpan={l.Reversements.length} style={{ ...d, fontWeight: 700 }}>{fcfa(l.Encaissement)}</td>
                      </>
                    )}
                    <td style={d}>{fcfa(rv.Montant)}</td><td style={{ minWidth: 220 }}>{rv.Nature}</td>
                    {i === 0 && (
                      <>
                        <td rowSpan={l.Reversements.length} style={d}>{fcfa(l.AccCourtier)}</td>
                        <td rowSpan={l.Reversements.length} style={d}>{l.Taux}%</td>
                        <td rowSpan={l.Reversements.length} style={{ ...d, fontWeight: 700 }}>{fcfa(l.CommissionAPercevoir)}</td>
                        <td rowSpan={l.Reversements.length} style={d}>{fcfa(l.CommissionPercue)}</td>
                        <td rowSpan={l.Reversements.length} style={{ ...d, fontWeight: 700 }}>{fcfa(l.SoldeCommission)}</td>
                        <td rowSpan={l.Reversements.length} style={{ minWidth: 200 }}>{l.ChequesCommission}</td>
                        <td rowSpan={l.Reversements.length} style={{ minWidth: 160, color: l.Soldee ? 'inherit' : 'var(--accent-amber, #d97706)' }}>{l.Observation}</td>
                      </>
                    )}
                  </tr>
                )))}
                <tr style={{ fontWeight: 700 }}>
                  <td colSpan={8}>TOTAL {moisFr(mois)}</td>
                  <td style={d}>{fcfa(somme(ls, 'PrimeHT'))}</td><td style={d}>{fcfa(somme(ls, 'PrimeTtc'))}</td><td style={d}>{fcfa(somme(ls, 'Encaissement'))}</td>
                  <td style={d}>{fcfa(somme(ls, 'Encaissement'))}</td><td />
                  <td style={d}>{fcfa(somme(ls, 'AccCourtier'))}</td><td />
                  <td style={d}>{fcfa(somme(ls, 'CommissionAPercevoir'))}</td><td style={d}>{fcfa(somme(ls, 'CommissionPercue'))}</td>
                  <td style={d}>{fcfa(somme(ls, 'SoldeCommission'))}</td><td colSpan={2} />
                </tr>
              </React.Fragment>
            ))}
            {!parMois.length && (
              <tr><td colSpan={20} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>
                {chargement ? 'Chargement…' : (donnees?.Lignes?.length ? 'Aucune ligne ne correspond à la recherche.' : 'Aucune prime transmise sur cette période.')}
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
      {parMois.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <h3 style={{ fontSize: '0.9rem', margin: '0 0 0.4rem' }}>État récapitulatif</h3>
          <div className="table-wrapper">
            <table className="data-table" style={{ fontSize: '0.82rem' }}>
              <thead>
                <tr><th>Mois</th><th style={d}>Prime TTC</th><th style={d}>Encaissements</th><th style={d}>Reversements</th><th style={d}>Commission à percevoir</th><th style={d}>Commission perçue</th><th style={d}>Solde</th></tr>
              </thead>
              <tbody>
                {parMois.map(([mois, ls]) => (
                  <tr key={mois}>
                    <td style={{ textTransform: 'capitalize' }}>{moisFr(mois)}</td><td style={d}>{fcfa(somme(ls, 'PrimeTtc'))}</td><td style={d}>{fcfa(somme(ls, 'Encaissement'))}</td>
                    <td style={d}>{fcfa(somme(ls, 'Encaissement'))}</td><td style={d}>{fcfa(somme(ls, 'CommissionAPercevoir'))}</td>
                    <td style={d}>{fcfa(somme(ls, 'CommissionPercue'))}</td><td style={d}>{fcfa(somme(ls, 'SoldeCommission'))}</td>
                  </tr>
                ))}
                <tr style={{ fontWeight: 700 }}>
                  <td>TOTAL</td><td style={d}>{fcfa(somme(visibles, 'PrimeTtc'))}</td><td style={d}>{fcfa(somme(visibles, 'Encaissement'))}</td><td style={d}>{fcfa(somme(visibles, 'Encaissement'))}</td>
                  <td style={d}>{fcfa(somme(visibles, 'CommissionAPercevoir'))}</td><td style={d}>{fcfa(somme(visibles, 'CommissionPercue'))}</td><td style={d}>{fcfa(somme(visibles, 'SoldeCommission'))}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export const CompanyRemittancePage = () => {
  const { success, error: toastError, warning } = useToast();
  const [onglet, setOnglet] = useState('a_transmettre');
  const [compagnies, setCompagnies] = useState([]);
  const [modes, setModes] = useState([]);
  const [banques, setBanques] = useState([]);
  const [compagnie, setCompagnie] = useState(String(ID_NSIA));
  const [lignes, setLignes] = useState([]);
  const [prochainNumero, setProchainNumero] = useState('');
  const [selection, setSelection] = useState(new Set());
  const [dateBordereau, setDateBordereau] = useState(aujourdhui());
  const [numero, setNumero] = useState('');
  const [paiement, setPaiement] = useState(paiementVide());
  const [chargement, setChargement] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [bordereaux, setBordereaux] = useState([]);
  const [ouvert, setOuvert] = useState(null);
  const [recherche, setRecherche] = useState('');
  const [natureFiltre, setNatureFiltre] = useState('');

  useEffect(() => {
    settingsApi.getCompanies().then((l) => setCompagnies(Array.isArray(l) ? l : [])).catch(() => {});
    settingsApi.getBanques().then((l) => setBanques(Array.isArray(l) ? l : [])).catch(() => {});
    settingsApi.getModesEncaissement()
      .then((l) => setModes((Array.isArray(l) ? l : []).filter((m) => MODES_PAIEMENT_CABINET.includes(String(m.abregereglement || '').trim().toUpperCase())
        && !/compagnie|ppa/i.test(m.libellemodepaiement || ''))))
      .catch(() => {});
  }, []);

  const chargerLignes = () => {
    if (!compagnie) return;
    setChargement(true);
    financeApi.aTransmettre(compagnie)
      .then((r) => {
        setLignes(r.Lignes || []);
        setSelection(new Set());
        setProchainNumero(r.ProchainNumero);
        setNumero(String(r.ProchainNumero || ''));
      })
      .catch((err) => toastError(`Primes à transmettre indisponibles : ${messageErreurApi(err)}`))
      .finally(() => setChargement(false));
  };
  const chargerBordereaux = () => {
    financeApi.bordereaux(compagnie ? { compagnie } : {})
      .then((r) => setBordereaux(r.Bordereaux || []))
      .catch((err) => toastError(`Bordereaux indisponibles : ${messageErreurApi(err)}`));
  };
  useEffect(() => { chargerLignes(); chargerBordereaux(); }, [compagnie]); // eslint-disable-line react-hooks/exhaustive-deps

  const nomCompagnie = useMemo(() => compagnies.find((c) => String(c.IdCompagnie ?? c.id) === String(compagnie))?.RaisonSociale || '', [compagnies, compagnie]);
  const lignesVisibles = useMemo(() => lignes
    .filter((l) => !natureFiltre || l.Nature === natureFiltre)
    .filter((l) => correspond(recherche, [
      l.Client, l.NumeroQuittance, l.NumeroPolice, l.PoliceCompagnie, l.AvenantCompagnie, l.Branche, l.Reglement, l.Mode, l.Reference,
      l.Banque, l.NumeroPiece, l.LibelleStatutPaiement, NATURES[l.Nature]?.libelle, dateFr(l.DateEncaissement), l.PrimeTtc, l.ResteAReverser,
    ]))
    .sort(recentsDabord((l) => l.DateEncaissement, (l) => l.IdDetailEncaissement)), [lignes, recherche, natureFiltre]);
  const bordereauxVisibles = useMemo(() => bordereaux
    .filter((b) => !natureFiltre || b.Nature === natureFiltre)
    .filter((b) => correspond(recherche, [
      b.Numero, b.NumeroReversement, b.Clients, NATURES[b.Nature]?.libelle, b.LibelleStatut, b.Paiement, dateFr(b.DateBordereau),
      dateFr(b.DateDecharge), b.MontantAReverser, b.MontantReverse,
    ]))
    .sort(recentsDabord((b) => b.DateBordereau, (b) => (b.Numero || 0) * 100000 + b.IdReversement)), [bordereaux, recherche, natureFiltre]);
  const filtre = Boolean(recherche.trim() || natureFiltre);
  const cochees = lignes.filter((l) => selection.has(l.IdDetailEncaissement));
  const masquees = cochees.filter((l) => !lignesVisibles.includes(l)).length;
  const parNature = (nature) => cochees.filter((l) => l.Nature === nature);
  const aReverser = parNature('REVERSEMENT');
  const directes = parNature('RECLAMATION');
  const somme = (ls, cle) => ls.reduce((t, l) => t + (Number(l[cle]) || 0), 0);
  // « Tout cocher » porte sur les lignes affichées (résultat de la recherche)
  const toutCoche = lignesVisibles.length > 0 && lignesVisibles.every((l) => selection.has(l.IdDetailEncaissement));
  const basculer = (id) => setSelection((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const toutBasculer = () => setSelection((s) => {
    const n = new Set(s);
    lignesVisibles.forEach((l) => (toutCoche ? n.delete(l.IdDetailEncaissement) : n.add(l.IdDetailEncaissement)));
    return n;
  });

  const majPolice = (idContrat, police, avenant) => setLignes((ls) => ls.map((l) => (l.IdContrat === idContrat ? { ...l, PoliceCompagnie: police, AvenantCompagnie: avenant } : l)));
  const changerOrdre = async (l, ordre) => {
    try {
      await financeApi.ordreEncaissement(l.IdEncaissement, ordre);
      const nature = ordre === 'COMPAGNIE' ? 'RECLAMATION' : 'REVERSEMENT';
      setLignes((ls) => ls.map((x) => (x.IdEncaissement === l.IdEncaissement ? { ...x, Ordre: ordre, Nature: nature } : x)));
    } catch (err) {
      toastError(`Ordre non modifié : ${messageErreurApi(err)}`);
    }
  };

  // Numéros attribués à l'émission : bordereau de reversement d'abord, puis de réclamation
  const numerosPrevus = () => {
    const depart = Number(numero) || Number(prochainNumero) || 0;
    const prevus = {};
    let n = depart;
    if (aReverser.length) { prevus.REVERSEMENT = n; n += 1; }
    if (directes.length) prevus.RECLAMATION = n;
    return prevus;
  };

  const emettre = async () => {
    const prevus = numerosPrevus();
    const sansPolice = cochees.filter((l) => !l.PoliceCompagnie).length;
    const details = [
      aReverser.length ? `N° ${prevus.REVERSEMENT} — BORDEREAU DE REVERSEMENT DE PRIME : ${aReverser.length} prime(s), ${fcfa(somme(aReverser, 'ResteAReverser'))} F à reverser par le cabinet` : '',
      directes.length ? `N° ${prevus.RECLAMATION} — BORDEREAU DE RECLAMATION DE COMMISSION : ${directes.length} prime(s) réglée(s) à l'ordre de la compagnie (Direct)` : '',
      sansPolice ? `${sansPolice} quittance(s) sans police de la compagnie : le numéro LE PHARE sera imprimé.` : '',
    ].filter(Boolean);
    const ok = await confirmer({
      titre: aReverser.length && directes.length ? 'Émettre deux bordereaux' : 'Émettre le bordereau',
      message: `${nomCompagnie} — bordereau(x) du ${dateFr(dateBordereau)}`,
      consequences: details.join('\n'),
      confirmer: 'Émettre',
      ton: sansPolice ? 'attention' : 'info',
    });
    if (!ok) return;
    setEnvoi(true);
    try {
      const resultat = await financeApi.emettreBordereaux({
        IdCompagnie: Number(compagnie),
        DateBordereau: dateBordereau,
        Numero: Number(numero) || null,
        Lignes: cochees.map((l) => l.IdDetailEncaissement),
        Paiement: aReverser.length && paiement.IdMode ? paiement : null,
      });
      const emis = resultat.Bordereaux || [];
      success(`${emis.length > 1 ? 'Bordereaux' : 'Bordereau'} ${emis.map((b) => `N° ${b.Numero}`).join(' et ')} émis pour ${nomCompagnie}.`);
      if (emis.some((b) => !b.Direct && !b.Valide)) warning('Bordereau de reversement : saisissez le paiement du cabinet avant d\'imprimer le courrier.');
      setPaiement(paiementVide());
      setOuvert(emis[0] || null);
      chargerLignes();
      chargerBordereaux();
    } catch (err) {
      toastError(`Bordereau non émis : ${messageErreurApi(err)}`);
    } finally {
      setEnvoi(false);
    }
  };

  const ouvrir = (id) => financeApi.bordereau(id).then(setOuvert).catch((err) => toastError(messageErreurApi(err)));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', paddingBottom: '2rem' }}>
      <div>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', margin: 0 }}>
          <Building2 size={26} style={{ color: 'var(--primary-500)' }} /> Reversements aux compagnies
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0.3rem 0 0', maxWidth: 980 }}>
          Chèque du client à l'ordre de la compagnie : transmis tel quel avec un bordereau de réclamation de commission (« Direct »).
          Prime encaissée par {nomCabinet()} : reversée entière par son chèque avec un bordereau de reversement de prime (Code CIMA : la commission n'est jamais déduite).
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '1rem 1.25rem', display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div className="form-group" style={{ margin: 0, minWidth: 240 }}>
          <label className="form-label" htmlFor="rv-cie">Compagnie</label>
          <select id="rv-cie" className="form-control" value={compagnie} onChange={(e) => setCompagnie(e.target.value)}>
            {trierParLibelle(compagnies, (c) => c.RaisonSociale).map((c) => (
              <option key={c.IdCompagnie ?? c.id} value={c.IdCompagnie ?? c.id}>{c.RaisonSociale}</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }} role="tablist">
          <Onglet actif={onglet === 'a_transmettre'} onClick={() => setOnglet('a_transmettre')} icone={Send}>
            Primes à transmettre ({filtre ? `${lignesVisibles.length}/${lignes.length}` : lignes.length})
          </Onglet>
          <Onglet actif={onglet === 'bordereaux'} onClick={() => setOnglet('bordereaux')} icone={ShieldCheck}>
            Bordereaux émis ({filtre ? `${bordereauxVisibles.length}/${bordereaux.length}` : bordereaux.length})
          </Onglet>
          <Onglet actif={onglet === 'tableau'} onClick={() => setOnglet('tableau')} icone={Table2}>Tableau de reversement</Onglet>
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => { chargerLignes(); chargerBordereaux(); }} style={{ marginLeft: 'auto' }} title="Actualiser" aria-label="Actualiser">
          {chargement ? <Loader2 size={15} className="spin" /> : <RefreshCw size={15} />}
        </button>
        <div style={{ flexBasis: '100%', display: 'flex', gap: '0.8rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 280 }}>
            <Search size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input type="text" className="form-control" style={{ paddingLeft: '2rem', paddingRight: '2rem' }} value={recherche}
              onChange={(e) => setRecherche(e.target.value)} aria-label="Rechercher"
              placeholder="Rechercher : client, quittance, police, n° de chèque ou de bordereau, banque, date (jj/mm/aaaa), montant…" />
            {recherche && (
              <button type="button" onClick={() => setRecherche('')} aria-label="Effacer la recherche"
                style={{ position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4, display: 'flex' }}>
                <X size={15} />
              </button>
            )}
          </div>
          {onglet !== 'tableau' && (
            <select className="form-control" style={{ width: 'auto', minWidth: 230 }} value={natureFiltre} onChange={(e) => setNatureFiltre(e.target.value)} aria-label="Nature du bordereau">
              <option value="">Toutes les natures</option>
              <option value="REVERSEMENT">Reversement de prime</option>
              <option value="RECLAMATION">Réclamation de commission (direct)</option>
            </select>
          )}
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Du plus récent au plus ancien</span>
        </div>
      </div>

      {onglet === 'a_transmettre' && (
        <div className="glass-panel" style={{ padding: '1rem 1.1rem' }}>
          <div className="table-wrapper" style={{ maxHeight: '55vh', overflow: 'auto' }}>
            <table className="data-table" style={{ fontSize: '0.82rem' }}>
              <thead>
                <tr>
                  <th><input type="checkbox" checked={toutCoche} onChange={toutBasculer} aria-label="Tout cocher" /></th>
                  <th>Encaissé le</th><th>Client</th><th>Assurance</th><th>Police compagnie / avt</th><th>Règlement</th><th>À l'ordre de</th>
                  <th>Paiement du client</th><th style={{ textAlign: 'right' }}>Prime TTC</th><th style={{ textAlign: 'right' }}>À transmettre</th>
                  <th style={{ textAlign: 'right' }}>Commission + acc.</th>
                </tr>
              </thead>
              <tbody>
                {lignesVisibles.map((l) => {
                  const coche = selection.has(l.IdDetailEncaissement);
                  return (
                    <tr key={l.IdDetailEncaissement} style={coche ? { background: 'var(--primary-glow)' } : undefined}>
                      <td><input type="checkbox" checked={coche} onChange={() => basculer(l.IdDetailEncaissement)} aria-label={`Transmettre ${l.NumeroQuittance}`} /></td>
                      <td>{dateFr(l.DateEncaissement)}</td>
                      <td>{l.Client}<div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{l.NumeroQuittance}</div></td>
                      <td>{l.Branche}</td>
                      <td><PoliceCompagnie ligne={l} onEnregistre={majPolice} /></td>
                      <td style={{ minWidth: 190 }}>{l.Reglement || [l.Mode, l.Reference].filter(Boolean).join(' — ')}</td>
                      <td>
                        <select className="form-control" style={{ padding: '0.2rem 0.35rem', minWidth: 170 }} value={l.Ordre}
                          disabled={!l.OrdreModifiable} onChange={(e) => changerOrdre(l, e.target.value)} aria-label="À l'ordre de">
                          <option value="CABINET">{nomCabinet()}</option>
                          <option value="COMPAGNIE">La compagnie</option>
                        </select>
                        <div style={{ marginTop: 3 }}><BadgeNature nature={l.Nature} /></div>
                      </td>
                      <td>
                        {l.LibelleStatutPaiement}
                        {l.Arriere > 0 && <div style={{ fontSize: '0.72rem', color: 'var(--accent-amber, #d97706)' }}>Arriéré {fcfa(l.Arriere)} F</div>}
                      </td>
                      <td style={{ textAlign: 'right' }}>{fcfa(l.PrimeTtc)}</td>
                      <td style={{ textAlign: 'right', fontWeight: 700 }}>{fcfa(l.ResteAReverser)}</td>
                      <td style={{ textAlign: 'right', color: 'var(--text-muted)' }}>{fcfa(l.Commission + l.AccCourtier)}</td>
                    </tr>
                  );
                })}
                {!lignesVisibles.length && (
                  <tr><td colSpan={11} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>
                    {chargement ? 'Chargement…' : (lignes.length ? 'Aucune prime ne correspond à la recherche.' : `Aucune prime encaissée à transmettre à ${nomCompagnie || 'cette compagnie'}.`)}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', marginTop: '1rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.9rem' }}>
            <div style={{ display: 'flex', gap: '1.2rem', flexWrap: 'wrap', fontSize: '0.88rem' }}>
              <span><strong>{cochees.length}</strong> prime(s) cochée(s){masquees > 0 && <span style={{ color: 'var(--accent-amber, #d97706)' }}> dont {masquees} masquée(s) par la recherche</span>}</span>
              {aReverser.length > 0 && <span><BadgeNature nature="REVERSEMENT" /> {aReverser.length} — à reverser par le cabinet : <strong>{fcfa(somme(aReverser, 'ResteAReverser'))} F</strong></span>}
              {directes.length > 0 && <span><BadgeNature nature="RECLAMATION" /> {directes.length} — chèques transmis : {fcfa(somme(directes, 'ResteAReverser'))} F</span>}
              {cochees.length > 0 && <span style={{ color: 'var(--text-muted)' }}>Commission à réclamer : {fcfa(somme(cochees, 'Commission') + somme(cochees, 'AccCourtier'))} F</span>}
            </div>
            {aReverser.length > 0 && <PaiementCabinet modes={modes} banques={banques} valeur={paiement} onChange={setPaiement} />}
            <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" htmlFor="rv-date">Date du bordereau et du courrier</label>
                <input id="rv-date" type="date" className="form-control" value={dateBordereau} onChange={(e) => setDateBordereau(e.target.value)} />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" htmlFor="rv-num">N° du bordereau</label>
                <input id="rv-num" type="number" min={1} className="form-control" style={{ width: 130 }} value={numero} onChange={(e) => setNumero(e.target.value)} />
              </div>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', maxWidth: 360 }}>
                Suite de la numérotation d'OREOLE (proposé : {prochainNumero}). Deux natures cochées : deux bordereaux, numéros consécutifs.
              </span>
              <button type="button" className="btn btn-primary" disabled={!cochees.length || envoi} onClick={emettre} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginLeft: 'auto' }}>
                {envoi ? <Loader2 size={15} className="spin" /> : <Send size={15} />} Émettre {aReverser.length && directes.length ? 'les bordereaux' : 'le bordereau'}
              </button>
            </div>
          </div>
        </div>
      )}

      {onglet === 'bordereaux' && (
        <div className="glass-panel" style={{ padding: '1rem 1.1rem' }}>
          <div className="table-wrapper">
            <table className="data-table" style={{ fontSize: '0.84rem' }}>
              <thead>
                <tr>
                  <th>N°</th><th>Date</th><th>Nature</th><th>Client(s)</th><th style={{ textAlign: 'right' }}>Quittances</th>
                  <th style={{ textAlign: 'right' }}>Montant à reverser</th><th>Décharge</th><th>Statut</th><th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {bordereauxVisibles.map((b) => (
                  <tr key={b.IdReversement}>
                    <td style={{ fontWeight: 700 }}>{b.Numero || <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>{b.NumeroReversement}</span>}</td>
                    <td>{dateFr(b.DateBordereau)}</td>
                    <td><BadgeNature nature={b.Nature} /></td>
                    <td style={{ maxWidth: 260 }}>{b.NombreQuittances > 1 && b.Clients.includes(',') ? 'Assurés divers' : b.Clients}</td>
                    <td style={{ textAlign: 'right' }}>{b.NombreQuittances}</td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>{b.Direct ? 'Direct' : fcfa(b.MontantAReverser)}</td>
                    <td>{b.DateDecharge ? dateFr(b.DateDecharge) : <span style={{ color: 'var(--text-muted)' }}>À recevoir</span>}</td>
                    <td><StatusBadge label={b.LibelleStatut} color={b.Statut === 'A_PAYER' ? 'amber' : 'emerald'} /></td>
                    <td style={{ textAlign: 'right' }}>
                      <button type="button" className="btn btn-secondary" style={{ padding: '0.25rem 0.55rem' }} onClick={() => ouvrir(b.IdReversement)}>Ouvrir</button>
                    </td>
                  </tr>
                ))}
                {!bordereauxVisibles.length && (
                  <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>
                    {bordereaux.length ? 'Aucun bordereau ne correspond à la recherche.' : 'Aucun bordereau pour cette compagnie.'}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {onglet === 'tableau' && <TableauReversement compagnie={compagnie} nomCompagnie={nomCompagnie} recherche={recherche} />}

      <BordereauModal bordereau={ouvert} modes={modes} banques={banques} onClose={() => setOuvert(null)}
        onChange={(b) => { setOuvert(b); chargerBordereaux(); if (!b) chargerLignes(); }} />
    </div>
  );
};

export default CompanyRemittancePage;
