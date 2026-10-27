import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, FilePlus2, Users } from 'lucide-react';
import { Modal } from '../../../components/common/Modal';
import { santeApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { messageErreurApi } from '../../../utils/financeUtils';
import { formatDate } from '../../../utils/dateUtils';

const jours = (debut, fin) => (debut && fin ? Math.round((new Date(fin) - new Date(debut)) / 86400000) + 1 : 0);
const pluriel = (n, mot) => `${n} ${mot}${n > 1 ? 's' : ''}`;

// Formule d'une famille dans les listes (sans parenthèses) : option MINENE et sa taille, sinon libellé de l'offre
const libelleFormule = (o) => (o.Option
  ? `${o.Option} — ${o.PersonnesMin === o.PersonnesMax ? pluriel(o.PersonnesMax, 'personne') : `${o.PersonnesMin} à ${o.PersonnesMax} personnes`}`
  : String(o.Formule || '').replace(/\s*\(([^)]*)\)/g, ' — $1'));

/**
 * Avenant de modification d'un contrat Santé en cours (CR OREOLE du 26-10-2026 : passer de FAMILLE à FAMILLE PLUS après
 * l'agrandissement de la famille). Crée le devis d'avenant sous la même police avec la composition en vigueur, la famille
 * choisie passant dans la nouvelle formule, puis ouvre l'écran Santé pour ajouter le nouveau membre (sante/avenant.py).
 */
export const AvenantSanteModal = ({ isOpen, onClose, idContrat }) => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();
  const [donnees, setDonnees] = useState(null);
  const [erreur, setErreur] = useState('');
  const [dateEffet, setDateEffet] = useState('');
  const [idAdherent, setIdAdherent] = useState(0);
  const [idOffre, setIdOffre] = useState(0);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    if (!isOpen || !idContrat) return undefined;
    let actif = true;
    setDonnees(null);
    setErreur('');
    santeApi.preparerAvenant(idContrat)
      .then((d) => {
        if (!actif) return;
        setDonnees(d);
        setDateEffet(d.DateEffet || '');
        setIdAdherent(0);
        setIdOffre(0);
      })
      .catch((err) => { if (actif) setErreur(messageErreurApi(err)); });
    return () => { actif = false; };
  }, [isOpen, idContrat]);

  const famille = useMemo(() => (donnees?.Familles || []).find((f) => f.IdAdherent === Number(idAdherent)), [donnees, idAdherent]);

  // Famille choisie : formule proposée d'office, celle qui accueille une personne de plus quand la formule actuelle est pleine
  const choisirFamille = (valeur) => {
    setIdAdherent(Number(valeur));
    const f = (donnees?.Familles || []).find((x) => x.IdAdherent === Number(valeur));
    if (!f) { setIdOffre(0); return; }
    const taille = Number(f.Personnes) + 1;
    const suivante = f.PersonnesMax && Number(f.Personnes) >= Number(f.PersonnesMax)
      ? f.Formules.find((o) => o.PersonnesMin <= taille && taille <= o.PersonnesMax) : null;
    setIdOffre(suivante ? suivante.IdOffre : f.IdOffre);
  };

  const contrat = donnees?.Contrat;
  const joursRestants = contrat ? jours(dateEffet, contrat.DateExpiration) : 0;
  const joursPeriode = contrat ? jours(contrat.DateEffet, contrat.DateExpiration) : 0;
  const enCours = donnees?.EnCours?.[0];

  const creer = async () => {
    if (!dateEffet) { toastError('Saisissez la date d\'effet de l\'avenant.'); return; }
    setEnvoi(true);
    try {
      const r = await santeApi.creerAvenant(idContrat, { DateEffet: dateEffet, IdAdherent: Number(idAdherent) || 0, IdOffre: Number(idOffre) || 0 });
      success(`Avenant ${r.NumeroDevis} créé${r.Formule ? ` : ${r.Famille} passe en ${r.Formule}` : ''}. Ajoutez le nouveau membre puis enregistrez le devis.`);
      onClose();
      navigate(`/user/quotes/sante?edit=${r.IdDevis}`);
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="medium" title="Changer de formule ou incorporer un membre"
      subtitle={contrat ? `Police ${contrat.NumeroPolice} — ${contrat.Client || ''}` : undefined}>
      {erreur && <div style={{ color: 'var(--accent-amber)', fontSize: '0.85rem' }}>{erreur}</div>}
      {!erreur && !donnees && <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Lecture du contrat…</div>}
      {donnees && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.85rem' }}>
          <div style={{ color: 'var(--text-secondary)' }}>
            Période du contrat : du <strong>{formatDate(contrat.DateEffet)}</strong> au <strong>{formatDate(contrat.DateExpiration)}</strong>.
            {' '}L'avenant reprend la composition en vigueur sous la même police ; sa prime est l'écart de prime annuelle entre la
            nouvelle composition et l'actuelle, au prorata des jours restants, sans ristourne.
          </div>

          {enCours ? (
            <div style={{ padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.45)', background: 'rgba(245, 158, 11, 0.08)' }}>
              Un avenant est déjà en cours de saisie : devis <strong>{enCours.NumeroDevis}</strong>, effet le {formatDate(enCours.DateEffet)}.
              <div style={{ marginTop: '0.6rem' }}>
                <button type="button" className="btn btn-primary" onClick={() => { onClose(); navigate(`/user/quotes/sante?edit=${enCours.IdDevis}`); }}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                  <ArrowRight size={14} /> Ouvrir l'avenant en cours
                </button>
              </div>
            </div>
          ) : !donnees.Familles?.length ? (
            <div style={{ color: 'var(--accent-amber)' }}>
              Aucune famille enregistrée pour ce contrat (contrat repris d'URANUS) : le changement se saisit par un nouveau devis.
            </div>
          ) : (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                  <span style={{ fontWeight: 600 }}>Date d'effet de l'avenant *</span>
                  <input type="date" className="form-control" value={dateEffet} min={contrat.DateEffet} max={contrat.DateExpiration}
                    onChange={(e) => setDateEffet(e.target.value)} />
                  {joursPeriode > 0 && joursRestants > 0 && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Prorata : {joursRestants} jours sur {joursPeriode}
                    </span>
                  )}
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                  <span style={{ fontWeight: 600 }}>Famille concernée</span>
                  <select className="form-control" value={idAdherent} onChange={(e) => choisirFamille(e.target.value)}>
                    <option value={0}>Aucune — incorporation saisie dans l'écran</option>
                    {donnees.Familles.map((f) => (
                      <option key={f.IdAdherent} value={f.IdAdherent}>
                        {f.Adherent} — {f.Option || libelleFormule(f)} — {pluriel(Number(f.Personnes), 'personne')}
                      </option>
                    ))}
                  </select>
                </label>
                {famille && (
                  <label style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                    <span style={{ fontWeight: 600 }}>Nouvelle formule</span>
                    <select className="form-control" value={idOffre} onChange={(e) => setIdOffre(Number(e.target.value))}>
                      {famille.Formules.map((o) => (
                        <option key={o.IdOffre} value={o.IdOffre}>
                          {libelleFormule(o)}{o.IdOffre === famille.IdOffre ? ' — actuelle' : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </div>
              {famille && Number(idOffre) !== Number(famille.IdOffre) && (
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', color: 'var(--text-secondary)' }}>
                  <Users size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                  <span>
                    La famille <strong>{famille.Adherent}</strong> passe de {famille.Option || 'sa formule'} à{' '}
                    <strong>{famille.Formules.find((o) => o.IdOffre === Number(idOffre))?.Option || 'la nouvelle formule'}</strong>.
                    {' '}Dans l'écran Santé qui s'ouvre, ajoutez le nouveau membre à la famille puis enregistrez le devis.
                  </span>
                </div>
              )}
              {donnees.Avenants?.length > 0 && (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                  Avenants déjà émis sur la période :{' '}
                  {donnees.Avenants.map((a) => `${formatDate(a.DateEffet)} — ${Math.round(a.PrimeTtc || 0).toLocaleString('fr-FR')} F TTC`).join(' ; ')}
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={onClose}>Annuler</button>
                <button type="button" className="btn btn-primary" onClick={creer} disabled={envoi}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <FilePlus2 size={15} /> {envoi ? 'Création…' : 'Créer l\'avenant'}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </Modal>
  );
};

export default AvenantSanteModal;
