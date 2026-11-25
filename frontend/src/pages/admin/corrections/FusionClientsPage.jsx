import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertTriangle, ArrowLeftRight, ArrowRight, CheckCircle2, Loader2, Merge, Search, Users } from 'lucide-react';
import { correctionsApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { confirmer } from '../../../utils/dialogue';
import { dateFr, fcfa, messageErreurApi, normaliserTexte } from '../../../utils/financeUtils';

/* =========================================================================
   FICHES CLIENTS EN DOUBLE (Administration > Corrections, customer/fusion.py)
   Groupes de fiches de même nom (« certain » : même téléphone, date de naissance ou pièce), comparaison côte à côte, puis
   fusion : tout ce qui désigne la fiche en double passe sur la fiche gardée, qui reçoit les coordonnées qui lui manquent,
   le solde et l'avoir ; la fiche en double est archivée. Motif obligatoire, trace au journal et dans le registre du
   dédoublonnage. ?garder=&fusionner= : comparaison ouverte directement (centre des corrections).
   ========================================================================= */

const Fiche = ({ titre, fiche, garder }) => (
  <article className={`fusion-fiche${garder ? ' gardee' : ' fusionnee'}`}>
    <span className="fusion-role">{titre}</span>
    <strong>{fiche.Nom || 'Sans nom'}</strong>
    <span className="corr-muet">Fiche n° {fiche.IdClient} · {fiche.Particulier ? 'Personne' : 'Entreprise'}{fiche.Statut === 'A' ? ' · archivée' : ''}</span>
    <dl>
      {fiche.Piece && <div><dt>Pièce</dt><dd>{fiche.Piece}</dd></div>}
      {Object.entries(fiche.Coordonnees || {}).map(([libelle, valeur]) => (
        <div key={libelle}><dt>{libelle}</dt><dd>{String(valeur).slice(0, 10).match(/^\d{4}-\d{2}-\d{2}$/) ? dateFr(valeur) : String(valeur)}</dd></div>
      ))}
      {(fiche.Solde !== 0 || fiche.Avoir !== 0) && <div><dt>Solde / avoir</dt><dd>{fcfa(fiche.Solde)} F / {fcfa(fiche.Avoir)} F</dd></div>}
    </dl>
    <div className="fusion-rattachements">
      {fiche.Rattachements.length
        ? fiche.Rattachements.map((r) => <span key={r.Cle}>{r.Libelle} : <strong>{r.Nombre}</strong></span>)
        : <span className="corr-muet">Aucun contrat, devis ni quittance</span>}
    </div>
  </article>
);

export const FusionClientsPage = () => {
  const { success, error: toastError } = useToast();
  const [parametres, setParametres] = useSearchParams();
  const [doublons, setDoublons] = useState(null);
  const [filtre, setFiltre] = useState('certains');
  const [recherche, setRecherche] = useState('');
  const [garder, setGarder] = useState(parametres.get('garder') || '');
  const [fusionner, setFusionner] = useState(parametres.get('fusionner') || '');
  const [apercu, setApercu] = useState(null);
  const [chargementApercu, setChargementApercu] = useState(false);
  const [motif, setMotif] = useState('');
  const [enregistrement, setEnregistrement] = useState(false);
  const [bilan, setBilan] = useState(null);

  const chargerDoublons = () => correctionsApi.doublonsClients().then(setDoublons).catch((e) => toastError(messageErreurApi(e)));
  const comparer = async (g = garder, f = fusionner) => {
    if (!Number(g) || !Number(f)) return;
    setChargementApercu(true);
    setBilan(null);
    try {
      setApercu(await correctionsApi.apercuFusion(g, f));
    } catch (e) {
      setApercu(null);
      toastError(messageErreurApi(e));
    } finally {
      setChargementApercu(false);
    }
  };
  useEffect(() => {
    chargerDoublons();
    if (parametres.get('garder')) {
      setParametres({}, { replace: true });
      comparer(parametres.get('garder'), parametres.get('fusionner'));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const choisir = (g, f) => {
    setGarder(String(g));
    setFusionner(String(f));
    setMotif('');
    comparer(g, f);
  };
  const inverser = () => choisir(fusionner, garder);

  const groupes = useMemo(() => (doublons?.Groupes || []).filter((g) => (filtre === 'tous' || (filtre === 'certains') === g.Certain)
    && (!recherche.trim() || normaliserTexte(g.Nom).includes(normaliserTexte(recherche.trim())) || g.Fiches.some((f) => String(f.IdClient) === recherche.trim()))), [doublons, filtre, recherche]);

  const fusionnerFiches = async () => {
    if (!apercu?.Garder || apercu.Refus?.length || motif.trim().length < 5) return;
    const ok = await confirmer({
      ton: 'danger',
      titre: 'Fusionner les deux fiches ?',
      message: `La fiche n° ${apercu.Fusionner.IdClient} (${apercu.Fusionner.Nom}) sera archivée ; tout ce qu'elle porte passe sur la fiche n° ${apercu.Garder.IdClient}.`,
      confirmer: 'Fusionner',
      annuler: 'Revenir',
    });
    if (!ok) return;
    setEnregistrement(true);
    try {
      const r = await correctionsApi.fusionnerClients(apercu.Garder.IdClient, apercu.Fusionner.IdClient, motif.trim());
      setBilan(r);
      setApercu(null);
      setMotif('');
      success(`Fiche n° ${r.Fusionner} fusionnée dans la fiche n° ${r.Garder}.`);
      chargerDoublons();
    } catch (e) {
      toastError(messageErreurApi(e));
    } finally {
      setEnregistrement(false);
    }
  };

  return (
    <div className="corr-page">
      <header className="corr-entete">
        <span className="corr-entete-icone" aria-hidden="true"><Users size={22} /></span>
        <div>
          <h1 className="title-xl">Fiches clients en double</h1>
          <p>Comparer deux fiches puis fusionner : contrats, devis, quittances et chèques passent sur la fiche gardée.</p>
        </div>
        <Link to="/admin/corrections" className="btn btn-secondary">Centre des corrections</Link>
      </header>

      <div className="fusion-grille">
        <aside className="glass-panel fusion-groupes" aria-label="Doublons probables">
          <div className="cs-onglets-boutons" role="tablist" aria-label="Doublons">
            {[['certains', `Certains${doublons ? ` (${doublons.Certains})` : ''}`], ['verifier', 'À vérifier'], ['tous', 'Tous']].map(([cle, libelle]) => (
              <button key={cle} type="button" role="tab" aria-selected={filtre === cle} className={`cs-onglet${filtre === cle ? ' actif' : ''}`} onClick={() => setFiltre(cle)}>{libelle}</button>
            ))}
          </div>
          <label className="fusion-filtre">
            <Search size={15} aria-hidden="true" />
            <input type="search" value={recherche} onChange={(e) => setRecherche(e.target.value)} placeholder="Nom ou n° de fiche" aria-label="Filtrer les doublons" />
          </label>
          {!doublons && <p className="corr-muet"><Loader2 className="spin" size={15} /> Recherche des doublons…</p>}
          <ul>
            {groupes.map((g) => (
              <li key={g.Nom} className="fusion-groupe">
                <div className="fusion-groupe-tete">
                  <strong>{g.Nom}</strong>
                  {g.Certain ? <span className="badge badge-rose">Doublon</span> : <span className="badge badge-amber">À vérifier</span>}
                </div>
                {g.Fiches.map((f, i) => (
                  <div key={f.IdClient} className="fusion-groupe-fiche">
                    <span>
                      n° {f.IdClient} · {f.Contrats} contrat{f.Contrats > 1 ? 's' : ''}, {f.Devis} devis
                      <small>{[f.Telephone, f.Naissance && `né le ${dateFr(f.Naissance)}`, f.Piece].filter(Boolean).join(' · ')}</small>
                    </span>
                    {i > 0 && (
                      <button type="button" className="btn btn-secondary" onClick={() => choisir(g.Fiches[0].IdClient, f.IdClient)}
                        title={`Comparer avec la fiche n° ${g.Fiches[0].IdClient}`}>
                        Comparer <ArrowRight size={13} />
                      </button>
                    )}
                  </div>
                ))}
              </li>
            ))}
            {doublons && !groupes.length && <li className="corr-muet">Aucun doublon dans cette liste.</li>}
          </ul>
        </aside>

        <section className="fusion-comparaison" aria-label="Comparaison">
          <form className="glass-panel fusion-choix" onSubmit={(e) => { e.preventDefault(); comparer(); }}>
            <label>Fiche à garder n°<input className="form-control" inputMode="numeric" value={garder} onChange={(e) => setGarder(e.target.value.replace(/\D/g, ''))} /></label>
            <label>Fiche à fusionner n°<input className="form-control" inputMode="numeric" value={fusionner} onChange={(e) => setFusionner(e.target.value.replace(/\D/g, ''))} /></label>
            <button type="submit" className="btn btn-primary" disabled={!garder || !fusionner || chargementApercu}>
              {chargementApercu ? <Loader2 className="spin" size={15} /> : <Search size={15} />} Comparer
            </button>
          </form>

          {bilan && (
            <div className="glass-panel fusion-bilan" role="status">
              <CheckCircle2 size={28} aria-hidden="true" />
              <div>
                <strong>Fiche n° {bilan.Fusionner} fusionnée dans la fiche n° {bilan.Garder} ({bilan.Nom})</strong>
                <span>{bilan.Rattachements.map((r) => `${r.Libelle} : ${r.Nombre}`).join(' · ') || 'Aucune ligne à déplacer'}</span>
                {bilan.Completes.length > 0 && <span>Coordonnées reprises : {bilan.Completes.join(', ')}</span>}
                <Link to={`/user/clients/${bilan.Garder}`}>Ouvrir la fiche gardée</Link>
              </div>
            </div>
          )}

          {apercu?.Garder && (
            <div className="glass-panel fusion-apercu">
              <div className="fusion-fiches">
                <Fiche titre="Fiche gardée" fiche={apercu.Garder} garder />
                <button type="button" className="fusion-inverser" onClick={inverser} title="Garder plutôt l'autre fiche" aria-label="Inverser les deux fiches">
                  <ArrowLeftRight size={18} />
                </button>
                <Fiche titre="Fiche fusionnée puis archivée" fiche={apercu.Fusionner} />
              </div>
              {apercu.Completes.length > 0 && <p className="corr-muet">Reprises sur la fiche gardée : {apercu.Completes.join(', ')}.</p>}
              {apercu.Refus.length > 0 ? (
                <ul className="guichet-erreurs" role="alert">{apercu.Refus.map((r) => <li key={r}>{r}</li>)}</ul>
              ) : (
                <>
                  <label className="admin-motif">
                    <span>Motif de la fusion (obligatoire, conservé au journal)</span>
                    <textarea className="form-control" rows={2} value={motif} onChange={(e) => setMotif(e.target.value)} placeholder="Ex. : même client saisi deux fois à la création du devis" />
                  </label>
                  <div className="fusion-actions">
                    <button type="button" className="btn btn-primary" onClick={fusionnerFiches} disabled={enregistrement || motif.trim().length < 5}>
                      {enregistrement ? <Loader2 className="spin" size={15} /> : <Merge size={15} />}
                      Fusionner la fiche n° {apercu.Fusionner.IdClient} dans la fiche n° {apercu.Garder.IdClient}
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
          {apercu && !apercu.Garder && (
            <ul className="guichet-erreurs" role="alert">{(apercu.Refus || []).map((r) => <li key={r}><AlertTriangle size={13} /> {r}</li>)}</ul>
          )}
          {!apercu && !bilan && <p className="corr-muet fusion-vide">Choisissez un doublon dans la liste ou saisissez deux numéros de fiche.</p>}
        </section>
      </div>
    </div>
  );
};

export default FusionClientsPage;
