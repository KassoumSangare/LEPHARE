import React, { useEffect, useMemo, useState } from 'react';
import { Printer, Loader2, AlertTriangle } from 'lucide-react';
import { Modal } from '../../../components/common/Modal';
import { contractApi } from '../../../api/endpoints';
import { printReleveCompte } from '../../../utils/exportUtils';

const fcfa = (v) => `${Math.round(Number(v) || 0).toLocaleString('fr-FR')}`;
const jma = (iso) => (iso ? String(iso).slice(0, 10).split('-').reverse().join('/') : '');

/**
 * Relevé de compte d'un contrat (quittance remise au client, modèle OREOLE) : la quittance du contrat
 * et les quittances non soldées du même client sont proposées, toutes cochées comme sur le relevé
 * d'origine ; le gestionnaire retire celles qui ne doivent pas y figurer puis imprime.
 */
export const ReleveCompteModal = ({ isOpen, onClose, idContrat }) => {
  const [releve, setReleve] = useState(null);
  const [erreur, setErreur] = useState('');
  const [retenues, setRetenues] = useState(new Set());

  useEffect(() => {
    if (!isOpen || !idContrat) return undefined;
    let actif = true;
    setReleve(null);
    setErreur('');
    contractApi.getReleveCompte(idContrat)
      .then((d) => {
        if (!actif) return;
        setReleve(d);
        setRetenues(new Set((d.Lignes || []).map((l) => l.IdContrat)));
      })
      .catch((err) => {
        if (actif) setErreur(err?.response?.data?.detail || err?.response?.data?.error || 'Relevé de compte indisponible : le serveur ne répond pas.');
      });
    return () => { actif = false; };
  }, [isOpen, idContrat]);

  const lignes = releve?.Lignes || [];
  const choisies = useMemo(() => lignes.filter((l) => retenues.has(l.IdContrat)), [lignes, retenues]);
  const total = (champ) => choisies.reduce((t, l) => t + (Number(l[champ]) || 0), 0);

  const basculer = (id) => setRetenues((s) => {
    const n = new Set(s);
    if (n.has(id)) n.delete(id); else n.add(id);
    return n;
  });

  const cellule = { padding: '0.5rem 0.6rem', borderBottom: '1px solid var(--border-subtle)', verticalAlign: 'middle' };
  const montant = { ...cellule, textAlign: 'right', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Relevé de compte" subtitle={releve?.Client?.Nom || 'Quittance remise au client'} size="large">
      {!releve && !erreur && (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          <Loader2 size={22} className="spin" /> <div style={{ marginTop: '0.5rem' }}>Chargement des quittances du client…</div>
        </div>
      )}
      {erreur && (
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', color: '#f87171', padding: '1rem 0' }}>
          <AlertTriangle size={18} /> {erreur}
        </div>
      )}
      {releve && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Quittance de ce contrat et quittances non soldées du client. Décochez celles qui ne doivent pas figurer sur le relevé.
          </p>
          <div style={{ overflowX: 'auto', maxHeight: '50vh', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', color: 'var(--text-primary)' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                  <th style={cellule} />
                  <th style={cellule}>Période</th>
                  <th style={cellule}>Opération</th>
                  <th style={cellule}>Chèque à l'ordre de</th>
                  <th style={{ ...cellule, textAlign: 'right' }}>Prime TTC</th>
                  <th style={{ ...cellule, textAlign: 'right' }}>Encaissé</th>
                  <th style={{ ...cellule, textAlign: 'right' }}>Solde</th>
                </tr>
              </thead>
              <tbody>
                {lignes.map((l) => (
                  <tr key={l.IdContrat} onClick={() => basculer(l.IdContrat)}
                    style={{ cursor: 'pointer', background: l.ContratCourant ? 'rgba(59, 130, 246, 0.10)' : undefined, opacity: retenues.has(l.IdContrat) ? 1 : 0.5 }}>
                    <td style={cellule}>
                      <input type="checkbox" checked={retenues.has(l.IdContrat)} onChange={() => basculer(l.IdContrat)} onClick={(ev) => ev.stopPropagation()}
                        aria-label={`Retenir ${l.Operation}`} />
                    </td>
                    <td style={{ ...cellule, whiteSpace: 'nowrap' }}>{jma(l.DateEffet)} au {jma(l.DateExpiration)}</td>
                    <td style={cellule}>
                      {l.Operation}
                      {l.ContratCourant && <span style={{ marginLeft: '0.4rem', fontSize: '0.7rem', fontWeight: 700, color: '#60a5fa' }}>CE CONTRAT</span>}
                      {l.NumeroQuittance && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Quittance {l.NumeroQuittance}</div>}
                    </td>
                    <td style={cellule}>{l.OrdreCheque}</td>
                    <td style={montant}>{fcfa(l.PrimeTtc)}</td>
                    <td style={montant}>{fcfa(l.Encaissement)}</td>
                    <td style={{ ...montant, fontWeight: 700 }}>{fcfa(l.Solde)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{ fontWeight: 700 }}>
                  <td style={cellule} colSpan={4}>Total retenu ({choisies.length} / {lignes.length})</td>
                  <td style={montant}>{fcfa(total('PrimeTtc'))}</td>
                  <td style={montant}>{fcfa(total('Encaissement'))}</td>
                  <td style={montant}>{fcfa(total('Solde'))}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setRetenues(new Set(lignes.map((l) => l.IdContrat)))}>Tout cocher</button>
              <button type="button" className="btn btn-secondary" onClick={() => setRetenues(new Set(lignes.filter((l) => l.ContratCourant).map((l) => l.IdContrat)))}>
                Ce contrat seulement
              </button>
            </div>
            <button type="button" className="btn btn-primary" disabled={!choisies.length} onClick={() => printReleveCompte(releve, choisies)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Printer size={15} /> Imprimer le relevé
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
};
