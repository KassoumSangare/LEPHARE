import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, FilePlus2, PencilLine, Repeat, UserPlus, Users } from 'lucide-react';
import { Modal } from '../../../components/common/Modal';
import { santeApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { fcfa, messageErreurApi } from '../../../utils/financeUtils';
import { formatDate } from '../../../utils/dateUtils';
import { reglagesMinene } from '../../../utils/parametrage';

const jours = (debut, fin) => (debut && fin ? Math.round((new Date(fin) - new Date(debut)) / 86400000) + 1 : 0);
const pluriel = (n, mot) => `${n} ${mot}${n > 1 ? 's' : ''}`;

// Formule d'une famille dans les listes (sans parenthèses) : option MINENE et sa taille, sinon libellé de l'offre
const libelleFormule = (o) => (o.Option
  ? `${o.Option} - ${o.PersonnesMin === o.PersonnesMax ? pluriel(o.PersonnesMax, 'personne') : `${o.PersonnesMin} à ${o.PersonnesMax} personnes`}`
  : String(o.Formule || '').replace(/\s*\(([^)]*)\)/g, ' - $1'));

// Âge révolu à une date (AAAA-MM-JJ), comme la base
const ageAu = (naissance, date) => {
  const n = new Date(naissance);
  const d = new Date(date);
  if (!naissance || !date || Number.isNaN(n.getTime()) || Number.isNaN(d.getTime())) return null;
  const anniversairePasse = d.getMonth() > n.getMonth() || (d.getMonth() === n.getMonth() && d.getDate() >= n.getDate());
  return d.getFullYear() - n.getFullYear() - (anniversairePasse ? 0 : 1);
};

// Formule d'une famille après l'arrivée d'une personne (sp_saisie_affilie_sante v6) : la sienne tant qu'elle n'est pas
// complète, sinon celle de sa nouvelle taille dans la même offre commerciale (FAMILLE de 3 personnes + 1 : FAMILLE PLUS) ;
// null si aucune formule ne l'accueille
const formuleApresIncorporation = (f) => {
  const taille = Number(f.Personnes) + 1;
  if (!f.PersonnesMax || taille <= Number(f.PersonnesMax)) return f.Formules.find((o) => o.IdOffre === f.IdOffre) || f;
  return f.Formules.find((o) => o.PersonnesMin && o.PersonnesMin <= taille && taille <= o.PersonnesMax) || null;
};

const MEMBRE_VIDE = { Lien: 'E', Nom: '', Prenom: '', DateNaissance: '', Sexe: '', Certificat: false, NombrePathologie: 0 };

const MODES = [
  ['incorporation', UserPlus, 'Incorporer un membre'],
  ['formule', Repeat, 'Changer de formule'],
  ['ecran', PencilLine, 'Autre modification'],
];

const champ = (libelle, controle, aide) => (
  <label style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
    <span style={{ fontWeight: 600 }}>{libelle}</span>
    {controle}
    {aide && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{aide}</span>}
  </label>
);

/**
 * Avenant de modification d'un contrat Santé en cours, sous la même police (sante/avenant.py) :
 * - incorporation d'un membre dans une famille (demande du 2026-11-02) : la famille complète passe d'office dans la
 *   formule de sa nouvelle taille (FAMILLE de 3 personnes + 1 : FAMILLE PLUS) et la prime de la nouvelle personne est
 *   l'écart entre les deux formules : dû en entier pour une police MINENE (tarif forfaitaire, 800 000 - 600 000 F TTC),
 *   au prorata des jours restants pour les autres offres ;
 * - changement de formule d'une famille (CR OREOLE du 26-10-2026) ;
 * - autre modification saisie dans l'écran Santé (nouvelle famille…).
 * Le devis d'avenant s'ouvre ensuite dans l'écran Santé.
 */
export const AvenantSanteModal = ({ isOpen, onClose, idContrat }) => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();
  const [donnees, setDonnees] = useState(null);
  const [erreur, setErreur] = useState('');
  const [dateEffet, setDateEffet] = useState('');
  const [mode, setMode] = useState('incorporation');
  const [idAdherent, setIdAdherent] = useState(0);
  const [idOffre, setIdOffre] = useState(0);
  const [membre, setMembre] = useState(MEMBRE_VIDE);
  const [envoi, setEnvoi] = useState(false);
  const surprimes = reglagesMinene().surprimes;

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
        setMode('incorporation');
        setIdAdherent(0);
        setIdOffre(0);
        setMembre(MEMBRE_VIDE);
      })
      .catch((err) => { if (actif) setErreur(messageErreurApi(err)); });
    return () => { actif = false; };
  }, [isOpen, idContrat]);

  const famille = useMemo(() => (donnees?.Familles || []).find((f) => f.IdAdherent === Number(idAdherent)), [donnees, idAdherent]);

  // Changement de formule : formule proposée d'office, celle qui accueille une personne de plus quand l'actuelle est pleine
  const choisirFamille = (valeur) => {
    setIdAdherent(Number(valeur));
    const f = (donnees?.Familles || []).find((x) => x.IdAdherent === Number(valeur));
    setIdOffre(f ? (formuleApresIncorporation(f) || f).IdOffre : 0);
  };

  const contrat = donnees?.Contrat;
  const joursRestants = contrat ? jours(dateEffet, contrat.DateExpiration) : 0;
  const joursPeriode = contrat ? jours(contrat.DateEffet, contrat.DateExpiration) : 0;
  const enCours = donnees?.EnCours?.[0];
  // Police MINENE : prime fixée par formule, l'écart annuel est dû en entier (sans prorata)
  const forfaitaire = Boolean(donnees?.Forfaitaire);

  // Incorporation : formule de la famille après l'arrivée du membre et écart de prime de base entre les deux formules
  const apres = famille ? formuleApresIncorporation(famille) : null;
  const changeFormule = Boolean(famille && apres && apres.IdOffre !== famille.IdOffre);
  const primesConnues = changeFormule && apres.PrimeBase != null && famille.PrimeBase != null;
  const ecartAnnuel = primesConnues ? Number(apres.PrimeBase) - Number(famille.PrimeBase) : 0;
  const estimation = joursPeriode > 0 ? Math.round((ecartAnnuel * Math.max(joursRestants, 0)) / joursPeriode) : 0;
  // Écart TTC au barème des deux formules (MINENE : 800 000 - 600 000 = 200 000 F)
  const ttcAvant = famille ? famille.Formules.find((o) => o.IdOffre === famille.IdOffre)?.PrimeTtc : null;
  const ecartTtc = changeFormule && ttcAvant != null && apres.PrimeTtc != null ? Number(apres.PrimeTtc) - Number(ttcAvant) : null;
  const age = ageAu(membre.DateNaissance, dateEffet);
  const certificatPropose = membre.Lien === 'E' && age !== null && age > Number(surprimes.ageMaxEnfant);
  const affectionsMax = Math.max(0, Number(surprimes.affectionsMax) || 0);
  const majMembre = (cle, valeur) => setMembre((m) => ({ ...m, [cle]: valeur }));

  const creer = async () => {
    if (!dateEffet) { toastError('Saisissez la date d\'effet de l\'avenant.'); return; }
    let envoiAvenant = { DateEffet: dateEffet, IdAdherent: 0, IdOffre: 0 };
    if (mode === 'incorporation') {
      if (!famille) { toastError('Choisissez la famille du nouveau membre.'); return; }
      if (!apres) { toastError('Aucune formule de l\'offre n\'accueille une famille de cette taille.'); return; }
      if (!membre.Nom.trim()) { toastError('Saisissez le nom du nouveau membre.'); return; }
      if (!membre.DateNaissance) { toastError('Saisissez la date de naissance du nouveau membre.'); return; }
      if (!membre.Sexe) { toastError('Précisez le sexe du nouveau membre.'); return; }
      envoiAvenant = {
        ...envoiAvenant, IdAdherent: famille.IdAdherent,
        Membre: { ...membre, Nom: membre.Nom.trim(), Prenom: membre.Prenom.trim(), Certificat: certificatPropose && membre.Certificat },
      };
    } else if (mode === 'formule') {
      if (!famille) { toastError('Choisissez la famille qui change de formule.'); return; }
      envoiAvenant = { ...envoiAvenant, IdAdherent: famille.IdAdherent, IdOffre: Number(idOffre) || 0 };
    }
    setEnvoi(true);
    try {
      const r = await santeApi.creerAvenant(idContrat, envoiAvenant);
      const passage = r.Formule ? `, qui passe de ${r.FormuleAvant} à ${r.Formule}` : '';
      if (mode === 'incorporation') {
        success(`Avenant ${r.NumeroDevis} créé : ${r.Membre} incorporé(e) dans la famille ${r.Famille}${passage}. `
          + `Prime de l'avenant : ${fcfa(r.PrimeTtc)} F TTC. Vérifiez-le dans l'écran Santé puis confirmez-le.`);
      } else if (mode === 'formule') {
        success(`Avenant ${r.NumeroDevis} créé${r.Formule ? ` : la famille ${r.Famille} passe de ${r.FormuleAvant} à ${r.Formule}` : ''}. `
          + 'Vérifiez la composition dans l\'écran Santé puis enregistrez le devis.');
      } else {
        success(`Avenant ${r.NumeroDevis} créé avec la composition en vigueur : faites la modification dans l'écran Santé puis enregistrez le devis.`);
      }
      onClose();
      navigate(`/user/quotes/sante?edit=${r.IdDevis}`);
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const grille = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '0.75rem' };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="medium" title="Incorporation ou changement de formule"
      subtitle={contrat ? `Police ${contrat.NumeroPolice} - ${contrat.Client || ''}` : undefined}>
      {erreur && <div style={{ color: 'var(--accent-amber)', fontSize: '0.85rem' }}>{erreur}</div>}
      {!erreur && !donnees && <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Lecture du contrat…</div>}
      {donnees && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.85rem' }}>
          <div style={{ color: 'var(--text-secondary)' }}>
            Période du contrat : du <strong>{formatDate(contrat.DateEffet)}</strong> au <strong>{formatDate(contrat.DateExpiration)}</strong>, échéance inchangée.
            {' '}L'avenant reprend la composition en vigueur sous la même police ; sa prime est l'écart de prime annuelle entre la
            nouvelle composition et l'actuelle, {forfaitaire
              ? <>dû <strong>en entier</strong> : tarif forfaitaire MINENE, sans prorata ni ristourne.</>
              : 'au prorata des jours restants, sans ristourne.'}
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
              <div className="qp-segments" role="group" aria-label="Type de modification" style={{ alignSelf: 'flex-start', flexWrap: 'wrap' }}>
                {MODES.map(([code, Icone, libelle]) => (
                  <button key={code} type="button" aria-pressed={mode === code} onClick={() => setMode(code)}>
                    <Icone size={13} /> {libelle}
                  </button>
                ))}
              </div>

              <div style={grille}>
                {champ(mode === 'incorporation' ? 'Date d\'incorporation *' : 'Date d\'effet de l\'avenant *',
                  <input type="date" className="form-control" value={dateEffet} min={contrat.DateEffet} max={contrat.DateExpiration}
                    onChange={(e) => setDateEffet(e.target.value)} />,
                  forfaitaire ? 'Tarif forfaitaire : pas de prorata'
                    : joursPeriode > 0 && joursRestants > 0 ? `Prorata : ${joursRestants} jours sur ${joursPeriode}` : undefined)}
                {mode !== 'ecran' && champ('Famille *',
                  <select className="form-control" value={idAdherent} onChange={(e) => choisirFamille(e.target.value)}>
                    <option value={0}>Choisir la famille</option>
                    {donnees.Familles.map((f) => (
                      <option key={f.IdAdherent} value={f.IdAdherent}>
                        {f.Adherent} - {f.Option || libelleFormule(f)} - {pluriel(Number(f.Personnes), 'personne')}
                      </option>
                    ))}
                  </select>)}
                {mode === 'formule' && famille && champ('Nouvelle formule',
                  <select className="form-control" value={idOffre} onChange={(e) => setIdOffre(Number(e.target.value))}>
                    {famille.Formules.map((o) => (
                      <option key={o.IdOffre} value={o.IdOffre}>
                        {libelleFormule(o)}{o.IdOffre === famille.IdOffre ? ' - actuelle' : ''}
                      </option>
                    ))}
                  </select>)}
              </div>

              {mode === 'incorporation' && (
                <>
                  <div style={{ fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <UserPlus size={15} /> Nouveau membre
                  </div>
                  <div style={grille}>
                    {champ('Lien *',
                      <select className="form-control" value={membre.Lien} onChange={(e) => majMembre('Lien', e.target.value)}>
                        <option value="C">Conjoint</option>
                        <option value="E">Enfant</option>
                      </select>)}
                    {champ('Nom *', <input className="form-control" value={membre.Nom} onChange={(e) => majMembre('Nom', e.target.value)} maxLength={60} />)}
                    {champ('Prénoms', <input className="form-control" value={membre.Prenom} onChange={(e) => majMembre('Prenom', e.target.value)} maxLength={80} />)}
                    {champ('Date de naissance *',
                      <input type="date" className="form-control" value={membre.DateNaissance} max={dateEffet || undefined}
                        onChange={(e) => majMembre('DateNaissance', e.target.value)} />,
                      age !== null && age >= 0 ? `${pluriel(age, 'an')} au ${formatDate(dateEffet)}` : undefined)}
                    {champ('Sexe *',
                      <select className="form-control" value={membre.Sexe} onChange={(e) => majMembre('Sexe', e.target.value)}>
                        <option value="">Choisir</option>
                        <option value="F">Féminin</option>
                        <option value="M">Masculin</option>
                      </select>)}
                    {champ('Affections chroniques',
                      <input type="number" min="0" max={affectionsMax} className="form-control" value={membre.NombrePathologie}
                        onChange={(e) => majMembre('NombrePathologie', Math.max(0, Math.min(affectionsMax, Number(e.target.value) || 0)))} />,
                      `Surprime de ${surprimes.affection} % de la prime de base par affection en MINENE.`)}
                  </div>
                  {certificatPropose && (
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <input type="checkbox" checked={membre.Certificat} onChange={(e) => majMembre('Certificat', e.target.checked)} />
                      <span>
                        Certificat de scolarité ou rapport médical fourni : enfant de plus de {surprimes.ageMaxEnfant} ans admis
                        jusqu'à {surprimes.ageMaxEnfantCertificat} ans.
                      </span>
                    </label>
                  )}

                  {famille && (
                    <div style={{
                      display: 'flex', gap: '0.6rem', alignItems: 'flex-start', padding: '0.75rem 0.9rem', borderRadius: '8px',
                      border: `1px solid ${!apres ? 'rgba(244, 63, 94, 0.45)' : changeFormule ? 'rgba(236, 72, 153, 0.45)' : 'var(--border-subtle)'}`,
                      background: !apres ? 'rgba(244, 63, 94, 0.07)' : changeFormule ? 'rgba(236, 72, 153, 0.07)' : 'var(--bg-surface-elevated)',
                      color: 'var(--text-secondary)',
                    }}>
                      <Users size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                      {!apres ? (
                        <span>
                          Aucune formule de l'offre n'accueille une famille de {pluriel(Number(famille.Personnes) + 1, 'personne')} :
                          la famille <strong>{famille.Adherent}</strong> est complète en {libelleFormule(famille)}.
                        </span>
                      ) : changeFormule ? (
                        <span style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                          <span>
                            <strong style={{ color: 'var(--text-primary)' }}>Changement de formule.</strong> La famille {famille.Adherent} passe
                            de {pluriel(Number(famille.Personnes), 'personne')} à {Number(famille.Personnes) + 1} : sa formule {famille.Option}
                            {' '}est complète, elle passe en <strong style={{ color: 'var(--text-primary)' }}>{apres.Option || apres.Formule}</strong>.
                          </span>
                          {forfaitaire && ecartTtc != null ? (
                            <span>
                              Prime de la nouvelle personne : écart entre les deux formules, {fcfa(apres.PrimeTtc)} − {fcfa(ttcAvant)} ={' '}
                              <strong style={{ color: 'var(--text-primary)' }}>{fcfa(ecartTtc)} F TTC</strong> (prime nette {fcfa(ecartAnnuel)} F),
                              dû en entier : tarif forfaitaire, sans prorata.
                            </span>
                          ) : primesConnues ? (
                            <span>
                              Prime de la nouvelle personne : écart entre les deux formules, {fcfa(apres.PrimeBase)} − {fcfa(famille.PrimeBase)} ={' '}
                              <strong style={{ color: 'var(--text-primary)' }}>{fcfa(ecartAnnuel)} F par an</strong>
                              {forfaitaire
                                ? ', dû en entier : tarif forfaitaire, sans prorata'
                                : joursPeriode > 0 && <>, soit environ <strong style={{ color: 'var(--text-primary)' }}>{fcfa(estimation)} F</strong> de prime nette pour {joursRestants} jours sur {joursPeriode}</>}.
                            </span>
                          ) : (
                            <span>
                              Prime de la nouvelle personne : écart entre les deux formules{forfaitaire ? ', dû en entier' : ', au prorata des jours restants'}.
                            </span>
                          )}
                          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                            {forfaitaire
                              ? 'Montant au barème : une réduction, une majoration ou des surprimes de la famille le modifient ; le montant exact est calculé à la création de l\'avenant.'
                              : 'Surprimes, réduction ou majoration de la famille, supplément d\'accessoire et taxe sont calculés à la création de l\'avenant.'}
                          </span>
                        </span>
                      ) : famille.PersonnesMax ? (
                        <span>
                          La famille {famille.Adherent} passe à {pluriel(Number(famille.Personnes) + 1, 'personne')} et reste
                          en <strong style={{ color: 'var(--text-primary)' }}>{libelleFormule(famille)}</strong> : pas
                          d'écart de formule. Seules d'éventuelles surprimes du nouveau membre (âge, affections) s'ajoutent{forfaitaire ? '' : ', au prorata'}.
                        </span>
                      ) : (
                        <span>
                          La famille {famille.Adherent} passe à {pluriel(Number(famille.Personnes) + 1, 'personne')}. Prime de
                          l'avenant : écart de prime annuelle avec la composition actuelle, au prorata des jours restants, calculé à la création.
                        </span>
                      )}
                    </div>
                  )}
                </>
              )}

              {mode === 'formule' && famille && Number(idOffre) !== Number(famille.IdOffre) && (
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', color: 'var(--text-secondary)' }}>
                  <Users size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                  <span>
                    La famille <strong>{famille.Adherent}</strong> passe de {famille.Option || 'sa formule'} à{' '}
                    <strong>{famille.Formules.find((o) => o.IdOffre === Number(idOffre))?.Option || 'la nouvelle formule'}</strong>.
                    {' '}La composition s'ouvre ensuite dans l'écran Santé.
                  </span>
                </div>
              )}
              {mode === 'ecran' && (
                <div style={{ color: 'var(--text-secondary)' }}>
                  L'avenant reprend la composition en vigueur et s'ouvre dans l'écran Santé : ajout d'une famille, d'un membre
                  ou d'une couverture. Un membre ajouté à une famille complète la fait passer d'office dans la formule de sa taille.
                </div>
              )}

              {donnees.Avenants?.length > 0 && (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                  Avenants déjà émis sur la période :{' '}
                  {donnees.Avenants.map((a) => `${formatDate(a.DateEffet)} - ${fcfa(a.PrimeTtc)} F TTC`).join(' ; ')}
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={onClose}>Annuler</button>
                <button type="button" className="btn btn-primary" onClick={creer} disabled={envoi || (mode === 'incorporation' && Boolean(famille) && !apres)}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <FilePlus2 size={15} /> {envoi ? 'Création…' : mode === 'incorporation' ? 'Incorporer' : 'Créer l\'avenant'}
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
