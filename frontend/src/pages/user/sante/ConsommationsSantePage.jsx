import React, { useCallback, useEffect, useState } from 'react';
import { BarChart3, Building2, FileSpreadsheet, Gauge, HeartPulse, ListChecks, Loader2, RefreshCw, Save, Search, ShieldAlert, Upload, UserSearch } from 'lucide-react';
import { consommationsApi } from '../../../api/endpoints';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { useToast } from '../../../context/ToastContext';
import { confirmer } from '../../../utils/dialogue';
import { aLeDroit } from '../../../utils/droits';
import { exportToExcel } from '../../../utils/exportUtils';
import { dateFr, fcfa, messageErreurApi } from '../../../utils/financeUtils';

/* =========================================================================
   Suivi des consommations santé : relevés du gestionnaire (MCI CARE) importés, droits, plafonds et soldes de chaque assuré et de ses
   bénéficiaires, statistiques par entreprise, contrôles des données et détection des cas de fraude. Calculs au serveur : sante/consommations.py.
   Données de santé : chaque onglet suit son droit (consommations.view, consommations.fraude, consommations.import).
   ========================================================================= */
const DROITE = { textAlign: 'right' };
const MONO = { fontFamily: 'var(--font-mono)', fontSize: '0.78rem' };
const pourcent = (v) => (v === null || v === undefined ? '-' : `${(Number(v) * 100).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %`);
const montant = (v) => (v === null || v === undefined ? '-' : `${fcfa(v)} F`);
const COULEUR_SITUATION = { Normal: 'emerald', Alerte: 'amber', 'Plafond dépassé': 'rose', 'Barème inconnu': 'slate' };
const COULEUR_NIVEAU = { Élevé: 'rose', Moyen: 'amber', Faible: 'blue' };
const COULEUR_GRAVITE = { Élevée: 'rose', Moyenne: 'amber', Faible: 'slate' };
const COULEUR_INSTRUCTION = { A_INSTRUIRE: 'blue', JUSTIFIE: 'emerald', FRAUDE: 'rose', SANS_SUITE: 'slate' };
const DECISIONS = [['A_INSTRUIRE', 'À instruire'], ['JUSTIFIE', 'Justifié'], ['FRAUDE', 'Fraude avérée'], ['SANS_SUITE', 'Sans suite']];

// Export Excel : colonnes = [[en-tête, valeur(ligne)], ...]
const exporter = (filename, title, colonnes, lignes) => exportToExcel({ filename, title, headers: colonnes.map(([h]) => h), rows: lignes.map((l) => colonnes.map(([, v]) => v(l))) });

const Onglet = ({ actif, onClick, icone: Icone, children }) => (
  <button type="button" role="tab" aria-selected={actif} className={`btn ${actif ? 'btn-primary' : 'btn-secondary'}`} onClick={onClick} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
    <Icone size={15} /> {children}
  </button>
);

const Tuile = ({ libelle, valeur, detail, couleur = 'var(--text-primary)' }) => (
  <div className="glass-panel" style={{ padding: '0.9rem 1.05rem' }}>
    <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>{libelle}</div>
    <div style={{ fontSize: '1.25rem', fontWeight: 900, color: couleur, marginTop: '0.15rem' }}>{valeur}</div>
    {detail && <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.1rem' }}>{detail}</div>}
  </div>
);

const Grille = ({ children, min = 190 }) => <div style={{ display: 'grid', gridTemplateColumns: `repeat(auto-fit, minmax(${min}px, 1fr))`, gap: '0.75rem' }}>{children}</div>;

const Panneau = ({ titre, children, actions }) => (
  <section className="glass-panel" style={{ padding: '0.95rem 1.05rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
    {(titre || actions) && (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.6rem', flexWrap: 'wrap' }}>
        {titre && <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 800 }}>{titre}</h2>}
        {actions}
      </div>
    )}
    {children}
  </section>
);

const Vide = ({ colonnes, chargement, texte }) => (
  <tr><td colSpan={colonnes} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.4rem' }}>{chargement ? <><Loader2 size={14} className="spin" /> Lecture…</> : texte}</td></tr>
);

const Champ = ({ id, libelle, children }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', minWidth: 160 }}>
    <label className="form-label" htmlFor={id} style={{ margin: 0 }}>{libelle}</label>
    {children}
  </div>
);

// Charge une lecture du serveur à chaque changement de paramètres ; erreur affichée une fois
const useLecture = (lire, dependances) => {
  const { error: toastError } = useToast();
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(true);
  const recharger = useCallback(async () => {
    setChargement(true);
    try {
      setDonnees(await lire());
    } catch (err) {
      toastError(`Lecture impossible : ${messageErreurApi(err)}`);
    } finally {
      setChargement(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependances);
  useEffect(() => { recharger(); }, [recharger]);
  return [donnees, chargement, recharger];
};

// ------------------------------------------------------------------ synthèse
const OngletSynthese = () => {
  const [filtres, setFiltres] = useState({ garant: '', police: '', du: '', au: '' });
  const [donnees, chargement, recharger] = useLecture(() => consommationsApi.synthese(filtres), [filtres]);
  const i = donnees?.Indicateurs || {};
  const champ = (cle) => (e) => setFiltres((f) => ({ ...f, [cle]: e.target.value }));
  return (
    <>
      <Panneau>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <Champ id="syn-garant" libelle="Garant">
            <select id="syn-garant" className="form-control" value={filtres.garant} onChange={champ('garant')}>
              <option value="">Tous les garants</option>
              {(donnees?.Filtres?.Garants || []).map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </Champ>
          <Champ id="syn-police" libelle="Police">
            <select id="syn-police" className="form-control" value={filtres.police} onChange={champ('police')} style={{ maxWidth: 320 }}>
              <option value="">Toutes les polices</option>
              {(donnees?.Filtres?.Polices || []).map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </Champ>
          <Champ id="syn-du" libelle="Clôture du"><input id="syn-du" type="date" className="form-control" value={filtres.du} onChange={champ('du')} /></Champ>
          <Champ id="syn-au" libelle="au"><input id="syn-au" type="date" className="form-control" value={filtres.au} onChange={champ('au')} /></Champ>
          <button type="button" className="btn btn-secondary" onClick={recharger} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><RefreshCw size={14} /> Actualiser</button>
        </div>
      </Panneau>
      {chargement && !donnees ? <Panneau><Loader2 size={16} className="spin" /> Lecture…</Panneau> : !i.Prestations ? (
        <Panneau><p style={{ margin: 0, color: 'var(--text-secondary)' }}>Aucune prestation : importez un relevé du gestionnaire dans l'onglet Imports.</p></Panneau>
      ) : (
        <>
          <Grille>
            <Tuile libelle="Assurés principaux" valeur={fcfa(i.AssuresPrincipaux)} detail={`${fcfa(i.Beneficiaires)} bénéficiaires actifs`} />
            <Tuile libelle="Prestations" valeur={fcfa(i.Prestations)} detail={`${fcfa(i.Polices)} polices concernées`} />
            <Tuile libelle="Consommants" valeur={fcfa(i.Consommants)} detail={`Taux de recours ${pourcent(i.TauxRecours)}`} />
            <Tuile libelle="Montant réclamé" valeur={montant(i.Reclame)} detail={`Exclusions ${montant(i.Exclusions)}, dépassements ${montant(i.Depassements)}`} />
            <Tuile libelle="Montant remboursé" valeur={montant(i.Rembourse)} couleur="var(--primary-500)" detail={`Prise en charge ${pourcent(i.TauxPriseEnCharge)}`} />
            <Tuile libelle="Tiers payant" valeur={montant(i.TiersPayant)} detail={`Hors tiers payant ${montant(i.HorsTiersPayant)}`} />
            <Tuile libelle="Reste à charge des assurés" valeur={montant(i.ResteACharge)} />
            <Tuile libelle="Coût moyen" valeur={montant(i.CoutParConsommant)} detail={`par consommant ; ${montant(i.CoutParActe)} par acte`} />
          </Grille>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '0.75rem' }}>
            <Panneau titre="Par famille de prestations">
              <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.83rem' }}>
                <thead><tr><th>Famille</th><th style={DROITE}>Prestations</th><th style={DROITE}>Remboursé</th><th style={DROITE}>Part</th></tr></thead>
                <tbody>{donnees.ParFamille.map((f) => <tr key={f.Famille}><td>{f.Famille}</td><td style={DROITE}>{fcfa(f.Prestations)}</td><td style={DROITE}>{montant(f.Rembourse)}</td><td style={DROITE}>{pourcent(f.Part)}</td></tr>)}</tbody>
              </table></div>
            </Panneau>
            <Panneau titre="Par mois de clôture">
              <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.83rem' }}>
                <thead><tr><th>Mois</th><th style={DROITE}>Prestations</th><th style={DROITE}>Réclamé</th><th style={DROITE}>Remboursé</th></tr></thead>
                <tbody>{donnees.ParMois.map((m) => <tr key={m.Mois}><td>{m.Mois.split('-').reverse().join('/')}</td><td style={DROITE}>{fcfa(m.Prestations)}</td><td style={DROITE}>{montant(m.Reclame)}</td><td style={DROITE}>{montant(m.Rembourse)}</td></tr>)}</tbody>
              </table></div>
            </Panneau>
          </div>
          <Panneau titre="Polices les plus consommatrices">
            <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.83rem' }}>
              <thead><tr><th>Police</th><th style={DROITE}>Prestations</th><th style={DROITE}>Consommants</th><th style={DROITE}>Remboursé</th></tr></thead>
              <tbody>{donnees.TopPolices.map((p) => <tr key={p.Police}><td>{p.Police}</td><td style={DROITE}>{fcfa(p.Prestations)}</td><td style={DROITE}>{fcfa(p.Consommants)}</td><td style={DROITE}>{montant(p.Rembourse)}</td></tr>)}</tbody>
            </table></div>
          </Panneau>
        </>
      )}
    </>
  );
};

// ------------------------------------------------------------------ fiche assuré
const FicheFamille = ({ fiche }) => {
  const d = fiche.Droits;
  const signaux = fiche.Signaux;
  return (
    <>
      <Panneau titre={`${fiche.Nom || 'Assuré principal'} - matricule ${fiche.MatriculeAssure}`}>
        <div style={{ display: 'flex', gap: '1.4rem', flexWrap: 'wrap', fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
          <span>Police <strong style={{ color: 'var(--text-primary)' }}>{fiche.Police || '-'}</strong></span>
          <span>Garant <strong style={{ color: 'var(--text-primary)' }}>{fiche.Garant || '-'}</strong></span>
          <span>Collège <strong style={{ color: 'var(--text-primary)' }}>{fiche.College || '-'}</strong></span>
          <span>{fiche.LibelleBareme}</span>
        </div>
        <Grille>
          <Tuile libelle={`Plafond annuel ${fiche.Exercice}`} valeur={montant(d.PlafondAnnuel)} detail="par famille" />
          <Tuile libelle="Consommé sur l'exercice" valeur={montant(d.ConsommeExercice)} detail={`${pourcent(d.Taux)} du plafond`} />
          <Tuile libelle="Solde disponible" valeur={montant(d.Solde)} couleur={d.Situation === 'Plafond dépassé' ? 'var(--danger-500, #e11d48)' : 'var(--primary-500)'} />
          <div className="glass-panel" style={{ padding: '0.9rem 1.05rem' }}>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>Situation</div>
            <div style={{ marginTop: '0.35rem' }}><StatusBadge label={d.Situation} color={COULEUR_SITUATION[d.Situation]} /></div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.3rem' }}>{`${fcfa(fiche.Totaux.Prestations)} prestations, reste à charge ${montant(fiche.Totaux.ResteACharge)}`}</div>
          </div>
        </Grille>
      </Panneau>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '0.75rem' }}>
        <Panneau titre="Droits du barème">
          {fiche.Garanties.length ? (
            <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.83rem' }}>
              <thead><tr><th>Garantie</th><th style={DROITE}>Plafond</th><th>Unité</th></tr></thead>
              <tbody>{fiche.Garanties.map((g) => <tr key={g.Garantie}><td>{g.Garantie}</td><td style={DROITE}>{montant(g.Plafond)}</td><td>{g.Unite}</td></tr>)}</tbody>
            </table></div>
          ) : <p style={{ margin: 0, color: 'var(--text-secondary)' }}>Information non déterminable : le collège n'a pas de barème connu.</p>}
          <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Carences : {fiche.Carences.map((c) => `${c.Famille.toLowerCase()} ${c.Mois} mois`).join(', ')}. Barème déduit du collège, à confirmer avec le contrat.
          </p>
        </Panneau>
        <Panneau titre="Consommation par famille de prestations">
          <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.83rem' }}>
            <thead><tr><th>Famille</th><th style={DROITE}>Prestations</th><th style={DROITE}>Remboursé</th><th style={DROITE}>Part</th></tr></thead>
            <tbody>
              {fiche.ParFamille.map((f) => <tr key={f.Famille}><td>{f.Famille}</td><td style={DROITE}>{fcfa(f.Prestations)}</td><td style={DROITE}>{montant(f.Rembourse)}</td><td style={DROITE}>{pourcent(f.Part)}</td></tr>)}
              {!fiche.ParFamille.length && <Vide colonnes={4} texte="Aucune prestation." />}
            </tbody>
          </table></div>
        </Panneau>
      </div>
      <Panneau titre="Bénéficiaires, plafonds individuels et soldes">
        <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.82rem' }}>
          <thead><tr><th>Lien</th><th>Nom</th><th>Naissance</th><th>Effet</th><th>Situation</th><th style={DROITE}>Prestations</th><th style={DROITE}>Remboursé</th>
            <th style={DROITE}>Solde dentaire</th><th style={DROITE}>Solde optique</th><th>Alertes</th>{signaux && <th>Fraude</th>}</tr></thead>
          <tbody>{fiche.Beneficiaires.map((b) => (
            <tr key={b.Matricule}>
              <td>{b.Lien}</td>
              <td style={{ fontWeight: 600 }}>{b.Nom}<div style={{ ...MONO, color: 'var(--text-muted)' }}>{b.Matricule}</div></td>
              <td>{dateFr(b.DateNaissance)}</td>
              <td>{dateFr(b.DateEffet)}</td>
              <td>{b.HorsEffectif ? <StatusBadge label="Absent de l'effectif" color="rose" /> : b.Actif ? <StatusBadge label="Couvert" color="emerald" /> : <StatusBadge label={`Sorti le ${dateFr(b.DateSortie)}`} color="slate" />}</td>
              <td style={DROITE}>{fcfa(b.Prestations)}</td>
              <td style={DROITE}>{montant(b.Rembourse)}</td>
              <td style={DROITE}>{montant(b.SoldeDentaire)}<div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>sur {montant(b.PlafondDentaire)}</div></td>
              <td style={DROITE}>{montant(b.SoldeOptique)}<div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>sur {montant(b.PlafondOptique)}</div></td>
              <td>{[b.AlerteBons && '15 bons ou plus', b.AlertePharmacie && 'Pharmacie 200 000 F ou plus'].filter(Boolean).join(', ') || '-'}</td>
              {signaux && <td>{b.Niveau ? <StatusBadge label={`${b.Niveau} - ${b.Score}`} color={COULEUR_NIVEAU[b.Niveau]} /> : '-'}</td>}
            </tr>
          ))}</tbody>
        </table></div>
      </Panneau>
      {signaux && signaux.length > 0 && (
        <Panneau titre={`Signaux de fraude de la famille : ${signaux.length}`}>
          <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Un signal est à instruire : ce n'est pas une preuve de fraude.</p>
          <TableSignaux signaux={signaux} />
        </Panneau>
      )}
      <Panneau titre="Historique des prestations" actions={(
        <button type="button" className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          onClick={() => exporter(`prestations-${fiche.MatriculeAssure}`, `Prestations de la famille ${fiche.MatriculeAssure}`, [
            ['Numéro', (p) => p.Numero], ['Date de soins', (p) => dateFr(p.DateSoins)], ['Bénéficiaire', (p) => p.Beneficiaire], ['Famille', (p) => p.Famille], ['Acte', (p) => p.Acte],
            ['Centre', (p) => p.Centre], ['Réclamé', (p) => p.Reclame], ['Base', (p) => p.Base], ['Ticket modérateur', (p) => p.TicketModerateur], ['Exclusion', (p) => p.Exclusion],
            ['Dépassement', (p) => p.Depassement], ['Remboursé', (p) => p.Rembourse], ['Type', (p) => p.Type]], fiche.Prestations)}>
          <FileSpreadsheet size={14} /> Excel
        </button>
      )}>
        <div className="table-wrapper" style={{ maxHeight: 460, overflow: 'auto' }}><table className="data-table" style={{ fontSize: '0.8rem' }}>
          <thead><tr><th>Soins</th><th>Bénéficiaire</th><th>Famille</th><th>Acte</th><th>Centre</th><th style={DROITE}>Réclamé</th><th style={DROITE}>Base</th><th style={DROITE}>TM</th><th style={DROITE}>Remboursé</th><th>Type</th></tr></thead>
          <tbody>
            {fiche.Prestations.map((p) => (
              <tr key={p.Numero}>
                <td>{dateFr(p.DateSoins)}{p.DateSoinsOrigine !== p.DateSoins && <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }} title="Jour et mois inversés dans le relevé">relevé : {dateFr(p.DateSoinsOrigine)}</div>}</td>
                <td>{p.Beneficiaire}</td><td>{p.Famille}</td><td style={MONO}>{p.Acte}</td><td>{p.Centre}</td>
                <td style={DROITE}>{fcfa(p.Reclame)}</td><td style={DROITE}>{fcfa(p.Base)}</td><td style={DROITE}>{fcfa(p.TicketModerateur)} %</td><td style={DROITE}>{fcfa(p.Rembourse)}</td><td>{p.Type}</td>
              </tr>
            ))}
            {!fiche.Prestations.length && <Vide colonnes={10} texte="Aucune prestation." />}
          </tbody>
        </table></div>
      </Panneau>
    </>
  );
};

const OngletFiche = ({ matriculeInitial }) => {
  const { error: toastError } = useToast();
  const [q, setQ] = useState('');
  const [resultats, setResultats] = useState([]);
  const [fiche, setFiche] = useState(null);
  const [chargement, setChargement] = useState(false);

  const ouvrir = useCallback(async (matricule) => {
    setChargement(true);
    try {
      setFiche(await consommationsApi.famille(matricule));
    } catch (err) {
      toastError(`Fiche non lue : ${messageErreurApi(err)}`);
    } finally {
      setChargement(false);
    }
  }, [toastError]);

  useEffect(() => { if (matriculeInitial) ouvrir(matriculeInitial); }, [matriculeInitial, ouvrir]);
  useEffect(() => {
    if (q.trim().length < 2) { setResultats([]); return undefined; }
    const minuteur = setTimeout(async () => {
      try { setResultats((await consommationsApi.rechercher(q.trim())).Lignes); } catch (err) { toastError(`Recherche impossible : ${messageErreurApi(err)}`); }
    }, 300);
    return () => clearTimeout(minuteur);
  }, [q, toastError]);

  return (
    <>
      <Panneau>
        <label className="form-label" htmlFor="fiche-recherche" style={{ margin: 0 }}>Assuré ou bénéficiaire</label>
        <div style={{ position: 'relative' }}>
          <Search size={15} style={{ position: 'absolute', left: 10, top: 11, color: 'var(--text-muted)' }} />
          <input id="fiche-recherche" className="form-control" style={{ paddingLeft: 32 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nom, matricule ou police" />
        </div>
        {resultats.length > 0 && (
          <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.83rem' }}>
            <thead><tr><th>Assuré principal</th><th>Matricule</th><th>Police</th><th style={DROITE}>Bénéficiaires</th><th /></tr></thead>
            <tbody>{resultats.map((r) => (
              <tr key={r.MatriculeAssure}>
                <td style={{ fontWeight: 600 }}>{r.Nom}</td><td style={MONO}>{r.MatriculeAssure}</td><td>{r.Police}</td><td style={DROITE}>{r.Beneficiaires}</td>
                <td style={DROITE}><button type="button" className="btn btn-primary" style={{ fontSize: '0.78rem', padding: '0.3rem 0.7rem' }} onClick={() => { setResultats([]); ouvrir(r.MatriculeAssure); }}>Ouvrir la fiche</button></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </Panneau>
      {chargement && <Panneau><span><Loader2 size={14} className="spin" /> Lecture de la fiche…</span></Panneau>}
      {!chargement && fiche && <FicheFamille fiche={fiche} />}
      {!chargement && !fiche && <Panneau><p style={{ margin: 0, color: 'var(--text-secondary)' }}>Recherchez un assuré : la fiche réunit ses droits, les prestations de toute la famille, les plafonds utilisés et les soldes disponibles.</p></Panneau>}
    </>
  );
};

// ------------------------------------------------------------------ plafonds
const OngletPlafonds = ({ onOuvrir }) => {
  const [situation, setSituation] = useState('');
  const [donnees, chargement] = useLecture(() => consommationsApi.plafonds({ situation }), [situation]);
  const lignes = donnees?.Lignes || [];
  return (
    <Panneau titre={`Plafonds de l'exercice ${donnees?.Exercice || ''}`} actions={(
      <select aria-label="Situation" className="form-control" style={{ maxWidth: 260 }} value={situation} onChange={(e) => setSituation(e.target.value)}>
        <option value="">Toutes les situations</option>
        {Object.entries(donnees?.Situations || {}).map(([s, n]) => <option key={s} value={s}>{`${s} - ${n}`}</option>)}
      </select>
    )}>
      <div className="table-wrapper" style={{ maxHeight: 560, overflow: 'auto' }}><table className="data-table" style={{ fontSize: '0.82rem' }}>
        <thead><tr><th>Niveau</th><th>Garantie</th><th>Assuré ou bénéficiaire</th><th>Police</th><th style={DROITE}>Plafond</th><th style={DROITE}>Consommé</th><th style={DROITE}>Taux</th><th style={DROITE}>Solde</th><th>Situation</th></tr></thead>
        <tbody>
          {lignes.map((l) => (
            <tr key={`${l.Niveau}${l.Garantie}${l.Matricule}`}>
              <td>{l.Niveau}</td><td>{l.Garantie}</td>
              <td><button type="button" className="btn btn-secondary" title="Ouvrir la fiche de la famille" style={{ fontSize: '0.78rem', padding: '0.2rem 0.55rem' }} onClick={() => onOuvrir(l.MatriculeAssure)}>{l.Nom || l.Matricule}</button></td>
              <td>{l.Police}</td><td style={DROITE}>{montant(l.Plafond)}</td><td style={DROITE}>{montant(l.Consomme)}</td><td style={DROITE}>{pourcent(l.Taux)}</td><td style={DROITE}>{montant(l.Solde)}</td>
              <td><StatusBadge label={l.Situation} color={COULEUR_SITUATION[l.Situation]} /></td>
            </tr>
          ))}
          {!lignes.length && <Vide colonnes={9} chargement={chargement} texte="Aucune consommation sur l'exercice." />}
        </tbody>
      </table></div>
    </Panneau>
  );
};

// ------------------------------------------------------------------ entreprises
const OngletEntreprises = () => {
  const [donnees, chargement] = useLecture(() => consommationsApi.entreprises({}), []);
  const lignes = donnees?.Lignes || [];
  return (
    <Panneau titre="Consommation par entreprise" actions={(
      <button type="button" className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
        onClick={() => exporter('consommations-entreprises', 'Consommation santé par entreprise', [
          ['Police', (l) => l.Police], ['Garant', (l) => l.Garant], ['Effectif', (l) => l.Effectif], ['Assurés', (l) => l.Assures], ['Conjoints', (l) => l.Conjoints], ['Enfants', (l) => l.Enfants],
          ['Consommants', (l) => l.Consommants], ['Taux de recours', (l) => pourcent(l.TauxRecours)], ['Prestations', (l) => l.Prestations], ['Réclamé', (l) => Math.round(l.Reclame)],
          ['Remboursé', (l) => Math.round(l.Rembourse)], ['Coût par consommant', (l) => (l.CoutParConsommant === null ? '' : Math.round(l.CoutParConsommant))], ['Part', (l) => pourcent(l.Part)]], lignes)}>
        <FileSpreadsheet size={14} /> Excel
      </button>
    )}>
      <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.82rem' }}>
        <thead><tr><th>Police</th><th>Garant</th><th style={DROITE}>Effectif</th><th style={DROITE}>A / C / E</th><th style={DROITE}>Consommants</th><th style={DROITE}>Recours</th><th style={DROITE}>Prestations</th><th style={DROITE}>Remboursé</th><th style={DROITE}>Par consommant</th><th style={DROITE}>Part</th></tr></thead>
        <tbody>
          {lignes.map((l) => (
            <tr key={l.Police}>
              <td style={{ fontWeight: 600 }}>{l.Police}</td><td>{l.Garant}</td><td style={DROITE}>{l.Effectif ? fcfa(l.Effectif) : <StatusBadge label="Sans effectif" color="amber" />}</td>
              <td style={DROITE}>{`${l.Assures} / ${l.Conjoints} / ${l.Enfants}`}</td><td style={DROITE}>{fcfa(l.Consommants)}</td><td style={DROITE}>{pourcent(l.TauxRecours)}</td>
              <td style={DROITE}>{fcfa(l.Prestations)}</td><td style={DROITE}>{montant(l.Rembourse)}</td><td style={DROITE}>{montant(l.CoutParConsommant)}</td><td style={DROITE}>{pourcent(l.Part)}</td>
            </tr>
          ))}
          {!lignes.length && <Vide colonnes={10} chargement={chargement} texte="Aucune entreprise." />}
        </tbody>
      </table></div>
    </Panneau>
  );
};

// ------------------------------------------------------------------ contrôles
const OngletControles = () => {
  const [code, setCode] = useState('');
  const [donnees, chargement] = useLecture(() => consommationsApi.controles(code), [code]);
  const lignes = donnees?.Lignes || [];
  return (
    <>
      <Panneau titre={`Anomalies des données : ${fcfa(donnees?.Total || 0)}`}>
        <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Contrôles de qualité des relevés et de l'effectif. Les comportements suspects relèvent de l'onglet Fraude.</p>
        <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.83rem' }}>
          <thead><tr><th>Anomalie</th><th>Gravité</th><th style={DROITE}>Nombre</th><th style={DROITE}>Montant concerné</th><th /></tr></thead>
          <tbody>
            {(donnees?.Synthese || []).map((s) => (
              <tr key={s.Code}>
                <td>{s.Anomalie}</td><td><StatusBadge label={s.Gravite} color={COULEUR_GRAVITE[s.Gravite]} /></td><td style={DROITE}>{fcfa(s.Nombre)}</td><td style={DROITE}>{montant(s.Montant)}</td>
                <td style={DROITE}><button type="button" className={`btn ${code === s.Code ? 'btn-primary' : 'btn-secondary'}`} style={{ fontSize: '0.76rem', padding: '0.2rem 0.6rem' }} onClick={() => setCode(code === s.Code ? '' : s.Code)}>{code === s.Code ? 'Tout voir' : 'Détail'}</button></td>
              </tr>
            ))}
            {!(donnees?.Synthese || []).length && <Vide colonnes={5} chargement={chargement} texte="Aucune anomalie." />}
          </tbody>
        </table></div>
      </Panneau>
      {lignes.length > 0 && (
        <Panneau titre="Détail">
          <div className="table-wrapper" style={{ maxHeight: 520, overflow: 'auto' }}><table className="data-table" style={{ fontSize: '0.8rem' }}>
            <thead><tr><th>Anomalie</th><th>Prestation</th><th>Matricule</th><th>Police</th><th>Explication</th><th style={DROITE}>Montant</th></tr></thead>
            <tbody>{lignes.slice(0, 500).map((l, n) => (
              <tr key={`${l.Code}${l.NumeroPrestation}${l.Matricule}${n}`}>
                <td>{l.Anomalie}</td><td style={MONO}>{l.NumeroPrestation || '-'}</td><td style={MONO}>{l.Matricule || '-'}</td><td>{l.Police}</td><td>{l.Explication}</td><td style={DROITE}>{montant(l.Montant)}</td>
              </tr>
            ))}</tbody>
          </table></div>
        </Panneau>
      )}
    </>
  );
};

// ------------------------------------------------------------------ fraude
const TableSignaux = ({ signaux }) => (
  <div className="table-wrapper" style={{ maxHeight: 420, overflow: 'auto' }}><table className="data-table" style={{ fontSize: '0.8rem' }}>
    <thead><tr><th>Règle</th><th>Prestation</th><th>Soins</th><th>Famille</th><th>Centre</th><th>Constat</th><th style={DROITE}>Montant</th></tr></thead>
    <tbody>{signaux.map((s, n) => (
      <tr key={`${s.Code}${s.NumeroPrestation}${n}`}>
        <td><span style={MONO}>{s.Code}</span> {s.Regle}</td><td style={MONO}>{s.NumeroPrestation}</td><td>{dateFr(s.Date)}</td><td>{s.Famille}</td><td>{s.Centre}</td><td>{s.Detail}</td><td style={DROITE}>{montant(s.Montant)}</td>
      </tr>
    ))}</tbody>
  </table></div>
);

const Instruction = ({ suspicion, onEnregistree }) => {
  const { success, error: toastError } = useToast();
  const [statut, setStatut] = useState(suspicion.Instruction);
  const [observation, setObservation] = useState(suspicion.Observation || '');
  const [envoi, setEnvoi] = useState(false);
  const enregistrer = async () => {
    if (statut === 'FRAUDE' && !(await confirmer({ titre: 'Fraude avérée', message: "Confirmer que l'instruction établit une fraude ? La décision et son auteur sont conservés.", confirmer: 'Confirmer la fraude', ton: 'danger' }))) return;
    setEnvoi(true);
    try {
      success((await consommationsApi.instruire(suspicion.MatriculeBeneficiaire, { Statut: statut, Observation: observation })).Message);
      onEnregistree();
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };
  return (
    <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
      <Champ id="instr-statut" libelle="Décision">
        <select id="instr-statut" className="form-control" value={statut} onChange={(e) => setStatut(e.target.value)}>
          {DECISIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </Champ>
      <div style={{ flex: 1, minWidth: 260, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        <label className="form-label" htmlFor="instr-observation" style={{ margin: 0 }}>Observation</label>
        <input id="instr-observation" className="form-control" maxLength={500} value={observation} onChange={(e) => setObservation(e.target.value)} placeholder="Constat du médecin-conseil ou du gestionnaire" />
      </div>
      <button type="button" className="btn btn-primary" disabled={envoi} onClick={enregistrer} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
        {envoi ? <Loader2 size={14} className="spin" /> : <Save size={14} />} Enregistrer la décision
      </button>
      {suspicion.InstruitPar && <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>{`Dernière décision par ${suspicion.InstruitPar} le ${dateFr(suspicion.InstruitLe)}`}</span>}
    </div>
  );
};

const OngletFraude = ({ onOuvrir }) => {
  const [filtres, setFiltres] = useState({ niveau: '', instruction: '', q: '' });
  const [recherche, setRecherche] = useState('');
  const [donnees, chargement, recharger] = useLecture(() => consommationsApi.fraude(filtres), [filtres]);
  const [ouverte, setOuverte] = useState(null);
  const [detail, setDetail] = useState(null);
  useEffect(() => { const m = setTimeout(() => setFiltres((f) => ({ ...f, q: recherche })), 350); return () => clearTimeout(m); }, [recherche]);

  const ouvrir = async (s) => {
    if (ouverte === s.MatriculeBeneficiaire) { setOuverte(null); return; }
    setOuverte(s.MatriculeBeneficiaire);
    setDetail(null);
    setDetail(await consommationsApi.fraudeBeneficiaire(s.MatriculeBeneficiaire));
  };
  const n = donnees?.Niveaux || {};
  return (
    <>
      <Grille>
        <Tuile libelle="Niveau élevé" valeur={fcfa(n['Élevé'] || 0)} couleur="#e11d48" detail="score de 15 et plus" />
        <Tuile libelle="Niveau moyen" valeur={fcfa(n.Moyen || 0)} couleur="#d97706" detail="score de 8 à 14" />
        <Tuile libelle="Niveau faible" valeur={fcfa(n.Faible || 0)} detail="moins de 8" />
        <Tuile libelle="Fraudes avérées" valeur={fcfa(donnees?.Instructions?.FRAUDE || 0)} detail={`${fcfa(donnees?.Instructions?.JUSTIFIE || 0)} justifiés, ${fcfa(donnees?.Instructions?.SANS_SUITE || 0)} sans suite`} />
      </Grille>
      <Panneau titre="Règles de détection">
        <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          Chaque règle produit des signaux à instruire par un gestionnaire ou un médecin-conseil : un signal n'est jamais une preuve et ne bloque aucune prise en charge.
          Le score d'un bénéficiaire additionne le poids des règles déclenchées, au plus trois signaux comptés par règle.
        </p>
        <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.82rem' }}>
          <thead><tr><th>Règle</th><th>Critère</th><th style={DROITE}>Poids</th><th style={DROITE}>Signaux</th><th style={DROITE}>Bénéficiaires</th><th style={DROITE}>Remboursé concerné</th></tr></thead>
          <tbody>
            {(donnees?.Regles || []).map((r) => (
              <tr key={r.Code}><td><span style={MONO}>{r.Code}</span> {r.Regle}</td><td>{r.Critere}</td><td style={DROITE}>{r.Poids}</td><td style={DROITE}>{fcfa(r.Signaux)}</td><td style={DROITE}>{fcfa(r.Beneficiaires)}</td><td style={DROITE}>{montant(r.Montant)}</td></tr>
            ))}
            {!(donnees?.Regles || []).length && <Vide colonnes={6} chargement={chargement} texte="Aucune règle." />}
          </tbody>
        </table></div>
      </Panneau>
      <Panneau titre={`Bénéficiaires signalés : ${fcfa(donnees?.Total || 0)}`} actions={(
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <input aria-label="Rechercher un bénéficiaire" className="form-control" style={{ maxWidth: 240 }} value={recherche} onChange={(e) => setRecherche(e.target.value)} placeholder="Nom, matricule ou police" />
          <select aria-label="Niveau" className="form-control" style={{ maxWidth: 190 }} value={filtres.niveau} onChange={(e) => setFiltres((f) => ({ ...f, niveau: e.target.value }))}>
            <option value="">Tous les niveaux</option><option value="Élevé">Élevé</option><option value="Moyen">Moyen</option><option value="Faible">Faible</option>
          </select>
          <select aria-label="Instruction" className="form-control" style={{ maxWidth: 210 }} value={filtres.instruction} onChange={(e) => setFiltres((f) => ({ ...f, instruction: e.target.value }))}>
            <option value="">Toutes les décisions</option>
            {DECISIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      )}>
        <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.82rem' }}>
          <thead><tr><th style={DROITE}>Score</th><th>Niveau</th><th>Bénéficiaire</th><th>Police</th><th>Règles déclenchées</th><th style={DROITE}>Montant concerné</th><th>Instruction</th><th /></tr></thead>
          <tbody>
            {(donnees?.Suspicions || []).map((s) => (
              <React.Fragment key={s.MatriculeBeneficiaire}>
                <tr>
                  <td style={{ ...DROITE, fontWeight: 800 }}>{s.Score}</td>
                  <td><StatusBadge label={s.Niveau} color={COULEUR_NIVEAU[s.Niveau]} /></td>
                  <td style={{ fontWeight: 600 }}>{s.Beneficiaire}<div style={{ ...MONO, color: 'var(--text-muted)' }}>{s.MatriculeBeneficiaire}</div></td>
                  <td>{s.Police}</td>
                  <td style={MONO}>{Object.entries(s.Regles).map(([c, k]) => `${c} x${k}`).join('  ')}</td>
                  <td style={DROITE}>{montant(s.Montant)}</td>
                  <td><StatusBadge label={s.LibelleInstruction} color={COULEUR_INSTRUCTION[s.Instruction]} /></td>
                  <td style={DROITE}><button type="button" className={`btn ${ouverte === s.MatriculeBeneficiaire ? 'btn-primary' : 'btn-secondary'}`} style={{ fontSize: '0.76rem', padding: '0.2rem 0.6rem' }} onClick={() => ouvrir(s)}>Instruire</button></td>
                </tr>
                {ouverte === s.MatriculeBeneficiaire && (
                  <tr><td colSpan={8} style={{ background: 'var(--bg-secondary, rgba(0,0,0,0.03))' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', padding: '0.4rem 0.2rem' }}>
                      {detail ? <TableSignaux signaux={detail.Signaux} /> : <span><Loader2 size={14} className="spin" /> Lecture des signaux…</span>}
                      <div><button type="button" className="btn btn-secondary" style={{ fontSize: '0.78rem' }} onClick={() => onOuvrir(s.MatriculeAssure)}>Voir la fiche de la famille</button></div>
                      <Instruction suspicion={s} onEnregistree={recharger} />
                    </div>
                  </td></tr>
                )}
              </React.Fragment>
            ))}
            {!(donnees?.Suspicions || []).length && <Vide colonnes={8} chargement={chargement} texte="Aucun bénéficiaire signalé." />}
          </tbody>
        </table></div>
      </Panneau>
    </>
  );
};

// ------------------------------------------------------------------ imports
const OngletImports = () => {
  const { success, error: toastError } = useToast();
  const [fichier, setFichier] = useState(null);
  const [situation, setSituation] = useState('');
  const [analyse, setAnalyse] = useState(null);
  const [envoi, setEnvoi] = useState(false);
  const [donnees, chargement, recharger] = useLecture(() => consommationsApi.synthese({}), []);

  const choisir = (e) => { setFichier(e.target.files?.[0] || null); setAnalyse(null); };
  const analyser = async () => {
    setEnvoi(true);
    try { setAnalyse(await consommationsApi.analyser(fichier)); } catch (err) { toastError(messageErreurApi(err)); } finally { setEnvoi(false); }
  };
  const importer = async () => {
    if (!(await confirmer({ titre: 'Importer le relevé', message: `${fcfa(analyse.Nouvelles)} prestations nouvelles et ${fcfa(analyse.Effectif)} bénéficiaires d'effectif seront enregistrés. Les prestations déjà connues ne sont pas réécrites.`, confirmer: 'Importer' }))) return;
    setEnvoi(true);
    try {
      const r = await consommationsApi.importer(fichier, situation);
      success(`Relevé importé : ${fcfa(r.Nouvelles)} prestations nouvelles${r.Sorties ? `, ${fcfa(r.Sorties)} bénéficiaires sortis` : ''}.`);
      setAnalyse(null);
      setFichier(null);
      recharger();
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };
  const releves = donnees?.Releves || [];
  return (
    <>
      <Panneau titre="Importer un fichier du gestionnaire">
        <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
          Relevé de prestations (colonne NUMERO_PREST) ou effectif (colonne MATBENEF) au format Excel, toutes feuilles lues. Les relevés sont cumulatifs :
          une prestation déjà importée n'est jamais réécrite et un montant changé est signalé. Une date de soins postérieure à la clôture, jour et mois inversés, est corrigée et la date du relevé conservée.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <Champ id="imp-fichier" libelle="Fichier Excel"><input id="imp-fichier" type="file" accept=".xlsx" className="form-control" onChange={choisir} /></Champ>
          <Champ id="imp-situation" libelle="Effectif à jour au"><input id="imp-situation" type="date" className="form-control" value={situation} onChange={(e) => setSituation(e.target.value)} /></Champ>
          <button type="button" className="btn btn-secondary" disabled={!fichier || envoi} onClick={analyser} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            {envoi && !analyse ? <Loader2 size={14} className="spin" /> : <Search size={14} />} Analyser
          </button>
          {analyse && <button type="button" className="btn btn-primary" disabled={envoi} onClick={importer} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            {envoi ? <Loader2 size={14} className="spin" /> : <Upload size={14} />} Importer
          </button>}
        </div>
        <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text-muted)' }}>La date de l'effectif date la sortie des bénéficiaires absents du nouvel effectif ; laissée vide, la date du jour est retenue.</p>
        {analyse && (
          <Grille min={170}>
            <Tuile libelle="Prestations lues" valeur={fcfa(analyse.Prestations)} detail={analyse.ClotureDu ? `clôtures du ${dateFr(analyse.ClotureDu)} au ${dateFr(analyse.ClotureAu)}` : ''} />
            <Tuile libelle="Nouvelles" valeur={fcfa(analyse.Nouvelles)} couleur="var(--primary-500)" detail={`${fcfa(analyse.Connues)} déjà connues`} />
            <Tuile libelle="Montants changés" valeur={fcfa(analyse.MontantsChanges)} detail="signalés, non réécrits" />
            <Tuile libelle="Dates corrigées" valeur={fcfa(analyse.DatesCorrigees)} detail="jour et mois inversés" />
            <Tuile libelle="Effectif lu" valeur={fcfa(analyse.Effectif)} detail={analyse.Garants.join(', ')} />
            <Tuile libelle="Remboursé du fichier" valeur={montant(analyse.Rembourse)} />
          </Grille>
        )}
        {analyse && (
          <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.8rem' }}>
            <thead><tr><th>Feuille</th><th>Nature</th><th style={DROITE}>Lignes</th></tr></thead>
            <tbody>{analyse.Feuilles.map((f) => <tr key={f.Feuille}><td>{f.Feuille}</td><td>{f.Nature === 'EFFECTIF' ? 'Effectif' : 'Prestations'}</td><td style={DROITE}>{fcfa(f.Lignes)}</td></tr>)}</tbody>
          </table></div>
        )}
        {analyse?.ColonnesManquantes?.length > 0 && <p style={{ margin: 0, color: '#d97706', fontSize: '0.8rem' }}>Feuilles écartées, colonnes absentes : {analyse.ColonnesManquantes.join(' ; ')}</p>}
      </Panneau>
      <Panneau titre="Fichiers importés">
        <div className="table-wrapper"><table className="data-table" style={{ fontSize: '0.82rem' }}>
          <thead><tr><th>Date</th><th>Fichier</th><th>Nature</th><th>Garants</th><th>Clôtures</th><th style={DROITE}>Lignes</th><th style={DROITE}>Nouvelles</th><th style={DROITE}>Montants changés</th><th>Par</th></tr></thead>
          <tbody>
            {releves.map((r) => (
              <tr key={r.Id}>
                <td>{dateFr(r.Date)}</td><td>{r.Fichier}</td><td>{r.Nature === 'EFFECTIF' ? 'Effectif' : 'Prestations'}</td><td>{r.Garants}</td>
                <td>{r.ClotureDu ? `${dateFr(r.ClotureDu)} au ${dateFr(r.ClotureAu)}` : '-'}</td><td style={DROITE}>{fcfa(r.Lignes)}</td><td style={DROITE}>{fcfa(r.Nouvelles)}</td><td style={DROITE}>{fcfa(r.Modifiees)}</td><td>{r.Operateur}</td>
              </tr>
            ))}
            {!releves.length && <Vide colonnes={9} chargement={chargement} texte="Aucun fichier importé." />}
          </tbody>
        </table></div>
      </Panneau>
    </>
  );
};

// ------------------------------------------------------------------ page
export default function ConsommationsSantePage() {
  const [onglet, setOnglet] = useState('synthese');
  const [matricule, setMatricule] = useState(null);
  const voirFraude = aLeDroit('consommations.fraude');
  const importer = aLeDroit('consommations.import');
  const ouvrirFiche = (m) => { setMatricule(m); setOnglet('fiche'); };
  const changer = (cle) => { setMatricule(null); setOnglet(cle); };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem', paddingBottom: '2rem' }}>
      <div>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', margin: 0 }}><HeartPulse size={26} style={{ color: 'var(--primary-500)' }} /> Consommations santé</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0.3rem 0 0', maxWidth: 940 }}>
          Pour chaque assuré : ses droits, les prestations consommées par lui et ses bénéficiaires, les montants engagés, les plafonds utilisés et les soldes disponibles.
          Données des relevés du gestionnaire ; données de santé à ne pas diffuser.
        </p>
      </div>
      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }} role="tablist">
        <Onglet actif={onglet === 'synthese'} onClick={() => changer('synthese')} icone={BarChart3}>Synthèse</Onglet>
        <Onglet actif={onglet === 'fiche'} onClick={() => changer('fiche')} icone={UserSearch}>Fiche assuré</Onglet>
        <Onglet actif={onglet === 'plafonds'} onClick={() => changer('plafonds')} icone={Gauge}>Plafonds</Onglet>
        <Onglet actif={onglet === 'entreprises'} onClick={() => changer('entreprises')} icone={Building2}>Entreprises</Onglet>
        <Onglet actif={onglet === 'controles'} onClick={() => changer('controles')} icone={ListChecks}>Contrôles</Onglet>
        {voirFraude && <Onglet actif={onglet === 'fraude'} onClick={() => changer('fraude')} icone={ShieldAlert}>Fraude</Onglet>}
        {importer && <Onglet actif={onglet === 'imports'} onClick={() => changer('imports')} icone={Upload}>Imports</Onglet>}
      </div>
      {onglet === 'synthese' && <OngletSynthese />}
      {onglet === 'fiche' && <OngletFiche matriculeInitial={matricule} />}
      {onglet === 'plafonds' && <OngletPlafonds onOuvrir={ouvrirFiche} />}
      {onglet === 'entreprises' && <OngletEntreprises />}
      {onglet === 'controles' && <OngletControles />}
      {onglet === 'fraude' && voirFraude && <OngletFraude onOuvrir={ouvrirFiche} />}
      {onglet === 'imports' && importer && <OngletImports />}
    </div>
  );
}
