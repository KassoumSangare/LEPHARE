import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeftRight, Ban, Banknote, Loader2, Printer, Search, Undo2 } from 'lucide-react';
import { cashApi, settingsApi } from '../../../api/endpoints';
import { ChoixBanque } from '../../../components/cash/BanqueModal';
import { AmountInput } from '../../../components/common/AmountInput';
import { Modal } from '../../../components/common/Modal';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { useToast } from '../../../context/ToastContext';
import { ouvrirApercuImpression } from '../../../utils/apercuImpression';
import { libelleAvenant } from '../../../utils/avenants';
import { saisirTexte } from '../../../utils/dialogue';
import { aLeDroit } from '../../../utils/droits';
import { dateFr, fcfa, messageErreurApi } from '../../../utils/financeUtils';
import { nomCabinet } from '../../../utils/parametrage';

/* =========================================================================
   Ristournes à régler (serveur : production/ristournes.py). Une ristourne est la part de prime rendue au client par un
   avenant de retrait ou de résiliation (quittance négative). Elle se rembourse (espèces, chèque ou virement du cabinet,
   paiement mobile, ou directement par la compagnie) ou s'impute sur une autre prime du même client. Une saisie erronée
   s'annule tant que rien n'a été reversé.
   ========================================================================= */
const PETIT = { padding: '0.3rem 0.55rem', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' };
const DROITE = { textAlign: 'right', whiteSpace: 'nowrap' };
const SECONDAIRE = { fontSize: '0.72rem', color: 'var(--text-muted)' };
const echapper = (t) => String(t ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const sansAccents = (t) => String(t ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const correspond = (recherche, valeurs) => {
  const mots = sansAccents(recherche).split(/\s+/).filter(Boolean);
  const texte = sansAccents(valeurs.filter((v) => v !== null && v !== undefined).join(' '));
  return mots.every((m) => texte.includes(m));
};
// Libellé de la référence selon le mode de remboursement
const libelleReference = (mode) => {
  if (!mode) return 'Référence';
  if (mode.Compagnie) return 'N° du chèque de la compagnie';
  return { CHQ: 'N° du chèque', VIR: 'N° du virement', PYM: "N° du reçu de l'opérateur", ESP: 'N° du bordereau de caisse' }[mode.Abrege] || 'Référence';
};
const referenceObligatoire = (mode) => Boolean(mode && (mode.Abrege === 'CHQ' || mode.Abrege === 'PYM'));
const avenantTexte = (r) => [(r.CodeAvenant || r.Mouvement) && libelleAvenant(r.CodeAvenant, r.Mouvement), r.NumeroAvenant && `n° ${Number(r.NumeroAvenant) || r.NumeroAvenant}`]
  .filter(Boolean).join(' ');

// Bon de remboursement ou d'imputation : pièce de caisse à faire signer, surtout quand de l'argent sort de la caisse
const imprimerBon = (p) => {
  const fenetre = ouvrirApercuImpression();
  if (!fenetre) return;
  const imputation = p.Type === 'IMPUTATION';
  const ligne = (q, libelle) => `<tr><td>${libelle}</td><td>${echapper(q.NumeroQuittance)}</td><td>${echapper(q.Police)}</td><td class="d">${fcfa(q.Montant)} F</td></tr>`;
  const lignes = [...p.Ristournes.map((q) => ligne(q, 'Ristourne')), ...p.PrimesPayees.map((q) => ligne(q, 'Prime payée'))].join('');
  fenetre.document.write(`<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>${imputation ? 'Imputation' : 'Remboursement'} de ristourne ${echapper(p.NumeroPiece)}</title>
    <style>body{font-family:Arial,sans-serif;color:#111;margin:24px;font-size:13px}h1{font-size:20px;margin:0 0 4px}table{width:100%;border-collapse:collapse;margin:14px 0}
    th,td{border:1px solid #999;padding:6px 8px;text-align:left}th{background:#eee}.d{text-align:right}.grille{display:grid;grid-template-columns:190px 1fr;gap:4px 12px;margin-top:14px}
    .signatures{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:40px}.signatures div{border-top:1px solid #111;padding-top:6px;height:70px}</style></head><body>
    <h1>${imputation ? 'Imputation de ristourne' : 'Bon de remboursement de ristourne'}</h1><div>${echapper(nomCabinet())} - pièce ${echapper(p.NumeroPiece)}</div>
    <div class="grille"><strong>Date</strong><span>${dateFr(p.Date)}</span><strong>Client</strong><span>${echapper(p.Client) || '-'}</span>
    ${imputation ? '' : `<strong>Bénéficiaire</strong><span>${echapper(p.Beneficiaire) || '-'}</span><strong>Mode</strong><span>${echapper(p.Mode)}</span>
    <strong>Référence</strong><span>${echapper([p.Banque, p.Reference].filter(Boolean).join(' ')) || '-'}</span>`}
    <strong>${imputation ? 'Montant imputé' : 'Montant remboursé'}</strong><span><strong>${fcfa(p.Montant)} F</strong></span>
    ${p.Motif ? `<strong>Motif</strong><span>${echapper(p.Motif)}</span>` : ''}<strong>Enregistré par</strong><span>${echapper(p.Operateur) || '-'}</span></div>
    <table><thead><tr><th></th><th>Quittance</th><th>Police</th><th class="d">Montant</th></tr></thead><tbody>${lignes}</tbody></table>
    ${p.Annulee ? `<p><strong>Règlement annulé</strong>${p.MotifAnnulation ? ` : ${echapper(p.MotifAnnulation)}` : ''}</p>` : ''}
    <div class="signatures"><div>Le caissier</div><div>${imputation ? 'Le client' : 'Le bénéficiaire'}</div></div></body></html>`);
  fenetre.document.close();
};

const Resume = ({ ristourne: r }) => (
  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))', gap: '0.6rem', padding: '0.75rem 0.9rem',
    border: '1px solid var(--border-subtle)', borderRadius: 10, marginBottom: '1rem', fontSize: '0.85rem' }}>
    <div><div style={SECONDAIRE}>Client</div><strong>{r.Client || '-'}</strong></div>
    <div><div style={SECONDAIRE}>Ristourne</div><strong>{r.NumeroQuittance}</strong><div style={SECONDAIRE}>{r.NumeroPolice}</div></div>
    <div><div style={SECONDAIRE}>Montant de la ristourne</div><strong>{fcfa(r.Ristourne)} F</strong></div>
    <div><div style={SECONDAIRE}>Reste à régler</div><strong style={{ color: 'var(--accent-amber, #d97706)' }}>{fcfa(r.Reste)} F</strong></div>
  </div>
);

// ------------------------------------------------------------------ remboursement
const FenetreRemboursement = ({ ristourne, modes, banques, onClose, onEnregistre }) => {
  const { error: toastError } = useToast();
  const [saisie, setSaisie] = useState({ IdMode: '', Montant: ristourne.Reste, Beneficiaire: ristourne.Client || '', IdBanque: '', Reference: '', DateCheque: '' });
  const [envoi, setEnvoi] = useState(false);
  const mode = modes.find((m) => String(m.IdMode) === String(saisie.IdMode));
  const changer = (cle, valeur) => setSaisie((s) => ({ ...s, [cle]: valeur }));
  const depasse = Number(saisie.Montant) > ristourne.Reste;
  const incomplet = !mode || !(Number(saisie.Montant) > 0) || depasse || !saisie.Beneficiaire.trim()
    || (mode.Banque && !(Number(saisie.IdBanque) > 1)) || (referenceObligatoire(mode) && !saisie.Reference.trim());

  const valider = async (e) => {
    e.preventDefault();
    if (incomplet) return;
    setEnvoi(true);
    try {
      const resultat = await cashApi.rembourserRistourne(ristourne.IdQuittance, {
        ...saisie, IdMode: Number(saisie.IdMode), IdBanque: mode.Banque ? Number(saisie.IdBanque) : null, DateCheque: mode.Banque ? saisie.DateCheque || null : null,
      });
      onEnregistre(resultat, `Remboursement de ${fcfa(resultat.Montant)} F enregistré, pièce ${resultat.NumeroPiece}.`);
    } catch (err) {
      toastError(`Remboursement non enregistré : ${messageErreurApi(err)}`);
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <Modal isOpen onClose={onClose} title="Rembourser une ristourne" subtitle={avenantTexte(ristourne) || undefined}>
      <form onSubmit={valider}>
        <Resume ristourne={ristourne} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: '0.8rem' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" htmlFor="rb-mode">Mode de remboursement</label>
            <select id="rb-mode" className="form-control" value={saisie.IdMode} onChange={(e) => changer('IdMode', e.target.value)} required>
              <option value="">Choisir</option>
              {modes.map((m) => <option key={m.IdMode} value={m.IdMode}>{m.Compagnie ? 'Par la compagnie, directement au client' : m.Libelle}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" htmlFor="rb-montant">Montant remboursé</label>
            <AmountInput id="rb-montant" value={saisie.Montant} onChange={(v) => changer('Montant', v)} suffix="F" required />
            {depasse && <span style={{ fontSize: '0.75rem', color: 'var(--accent-rose, #e11d48)' }}>Au plus {fcfa(ristourne.Reste)} F</span>}
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" htmlFor="rb-beneficiaire">Bénéficiaire</label>
            <input id="rb-beneficiaire" className="form-control" maxLength={50} value={saisie.Beneficiaire} onChange={(e) => changer('Beneficiaire', e.target.value)} required />
          </div>
          {mode?.Banque && (
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" htmlFor="rb-banque">Banque</label>
              <ChoixBanque id="rb-banque" banques={banques} value={saisie.IdBanque} onChange={(v) => changer('IdBanque', v)} required />
            </div>
          )}
          {mode && (
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" htmlFor="rb-reference">{libelleReference(mode)}{referenceObligatoire(mode) ? '' : ' (facultatif)'}</label>
              <input id="rb-reference" className="form-control" maxLength={50} value={saisie.Reference} onChange={(e) => changer('Reference', e.target.value)} required={referenceObligatoire(mode)} />
            </div>
          )}
          {mode?.Banque && (
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" htmlFor="rb-date">Date du chèque ou du virement (facultatif)</label>
              <input id="rb-date" type="date" className="form-control" value={saisie.DateCheque} onChange={(e) => changer('DateCheque', e.target.value)} />
            </div>
          )}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.1rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Fermer</button>
          <button type="submit" className="btn btn-primary" disabled={incomplet || envoi} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {envoi ? <Loader2 size={15} className="spin" /> : <Banknote size={15} />} Rembourser {fcfa(saisie.Montant)} F
          </button>
        </div>
      </form>
    </Modal>
  );
};

// ------------------------------------------------------------------ imputation
const FenetreImputation = ({ ristourne, onClose, onEnregistre }) => {
  const { error: toastError } = useToast();
  const [primes, setPrimes] = useState(null);
  const [montants, setMontants] = useState({});
  const [motif, setMotif] = useState('');
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    cashApi.getPrimesImputables(ristourne.IdQuittance)
      .then((r) => setPrimes(r.Primes || []))
      .catch((err) => { toastError(`Primes du client non lues : ${messageErreurApi(err)}`); setPrimes([]); });
  }, [ristourne.IdQuittance, toastError]);

  const total = Object.values(montants).reduce((s, v) => s + (Number(v) || 0), 0);
  const disponible = ristourne.Reste - total;
  const basculer = (p) => setMontants((m) => {
    if (p.NumeroQuittance in m) {
      const { [p.NumeroQuittance]: _retire, ...reste } = m;
      return reste;
    }
    const libre = ristourne.Reste - Object.values(m).reduce((s, v) => s + (Number(v) || 0), 0);
    return { ...m, [p.NumeroQuittance]: Math.max(0, Math.min(p.Reste, libre)) };
  });
  const erreurLigne = (p) => (p.NumeroQuittance in montants && Number(montants[p.NumeroQuittance]) > p.Reste ? `Au plus ${fcfa(p.Reste)} F` : '');
  const lignes = Object.entries(montants).filter(([, v]) => Number(v) > 0);
  const invalide = !lignes.length || disponible < 0 || (primes || []).some((p) => erreurLigne(p));

  const valider = async () => {
    if (invalide) return;
    setEnvoi(true);
    try {
      const resultat = await cashApi.imputerRistourne(ristourne.IdQuittance, {
        Lignes: lignes.map(([NumeroQuittance, Montant]) => ({ NumeroQuittance, Montant })), Motif: motif.trim(),
      });
      onEnregistre(resultat, `Ristourne imputée : ${fcfa(resultat.Montant)} F, pièce ${resultat.NumeroPiece}.`);
    } catch (err) {
      toastError(`Imputation non enregistrée : ${messageErreurApi(err)}`);
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <Modal isOpen onClose={onClose} size="large" title="Imputer une ristourne sur une prime" subtitle={avenantTexte(ristourne) || undefined}>
      <Resume ristourne={ristourne} />
      {primes === null ? (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}><Loader2 size={18} className="spin" /> Chargement des primes du client…</div>
      ) : primes.length ? (
        <div className="table-wrapper" style={{ maxHeight: '45vh', overflow: 'auto' }}>
          <table className="data-table" style={{ fontSize: '0.82rem' }}>
            <thead>
              <tr><th aria-label="Choisir" /><th>Quittance / police</th><th>Compagnie / branche</th><th>Période</th>
                <th style={DROITE}>Reste à payer</th><th style={DROITE}>Montant imputé</th></tr>
            </thead>
            <tbody>
              {primes.map((p) => {
                const choisie = p.NumeroQuittance in montants;
                return (
                  <tr key={p.IdQuittance} style={choisie ? { background: 'var(--primary-glow)' } : undefined}>
                    <td><input type="checkbox" checked={choisie} onChange={() => basculer(p)} aria-label={`Imputer sur la quittance ${p.NumeroQuittance}`}
                      disabled={!choisie && disponible <= 0} /></td>
                    <td>{p.NumeroQuittance}<div style={SECONDAIRE}>{p.NumeroPolice}</div></td>
                    <td>{p.Compagnie}<div style={SECONDAIRE}>{p.Branche}{p.CodeAvenant || p.Mouvement ? ` - ${libelleAvenant(p.CodeAvenant, p.Mouvement).toLowerCase()}` : ''}</div></td>
                    <td style={{ whiteSpace: 'nowrap' }}>{dateFr(p.DateEffet)}<div style={SECONDAIRE}>au {dateFr(p.DateExpiration)}</div></td>
                    <td style={DROITE}>{fcfa(p.Reste)} F</td>
                    <td style={{ ...DROITE, minWidth: 150 }}>
                      {choisie && <AmountInput value={montants[p.NumeroQuittance]} onChange={(v) => setMontants((m) => ({ ...m, [p.NumeroQuittance]: v }))} suffix="F" />}
                      {erreurLigne(p) && <div style={{ fontSize: '0.72rem', color: 'var(--accent-rose, #e11d48)' }}>{erreurLigne(p)}</div>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p style={{ color: 'var(--text-muted)', margin: '0.5rem 0' }}>Ce client n'a aucune autre prime à payer : la ristourne se rembourse.</p>
      )}
      <div className="form-group" style={{ margin: '0.9rem 0 0' }}>
        <label className="form-label" htmlFor="im-motif">Motif (facultatif)</label>
        <input id="im-motif" className="form-control" maxLength={255} value={motif} onChange={(e) => setMotif(e.target.value)}
          placeholder="Par défaut : ristourne imputée sur les quittances choisies" />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', marginTop: '1rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.85rem' }}>
          Imputé : <strong>{fcfa(total)} F</strong>
          <span style={{ color: disponible < 0 ? 'var(--accent-rose, #e11d48)' : 'var(--text-muted)' }}> - reste de la ristourne après : {fcfa(disponible)} F</span>
        </span>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Fermer</button>
          <button type="button" className="btn btn-primary" disabled={invalide || envoi} onClick={valider} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {envoi ? <Loader2 size={15} className="spin" /> : <ArrowLeftRight size={15} />} Imputer {fcfa(total)} F
          </button>
        </div>
      </div>
    </Modal>
  );
};

// ------------------------------------------------------------------ page
const RistournesPage = () => {
  const { success, error: toastError } = useToast();
  const [parametres] = useSearchParams();
  const [donnees, setDonnees] = useState({ ARegler: [], Reglees: [], Modes: [], Imputation: false });
  const [banques, setBanques] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [onglet, setOnglet] = useState('a_regler');
  const [recherche, setRecherche] = useState(parametres.get('quittance') || '');
  const [remboursement, setRemboursement] = useState(null);
  const [imputation, setImputation] = useState(null);
  const peutRegler = aLeDroit('encaissements.create');
  const peutAnnuler = aLeDroit('encaissements.cancel');

  const charger = useCallback(async () => {
    setChargement(true);
    try {
      setDonnees(await cashApi.getRistournes());
    } catch (err) {
      toastError(`Ristournes non lues : ${messageErreurApi(err)}`);
    } finally {
      setChargement(false);
    }
  }, [toastError]);
  useEffect(() => { charger(); }, [charger]);
  useEffect(() => { settingsApi.getBanques().then((l) => setBanques(Array.isArray(l) ? l : [])).catch(() => {}); }, []);

  const aRegler = useMemo(() => donnees.ARegler.filter((r) => correspond(recherche, [
    r.Client, r.NumeroQuittance, r.NumeroPolice, r.Compagnie, r.Branche, r.Mouvement, dateFr(r.DateEmission), r.Reste,
  ])), [donnees.ARegler, recherche]);
  const reglees = useMemo(() => donnees.Reglees.filter((p) => correspond(recherche, [
    p.Client, p.NumeroPiece, p.Mode, p.Reference, p.Beneficiaire, dateFr(p.Date), p.Montant,
    ...p.Ristournes.flatMap((q) => [q.NumeroQuittance, q.Police]), ...p.PrimesPayees.flatMap((q) => [q.NumeroQuittance, q.Police]),
  ])), [donnees.Reglees, recherche]);
  const totalARegler = aRegler.reduce((s, r) => s + r.Reste, 0);

  const enregistre = (resultat, message) => {
    setRemboursement(null);
    setImputation(null);
    success(message);
    charger();
  };
  const annuler = async (p) => {
    const motif = await saisirTexte({
      titre: `Annuler ${p.Type === 'IMPUTATION' ? "l'imputation" : 'le remboursement'} ${p.NumeroPiece}`,
      message: p.Type === 'IMPUTATION' ? 'La ristourne et la prime payée redeviennent à régler. Indiquez le motif.' : 'La ristourne redevient à rembourser. Indiquez le motif.',
      minimum: 5, maximum: 255, confirmer: 'Annuler le règlement', ton: 'danger',
    });
    if (!motif) return;
    try {
      await cashApi.annulerReglementRistourne(p.IdEncaissement, motif);
      success(`Règlement ${p.NumeroPiece} annulé.`);
      charger();
    } catch (err) {
      toastError(`Annulation refusée : ${messageErreurApi(err)}`);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', paddingBottom: '2rem' }}>
      <div>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', margin: 0 }}>
          <Undo2 size={26} style={{ color: 'var(--primary-500)' }} /> Ristournes à régler
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0.3rem 0 0', maxWidth: 980 }}>
          Part de prime rendue au client par un avenant de retrait ou de résiliation : remboursée, ou imputée sur une autre de ses primes.
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '1rem 1.1rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center', marginBottom: '0.9rem' }}>
          <div role="tablist" style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
            <button type="button" role="tab" aria-selected={onglet === 'a_regler'} className={`btn ${onglet === 'a_regler' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setOnglet('a_regler')}>
              À régler ({donnees.ARegler.length})
            </button>
            <button type="button" role="tab" aria-selected={onglet === 'reglees'} className={`btn ${onglet === 'reglees' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setOnglet('reglees')}>
              Réglées ({donnees.Reglees.length})
            </button>
          </div>
          <div style={{ position: 'relative', flex: '1 1 240px', maxWidth: 420, marginLeft: 'auto' }}>
            <Search size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input className="form-control" style={{ paddingLeft: 32 }} value={recherche} onChange={(e) => setRecherche(e.target.value)}
              placeholder="Client, quittance, police, compagnie, montant" aria-label="Rechercher" />
          </div>
        </div>

        {onglet === 'a_regler' && (
          <>
            <div style={{ fontSize: '0.85rem', marginBottom: '0.6rem' }}>
              {aRegler.length} ristourne{aRegler.length > 1 ? 's' : ''}, <strong>{fcfa(totalARegler)} F</strong> à rendre aux clients
            </div>
            <div className="table-wrapper" style={{ maxHeight: '64vh', overflow: 'auto' }}>
              <table className="data-table" style={{ fontSize: '0.82rem' }}>
                <thead>
                  <tr><th>Émise le</th><th>Client</th><th>Quittance / police</th><th>Compagnie / branche</th><th>Avenant</th>
                    <th style={DROITE}>Ristourne</th><th style={DROITE}>Déjà réglé</th><th style={DROITE}>Reste à régler</th>{peutRegler && <th aria-label="Actions" />}</tr>
                </thead>
                <tbody>
                  {aRegler.map((r) => (
                    <tr key={r.IdQuittance}>
                      <td style={{ whiteSpace: 'nowrap' }}>{dateFr(r.DateEmission)}</td>
                      <td>{r.Client || '-'}</td>
                      <td>{r.NumeroQuittance}<div style={SECONDAIRE}>{r.IdContrat ? <Link to={`/user/contracts/${r.IdContrat}`}>{r.NumeroPolice}</Link> : r.NumeroPolice}</div></td>
                      <td>{r.Compagnie}<div style={SECONDAIRE}>{r.Branche}</div></td>
                      <td style={{ whiteSpace: 'nowrap' }}>{avenantTexte(r) || '-'}<div style={SECONDAIRE}>effet {dateFr(r.DateEffet)}</div></td>
                      <td style={DROITE}>{fcfa(r.Ristourne)} F</td>
                      <td style={DROITE}>{r.DejaRegle ? `${fcfa(r.DejaRegle)} F` : '-'}</td>
                      <td style={{ ...DROITE, fontWeight: 700 }}>{fcfa(r.Reste)} F</td>
                      {peutRegler && (
                        <td style={{ whiteSpace: 'nowrap' }}>
                          <button type="button" className="btn btn-primary" style={PETIT} onClick={() => setRemboursement(r)}><Banknote size={13} /> Rembourser</button>{' '}
                          {donnees.Imputation && <button type="button" className="btn btn-secondary" style={PETIT} onClick={() => setImputation(r)}><ArrowLeftRight size={13} /> Imputer</button>}
                        </td>
                      )}
                    </tr>
                  ))}
                  {!aRegler.length && (
                    <tr><td colSpan={peutRegler ? 9 : 8} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>
                      {chargement ? 'Chargement…' : (donnees.ARegler.length ? 'Aucune ristourne ne correspond à la recherche.' : 'Aucune ristourne à régler.')}
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {onglet === 'reglees' && (
          <div className="table-wrapper" style={{ maxHeight: '64vh', overflow: 'auto' }}>
            <table className="data-table" style={{ fontSize: '0.82rem' }}>
              <thead>
                <tr><th>Date</th><th>Pièce</th><th>Règlement</th><th>Client</th><th>Ristourne</th><th>Mode / imputée sur</th>
                  <th style={DROITE}>Montant</th><th aria-label="Actions" /></tr>
              </thead>
              <tbody>
                {reglees.map((p) => (
                  <tr key={p.IdEncaissement} style={p.Annulee ? { opacity: 0.6 } : undefined}>
                    <td style={{ whiteSpace: 'nowrap' }}>{dateFr(p.Date)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{p.NumeroPiece}</td>
                    <td>
                      <StatusBadge label={p.Type === 'IMPUTATION' ? 'Imputation' : 'Remboursement'} color={p.Type === 'IMPUTATION' ? 'blue' : 'emerald'} />
                      {p.Annulee && <div style={{ marginTop: 4 }}><StatusBadge label="Annulé" color="rose" /></div>}
                    </td>
                    <td>{p.Client || '-'}{p.Beneficiaire && p.Type !== 'IMPUTATION' && p.Beneficiaire !== p.Client && <div style={SECONDAIRE}>à {p.Beneficiaire}</div>}</td>
                    <td>{p.Ristournes.map((q) => <div key={q.NumeroQuittance}>{q.NumeroQuittance}<div style={SECONDAIRE}>{q.Police}</div></div>)}</td>
                    <td>
                      {p.Type === 'IMPUTATION'
                        ? p.PrimesPayees.map((q) => <div key={q.NumeroQuittance}>{q.NumeroQuittance} <span style={SECONDAIRE}>{fcfa(q.Montant)} F</span></div>)
                        : <>{p.Mode}<div style={SECONDAIRE}>{[p.Banque, p.Reference].filter(Boolean).join(' ')}</div></>}
                    </td>
                    <td style={{ ...DROITE, fontWeight: 700 }}>{fcfa(p.Montant)} F</td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <button type="button" className="btn btn-secondary" style={PETIT} onClick={() => imprimerBon(p)} title="Bon à faire signer"><Printer size={13} /> Bon</button>{' '}
                      {peutAnnuler && p.Annulable && <button type="button" className="btn btn-secondary" style={PETIT} onClick={() => annuler(p)}><Ban size={13} /> Annuler</button>}
                    </td>
                  </tr>
                ))}
                {!reglees.length && (
                  <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>
                    {chargement ? 'Chargement…' : (donnees.Reglees.length ? 'Aucun règlement ne correspond à la recherche.' : 'Aucune ristourne réglée.')}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {remboursement && (
        <FenetreRemboursement ristourne={remboursement} modes={donnees.Modes} banques={banques}
          onClose={() => setRemboursement(null)} onEnregistre={enregistre} />
      )}
      {imputation && <FenetreImputation ristourne={imputation} onClose={() => setImputation(null)} onEnregistre={enregistre} />}
    </div>
  );
};

export default RistournesPage;
