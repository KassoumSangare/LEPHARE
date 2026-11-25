import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Loader2, PencilLine, Receipt, Search, X } from 'lucide-react';
import { financeApi } from '../../../api/endpoints';
import { CorrectionEncaissement } from '../../../components/cash/CorrectionEncaissement';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { dateFr, fcfa, messageErreurApi } from '../../../utils/financeUtils';

/* =========================================================================
   CORRIGER UN ENCAISSEMENT (Administration > Corrections)
   Tout encaissement, quelle que soit sa date : la caisse ne propose que les saisies du jour. Recherche par n° de pièce, de
   chèque, de quittance, de police, client, émetteur ou montant (GET finance/encaissements/recherche/), puis la correction
   de la caisse (components/cash/CorrectionEncaissement.jsx) : références, annuler et réaffecter, annuler un doublon.
   ?q= : recherche lancée à l'arrivée ; ?piece=<id> : correction ouverte directement (centre des corrections).
   ========================================================================= */

const ANNULES = new Set(['ANNULE', 'IMPAYE', 'DECAISSEMENT']);

// Une ligne par pièce : la recherche renvoie une ligne par quittance réglée
const pieces = (reglements) => {
  const parPiece = new Map();
  reglements.forEach((r) => r.Lignes.forEach((l) => {
    const piece = parPiece.get(l.IdEncaissement) || {
      IdEncaissement: l.IdEncaissement, NumeroPiece: l.NumeroPiece, Date: l.DateEncaissement, Mode: l.Mode,
      Reference: [l.Reference, l.Banque].filter(Boolean).join(' - '), Clients: new Set(), Quittances: new Set(), Montant: 0,
      Statut: l.Statut, LibelleStatut: l.LibelleStatut,
    };
    if (l.Client) piece.Clients.add(l.Client);
    if (l.NumeroQuittance) piece.Quittances.add(l.NumeroQuittance);
    piece.Montant += Number(l.Montant) || 0;
    parPiece.set(l.IdEncaissement, piece);
  }));
  return [...parPiece.values()].sort((a, b) => String(b.Date).localeCompare(String(a.Date)) || b.IdEncaissement - a.IdEncaissement);
};

export const CorrectionEncaissementsPage = () => {
  const [parametres, setParametres] = useSearchParams();
  const [texte, setTexte] = useState(parametres.get('q') || '');
  const [resultat, setResultat] = useState(null);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState('');
  const [aCorriger, setACorriger] = useState(Number(parametres.get('piece')) || null);

  const rechercher = async (q = texte) => {
    const recherche = q.trim();
    if (recherche.length < 2) {
      setErreur('Saisissez au moins 2 caractères : n° de pièce, de chèque, de quittance, de police, client, émetteur ou montant.');
      return;
    }
    setChargement(true);
    setErreur('');
    try {
      setResultat(await financeApi.rechercherReglements({ q: recherche }));
    } catch (e) {
      setErreur(messageErreurApi(e));
    } finally {
      setChargement(false);
    }
  };

  useEffect(() => {
    if (parametres.get('q') || parametres.get('piece')) setParametres({}, { replace: true });
    if (texte.trim().length >= 2) rechercher(texte);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const liste = useMemo(() => (resultat ? pieces(resultat.Reglements || []) : []), [resultat]);

  return (
    <div className="corr-page">
      <header className="corr-entete">
        <span className="corr-entete-icone" aria-hidden="true"><Receipt size={22} /></span>
        <div>
          <h1 className="title-xl">Corriger un encaissement</h1>
          <p>Tout encaissement, quelle que soit sa date : références, annulation et réaffectation, doublon.</p>
        </div>
        <Link to="/admin/corrections" className="btn btn-secondary">Centre des corrections</Link>
      </header>

      <form className="glass-panel corr-recherche" onSubmit={(e) => { e.preventDefault(); rechercher(); }}>
        <Search size={18} aria-hidden="true" />
        <input type="search" autoFocus value={texte} onChange={(e) => setTexte(e.target.value)} aria-label="Rechercher un encaissement"
          placeholder="N° de pièce, de chèque, de quittance, de police, client, émetteur ou montant…" />
        {texte && <button type="button" className="corr-effacer" onClick={() => { setTexte(''); setResultat(null); }} aria-label="Effacer"><X size={16} /></button>}
        <button type="submit" className="btn btn-primary" disabled={chargement}>
          {chargement ? <Loader2 className="spin" size={15} /> : <Search size={15} />} Rechercher
        </button>
      </form>

      {erreur && <p className="corr-erreur">{erreur}</p>}
      {resultat && (
        <section className="glass-panel corr-journal" aria-label="Encaissements trouvés">
          <div className="corr-muet" style={{ marginBottom: '0.6rem' }}>
            {liste.length} pièce{liste.length > 1 ? 's' : ''}{resultat.Tronque ? ' : précisez la recherche pour voir les autres' : ''}
          </div>
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Pièce</th><th>Date de saisie</th><th>Règlement</th><th>Client</th><th>Quittance</th><th className="nombre">Montant</th><th>État</th><th aria-label="Action" /></tr></thead>
              <tbody>
                {liste.map((p) => (
                  <tr key={p.IdEncaissement}>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{p.NumeroPiece || p.IdEncaissement}</td>
                    <td>{dateFr(p.Date)}</td>
                    <td>{p.Mode}{p.Reference ? <div className="corr-muet">{p.Reference}</div> : null}</td>
                    <td>{[...p.Clients].join(', ') || '-'}</td>
                    <td>{[...p.Quittances].join(', ')}</td>
                    <td className="nombre"><strong>{fcfa(p.Montant)} F</strong></td>
                    <td><StatusBadge label={p.LibelleStatut} color={ANNULES.has(p.Statut) ? 'rose' : 'emerald'} /></td>
                    <td>
                      {!ANNULES.has(p.Statut) && (
                        <button type="button" className="btn btn-primary" style={{ padding: '0.3rem 0.65rem', fontSize: '0.78rem' }} onClick={() => setACorriger(p.IdEncaissement)}>
                          <PencilLine size={14} /> Corriger
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {!liste.length && <tr><td colSpan={8} className="corr-muet">Aucun encaissement ne correspond.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {aCorriger && (
        <CorrectionEncaissement idEncaissement={aCorriger} onClose={() => setACorriger(null)} onCorrige={() => { if (texte.trim().length >= 2) rechercher(); }} />
      )}
    </div>
  );
};

export default CorrectionEncaissementsPage;
