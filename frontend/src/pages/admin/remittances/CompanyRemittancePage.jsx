import React, { useEffect, useMemo, useState } from 'react';
import { Building2, CheckCircle2, FileSpreadsheet, FileText, Loader2, RefreshCw, Send, ShieldCheck, Wallet } from 'lucide-react';
import { financeApi, settingsApi } from '../../../api/endpoints';
import { Modal } from '../../../components/common/Modal';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { useToast } from '../../../context/ToastContext';
import { aujourdhui, dateFr, exporterBordereauReversement, fcfa, messageErreurApi } from '../../../utils/financeUtils';
import { trierParLibelle } from '../../../utils/sortUtils';

// Reversements aux compagnies (Code CIMA) : le cabinet reverse la prime encaissée ENTIÈRE ; sa
// commission n'est pas déduite (elle est réclamée ensuite, écran Commissions). Les primes
// encaissées sont cochées par compagnie (sp_enregistrement_reversement), le bordereau suit le
// modèle d'OREOLE, puis le paiement à la compagnie est enregistré (sp_validation_reversement).
const ID_NSIA = 1;
const MODES_REVERSEMENT = ['ESP', 'CHQ', 'VIR', 'TRT', 'CMP'];

const Onglet = ({ actif, onClick, icone: Icone, children }) => (
  <button type="button" role="tab" aria-selected={actif} className={`btn ${actif ? 'btn-primary' : 'btn-secondary'}`}
    onClick={onClick} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
    <Icone size={15} /> {children}
  </button>
);

const BordereauModal = ({ reversement, onClose, onPayer }) => (
  <Modal isOpen={Boolean(reversement)} onClose={onClose} size="large"
    title={reversement ? `Bordereau de reversement N° ${reversement.Numero}` : ''}
    subtitle={reversement ? `${reversement.Compagnie} — ${dateFr(reversement.DateReversement)} — ${reversement.LibelleStatut}` : ''}>
    {reversement && (
      <>
        <div style={{ display: 'flex', gap: '1.25rem', flexWrap: 'wrap', fontSize: '0.88rem', marginBottom: '0.9rem' }}>
          <span>Montant reversé : <strong>{fcfa(reversement.Montant)} F</strong></span>
          <span>Quittances : <strong>{reversement.Lignes.length}</strong></span>
          <span>Commission due au cabinet (non déduite) : <strong>{fcfa(reversement.Commissions)} F</strong></span>
          {reversement.Valide && <span>Payé le {dateFr(reversement.DateValidation)} : <strong>{reversement.Mode} {reversement.Reference}</strong></span>}
        </div>
        <div className="table-wrapper" style={{ maxHeight: '50vh', overflow: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Client</th><th>Branche</th><th>N° Police</th><th>N° quittance</th><th>Avenant</th><th>Émission</th><th>Effet</th><th>Expiration</th>
                <th style={{ textAlign: 'right' }}>Prime nette</th><th style={{ textAlign: 'right' }}>Accessoire</th><th style={{ textAlign: 'right' }}>Taxe</th>
                <th style={{ textAlign: 'right' }}>Prime TTC</th><th style={{ textAlign: 'right' }}>Reversé</th><th style={{ textAlign: 'right' }}>Comm. Interm.</th>
              </tr>
            </thead>
            <tbody>
              {reversement.Lignes.map((l) => (
                <tr key={l.IdDetailReversement}>
                  <td>{l.Client}</td><td>{l.Branche}</td><td>{l.NumeroPolice}</td><td>{l.NumeroQuittance}</td><td>{l.NumeroAvenant}</td>
                  <td>{dateFr(l.DateEmission)}</td><td>{dateFr(l.DateEffet)}</td><td>{dateFr(l.DateExpiration)}</td>
                  <td style={{ textAlign: 'right' }}>{fcfa(l.PrimeNette)}</td><td style={{ textAlign: 'right' }}>{fcfa(l.Accessoire)}</td>
                  <td style={{ textAlign: 'right' }}>{fcfa(l.Taxe)}</td><td style={{ textAlign: 'right' }}>{fcfa(l.PrimeTtc)}</td>
                  <td style={{ textAlign: 'right', fontWeight: 700 }}>{fcfa(l.MontantReverse)}</td><td style={{ textAlign: 'right' }}>{fcfa(l.Commission)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '0.6rem 0 0' }}>
          Code CIMA : la prime est reversée entière ; la commission (« Comm. Interm. ») est réclamée à la compagnie par un bordereau récapitulatif.
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secondary" onClick={() => exporterBordereauReversement(reversement, 'excel')} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><FileSpreadsheet size={15} /> Excel</button>
          <button type="button" className="btn btn-secondary" onClick={() => exporterBordereauReversement(reversement, 'pdf')} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><FileText size={15} /> Imprimer / PDF</button>
          {!reversement.Valide && (
            <button type="button" className="btn btn-primary" onClick={() => onPayer(reversement)} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Wallet size={15} /> Enregistrer le paiement à la compagnie</button>
          )}
        </div>
      </>
    )}
  </Modal>
);

const PaiementModal = ({ reversement, modes, banques, onClose, onValide }) => {
  const { success, error: toastError } = useToast();
  const [saisie, setSaisie] = useState({ IdMode: '', IdBanque: '', NumeroCheque: '', NomEmetteur: '', ReferenceCompensation: '', DateReversement: aujourdhui() });
  const [envoi, setEnvoi] = useState(false);
  useEffect(() => { if (reversement) setSaisie((s) => ({ ...s, DateReversement: aujourdhui() })); }, [reversement]);
  const mode = modes.find((m) => String(m.idmodeencaissement) === String(saisie.IdMode));
  const abrege = String(mode?.abregereglement || '').trim().toUpperCase();
  const champ = (cle) => (e) => setSaisie((s) => ({ ...s, [cle]: e.target.value }));

  const valider = async (e) => {
    e.preventDefault();
    setEnvoi(true);
    try {
      const resultat = await financeApi.validerReversement(reversement.IdReversement, saisie);
      success(`Reversement ${resultat.Numero} payé à ${resultat.Compagnie}.`);
      onValide(resultat);
    } catch (err) {
      toastError(`Paiement non enregistré : ${messageErreurApi(err)}`);
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <Modal isOpen={Boolean(reversement)} onClose={onClose} size="medium" title="Paiement du reversement à la compagnie"
      subtitle={reversement ? `${reversement.Numero} — ${reversement.Compagnie} — ${fcfa(reversement.Montant)} F` : ''}>
      {reversement && (
        <form onSubmit={valider} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.8rem' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" htmlFor="rv-mode">Mode de paiement</label>
            <select id="rv-mode" className="form-control" required value={saisie.IdMode} onChange={champ('IdMode')}>
              <option value="">— Choisir —</option>
              {modes.map((m) => <option key={m.idmodeencaissement} value={m.idmodeencaissement}>{m.libellemodepaiement}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" htmlFor="rv-date">Date du paiement</label>
            <input id="rv-date" type="date" className="form-control" required value={saisie.DateReversement} onChange={champ('DateReversement')} />
          </div>
          {mode?.banque && (
            <>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" htmlFor="rv-banque">Banque</label>
                <select id="rv-banque" className="form-control" required value={saisie.IdBanque} onChange={champ('IdBanque')}>
                  <option value="">— Choisir —</option>
                  {banques.map((b) => <option key={b.idbanque} value={b.idbanque}>{b.libelle}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" htmlFor="rv-num">{abrege === 'VIR' ? 'N° de virement' : abrege === 'TRT' ? 'N° de traite' : 'N° du chèque'}</label>
                <input id="rv-num" className="form-control" maxLength={50} required={abrege === 'CHQ'} value={saisie.NumeroCheque} onChange={champ('NumeroCheque')} />
              </div>
            </>
          )}
          {mode?.compensation && (
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" htmlFor="rv-comp">Référence de la compensation</label>
              <input id="rv-comp" className="form-control" required maxLength={50} value={saisie.ReferenceCompensation} onChange={champ('ReferenceCompensation')} />
            </div>
          )}
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" htmlFor="rv-emet">Émis par</label>
            <input id="rv-emet" className="form-control" maxLength={50} value={saisie.NomEmetteur} onChange={champ('NomEmetteur')} placeholder="Facultatif" />
          </div>
          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={envoi} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {envoi ? <Loader2 size={15} className="spin" /> : <CheckCircle2 size={15} />} Enregistrer le paiement
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
};

export const CompanyRemittancePage = () => {
  const { success, error: toastError } = useToast();
  const [onglet, setOnglet] = useState('a_reverser');
  const [compagnies, setCompagnies] = useState([]);
  const [modes, setModes] = useState([]);
  const [banques, setBanques] = useState([]);
  const [compagnie, setCompagnie] = useState(String(ID_NSIA));
  const [lignes, setLignes] = useState([]);
  const [selection, setSelection] = useState({}); // IdDetailEncaissement -> montant
  const [dateReversement, setDateReversement] = useState(aujourdhui());
  const [chargement, setChargement] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [reversements, setReversements] = useState([]);
  const [bordereau, setBordereau] = useState(null);
  const [aPayer, setAPayer] = useState(null);

  useEffect(() => {
    settingsApi.getCompanies().then((l) => setCompagnies(Array.isArray(l) ? l : [])).catch(() => {});
    settingsApi.getBanques().then((l) => setBanques(Array.isArray(l) ? l : [])).catch(() => {});
    settingsApi.getModesEncaissement()
      .then((l) => setModes((Array.isArray(l) ? l : []).filter((m) => MODES_REVERSEMENT.includes(String(m.abregereglement || '').trim().toUpperCase()) || m.compensation)))
      .catch(() => {});
  }, []);

  const chargerLignes = () => {
    if (!compagnie) return;
    setChargement(true);
    financeApi.lignesAReverser(compagnie)
      .then((r) => { setLignes(r.Lignes || []); setSelection({}); })
      .catch((err) => toastError(`Primes à reverser indisponibles : ${messageErreurApi(err)}`))
      .finally(() => setChargement(false));
  };
  const chargerReversements = () => {
    financeApi.reversements(compagnie ? { compagnie } : {})
      .then((r) => setReversements(r.Reversements || []))
      .catch((err) => toastError(`Reversements indisponibles : ${messageErreurApi(err)}`));
  };
  useEffect(() => { chargerLignes(); chargerReversements(); }, [compagnie]); // eslint-disable-line react-hooks/exhaustive-deps

  const cochees = lignes.filter((l) => selection[l.IdDetailEncaissement] !== undefined);
  const totalCoche = cochees.reduce((s, l) => s + (Number(selection[l.IdDetailEncaissement]) || 0), 0);
  const commissionCochee = cochees.reduce((s, l) => s + (l.PrimeTtc ? l.Commission * (Number(selection[l.IdDetailEncaissement]) || 0) / l.PrimeTtc : 0), 0);
  const toutCoche = lignes.length > 0 && cochees.length === lignes.length;
  const basculer = (l) => setSelection((s) => {
    const suivant = { ...s };
    if (suivant[l.IdDetailEncaissement] !== undefined) delete suivant[l.IdDetailEncaissement];
    else suivant[l.IdDetailEncaissement] = l.ResteAReverser;
    return suivant;
  });
  const toutBasculer = () => setSelection(toutCoche ? {} : Object.fromEntries(lignes.map((l) => [l.IdDetailEncaissement, l.ResteAReverser])));
  const nomCompagnie = useMemo(() => compagnies.find((c) => String(c.IdCompagnie ?? c.id) === String(compagnie))?.RaisonSociale || '', [compagnies, compagnie]);

  const reverser = async () => {
    const depassement = cochees.find((l) => Number(selection[l.IdDetailEncaissement]) > l.ResteAReverser || Number(selection[l.IdDetailEncaissement]) <= 0);
    if (depassement) {
      toastError(`Quittance ${depassement.NumeroQuittance} : le montant doit être compris entre 1 et ${fcfa(depassement.ResteAReverser)} F.`);
      return;
    }
    setEnvoi(true);
    try {
      const resultat = await financeApi.reverser({
        IdCompagnie: Number(compagnie),
        DateReversement: dateReversement,
        Lignes: cochees.map((l) => ({ IdDetailEncaissement: l.IdDetailEncaissement, Montant: Number(selection[l.IdDetailEncaissement]) })),
      });
      success(`Reversement ${resultat.Numero} enregistré : ${fcfa(resultat.Montant)} F à reverser à ${resultat.Compagnie}.`);
      setBordereau(resultat);
      chargerLignes();
      chargerReversements();
    } catch (err) {
      toastError(`Reversement non enregistré : ${messageErreurApi(err)}`);
    } finally {
      setEnvoi(false);
    }
  };

  const ouvrirBordereau = (id) => financeApi.reversement(id).then(setBordereau).catch((err) => toastError(messageErreurApi(err)));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', paddingBottom: '2rem' }}>
      <div>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', margin: 0 }}>
          <Building2 size={26} style={{ color: 'var(--primary-500)' }} /> Reversements aux compagnies
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0.3rem 0 0', maxWidth: 900 }}>
          Les primes encaissées sont reversées entières à la compagnie (Code CIMA : le courtier ne déduit pas sa commission des primes à reverser).
          La commission figure sur le bordereau et se réclame ensuite dans l'écran Commissions.
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
          <Onglet actif={onglet === 'a_reverser'} onClick={() => setOnglet('a_reverser')} icone={Send}>Primes à reverser ({lignes.length})</Onglet>
          <Onglet actif={onglet === 'reversements'} onClick={() => setOnglet('reversements')} icone={ShieldCheck}>Reversements effectués ({reversements.length})</Onglet>
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => { chargerLignes(); chargerReversements(); }} style={{ marginLeft: 'auto' }} title="Actualiser">
          {chargement ? <Loader2 size={15} className="spin" /> : <RefreshCw size={15} />}
        </button>
      </div>

      {onglet === 'a_reverser' && (
        <div className="glass-panel" style={{ padding: '1rem 1.1rem' }}>
          <div className="table-wrapper" style={{ maxHeight: '58vh', overflow: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th><input type="checkbox" checked={toutCoche} onChange={toutBasculer} aria-label="Tout cocher" /></th>
                  <th>Encaissé le</th><th>Client</th><th>Branche</th><th>N° Police</th><th>Quittance</th><th>Mode / référence</th>
                  <th style={{ textAlign: 'right' }}>Encaissé</th><th style={{ textAlign: 'right' }}>Déjà reversé</th>
                  <th style={{ textAlign: 'right' }}>À reverser</th><th style={{ textAlign: 'right' }}>Comm. (info)</th>
                </tr>
              </thead>
              <tbody>
                {lignes.map((l) => {
                  const coche = selection[l.IdDetailEncaissement] !== undefined;
                  return (
                    <tr key={l.IdDetailEncaissement} style={coche ? { background: 'var(--primary-glow)' } : undefined}>
                      <td><input type="checkbox" checked={coche} onChange={() => basculer(l)} aria-label={`Reverser ${l.NumeroQuittance}`} /></td>
                      <td>{dateFr(l.DateEncaissement)}</td><td>{l.Client}</td><td>{l.Branche}</td><td>{l.NumeroPolice}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{l.NumeroQuittance}</td>
                      <td>{[l.Mode, l.Reference].filter(Boolean).join(' — ')}</td>
                      <td style={{ textAlign: 'right' }}>{fcfa(l.Montant)}</td>
                      <td style={{ textAlign: 'right' }}>{fcfa(l.MontantReverse)}</td>
                      <td style={{ textAlign: 'right', minWidth: 120 }}>
                        {coche ? (
                          <input type="number" className="form-control" min={1} max={l.ResteAReverser} step="1" style={{ textAlign: 'right', padding: '0.25rem 0.4rem' }}
                            value={selection[l.IdDetailEncaissement]} onChange={(e) => setSelection((s) => ({ ...s, [l.IdDetailEncaissement]: e.target.value }))} />
                        ) : <strong>{fcfa(l.ResteAReverser)}</strong>}
                      </td>
                      <td style={{ textAlign: 'right', color: 'var(--text-muted)' }}>{fcfa(l.Commission)}</td>
                    </tr>
                  );
                })}
                {!lignes.length && (
                  <tr><td colSpan={11} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>
                    {chargement ? 'Chargement…' : `Aucune prime encaissée à reverser à ${nomCompagnie || 'cette compagnie'}.`}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap', marginTop: '1rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.9rem' }}>
            <div style={{ fontSize: '0.9rem' }}>
              <div><strong>{cochees.length}</strong> quittance(s) cochée(s) — à reverser : <strong style={{ fontSize: '1.1rem' }}>{fcfa(totalCoche)} F</strong></div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Commission du cabinet sur ces primes (non déduite, réclamée ensuite) : {fcfa(commissionCochee)} F</div>
            </div>
            <div className="form-group" style={{ margin: '0 0 0 auto' }}>
              <label className="form-label" htmlFor="rv-date-rev">Date du reversement</label>
              <input id="rv-date-rev" type="date" className="form-control" value={dateReversement} onChange={(e) => setDateReversement(e.target.value)} />
            </div>
            <button type="button" className="btn btn-primary" disabled={!cochees.length || envoi} onClick={reverser} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {envoi ? <Loader2 size={15} className="spin" /> : <Send size={15} />} Établir le bordereau de reversement
            </button>
          </div>
        </div>
      )}

      {onglet === 'reversements' && (
        <div className="glass-panel" style={{ padding: '1rem 1.1rem' }}>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>N° reversement</th><th>Date</th><th>Compagnie</th><th style={{ textAlign: 'right' }}>Quittances</th>
                  <th style={{ textAlign: 'right' }}>Montant reversé</th><th style={{ textAlign: 'right' }}>Commission due</th>
                  <th>Statut</th><th>Paiement</th><th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {reversements.map((r) => (
                  <tr key={r.IdReversement}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{r.Numero}</td>
                    <td>{dateFr(r.DateReversement)}</td><td>{r.Compagnie}</td>
                    <td style={{ textAlign: 'right' }}>{r.NombreQuittances}</td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>{fcfa(r.Montant)}</td>
                    <td style={{ textAlign: 'right' }}>{fcfa(r.Commissions)}</td>
                    <td><StatusBadge label={r.LibelleStatut} color={r.Valide ? 'emerald' : 'amber'} /></td>
                    <td>{r.Valide ? `${r.Mode} ${r.Reference}`.trim() : '—'}</td>
                    <td style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
                      <button type="button" className="btn btn-secondary" style={{ padding: '0.25rem 0.55rem' }} onClick={() => ouvrirBordereau(r.IdReversement)}>Bordereau</button>{' '}
                      {!r.Valide && (
                        <button type="button" className="btn btn-primary" style={{ padding: '0.25rem 0.55rem' }}
                          onClick={() => financeApi.reversement(r.IdReversement).then(setAPayer)}>Payer</button>
                      )}
                    </td>
                  </tr>
                ))}
                {!reversements.length && <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>Aucun reversement pour cette compagnie.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <BordereauModal reversement={bordereau} onClose={() => setBordereau(null)} onPayer={(r) => { setBordereau(null); setAPayer(r); }} />
      <PaiementModal reversement={aPayer} modes={modes} banques={banques} onClose={() => setAPayer(null)}
        onValide={(r) => { setAPayer(null); setBordereau(r); chargerReversements(); }} />
    </div>
  );
};

export default CompanyRemittancePage;
