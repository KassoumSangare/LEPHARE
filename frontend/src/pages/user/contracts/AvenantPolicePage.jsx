import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, Ban, Car, FileSignature, Loader2, Search, UserMinus } from 'lucide-react';
import { contractApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { confirmer } from '../../../utils/dialogue';
import { messageErreurApi } from '../../../utils/financeUtils';
import { imprimerAvenantPolice } from '../../../utils/impressionsAvenants';

/* =========================================================================
   AVENANTS DE LA POLICE (production/avenants.py, demande du 2026-11-19)
   Retrait d'objets (flotte Automobile, polices de groupe), résiliation, changement d'immatriculation.
   Les montants viennent du serveur (simulation, rien n'est écrit) ; l'émission crée l'avenant et sa quittance.
   ========================================================================= */

const ACTES = {
  RET: { libelle: 'Retrait', icone: UserMinus, date: 'Date du retrait' },
  RES: { libelle: 'Résiliation', icone: Ban, date: 'Date de résiliation' },
  CHI: { libelle: 'Changement d’immatriculation', icone: Car, date: 'Date du changement' },
};
const ORDRE = ['RET', 'CHI', 'RES'];
const libelleRetrait = (idProduit) => ({ 1: 'Retirer un véhicule', 4: 'Retirer une maison' }[idProduit] || 'Retirer une personne');

const dateFr = (iso) => (iso ? String(iso).slice(0, 10).split('-').reverse().join('/') : '');
const montant = (v) => `${Math.round(Number(v) || 0).toLocaleString('fr-FR')} F`;
const lendemain = (iso) => {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

export const AvenantPolicePage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { success, error: toastError } = useToast();
  const [prep, setPrep] = useState(null);
  const [erreurChargement, setErreurChargement] = useState('');
  const [type, setType] = useState('');
  const [dateEffet, setDateEffet] = useState('');
  const [objets, setObjets] = useState([]);
  const [vehicule, setVehicule] = useState('');
  const [immatriculation, setImmatriculation] = useState('');
  const [ristourne, setRistourne] = useState(true);
  const [accessoire, setAccessoire] = useState('');
  const [motif, setMotif] = useState('');
  const [filtre, setFiltre] = useState('');
  const [calcul, setCalcul] = useState({ resultat: null, erreur: '', enCours: false });
  const [envoi, setEnvoi] = useState(false);
  const numeroCalcul = useRef(0);

  useEffect(() => {
    let actif = true;
    contractApi.preparerAvenant(id)
      .then((p) => {
        if (!actif) return;
        setPrep(p);
        const demande = String(params.get('type') || '').toUpperCase();
        const possible = ORDRE.filter((code) => p.Actes?.[code]?.Possible);
        setType(possible.includes(demande) ? demande : possible[0] || '');
        const { DateEffet: debut, DateExpiration: fin } = p.Contrat;
        setDateEffet(p.DateDuJour < debut ? debut : p.DateDuJour > fin ? fin : p.DateDuJour);
      })
      .catch((e) => { if (actif) setErreurChargement(messageErreurApi(e)); });
    return () => { actif = false; };
  }, [id]);

  const contrat = prep?.Contrat;
  const acte = prep?.Actes?.[type];
  // Ristourne proposée selon l'acte et la branche (tarifs forfaitaires : aucune par défaut)
  useEffect(() => {
    if (acte) setRistourne(Boolean(acte.RistourneParDefaut));
    setObjets([]);
    setVehicule('');
    setImmatriculation('');
  }, [type]);

  const aEcheance = type === 'RES' && contrat && dateEffet > contrat.DateExpiration;
  const payload = useMemo(() => ({
    Type: type,
    DateEffet: dateEffet,
    Objets: type === 'RET' ? objets : type === 'CHI' && vehicule ? [vehicule] : [],
    NouvelleImmatriculation: type === 'CHI' ? immatriculation.trim().toUpperCase() : '',
    Ristourne: type !== 'CHI' && ristourne && !aEcheance,
    Accessoire: Number(String(accessoire).replace(/\s/g, '')) || 0,
  }), [type, dateEffet, objets, vehicule, immatriculation, ristourne, aEcheance, accessoire]);
  const complet = Boolean(type && dateEffet) && (type !== 'RET' || objets.length > 0)
    && (type !== 'CHI' || (vehicule && payload.NouvelleImmatriculation.length >= 4));

  // Montants de l'avenant calculés par le serveur à chaque saisie ; une réponse dépassée est ignorée
  useEffect(() => {
    numeroCalcul.current += 1;
    const numero = numeroCalcul.current;
    if (!complet) {
      setCalcul({ resultat: null, erreur: '', enCours: false });
      return undefined;
    }
    setCalcul((c) => ({ ...c, enCours: true }));
    const minuteur = setTimeout(async () => {
      try {
        const resultat = await contractApi.simulerAvenant(id, payload);
        if (numero === numeroCalcul.current) setCalcul({ resultat, erreur: '', enCours: false });
      } catch (e) {
        if (numero === numeroCalcul.current) setCalcul({ resultat: null, erreur: messageErreurApi(e), enCours: false });
      }
    }, 400);
    return () => clearTimeout(minuteur);
  }, [payload, complet, id]);

  const objetsFiltres = (prep?.Objets || []).filter((o) => !filtre.trim()
    || `${o.Matricule} ${o.Libelle}`.toLowerCase().includes(filtre.trim().toLowerCase()));
  const basculer = (matricule) => setObjets((liste) => (liste.includes(matricule) ? liste.filter((m) => m !== matricule) : [...liste, matricule]));

  const emettre = async () => {
    if (motif.trim().length < 5) { toastError('Indiquez le motif de l’avenant (5 caractères au moins).'); return; }
    const r = calcul.resultat;
    if (!r) { toastError(calcul.erreur || 'Les montants de l’avenant ne sont pas encore calculés.'); return; }
    const ttc = Number(r.PrimeTtc) || 0;
    const incidence = ttc < 0 ? `Ristourne de ${montant(-ttc)} TTC au client.` : ttc > 0 ? `Prime de ${montant(ttc)} TTC.` : 'Sans incidence financière.';
    if (!(await confirmer({
      ton: type === 'RES' ? 'danger' : 'attention',
      titre: `Émettre l’avenant de ${ACTES[type].libelle.toLowerCase()} ?`,
      message: `Police ${contrat.NumeroPolice}, effet le ${dateFr(dateEffet)}. ${incidence}${type === 'RES' ? ' La police ne pourra plus être renouvelée.' : ''}`,
      confirmer: 'Émettre l’avenant',
      annuler: 'Revenir à la saisie',
    }))) return;
    setEnvoi(true);
    try {
      const resultat = await contractApi.emettreAvenant(id, { ...payload, Motif: motif.trim() });
      success(`Avenant n° ${resultat.NumeroAvenant} émis${resultat.NumeroQuittance ? `, quittance ${resultat.NumeroQuittance}` : ''}.`
        + (Number(resultat.PrimeTtc) < 0 && resultat.NumeroQuittance ? ' La ristourne se règle dans Caisse > Ristournes à régler.' : ''));
      imprimerAvenantPolice(resultat.IdContrat);
      navigate(`/user/contracts/${resultat.IdContrat}`);
    } catch (e) {
      toastError(`L’avenant n’a pas été émis : ${messageErreurApi(e)}`);
    } finally {
      setEnvoi(false);
    }
  };

  const r = calcul.resultat;
  const auto = Number(contrat?.IdProduit) === 1;

  return (
    <main className="page-container avenant-page">
      <button type="button" className="btn btn-secondary avenant-retour" onClick={() => navigate(`/user/contracts/${id}`)}>
        <ArrowLeft size={15} /> Retour au contrat
      </button>
      <h1 className="title-xl avenant-titre"><FileSignature size={24} /> Avenant de la police</h1>

      {!prep && !erreurChargement && <p role="status" className="avenant-attente"><Loader2 size={15} className="spin" /> Lecture du contrat…</p>}
      {erreurChargement && <p className="avenant-alerte" role="alert"><AlertTriangle size={15} /> {erreurChargement}</p>}

      {contrat && (
        <>
          <section className="glass-panel avenant-resume" aria-label="Contrat">
            <div><span>Police</span><strong>{contrat.NumeroPolice}</strong></div>
            <div><span>Souscripteur</span><strong title={contrat.Client}>{contrat.Client}</strong></div>
            <div><span>{contrat.Produit}</span><strong title={contrat.Compagnie}>{contrat.Compagnie}</strong></div>
            <div><span>Période</span><strong>{dateFr(contrat.DateEffet)} au {dateFr(contrat.DateExpiration)}</strong></div>
          </section>

          <nav className="avenant-actes" role="tablist" aria-label="Avenant">
            {ORDRE.map((code) => {
              const a = prep.Actes[code];
              const Icone = ACTES[code].icone;
              return (
                <button key={code} type="button" role="tab" aria-selected={type === code} disabled={!a.Possible}
                  className={`avenant-acte${type === code ? ' actif' : ''}`} onClick={() => setType(code)} title={a.Possible ? '' : a.Raison}>
                  <Icone size={17} />
                  <span>{code === 'RET' ? libelleRetrait(contrat.IdProduit) : ACTES[code].libelle}</span>
                </button>
              );
            })}
          </nav>

          {!type && <p className="avenant-alerte"><AlertTriangle size={15} /> {prep.Actes.RES.Raison || prep.Actes.RET.Raison}</p>}

          {type && (
            <div className="avenant-grille">
              <section className="glass-panel avenant-saisie" aria-label="Saisie de l'avenant">
                <div className="avenant-champs">
                  <label className="avenant-champ">
                    <span>{ACTES[type].date} *</span>
                    <input type="date" className="form-control" value={dateEffet} min={contrat.DateEffet}
                      max={type === 'RES' ? lendemain(contrat.DateExpiration) : contrat.DateExpiration}
                      onChange={(e) => setDateEffet(e.target.value)} />
                  </label>
                  {type === 'RES' && (
                    <div className="avenant-champ avenant-echeance">
                      <span>Échéance</span>
                      <button type="button" className={`btn btn-secondary${aEcheance ? ' actif' : ''}`} onClick={() => setDateEffet(lendemain(contrat.DateExpiration))}>
                        À l’échéance du {dateFr(contrat.DateExpiration)}
                      </button>
                    </div>
                  )}
                  <label className="avenant-champ">
                    <span>Accessoires de l’avenant</span>
                    <input type="text" inputMode="numeric" className="form-control" value={accessoire} placeholder="0"
                      onChange={(e) => setAccessoire(e.target.value.replace(/[^\d\s]/g, ''))} />
                  </label>
                </div>

                {type !== 'CHI' && (
                  <label className="avenant-option">
                    <input type="checkbox" checked={ristourne && !aEcheance} disabled={aEcheance} onChange={(e) => setRistourne(e.target.checked)} />
                    <span>Ristourne au prorata du temps restant à courir</span>
                  </label>
                )}

                {type === 'RET' && (
                  <fieldset className="avenant-objets">
                    <legend>{auto ? 'Véhicules' : 'Assurés'} à retirer · {objets.length} / {prep.Objets.length}</legend>
                    {prep.Objets.length > 8 && (
                      <div className="avenant-recherche">
                        <Search size={14} aria-hidden="true" />
                        <input type="search" className="form-control" value={filtre} onChange={(e) => setFiltre(e.target.value)}
                          placeholder={auto ? 'Immatriculation, marque…' : 'Nom, matricule…'} aria-label="Filtrer la liste" />
                      </div>
                    )}
                    <ul>
                      {objetsFiltres.map((o) => (
                        <li key={o.Matricule || o.IdContrat}>
                          <label className={objets.includes(o.Matricule) ? 'coche' : ''}>
                            <input type="checkbox" checked={objets.includes(o.Matricule)} onChange={() => basculer(o.Matricule)} />
                            <span className="avenant-objet-nom">{o.Libelle}</span>
                            <span className="avenant-objet-info">{o.Mouvement} · {montant(o.PrimeNette)}</span>
                          </label>
                        </li>
                      ))}
                    </ul>
                  </fieldset>
                )}

                {type === 'CHI' && (
                  <div className="avenant-champs">
                    <label className="avenant-champ">
                      <span>Véhicule *</span>
                      <select className="form-control" value={vehicule} onChange={(e) => setVehicule(e.target.value)}>
                        <option value="">Choisir le véhicule</option>
                        {prep.Objets.map((o) => <option key={o.Matricule} value={o.Matricule}>{o.Libelle}</option>)}
                      </select>
                    </label>
                    <label className="avenant-champ">
                      <span>Nouvelle immatriculation *</span>
                      <input type="text" className="form-control avenant-plaque" value={immatriculation} maxLength={20}
                        onChange={(e) => setImmatriculation(e.target.value.toUpperCase())} placeholder="Ex. 1234AB01" />
                    </label>
                  </div>
                )}

                <label className="avenant-champ avenant-motif">
                  <span>Motif *</span>
                  <textarea className="form-control" rows={3} value={motif} onChange={(e) => setMotif(e.target.value)}
                    placeholder={type === 'RES' ? 'Ex. : demande du client du 12/11/2026, vente du véhicule…' : 'Ex. : véhicule vendu, salarié sorti de l’entreprise…'} />
                </label>
              </section>

              <aside className="glass-panel avenant-montants" aria-label="Montants de l'avenant" aria-busy={calcul.enCours}>
                <h2>Montants {calcul.enCours && <Loader2 size={14} className="spin" aria-label="Calcul en cours" />}</h2>
                {!r && !calcul.erreur && (
                  <p className="avenant-vide">{type === 'RET' ? 'Cochez le ou les objets à retirer.' : type === 'CHI' ? 'Choisissez le véhicule et sa nouvelle immatriculation.' : 'Saisissez la date de résiliation.'}</p>
                )}
                {calcul.erreur && <p className="avenant-alerte" role="alert"><AlertTriangle size={15} /> {calcul.erreur}</p>}
                {r && (
                  <>
                    {r.Ristourne && r.Lignes.length > 0 && (
                      <ul className="avenant-lignes">
                        {r.Lignes.map((l) => (
                          <li key={l.Matricule || l.IdContratDetail}><span>{l.Libelle}</span><strong>{montant(l.PrimeNette + l.Fga)}</strong></li>
                        ))}
                      </ul>
                    )}
                    <dl className="avenant-totaux">
                      <div><dt>Prime nette</dt><dd>{montant(r.PrimeNette)}</dd></div>
                      {auto && Number(r.Fga) !== 0 && <div><dt>Dont FGA</dt><dd>{montant(r.Fga)}</dd></div>}
                      <div><dt>Accessoires</dt><dd>{montant(r.Accessoire)}</dd></div>
                      <div><dt>Taxe</dt><dd>{montant(r.Taxe)}</dd></div>
                      <div className="avenant-ttc"><dt>{r.PrimeTtc < 0 ? 'Ristourne TTC' : 'Prime TTC'}</dt><dd>{montant(Math.abs(r.PrimeTtc))}</dd></div>
                      {Number(r.Commission) !== 0 && <div className="avenant-secondaire"><dt>Commission du cabinet</dt><dd>{montant(r.Commission)}</dd></div>}
                    </dl>
                    {r.Ristourne && <p className="avenant-secondaire">{r.JoursRestants} jours restants sur {r.JoursPeriode}</p>}
                    {r.AEcheance && <p className="avenant-secondaire">Résiliation à l’échéance : aucune ristourne.</p>}
                  </>
                )}
                <button type="button" className="btn btn-primary avenant-emettre" onClick={emettre}
                  disabled={envoi || !r || calcul.enCours || motif.trim().length < 5}>
                  {envoi ? <Loader2 size={15} className="spin" /> : <FileSignature size={15} />} Émettre l’avenant
                </button>
              </aside>
            </div>
          )}
        </>
      )}
    </main>
  );
};

export default AvenantPolicePage;
