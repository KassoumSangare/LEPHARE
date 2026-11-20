import React, { useEffect, useMemo, useState } from 'react';
import {
  ChevronRight, CircleAlert, CircleCheck, CircleDashed, Filter, Info, Loader2, RotateCcw, Search, ShieldAlert, TriangleAlert,
} from 'lucide-react';
import { consommationsApi } from '../../../../api/endpoints';
import { useToast } from '../../../../context/ToastContext';
import { dateFr, messageErreurApi } from '../../../../utils/financeUtils';
import { Tiroir } from './AnalyseConsommations';
import {
  BarreSegmentee, BarresClassees, Cadre, Colonnes, EchelleChaleur, Jauge, Pyramide, Sparkline, TableauChaleur, entier, francs, francsCourts, pct,
} from './graphiques';

/* =========================================================================
   CONSOMMATIONS MINENE SANTÉ (sante/consommations_minene.py, demande du 2026-11-19)
   Détail des sinistres du gestionnaire (états personnalisés, garant OREOLEMINENE) : tiers payant et remboursement direct, affections,
   familles rattachées aux polices MINENE de LE PHARE (formule, prime acquise, taux de consommation), prestataires, profil, anomalies.
   Une lecture GET /api/consommations/minene/ partagée par les quatre onglets.
   ========================================================================= */

export const ONGLETS_MINENE = new Set(['m-ensemble', 'm-entreprises', 'm-familles', 'm-prestations', 'm-beneficiaires']);
export const FILTRES_MINENE = { du: '', au: '', police: '', entreprise: '' };
const MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
const libelleMois = (code) => { const [a, m] = String(code).split('-'); return `${MOIS[Number(m) - 1] || m} ${a}`; };
const SITUATIONS = {
  DEPASSEE: { libelle: 'Prime dépassée', ton: 'critique', icone: CircleAlert, jauge: 'critique' },
  A_SURVEILLER: { libelle: 'À surveiller', ton: 'attention', icone: TriangleAlert, jauge: 'attention' },
  NORMALE: { libelle: 'Normale', ton: 'bon', icone: CircleCheck, jauge: 'normal' },
  SANS_CONTRAT: { libelle: 'Sans contrat LE PHARE', ton: 'neutre', icone: CircleDashed, jauge: 'normal' },
};
const tonTaux = (t) => (t === null || t === undefined ? 'normal' : t >= 1 ? 'critique' : t >= 0.8 ? 'attention' : 'normal');

// ------------------------------------------------------------------ lecture partagée
// version : changée après un import, elle fait relire l'analyse sans recharger la page
export const useMinene = (filtres, actif, version = 0) => {
  const { error: toastError } = useToast();
  const [etat, setEtat] = useState({ donnees: null, chargement: false, cle: null });
  const cle = JSON.stringify([filtres, version]);
  useEffect(() => {
    if (!actif || etat.cle === cle) return undefined;
    let annule = false;
    setEtat((e) => ({ ...e, chargement: true }));
    consommationsApi.minene(filtres)
      .then((donnees) => { if (!annule) setEtat({ donnees, chargement: false, cle }); })
      .catch((err) => {
        if (annule) return;
        setEtat((e) => ({ ...e, chargement: false, cle }));
        toastError(`Analyse MINENE impossible : ${messageErreurApi(err)}`);
      });
    return () => { annule = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cle, actif, etat.cle]);
  return [etat.donnees, etat.chargement];
};

// ------------------------------------------------------------------ briques
const Carte = ({ titre, sousTitre, children, className = '' }) => (
  <section className={`glass-panel cs-carte ${className}`}>
    {titre && (
      <header className="cs-carte-entete">
        <div>
          <h2>{titre}</h2>
          {sousTitre && <p>{sousTitre}</p>}
        </div>
      </header>
    )}
    {children}
  </section>
);

const Tuile = ({ libelle, valeur, detail, children }) => (
  <div className="cs-tuile">
    <div className="cs-tuile-libelle">{libelle}</div>
    <div className="cs-tuile-corps"><div className="cs-tuile-valeur">{valeur}</div></div>
    {children}
    {detail && <div className="cs-tuile-detail">{detail}</div>}
  </div>
);

const Situation = ({ code }) => {
  const s = SITUATIONS[code] || SITUATIONS.SANS_CONTRAT;
  const Icone = s.icone;
  return <span className={`cs-etat ton-${s.ton}`}><Icone size={13} aria-hidden="true" />{s.libelle}</span>;
};

const Vide = ({ texte }) => <p className="cs-vide etat-anime">{texte}</p>;

const barres = (lignes, annexe) => lignes.map((l) => ({
  cle: String(l.Code ?? l.Libelle), libelle: l.Libelle || 'Non renseigné', valeur: l.Rembourse,
  detail: `${entier(l.Prestations)} prestation${l.Prestations > 1 ? 's' : ''} · ${pct(l.Part, 0)}`,
  annexes: annexe ? annexe(l) : undefined,
}));

// ------------------------------------------------------------------ filtres
export const FiltresMinene = ({ filtres, setFiltres, donnees, chargement }) => {
  const champ = (cle) => (e) => setFiltres((f) => ({ ...f, [cle]: e.target.value }));
  const actifs = Object.values(filtres).some(Boolean);
  return (
    <div className="glass-panel cs-filtres" role="search" aria-label="Filtres de l'analyse MINENE">
      <label className="cs-filtre">
        <span>Soins du</span>
        <input type="date" className="form-control" value={filtres.du} onChange={champ('du')} />
      </label>
      <label className="cs-filtre">
        <span>au</span>
        <input type="date" className="form-control" value={filtres.au} onChange={champ('au')} />
      </label>
      <label className="cs-filtre large">
        <span>Police du gestionnaire</span>
        <select className="form-control" value={filtres.police} onChange={champ('police')}>
          <option value="">Toutes les polices MINENE</option>
          {(donnees?.Filtres?.Polices || []).map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </label>
      <label className="cs-filtre large">
        <span>Entreprise</span>
        <select className="form-control" value={filtres.entreprise} onChange={champ('entreprise')}>
          <option value="">Toutes les entreprises</option>
          {(donnees?.Filtres?.Entreprises || []).map((e) => <option key={e} value={e}>{e}</option>)}
        </select>
      </label>
      {actifs && (
        <button type="button" className="btn btn-secondary cs-filtre-bouton" onClick={() => setFiltres(FILTRES_MINENE)}>
          <RotateCcw size={14} aria-hidden="true" /> Réinitialiser
        </button>
      )}
      <p className="cs-filtres-note" aria-live="polite">
        {chargement ? <><Loader2 size={13} className="spin" aria-hidden="true" /> Calcul en cours…</>
          : donnees?.Periode?.Du ? `Soins du ${dateFr(donnees.Periode.Du)} au ${dateFr(donnees.Periode.Au)}, ${donnees.Periode.NombreMois} mois.` : ''}
      </p>
    </div>
  );
};

// ------------------------------------------------------------------ vue d'ensemble
const Ensemble = ({ d }) => {
  const i = d.Indicateurs;
  const points = d.ParMois.map((m) => ({ cle: m.Code, libelle: libelleMois(m.Code), libelleCourt: libelleMois(m.Code).split(' ')[0], valeur: m.Rembourse, prestations: m.Prestations }));
  const a = d.Anomalies;
  return (
    <>
      <div className="cs-tuiles">
        <Tuile libelle="Remboursé" valeur={francsCourts(i.Rembourse)} detail={`Réclamé ${francs(i.Reclame)}`} />
        <Tuile libelle="Prestations" valeur={entier(i.Prestations)} detail={`${entier(i.Beneficiaires)} bénéficiaires · ${entier(i.Familles)} familles`} />
        <Tuile libelle="Prise en charge" valeur={pct(i.TauxPriseEnCharge, 0)} detail={`À la charge des assurés : ${francs(i.PartAssures)}`}>
          <Jauge taux={i.TauxPriseEnCharge} libelle="Part des montants réclamés remboursée" fine />
        </Tuile>
        <Tuile libelle="Coût moyen" valeur={francs(i.CoutMoyenBeneficiaire)} detail={`par bénéficiaire · ${francs(i.CoutMoyenPrestation)} par prestation`} />
        <Tuile libelle="Consommation du portefeuille" valeur={i.TauxConsommation === null ? '-' : pct(i.TauxConsommation)}
          detail={`${francs(i.RembourseRattache)} sur ${francs(i.PrimesAcquises)} de primes acquises · ${entier(i.FamillesPortefeuille)} familles`}>
          <Jauge taux={i.TauxConsommation} repere={0.8} ton={tonTaux(i.TauxConsommation)} libelle="Remboursements face aux primes acquises" fine />
        </Tuile>
      </div>

      <div className="cs-deux">
        <Carte titre="Remboursements par mois" sousTitre="Selon la date des soins">
          {points.length ? (
            <Cadre tableau={{ entetes: ['Mois', 'Prestations', 'Remboursé'], lignes: d.ParMois.map((m) => [libelleMois(m.Code), entier(m.Prestations), francs(m.Rembourse)]) }}>
              <Colonnes points={points} libelleAria="Remboursements par mois"
                lignesBulle={(p) => [{ libelle: 'Remboursé', valeur: francs(p.valeur), couleur: 'var(--cs-viz-1)' }, { libelle: 'Prestations', valeur: entier(p.prestations) }]} />
            </Cadre>
          ) : <Vide texte="Aucune prestation sur la période." />}
        </Carte>
        <Carte titre="Mode de prise en charge" sousTitre="Tiers payant et remboursement direct">
          <Cadre tableau={{ entetes: ['Mode', 'Prestations', 'Remboursé', 'Part'], lignes: d.ParType.map((t) => [t.Libelle, entier(t.Prestations), francs(t.Rembourse), pct(t.Part, 0)]) }}>
            <BarreSegmentee parts={d.ParType.map((t) => ({ libelle: t.Libelle, valeur: t.Rembourse }))} libelleAria="Remboursements par mode de prise en charge" />
          </Cadre>
          <Cadre titre="Familles de prestations">
            <BarresClassees lignes={barres(d.ParFamillePrestation.slice(0, 6))} libelleValeur="Remboursé" />
          </Cadre>
        </Carte>
      </div>

      <div className={a ? 'cs-deux' : 'cs-pile'}>
        <Carte titre="Constats">
          {d.Constats.length ? (
            <ul className="cs-constats">
              {d.Constats.map((c) => <li key={c} className="ton-info"><Info size={16} aria-hidden="true" /><div><p>{c}</p></div></li>)}
            </ul>
          ) : <Vide texte="Aucun constat sur la période." />}
        </Carte>
        {a && <Carte titre="Anomalies" sousTitre="Règles des consommations sur les seules prestations MINENE">
          {a.Signales ? (
            <>
              <div className="cs-tuiles compactes">
                <Tuile libelle="Bénéficiaires signalés" valeur={entier(a.Signales)} />
                {Object.entries(a.Niveaux).map(([niveau, n]) => <Tuile key={niveau} libelle={`Niveau ${niveau.toLowerCase()}`} valeur={entier(n)} />)}
              </div>
              <ul className="cs-constats">
                {a.Regles.slice(0, 5).map((r) => (
                  <li key={r.Regle} className="ton-attention"><ShieldAlert size={16} aria-hidden="true" /><div><strong>{r.Regle}</strong><p>{entier(r.Signaux)} signal{r.Signaux > 1 ? 'aux' : ''}</p></div></li>
                ))}
              </ul>
            </>
          ) : <Vide texte="Aucune anomalie détectée." />}
        </Carte>}
      </div>
    </>
  );
};

// ------------------------------------------------------------------ familles et formules
const Familles = ({ d }) => (
  <>
    <Carte titre="Formules MINENE" sousTitre="Familles en vigueur dans LE PHARE, primes acquises sur la période et remboursements de leurs membres">
      {d.Formules.length ? (
        <div className="table-wrapper">
          <table className="data-table">
            <thead><tr><th>Formule</th><th className="cs-nombre">Familles</th><th className="cs-nombre">Personnes</th><th className="cs-nombre">Consommatrices</th>
              <th className="cs-nombre">Primes acquises</th><th className="cs-nombre">Remboursé</th><th>Consommation</th><th className="cs-nombre">Coût moyen par famille</th></tr></thead>
            <tbody>
              {d.Formules.map((f) => (
                <tr key={f.Formule}>
                  <td><strong>{f.Formule}</strong></td><td className="cs-nombre">{entier(f.Familles)}</td><td className="cs-nombre">{entier(f.Personnes)}</td>
                  <td className="cs-nombre">{entier(f.Consommatrices)}</td><td className="cs-nombre">{francs(f.PrimesAcquises)}</td><td className="cs-nombre">{francs(f.Rembourse)}</td>
                  <td className="cs-cellule-jauge"><Jauge taux={f.Taux} repere={0.8} ton={tonTaux(f.Taux)} libelle={`Consommation ${f.Formule}`} fine /><span>{f.Taux === null ? '-' : pct(f.Taux)}</span></td>
                  <td className="cs-nombre">{francs(f.CoutMoyenFamille)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <Vide texte="Aucune police MINENE en vigueur dans LE PHARE." />}
    </Carte>
    <Carte titre="Familles consommatrices" sousTitre="Assuré principal du relevé ; prime acquise = prime nette annuelle de la formule au prorata des mois de la période">
      {d.Familles.length ? (
        <div className="table-wrapper">
          <table className="data-table">
            <thead><tr><th>Famille</th><th>Police du gestionnaire</th><th>Police LE PHARE · formule</th><th className="cs-nombre">Bénéficiaires</th>
              <th className="cs-nombre">Prestations</th><th className="cs-nombre">Remboursé</th><th>Consommation</th><th className="cs-nombre">Projection 12 mois</th><th>Situation</th></tr></thead>
            <tbody>
              {d.Familles.map((f) => (
                <tr key={f.Code}>
                  <td><strong>{f.Libelle}</strong><div className="cs-muet">{f.Code}</div></td>
                  <td>{f.PoliceGestionnaire || '-'}</td>
                  <td>{f.PoliceLePhare ? <>{f.PoliceLePhare}<div className="cs-muet">{f.Formule}</div></> : '-'}</td>
                  <td className="cs-nombre">{entier(f.Beneficiaires)}</td><td className="cs-nombre">{entier(f.Prestations)}</td><td className="cs-nombre">{francs(f.Rembourse)}</td>
                  <td className="cs-cellule-jauge">{f.Taux === null ? <span className="cs-muet">-</span> : <><Jauge taux={f.Taux} repere={0.8} ton={SITUATIONS[f.Situation]?.jauge} libelle={`Consommation de la famille ${f.Libelle}`} fine /><span>{pct(f.Taux)}</span></>}</td>
                  <td className="cs-nombre">{f.Projection === null ? '-' : pct(f.Projection, 0)}</td>
                  <td><Situation code={f.Situation} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <Vide texte="Aucune famille sur la période." />}
    </Carte>
  </>
);

// ------------------------------------------------------------------ prestations
const Prestations = ({ d }) => {
  const colonnes = d.Chaleur.Mois.map((m) => ({ cle: m, libelle: libelleMois(m).split(' ')[0], libelleLong: libelleMois(m) }));
  return (
    <>
      <div className="cs-deux">
        <Carte titre="Familles de prestations">
          <Cadre tableau={{ entetes: ['Famille', 'Prestations', 'Remboursé', 'Coût moyen'], lignes: d.ParFamillePrestation.map((l) => [l.Libelle, entier(l.Prestations), francs(l.Rembourse), francs(l.CoutMoyen)]) }}>
            <BarresClassees lignes={barres(d.ParFamillePrestation, (l) => [francs(l.CoutMoyen)])} colonnes={['Coût moyen']} libelleValeur="Remboursé" />
          </Cadre>
        </Carte>
        <Carte titre="Types d’affection" sousTitre="Selon le gestionnaire">
          {d.ParAffection.some((l) => l.Libelle !== 'Non renseigné') ? (
            <Cadre tableau={{ entetes: ['Affection', 'Prestations', 'Bénéficiaires', 'Remboursé'], lignes: d.ParAffection.map((l) => [l.Libelle, entier(l.Prestations), entier(l.Beneficiaires), francs(l.Rembourse)]) }}>
              <BarresClassees lignes={barres(d.ParAffection, (l) => [entier(l.Beneficiaires)])} colonnes={['Bénéficiaires']} libelleValeur="Remboursé" />
            </Cadre>
          ) : <Vide texte="Type d'affection absent des relevés importés." />}
        </Carte>
      </div>
      {colonnes.length > 1 && (
        <Carte titre="Familles de prestations par mois">
          <TableauChaleur colonnes={colonnes} lignes={d.Chaleur.Lignes.map((l) => ({ cle: l.Libelle, libelle: l.Libelle, valeurs: l.Valeurs }))} libelleLigne="Famille" />
          <EchelleChaleur />
        </Carte>
      )}
      <div className="cs-deux">
        <Carte titre="Actes les plus remboursés">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Acte</th><th className="cs-nombre">Prestations</th><th className="cs-nombre">Remboursé</th><th className="cs-nombre">Coût moyen</th></tr></thead>
              <tbody>{d.Actes.map((l) => <tr key={l.Code}><td>{l.Libelle}<div className="cs-muet">{l.Code}</div></td><td className="cs-nombre">{entier(l.Prestations)}</td><td className="cs-nombre">{francs(l.Rembourse)}</td><td className="cs-nombre">{francs(l.CoutMoyen)}</td></tr>)}</tbody>
            </table>
          </div>
        </Carte>
        <Carte titre="Centres exécutants">
          <BarresClassees lignes={d.Centres.map((c) => ({ cle: c.Code, libelle: c.Libelle, valeur: c.Rembourse, detail: [c.Localite, `${entier(c.Prestations)} prestations`].filter(Boolean).join(' · ') }))} libelleValeur="Remboursé" />
        </Carte>
      </div>
      <div className="cs-deux">
        <Carte titre="Communes des centres">
          <BarresClassees lignes={barres(d.Localites)} libelleValeur="Remboursé" />
        </Carte>
        <Carte titre="Médecins">
          <BarresClassees lignes={barres(d.Medecins, (l) => [entier(l.Beneficiaires)])} colonnes={['Bénéficiaires']} libelleValeur="Remboursé" />
        </Carte>
      </div>
    </>
  );
};

// ------------------------------------------------------------------ bénéficiaires
const Beneficiaires = ({ d }) => (
  <>
    <div className="cs-deux">
      <Carte titre="Statut dans la famille">
        <Cadre tableau={{ entetes: ['Statut', 'Bénéficiaires', 'Prestations', 'Remboursé'], lignes: d.ParStatut.map((l) => [l.Libelle, entier(l.Beneficiaires), entier(l.Prestations), francs(l.Rembourse)]) }}>
          <BarreSegmentee parts={d.ParStatut.map((l) => ({ libelle: l.Libelle, valeur: l.Rembourse }))} libelleAria="Remboursements par statut" />
        </Cadre>
      </Carte>
      <Carte titre="Sexe">
        <Cadre tableau={{ entetes: ['Sexe', 'Bénéficiaires', 'Prestations', 'Remboursé'], lignes: d.ParSexe.map((l) => [l.Libelle, entier(l.Beneficiaires), entier(l.Prestations), francs(l.Rembourse)]) }}>
          <BarreSegmentee parts={d.ParSexe.map((l) => ({ libelle: l.Libelle, valeur: l.Rembourse }))} libelleAria="Remboursements par sexe" />
        </Cadre>
      </Carte>
    </div>
    <Carte titre="Remboursements par âge et par sexe" sousTitre="Âge à la date des soins, en francs">
      {d.Pyramide.length ? (
        <Cadre tableau={{ entetes: ['Tranche', 'Femmes', 'Hommes', 'Bénéficiaires'], lignes: d.Pyramide.map((l) => [l.Tranche, francs(l.Femmes), francs(l.Hommes), entier(l.Beneficiaires)]) }}>
          <Pyramide lignes={d.Pyramide.map((l) => ({ cle: l.Tranche, libelle: l.Tranche, gauche: l.Femmes, droite: l.Hommes }))} libelleGauche="Femmes" libelleDroite="Hommes" />
        </Cadre>
      ) : <Vide texte="Aucune date de naissance dans les relevés." />}
    </Carte>
    {d.Anomalies && <Carte titre="Bénéficiaires signalés" sousTitre="Score des anomalies, du plus élevé au plus faible">
      {d.Anomalies.Beneficiaires.length ? (
        <div className="table-wrapper">
          <table className="data-table">
            <thead><tr><th>Bénéficiaire</th><th>Police</th><th className="cs-nombre">Score</th><th>Niveau</th><th className="cs-nombre">Montant concerné</th><th>Règles</th></tr></thead>
            <tbody>
              {d.Anomalies.Beneficiaires.map((b) => (
                <tr key={b.MatriculeBeneficiaire}>
                  <td><strong>{b.Beneficiaire}</strong><div className="cs-muet">{b.MatriculeBeneficiaire}</div></td><td>{b.Police}</td>
                  <td className="cs-nombre">{entier(b.Score)}</td><td>{b.Niveau}</td><td className="cs-nombre">{francs(b.Montant)}</td>
                  <td>{Object.entries(b.Regles || {}).map(([code, n]) => `${code} × ${n}`).join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <Vide texte="Aucun bénéficiaire signalé." />}
    </Carte>}
  </>
);

// ------------------------------------------------------------------ entreprises (demande du 2026-11-20)
// Entreprise = souscripteur du relevé du gestionnaire ; rattachée à LE PHARE par ses membres ou par le nom du souscripteur de la police
const modes = (e) => (e.Rembourse ? `TP ${pct(e.TiersPayant / e.Rembourse, 0)} · RD ${pct(e.RemboursementDirect / e.Rembourse, 0)}` : '-');
const polices = (e) => [
  e.PolicesGestionnaire?.length ? `police MCI ${e.PolicesGestionnaire.join(', ')}` : '',
  e.PolicesLePhare?.length ? `LE PHARE ${e.PolicesLePhare.join(', ')}` : '',
].filter(Boolean).join(' - ');
const ORDRE_SITUATIONS_MINENE = ['DEPASSEE', 'A_SURVEILLER', 'NORMALE', 'SANS_CONTRAT'];

const Entreprises = ({ d, onOuvrir }) => {
  const [texte, setTexte] = useState('');
  const [situation, setSituation] = useState('');
  const comptes = useMemo(() => d.Entreprises.reduce((c, e) => ({ ...c, [e.Situation]: (c[e.Situation] || 0) + 1 }), {}), [d.Entreprises]);
  const lignes = useMemo(() => {
    const q = texte.trim().toLowerCase();
    return d.Entreprises.filter((e) => (!situation || e.Situation === situation)
      && (!q || `${e.Libelle} ${polices(e)} ${e.PremierPoste} ${e.PremiereAffection}`.toLowerCase().includes(q)));
  }, [d.Entreprises, texte, situation]);
  const premiere = d.Entreprises[0];
  return (
    <>
      <div className="cs-tuiles">
        <Tuile libelle="Entreprises" valeur={entier(d.Entreprises.length)} detail={`${entier(d.Indicateurs.Familles)} familles et ${entier(d.Indicateurs.Beneficiaires)} bénéficiaires consommateurs`} />
        <Tuile libelle="Première entreprise" valeur={premiere ? pct(premiere.Part, 0) : '-'} detail={premiere ? `${premiere.Libelle} · ${francs(premiere.Rembourse)}` : ''} />
        <Tuile libelle="Primes à surveiller ou dépassées" valeur={entier((comptes.DEPASSEE || 0) + (comptes.A_SURVEILLER || 0))} detail="consommation d'au moins 80 % des primes acquises" />
        <Tuile libelle="Sans police LE PHARE" valeur={entier(comptes.SANS_CONTRAT || 0)} detail="ni membre ni souscripteur retrouvé dans LE PHARE" />
      </div>
      <Carte titre={`Entreprises : ${entier(lignes.length)}`} sousTitre="Cliquez une entreprise pour le détail de sa consommation : mois, prise en charge, postes, affections, familles, centres et actes.">
        <div className="cs-outils">
          <div className="cs-pastilles" role="group" aria-label="Situation face aux primes acquises">
            <button type="button" className={`cs-pastille${!situation ? ' active' : ''}`} aria-pressed={!situation} onClick={() => setSituation('')}>
              Toutes <span>{entier(d.Entreprises.length)}</span>
            </button>
            {ORDRE_SITUATIONS_MINENE.filter((s) => comptes[s]).map((s) => {
              const Icone = SITUATIONS[s].icone;
              return (
                <button key={s} type="button" className={`cs-pastille ton-${SITUATIONS[s].ton}${situation === s ? ' active' : ''}`} aria-pressed={situation === s}
                  onClick={() => setSituation(situation === s ? '' : s)}>
                  <Icone size={13} aria-hidden="true" />{SITUATIONS[s].libelle} <span>{entier(comptes[s])}</span>
                </button>
              );
            })}
          </div>
          <div className="cs-outils-droite">
            <label className="cs-recherche">
              <Search size={14} aria-hidden="true" />
              <input className="form-control" value={texte} onChange={(e) => setTexte(e.target.value)} placeholder="Entreprise, police, poste ou affection" aria-label="Rechercher une entreprise" />
            </label>
          </div>
        </div>
        <div className="table-wrapper cs-table-entreprises">
          <table className="data-table">
            <thead>
              <tr>
                <th>Entreprise</th><th className="cs-nombre">Bénéficiaires</th><th className="cs-nombre">Prestations</th><th className="cs-nombre">Remboursé par mois</th>
                <th className="cs-nombre">Coût / bénéf.</th><th>Prise en charge</th><th>Consommation des primes</th><th>Situation</th><th aria-label="Ouvrir" />
              </tr>
            </thead>
            <tbody>
              {lignes.map((e) => (
                <tr key={e.Code} className="cs-ligne-cliquable" onClick={() => onOuvrir(e)}>
                  <td>
                    <button type="button" className="cs-lien-ligne" onClick={(ev) => { ev.stopPropagation(); onOuvrir(e); }}>{e.Libelle}</button>
                    <div className="cs-sous-texte">{polices(e)}</div>
                  </td>
                  <td className="cs-nombre">{entier(e.Beneficiaires)}<div className="cs-sous-texte">{entier(e.Familles)} famille{e.Familles > 1 ? 's' : ''}</div></td>
                  <td className="cs-nombre">{entier(e.Prestations)}</td>
                  <td className="cs-nombre">
                    <div className="cs-depenses-cellule">
                      {e.Serie.length > 1 && <Sparkline valeurs={e.Serie} largeur={84} hauteur={24} libelle={`Remboursements mensuels de ${e.Libelle}`} />}
                      <span>{francsCourts(e.Rembourse)}<span className="cs-sous-texte">{pct(e.Part, 1)}</span></span>
                    </div>
                  </td>
                  <td className="cs-nombre">{francs(e.CoutMoyenBeneficiaire)}</td>
                  <td>{modes(e)}<div className="cs-sous-texte">{[e.PremierPoste, e.PremiereAffection].filter(Boolean).join(' · ').toLowerCase()}</div></td>
                  <td className="cs-cellule-jauge">
                    {e.Taux === null ? <span className="cs-muet">Aucune prime rattachée</span> : (
                      <>
                        <Jauge fine taux={e.Taux} repere={0.8} ton={SITUATIONS[e.Situation]?.jauge} libelle={`${e.Libelle} : ${pct(e.Taux)} des primes acquises consommés`} />
                        <div className="cs-sous-texte">{`${pct(e.Taux, 0)} de ${francsCourts(e.PrimesAcquises)} · ${entier(e.FamillesPortefeuille)} familles`}</div>
                      </>
                    )}
                  </td>
                  <td>
                    <Situation code={e.Situation} />
                    {e.FamillesSurveillees > 0 && <div className="cs-sous-texte">{entier(e.FamillesSurveillees)} famille{e.FamillesSurveillees > 1 ? 's' : ''} à 80 % ou plus</div>}
                  </td>
                  <td className="cs-nombre"><ChevronRight size={16} className="cs-muet" aria-hidden="true" /></td>
                </tr>
              ))}
              {!lignes.length && <tr><td colSpan={9}><Vide texte="Aucune entreprise ne correspond." /></td></tr>}
            </tbody>
          </table>
        </div>
        <p className="cs-note">
          Entreprise : souscripteur du relevé du gestionnaire. Primes acquises : primes nettes annuelles des familles en vigueur de ses polices MINENE
          dans LE PHARE (retrouvées par les membres ou par le nom du souscripteur), au prorata des mois de la période ; consommation : tout ce que
          l'entreprise a consommé face à ces primes, « À surveiller » à partir de 80 %.
        </p>
      </Carte>
    </>
  );
};

// Fiche d'une entreprise : l'analyse MINENE limitée à ses prestations et à son portefeuille LE PHARE, sur la même période
const FicheEntreprise = ({ entreprise, filtres, onFermer, onAnalyser }) => {
  const filtresFiche = useMemo(() => ({ ...filtres, entreprise: entreprise?.Libelle || '' }), [filtres, entreprise]);
  const [a, chargement] = useMinene(filtresFiche, Boolean(entreprise));
  const i = a?.Indicateurs;
  const pret = a && !chargement && a.Entreprise?.Nom === entreprise?.Libelle;
  return (
    <Tiroir ouvert={Boolean(entreprise)} onFermer={onFermer} titre={entreprise?.Libelle || ''} sousTitre={entreprise ? polices(entreprise) : ''}>
      {!pret ? <p className="cs-vide"><Loader2 size={15} className="spin" aria-hidden="true" /> Calcul de la consommation de l'entreprise…</p> : (
        <div className="cs-pile">
          <div className="cs-tuiles compactes">
            <Tuile libelle="Remboursé" valeur={francsCourts(i.Rembourse)} detail={`Réclamé ${francs(i.Reclame)}`} />
            <Tuile libelle="Prestations" valeur={entier(i.Prestations)} detail={`${entier(i.Beneficiaires)} bénéficiaires · ${entier(i.Familles)} familles`} />
            <Tuile libelle="Prise en charge" valeur={pct(i.TauxPriseEnCharge, 0)} detail={`À la charge des assurés : ${francs(i.PartAssures)}`} />
            <Tuile libelle="Coût moyen" valeur={francs(i.CoutMoyenBeneficiaire)} detail={`par bénéficiaire · ${francs(i.CoutMoyenPrestation)} par prestation`} />
            <Tuile libelle="Consommation des primes" valeur={i.TauxConsommation === null ? '-' : pct(i.TauxConsommation)}
              detail={i.PrimesAcquises ? `${francs(i.RembourseRattache)} sur ${francs(i.PrimesAcquises)} acquis · ${entier(i.FamillesPortefeuille)} familles, ${entier(i.PersonnesPortefeuille)} personnes` : 'Aucune police LE PHARE rattachée'}>
              <Jauge taux={i.TauxConsommation} repere={0.8} ton={tonTaux(i.TauxConsommation)} libelle="Remboursements face aux primes acquises" fine />
            </Tuile>
          </div>
          <Cadre titre="Remboursements par mois" sousTitre="Selon la date des soins"
            tableau={{ entetes: ['Mois', 'Prestations', 'Remboursé'], lignes: a.ParMois.map((m) => [libelleMois(m.Code), entier(m.Prestations), francs(m.Rembourse)]) }}>
            <Colonnes points={a.ParMois.map((m) => ({ cle: m.Code, libelle: libelleMois(m.Code), libelleCourt: libelleMois(m.Code).split(' ')[0], valeur: m.Rembourse, prestations: m.Prestations }))}
              libelleAria={`Remboursements mensuels de ${entreprise.Libelle}`} hauteur={180}
              lignesBulle={(p) => [{ libelle: 'Remboursé', valeur: francs(p.valeur), couleur: 'var(--cs-viz-1)' }, { libelle: 'Prestations', valeur: entier(p.prestations) }]} />
          </Cadre>
          <Cadre titre="Mode de prise en charge" tableau={{ entetes: ['Mode', 'Prestations', 'Remboursé', 'Part'], lignes: a.ParType.map((t) => [t.Libelle, entier(t.Prestations), francs(t.Rembourse), pct(t.Part, 0)]) }}>
            <BarreSegmentee parts={a.ParType.map((t) => ({ libelle: t.Libelle, valeur: t.Rembourse }))} libelleAria="Remboursements par mode de prise en charge" />
          </Cadre>
          <Cadre titre="Familles de prestations">
            <BarresClassees lignes={barres(a.ParFamillePrestation.slice(0, 8), (l) => [francs(l.CoutMoyen)])} colonnes={['Coût moyen']} libelleValeur="Remboursé" />
          </Cadre>
          {a.ParAffection.some((l) => l.Libelle !== 'Non renseigné') && (
            <Cadre titre="Types d’affection">
              <BarresClassees lignes={barres(a.ParAffection.slice(0, 8), (l) => [entier(l.Beneficiaires)])} colonnes={['Bénéficiaires']} libelleValeur="Remboursé" />
            </Cadre>
          )}
          <Cadre titre="Familles consommatrices" sousTitre="Assuré principal du relevé, police LE PHARE et consommation de sa prime">
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Famille</th><th>Police LE PHARE · formule</th><th className="cs-nombre">Bénéf.</th><th className="cs-nombre">Remboursé</th><th>Consommation</th><th>Situation</th></tr></thead>
                <tbody>
                  {a.Familles.slice(0, 12).map((f) => (
                    <tr key={f.Code}>
                      <td><strong>{f.Libelle}</strong><div className="cs-muet">{f.Code}</div></td>
                      <td>{f.PoliceLePhare ? <>{f.PoliceLePhare}<div className="cs-muet">{f.Formule}</div></> : '-'}</td>
                      <td className="cs-nombre">{entier(f.Beneficiaires)}</td><td className="cs-nombre">{francs(f.Rembourse)}</td>
                      <td>{f.Taux === null ? <span className="cs-muet">-</span> : pct(f.Taux, 0)}</td>
                      <td><Situation code={f.Situation} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Cadre>
          <Cadre titre="Centres exécutants">
            <BarresClassees lignes={a.Centres.slice(0, 8).map((c) => ({ cle: c.Code, libelle: c.Libelle, valeur: c.Rembourse, detail: [c.Localite, `${entier(c.Prestations)} prestations`].filter(Boolean).join(' · ') }))} libelleValeur="Remboursé" />
          </Cadre>
          <Cadre titre="Actes les plus remboursés">
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Acte</th><th className="cs-nombre">Prestations</th><th className="cs-nombre">Remboursé</th></tr></thead>
                <tbody>{a.Actes.slice(0, 8).map((l) => <tr key={l.Code}><td>{l.Libelle}</td><td className="cs-nombre">{entier(l.Prestations)}</td><td className="cs-nombre">{francs(l.Rembourse)}</td></tr>)}</tbody>
              </table>
            </div>
          </Cadre>
          {a.Constats.length > 0 && (
            <Cadre titre="Constats">
              <ul className="cs-constats">
                {a.Constats.map((c) => <li key={c} className="ton-info"><Info size={16} aria-hidden="true" /><div><p>{c}</p></div></li>)}
              </ul>
            </Cadre>
          )}
          <div>
            <button type="button" className="btn btn-primary" onClick={() => onAnalyser(entreprise.Libelle)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
              <Filter size={15} aria-hidden="true" /> Analyser cette entreprise dans tous les onglets
            </button>
          </div>
        </div>
      )}
    </Tiroir>
  );
};

// ------------------------------------------------------------------ onglets
export const MineneConsommations = ({ onglet, donnees, chargement, filtres, onFiltrer, onChangerOnglet }) => {
  const [fiche, setFiche] = useState(null);
  if (!donnees) return chargement ? <p className="cs-vide"><Loader2 size={15} className="spin" aria-hidden="true" /> Lecture des relevés MINENE…</p> : null;
  if (!donnees.Indicateurs.Prestations) {
    return (
      <Carte titre="Aucune consommation MINENE">
        <Vide texte="Importez le détail des sinistres MINENE du gestionnaire (états personnalisés, garant OREOLEMINENE) dans l'onglet Imports." />
      </Carte>
    );
  }
  return (
    <div className={`cs-pile${chargement ? ' cs-rechargement' : ''}`}>
      {onglet === 'm-ensemble' && <Ensemble d={donnees} />}
      {onglet === 'm-entreprises' && <Entreprises d={donnees} onOuvrir={setFiche} />}
      {onglet === 'm-familles' && <Familles d={donnees} />}
      {onglet === 'm-prestations' && <Prestations d={donnees} />}
      {onglet === 'm-beneficiaires' && <Beneficiaires d={donnees} />}
      <FicheEntreprise entreprise={fiche} filtres={filtres || FILTRES_MINENE} onFermer={() => setFiche(null)}
        onAnalyser={(nom) => { setFiche(null); onFiltrer?.((f) => ({ ...f, entreprise: nom })); onChangerOnglet?.('m-ensemble'); }} />
    </div>
  );
};
