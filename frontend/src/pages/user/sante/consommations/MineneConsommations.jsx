import React, { useEffect, useState } from 'react';
import { CircleAlert, CircleCheck, CircleDashed, Info, Loader2, RotateCcw, ShieldAlert, TriangleAlert } from 'lucide-react';
import { consommationsApi } from '../../../../api/endpoints';
import { useToast } from '../../../../context/ToastContext';
import { dateFr, messageErreurApi } from '../../../../utils/financeUtils';
import {
  BarreSegmentee, BarresClassees, Cadre, Colonnes, EchelleChaleur, Jauge, Pyramide, TableauChaleur, entier, francs, francsCourts, pct,
} from './graphiques';

/* =========================================================================
   CONSOMMATIONS MINENE SANTÉ (sante/consommations_minene.py, demande du 2026-11-19)
   Détail des sinistres du gestionnaire (états personnalisés, garant OREOLEMINENE) : tiers payant et remboursement direct, affections,
   familles rattachées aux polices MINENE de LE PHARE (formule, prime acquise, taux de consommation), prestataires, profil, anomalies.
   Une lecture GET /api/consommations/minene/ partagée par les quatre onglets.
   ========================================================================= */

export const ONGLETS_MINENE = new Set(['m-ensemble', 'm-familles', 'm-prestations', 'm-beneficiaires']);
export const FILTRES_MINENE = { du: '', au: '', police: '' };
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

// ------------------------------------------------------------------ onglets
export const MineneConsommations = ({ onglet, donnees, chargement }) => {
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
      {onglet === 'm-familles' && <Familles d={donnees} />}
      {onglet === 'm-prestations' && <Prestations d={donnees} />}
      {onglet === 'm-beneficiaires' && <Beneficiaires d={donnees} />}
    </div>
  );
};
