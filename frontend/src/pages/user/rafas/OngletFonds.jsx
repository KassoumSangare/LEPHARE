import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Ban, Banknote, Building2, Check, Coins, HandCoins, Loader2, Plus, Printer, ReceiptText, ShieldCheck, Trash2, TrendingUp, Undo2, UserMinus, UserPlus, Wallet,
} from 'lucide-react';
import { rafasApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { aLeDroit } from '../../../utils/droits';
import { confirmer, saisirTexte } from '../../../utils/dialogue';
import { messageErreurApi } from '../../../utils/financeUtils';
import { imprimerAppel, imprimerFacture, imprimerMouvement } from '../../../utils/impressionsRafas';
import Modal from '../../../components/common/Modal';
import { Cadre, Courbes } from '../sante/consommations/graphiques';
import { Badge, Carte, Champ, ChampMontant, Tableau, Tuile, dateFr, entier, francs, francsCourts, libelleRang, pct, periode, taux as tauxFr } from './rafasCommun';

/* Fonds du régime d'un exercice : budget (familles de la convention et effectif du gestionnaire), dépenses remboursées, appels de fonds et
   versements du souscripteur, solde et appel conseillé ; honoraires du gestionnaire et commission du cabinet (chiffre d'affaires). */

const MODES = [['VIREMENT', 'Virement'], ['CHEQUE', 'Chèque'], ['ESPECES', 'Espèces'], ['MOBILE', 'Mobile money'], ['COMPENSATION', 'Compensation']];
const libelleMode = (m) => (MODES.find((x) => x[0] === m) || [m, m || '-'])[1];
const aujourdhui = () => new Date().toISOString().slice(0, 10);
const joursEntre = (du, au) => Math.round((new Date(`${au}T00:00:00`) - new Date(`${du}T00:00:00`)) / 86400000) + 1;
const jourSuivant = (iso) => {
  const x = new Date(`${iso}T00:00:00`);
  x.setDate(x.getDate() + 1);
  return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`;
};

const FormulaireAppel = ({ fonds, ouvert, onFermer, onValider }) => {
  const [d, setD] = useState({});
  useEffect(() => {
    if (ouvert) setD({ date_appel: aujourdhui(), montant: fonds.AppelConseille || '', objet: fonds.Appels.length ? 'Réapprovisionnement du fonds' : 'Provision initiale pour dépenses de santé', date_limite: '' });
  }, [ouvert, fonds]);
  return (
    <Modal isOpen={ouvert} onClose={onFermer} title="Appel de fonds au souscripteur" subtitle="Provision mise à la disposition du cabinet pour faire face aux dépenses de santé">
      <div className="rafas-grille-2">
        <Champ libelle="Date de l'appel" requis><input type="date" className="form-control" value={d.date_appel || ''} onChange={(e) => setD({ ...d, date_appel: e.target.value })} /></Champ>
        <Champ libelle="À verser au plus tard"><input type="date" className="form-control" value={d.date_limite || ''} onChange={(e) => setD({ ...d, date_limite: e.target.value })} /></Champ>
        <Champ libelle="Montant (F)" requis aide={fonds.AppelConseille ? `Conseillé : ${francs(fonds.AppelConseille)} (${fonds.Exercice.mois_provision} mois de dépenses au rythme moyen, moins le solde)` : undefined}>
          <ChampMontant valeur={d.montant} onChange={(v) => setD({ ...d, montant: v })} />
        </Champ>
        <Champ libelle="Objet"><input className="form-control" value={d.objet || ''} onChange={(e) => setD({ ...d, objet: e.target.value })} /></Champ>
      </div>
      <div className="rafas-pied-assistant">
        <button type="button" className="btn btn-secondary" onClick={onFermer}>Annuler</button>
        <button type="button" className="btn btn-primary rafas-bouton" disabled={!d.montant} onClick={() => onValider(d)}><Check size={15} /> Émettre l'appel</button>
      </div>
    </Modal>
  );
};

const FormulaireVersement = ({ fonds, appel, ouvert, onFermer, onValider }) => {
  const [d, setD] = useState({});
  useEffect(() => {
    if (ouvert) setD({ date_versement: aujourdhui(), montant: appel ? appel.reste : '', mode: 'VIREMENT', reference: '', banque: '', idappel: appel?.idappel || '' });
  }, [ouvert, appel]);
  const ouverts = fonds.Appels.filter((x) => x.reste > 0);
  return (
    <Modal isOpen={ouvert} onClose={onFermer} title="Versement du souscripteur" subtitle="Somme reçue pour alimenter le fonds du régime">
      <div className="rafas-grille-2">
        <Champ libelle="Appel de fonds réglé">
          <select className="form-control" value={d.idappel || ''} onChange={(e) => { const x = ouverts.find((o) => String(o.idappel) === e.target.value); setD({ ...d, idappel: e.target.value, montant: x ? x.reste : d.montant }); }}>
            <option value="">Sans appel de fonds</option>
            {ouverts.map((x) => <option key={x.idappel} value={x.idappel}>{`${x.numero} - reste ${francs(x.reste)}`}</option>)}
          </select>
        </Champ>
        <Champ libelle="Date du versement" requis><input type="date" className="form-control" value={d.date_versement || ''} onChange={(e) => setD({ ...d, date_versement: e.target.value })} /></Champ>
        <Champ libelle="Montant (F)" requis><ChampMontant valeur={d.montant} onChange={(v) => setD({ ...d, montant: v })} /></Champ>
        <Champ libelle="Mode"><select className="form-control" value={d.mode} onChange={(e) => setD({ ...d, mode: e.target.value })}>{MODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></Champ>
        <Champ libelle="Référence"><input className="form-control" value={d.reference || ''} onChange={(e) => setD({ ...d, reference: e.target.value })} placeholder="N° de virement ou de chèque" /></Champ>
        <Champ libelle="Banque"><input className="form-control" value={d.banque || ''} onChange={(e) => setD({ ...d, banque: e.target.value })} /></Champ>
      </div>
      <div className="rafas-pied-assistant">
        <button type="button" className="btn btn-secondary" onClick={onFermer}>Annuler</button>
        <button type="button" className="btn btn-primary rafas-bouton" disabled={!d.montant || !d.date_versement} onClick={() => onValider({ ...d, idappel: d.idappel || null })}><Check size={15} /> Enregistrer</button>
      </div>
    </Modal>
  );
};

const FormulaireFacture = ({ fonds, beneficiaire, ouvert, onFermer, onValider }) => {
  const [d, setD] = useState({});
  const ex = fonds.Exercice;
  const taux = Number(beneficiaire === 'COURTIER' ? ex.taux_commission : ex.taux_honoraires);
  useEffect(() => {
    if (ouvert) setD({ periode_du: ex.date_effet, periode_au: ex.date_echeance, source: fonds.BudgetReel ? 'effectif' : 'convention', date_emission: aujourdhui(), numero: '', montant: null });
  }, [ouvert, ex, fonds.BudgetReel]);
  const cotisations = (d.source === 'effectif' ? fonds.BudgetReel : fonds.Budget)?.Cotisations || 0;
  const base = d.periode_du && d.periode_au ? Math.round((cotisations * joursEntre(d.periode_du, d.periode_au)) / fonds.JoursExercice) : 0;
  const calcule = Math.round((base * taux) / 100);
  const montant = d.montant === null || d.montant === undefined || d.montant === '' ? calcule : d.montant;
  return (
    <Modal isOpen={ouvert} onClose={onFermer} title={beneficiaire === 'COURTIER' ? 'Facture de commission du cabinet' : 'Honoraires du gestionnaire'}
      subtitle={beneficiaire === 'COURTIER' ? `${tauxFr(taux)} des cotisations : chiffre d'affaires du cabinet, compté au tableau de bord à la date d'émission` : `${tauxFr(taux)} des cotisations, réglés sur le fonds du régime`}>
      <div className="rafas-grille-2">
        <Champ libelle="Période du" requis><input type="date" className="form-control" value={d.periode_du || ''} onChange={(e) => setD({ ...d, periode_du: e.target.value, montant: null })} /></Champ>
        <Champ libelle="au" requis><input type="date" className="form-control" value={d.periode_au || ''} onChange={(e) => setD({ ...d, periode_au: e.target.value, montant: null })} /></Champ>
        <Champ libelle="Familles retenues" aide="La convention calcule les honoraires sur l'ensemble des familles bénéficiant des prestations.">
          <select className="form-control" value={d.source} onChange={(e) => setD({ ...d, source: e.target.value, montant: null })}>
            <option value="convention">{`Familles de la convention${fonds.BudgetInitial && fonds.BudgetInitial.Cotisations !== fonds.Budget.Cotisations ? ', après incorporations et retraits' : ''} : ${francs(fonds.Budget.Cotisations)} de cotisations`}</option>
            {fonds.BudgetReel && <option value="effectif">{`Familles de l'effectif du gestionnaire : ${francs(fonds.BudgetReel.Cotisations)}`}</option>}
          </select>
        </Champ>
        <Champ libelle="Date d'émission" requis><input type="date" className="form-control" value={d.date_emission || ''} onChange={(e) => setD({ ...d, date_emission: e.target.value })} /></Champ>
        <Champ libelle="Base : cotisations de la période" aide={`${entier(d.periode_du && d.periode_au ? joursEntre(d.periode_du, d.periode_au) : 0)} jours sur ${entier(fonds.JoursExercice)}`}>
          <input className="form-control rafas-nombre" value={francs(base)} readOnly />
        </Champ>
        <Champ libelle="Montant (F)" aide={`Calculé : ${francs(calcule)} ; modifiable`}>
          <ChampMontant valeur={montant} onChange={(v) => setD({ ...d, montant: v })} />
        </Champ>
        {beneficiaire === 'GESTIONNAIRE' && <Champ libelle="N° de la facture du gestionnaire" aide="Vide : numéro attribué par LE PHARE."><input className="form-control" value={d.numero || ''} onChange={(e) => setD({ ...d, numero: e.target.value })} /></Champ>}
      </div>
      <div className="rafas-pied-assistant">
        <button type="button" className="btn btn-secondary" onClick={onFermer}>Annuler</button>
        <button type="button" className="btn btn-primary rafas-bouton" disabled={!d.periode_du || !d.periode_au}
          onClick={() => onValider({ beneficiaire, periode_du: d.periode_du, periode_au: d.periode_au, base, taux, montant, date_emission: d.date_emission, numero: d.numero })}>
          <Check size={15} /> Enregistrer
        </button>
      </div>
    </Modal>
  );
};

const FormulaireReglement = ({ facture, onFermer, onValider }) => {
  const [d, setD] = useState({});
  useEffect(() => { if (facture) setD({ date_paiement: aujourdhui(), mode: 'VIREMENT', reference: '' }); }, [facture]);
  return (
    <Modal isOpen={Boolean(facture)} onClose={onFermer} title={`Règlement de ${facture?.numero || ''}`} subtitle={facture ? francs(facture.montant) : ''}>
      <div className="rafas-grille-2">
        <Champ libelle="Date du règlement" requis><input type="date" className="form-control" value={d.date_paiement || ''} onChange={(e) => setD({ ...d, date_paiement: e.target.value })} /></Champ>
        <Champ libelle="Mode"><select className="form-control" value={d.mode} onChange={(e) => setD({ ...d, mode: e.target.value })}>{MODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></Champ>
        <Champ libelle="Référence" large><input className="form-control" value={d.reference || ''} onChange={(e) => setD({ ...d, reference: e.target.value })} /></Champ>
      </div>
      <div className="rafas-pied-assistant">
        <button type="button" className="btn btn-secondary" onClick={onFermer}>Annuler</button>
        <button type="button" className="btn btn-primary rafas-bouton" disabled={!d.date_paiement} onClick={() => onValider(d)}><Check size={15} /> Enregistrer le règlement</button>
      </div>
    </Modal>
  );
};

// Incorporation ou retrait de familles dans un collège de l'exercice (demande du 2026-11-20). Les familles se choisissent dans la liste du
// collège : pour un retrait, ses familles ; pour une incorporation, celles entrées dans l'effectif du gestionnaire depuis le début de
// l'exercice, plus les familles pas encore dans l'effectif, ajoutées une à une. Cotisation annuelle entière par défaut (tarif forfaitaire),
// au prorata des jours restants si la case est cochée.
const cleFamille = (f) => (f.Matricule ? `M${f.Matricule}` : `N${String(f.Nom || '').trim().toUpperCase()}`);

const ChoixFamilles = ({ titre, liste, choisies, onBasculer, raison, origine, avecEntree }) => {
  const [texte, setTexte] = useState('');
  const visibles = liste.filter((f) => !texte.trim() || `${f.Nom} ${f.Matricule}`.toLowerCase().includes(texte.trim().toLowerCase()));
  return (
    <div className="rafas-champ large">
      <span className="form-label">{`${titre} : ${entier(choisies.size)} cochée${choisies.size > 1 ? 's' : ''} sur ${entier(liste.filter((f) => !raison(f)).length)}`}</span>
      <input className="form-control" value={texte} onChange={(e) => setTexte(e.target.value)} placeholder="Rechercher un adhérent ou un matricule" aria-label="Rechercher une famille" />
      <div className="table-wrapper" style={{ maxHeight: 240, overflow: 'auto', marginTop: '0.4rem' }}>
        <table className="data-table" style={{ fontSize: '0.82rem' }}>
          <thead><tr><th aria-label="Choisir" /><th>Adhérent</th><th>Matricule</th><th className="rafas-nombre">Personnes</th>{avecEntree && <th>Entrée</th>}<th>Origine</th></tr></thead>
          <tbody>
            {visibles.map((f) => {
              const cle = cleFamille(f);
              const bloque = raison(f);
              return (
                <tr key={cle} style={bloque ? { opacity: 0.55 } : choisies.has(cle) ? { background: 'var(--primary-glow)' } : undefined}>
                  <td><input type="checkbox" checked={choisies.has(cle)} disabled={Boolean(bloque)} onChange={() => onBasculer(f)} aria-label={`Choisir la famille ${f.Nom}`} /></td>
                  <td>{f.Nom}</td>
                  <td>{f.Matricule || '-'}</td>
                  <td className="rafas-nombre">{f.Personnes ? entier(f.Personnes) : '-'}</td>
                  {avecEntree && <td>{f.Entree ? dateFr(f.Entree) : '-'}</td>}
                  <td>{bloque || origine(f)}</td>
                </tr>
              );
            })}
            {!visibles.length && <tr><td colSpan={avecEntree ? 6 : 5} className="cs-muet">{liste.length ? 'Aucune famille ne correspond.' : 'Aucune famille.'}</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Familles ajoutées une à une (pas encore dans l'effectif du gestionnaire) : adhérent, matricule, personnes
const AjoutFamilles = ({ titre, ajoutees, onChange }) => {
  const [f, setF] = useState({ Nom: '', Matricule: '', Personnes: '1' });
  const ajouter = () => {
    const nom = f.Nom.trim().toUpperCase();
    if (!nom) return;
    onChange([...ajoutees, { Nom: nom, Matricule: f.Matricule.trim(), Personnes: Number(f.Personnes) > 0 ? Number(f.Personnes) : null }]);
    setF({ Nom: '', Matricule: '', Personnes: '1' });
  };
  return (
    <div className="rafas-champ large">
      <span className="form-label">{titre}</span>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr) 90px auto', gap: '0.4rem', alignItems: 'center' }}>
        <input className="form-control" value={f.Nom} onChange={(e) => setF({ ...f, Nom: e.target.value })} placeholder="Nom et prénoms de l'adhérent" aria-label="Nom de l'adhérent"
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); ajouter(); } }} />
        <input className="form-control" value={f.Matricule} onChange={(e) => setF({ ...f, Matricule: e.target.value })} placeholder="Matricule" aria-label="Matricule de l'adhérent" />
        <input type="number" min="1" max="30" className="form-control rafas-nombre" value={f.Personnes} onChange={(e) => setF({ ...f, Personnes: e.target.value })} aria-label="Nombre de personnes" title="Personnes de la famille" />
        <button type="button" className="btn btn-secondary rafas-bouton" disabled={!f.Nom.trim()} onClick={ajouter}><Plus size={15} /> Ajouter</button>
      </div>
      {ajoutees.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, margin: '0.4rem 0 0', display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
          {ajoutees.map((a, i) => (
            <li key={`${a.Nom}-${i}`} className="cs-etat ton-neutre">
              {`${a.Nom}${a.Matricule ? `, ${a.Matricule}` : ''}${a.Personnes ? `, ${a.Personnes} pers.` : ''}`}
              <button type="button" className="rafas-icone-bouton" style={{ marginLeft: 4, width: 20, height: 20 }} title="Retirer de la liste" aria-label={`Retirer ${a.Nom} de la liste`}
                onClick={() => onChange(ajoutees.filter((_x, j) => j !== i))}><Trash2 size={12} /></button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

const FormulaireMouvement = ({ fonds, nature, ouvert, onFermer, onValider }) => {
  const ex = fonds.Exercice;
  const [d, setD] = useState({});
  const [liste, setListe] = useState(null);
  const [choisies, setChoisies] = useState(new Map());
  const [ajoutees, setAjoutees] = useState([]);
  const incorporation = nature === 'INCORPORATION';
  // Une incorporation se fait en cours de contrat : au plus tôt le lendemain du premier jour de l'exercice
  const debut = incorporation ? jourSuivant(ex.date_effet) : ex.date_effet;
  useEffect(() => {
    if (!ouvert) return;
    const jour = aujourdhui();
    setD({ code_college: fonds.Colleges[0]?.Code || '', date_effet: jour < debut ? debut : jour > ex.date_echeance ? ex.date_echeance : jour,
      familles: '', prorata: false, motif: '' });
  }, [ouvert, fonds, ex, debut]);
  // Familles du collège choisi (effectif du gestionnaire et avenants) ; situation : date de l'effectif importé, null sans effectif
  const [situation, setSituation] = useState(null);
  useEffect(() => {
    setChoisies(new Map());
    setAjoutees([]);
    setListe(null);
    setSituation(null);
    if (!ouvert || !d.code_college) return undefined;
    let annule = false;
    rafasApi.famillesCollege(ex.idexercice, d.code_college)
      .then((r) => { if (!annule) { setListe(r.Familles || []); setSituation(r.Situation || null); } })
      .catch(() => { if (!annule) setListe([]); });
    return () => { annule = true; };
  }, [ouvert, d.code_college, ex.idexercice]);
  const basculer = (f) => setChoisies((m) => { const n = new Map(m); const cle = cleFamille(f); if (n.has(cle)) n.delete(cle); else n.set(cle, f); return n; });

  // Incorporation : familles entrées dans l'effectif depuis le début de l'exercice ; retrait : toutes les familles du collège, sorties en tête
  const proposees = (liste || []).filter((f) => f.Source === 'EFFECTIF' && f.Nouvelle && !f.Retiree)
    .sort((a, b) => Boolean(a.Sortie) - Boolean(b.Sortie) || String(a.Nom).localeCompare(String(b.Nom), 'fr'));
  const avecEffectif = Boolean(situation);
  const choix = [...choisies.values()].map((f) => ({ Nom: f.Nom, Matricule: f.Matricule, Personnes: f.Personnes || null }));
  const adherents = [...choix, ...ajoutees];
  // Retrait sans effectif importé : les familles de la convention ne sont pas nommées, leur nombre peut se saisir seul
  const nombreLibre = !incorporation && liste !== null && !avecEffectif;
  const familles = adherents.length || (nombreLibre ? Number(d.familles) || 0 : 0);
  const college = fonds.Colleges.find((c) => c.Code === d.code_college);
  const fraction = d.prorata && d.date_effet ? Math.max(0, Math.min(1, joursEntre(d.date_effet, ex.date_echeance) / fonds.JoursExercice)) : 1;
  const montant = college ? Math.round(college.Cotisation * familles * fraction) : 0;
  const maximum = college?.FamillesApresMouvements ?? 0;
  const trop = !incorporation && familles > maximum;
  const raisonIncorporation = (f) => (f.Incorporee ? `Déjà incorporée, ${f.Incorporee}` : '');
  const raisonRetrait = (f) => (f.Retiree ? `Déjà retirée, ${f.Retiree}` : '');
  const sortie = (f) => (f.Sortie ? `Sortie ${f.Sortie > aujourdhui() ? 'prévue ' : ''}le ${dateFr(f.Sortie)}` : '');
  return (
    <Modal isOpen={ouvert} onClose={onFermer} size="large" title={incorporation ? 'Incorporer des familles' : 'Retirer des familles'}
      subtitle={`Exercice du ${dateFr(ex.date_effet)} au ${dateFr(ex.date_echeance)}`}>
      <div className="rafas-grille-2">
        <Champ libelle="Collège" requis>
          <select className="form-control" value={d.code_college || ''} onChange={(e) => setD({ ...d, code_college: e.target.value })}>
            {fonds.Colleges.map((c) => <option key={c.Code} value={c.Code}>{`${c.Libelle} - ${francs(c.Cotisation)} par famille, ${entier(c.FamillesApresMouvements)} familles`}</option>)}
          </select>
        </Champ>
        <Champ libelle="Date d'effet" requis>
          <input type="date" className="form-control" min={debut} max={ex.date_echeance} value={d.date_effet || ''} onChange={(e) => setD({ ...d, date_effet: e.target.value })} />
        </Champ>
        <Champ libelle="Nombre de familles" requis aide={trop ? `Le collège compte ${entier(maximum)} familles.` : undefined}>
          <input type="number" min="1" className="form-control rafas-nombre" disabled={!nombreLibre || adherents.length > 0}
            value={familles || d.familles || ''} onChange={(e) => setD({ ...d, familles: e.target.value })} />
        </Champ>
        <Champ libelle={incorporation ? 'Cotisations ajoutées' : 'Cotisations retirées'}>
          <input className="form-control rafas-nombre" value={francs(montant)} readOnly />
        </Champ>
        {liste === null && <p className="cs-muet rafas-champ large"><Loader2 size={14} className="spin" /> Familles du collège…</p>}
        {liste !== null && incorporation && (
          <>
            {avecEffectif && (
              <ChoixFamilles titre={`Familles entrées en cours de contrat, après le ${dateFr(ex.date_effet)}`} liste={proposees} choisies={choisies}
                onBasculer={basculer} raison={raisonIncorporation} origine={(f) => sortie(f) || 'Effectif du gestionnaire'} avecEntree />
            )}
            <AjoutFamilles titre={avecEffectif ? "Famille pas encore dans l'effectif du gestionnaire" : 'Familles à incorporer'} ajoutees={ajoutees} onChange={setAjoutees} />
          </>
        )}
        {!incorporation && liste !== null && liste.length > 0 && (
          <ChoixFamilles titre={avecEffectif ? 'Familles à retirer' : 'Familles incorporées par avenant'} liste={liste} choisies={choisies} onBasculer={basculer}
            raison={raisonRetrait} origine={(f) => sortie(f) || (f.Source === 'INCORPORATION' ? `Incorporée, ${f.Avenant}` : 'Effectif du gestionnaire')} />
        )}
        {nombreLibre && (
          <AjoutFamilles titre={liste.length ? 'Autres familles à retirer, ou leur nombre' : 'Familles à retirer, ou leur nombre'} ajoutees={ajoutees} onChange={setAjoutees} />
        )}
        <Champ libelle="Motif" large>
          <input className="form-control" maxLength={500} value={d.motif || ''} onChange={(e) => setD({ ...d, motif: e.target.value })}
            placeholder={incorporation ? 'Embauches, mutations…' : 'Départs, démissions…'} />
        </Champ>
      </div>
      <label className="cs-filtre en-ligne" style={{ marginTop: '0.6rem' }}>
        <input type="checkbox" checked={Boolean(d.prorata)} onChange={(e) => setD({ ...d, prorata: e.target.checked })} />
        <span>{`Au prorata des jours restants de l'exercice${d.prorata && d.date_effet ? ` : ${entier(joursEntre(d.date_effet, ex.date_echeance))} jours sur ${entier(fonds.JoursExercice)}` : ''}`}</span>
      </label>
      <div className="rafas-pied-assistant">
        <button type="button" className="btn btn-secondary" onClick={onFermer}>Annuler</button>
        <button type="button" className="btn btn-primary rafas-bouton" disabled={!college || !familles || !d.date_effet || d.date_effet < debut || d.date_effet > ex.date_echeance || trop}
          onClick={() => onValider({ nature, code_college: d.code_college, date_effet: d.date_effet, familles, adherents, prorata: Boolean(d.prorata), motif: d.motif })}>
          <Check size={15} /> {`${incorporation ? 'Incorporer' : 'Retirer'}${familles > 1 ? ` ${entier(familles)} familles` : familles === 1 ? ' la famille' : ''}`}
        </button>
      </div>
    </Modal>
  );
};

const OngletFonds = ({ id, convention, onModifie }) => {
  const { success, error: toastError } = useToast();
  const [exercice, setExercice] = useState(convention.ExerciceCourant ? String(convention.ExerciceCourant) : '');
  const [fonds, setFonds] = useState(null);
  const [reel, setReel] = useState(true);
  const [fenetre, setFenetre] = useState(null);
  const [envoi, setEnvoi] = useState(false);
  const peut = aLeDroit('rafas.manage');
  const charger = useCallback(() => rafasApi.fonds(id, exercice).then(setFonds).catch((err) => toastError(messageErreurApi(err))), [id, exercice, toastError]);
  useEffect(() => { charger(); }, [charger]);

  const action = async (fonction, message) => {
    setEnvoi(true);
    try {
      const r = await fonction();
      setFonds((f) => ({ ...f, ...r }));
      setFenetre(null);
      if (message) success(message);
      onModifie?.();
      return r;
    } catch (err) {
      toastError(messageErreurApi(err));
      return null;
    } finally {
      setEnvoi(false);
    }
  };
  const supprimer = async (texte, fonction, message) => {
    if (await confirmer({ titre: 'Confirmer la suppression', message: texte, confirmer: 'Supprimer', ton: 'danger' })) action(fonction, message);
  };

  const serie = useMemo(() => (fonds ? fonds.Mensuel : []), [fonds]);
  if (!fonds) return <div className="rafas-chargement"><Loader2 size={22} className="spin" /> Situation du fonds…</div>;
  const ex = fonds.Exercice;
  const budget = reel && fonds.BudgetReel ? fonds.BudgetReel : fonds.Budget;
  const taux = reel && fonds.BudgetReel ? fonds.TauxEnveloppeReel : fonds.TauxEnveloppe;
  const conv = convention.Convention;
  const exerciceComplet = convention.Exercices.find((e) => e.idexercice === ex.idexercice);
  const factures = (b) => fonds.Honoraires.filter((h) => h.beneficiaire === b);
  const actifs = (fonds.Mouvements || []).filter((m) => !m.Annule);
  const ajustement = (code) => actifs.filter((m) => m.CodeCollege === code).reduce((s, m) => s + Number(m.Montant), 0);
  const annulerMouvement = async (m) => {
    const motif = await saisirTexte({
      titre: `Annuler ${m.Numero}`, message: `${m.Libelle} de ${entier(m.Familles)} famille${m.Familles > 1 ? 's' : ''} : les cotisations de l'exercice seront rétablies. Indiquez le motif.`,
      minimum: 5, maximum: 500, confirmer: 'Annuler le mouvement', ton: 'danger',
    });
    if (motif) action(() => rafasApi.annulerMouvement(m.IdMouvement, motif), `${m.Numero} annulé.`);
  };
  const colonnesFactures = [
    { cle: 'numero', libelle: 'Facture', rendu: (h) => <span className="rafas-facture"><strong>{h.numero}</strong><span>{`émise le ${dateFr(h.date_emission)}`}</span></span> },
    { cle: 'periode', libelle: 'Période', rendu: (h) => <span className="rafas-facture"><span>{`du ${dateFr(h.periode_du)}`}</span><span>{`au ${dateFr(h.periode_au)}`}</span></span> },
    { cle: 'montant', libelle: 'Montant', nombre: true, rendu: (h) => <span className="rafas-facture droite"><strong>{francs(h.montant)}</strong><span>{`sur ${francsCourts(h.base)}`}</span></span> },
    { cle: 'statut', libelle: 'Règlement', rendu: (h) => (h.date_paiement ? <Badge ton="bon">{`Réglé le ${dateFr(h.date_paiement)}`}</Badge> : <Badge ton="attention">À régler</Badge>) },
    { cle: 'actions', libelle: '', rendu: (h) => (
      <div className="rafas-actions-ligne">
        <button type="button" className="rafas-icone-bouton" title="Imprimer" onClick={() => imprimerFacture(conv, exerciceComplet || ex, h)}><Printer size={15} /></button>
        {peut && !h.date_paiement && <button type="button" className="rafas-icone-bouton" title="Enregistrer le règlement" onClick={() => setFenetre({ type: 'reglement', facture: h })}><Banknote size={15} /></button>}
        {peut && h.date_paiement && <button type="button" className="rafas-icone-bouton" title="Annuler le règlement" onClick={() => action(() => rafasApi.reglerHonoraire(h.idhonoraire, {}), 'Règlement annulé.')}><Undo2 size={15} /></button>}
        {peut && !h.date_paiement && <button type="button" className="rafas-icone-bouton danger" title="Supprimer" onClick={() => supprimer(`Supprimer ${h.numero} ?`, () => rafasApi.supprimerHonoraire(h.idhonoraire), 'Facture supprimée.')}><Trash2 size={15} /></button>}
      </div>
    ) },
  ];
  return (
    <div className="cs-pile">
      <div className="glass-panel cs-filtres">
        <label className="cs-filtre large">
          <span>Exercice</span>
          <select className="form-control" value={String(ex.idexercice)} onChange={(e) => setExercice(e.target.value)}>
            {fonds.ExercicesListe.map((e) => <option key={e.idexercice} value={e.idexercice}>{`${libelleRang(e.rang)} ${periode(e)}`}</option>)}
          </select>
        </label>
        {fonds.BudgetReel && (
          <label className="cs-filtre en-ligne">
            <input type="checkbox" checked={reel} onChange={(e) => setReel(e.target.checked)} />
            <span>{`Budget sur l'effectif du gestionnaire du ${dateFr(fonds.SituationEffectif)}`}</span>
          </label>
        )}
        <p className="cs-filtres-note">{`Échéance le ${dateFr(fonds.Echeance)} ; préavis de dénonciation avant le ${dateFr(fonds.Preavis)}.`}</p>
      </div>

      <div className="cs-une">
        <Carte className={`cs-heros rafas-solde ${fonds.Solde < 0 ? 'negatif' : ''}`}>
          <div className="cs-heros-libelle">Solde du fonds</div>
          <div className={`cs-heros-valeur${fonds.Solde < 0 ? ' rafas-negatif' : ''}`}>{francsCourts(fonds.Solde)}</div>
          <div className="cs-heros-detail">{`Versements ${francs(fonds.Versements)} - dépenses ${francs(fonds.Depenses)} - honoraires réglés ${francs(fonds.HonorairesRegles.GESTIONNAIRE + fonds.HonorairesRegles.COURTIER)}`}</div>
          {fonds.Alerte ? (
            <div className="rafas-alerte">
              <Wallet size={18} aria-hidden="true" />
              <div>
                <strong>{`Appel de fonds conseillé : ${francs(fonds.AppelConseille)}`}</strong>
                <p>{fonds.Seuil ? `Le solde est sous le seuil d'alerte de ${francs(fonds.Seuil)} (${ex.seuil_alerte_mois} mois de dépenses au rythme moyen de ${francs(fonds.Rythme)}).` : 'Des dépenses sont remboursées sans versement du souscripteur sur cet exercice.'}</p>
              </div>
              {peut && <button type="button" className="btn btn-primary rafas-bouton" onClick={() => setFenetre({ type: 'appel' })}><HandCoins size={15} /> Préparer l'appel</button>}
            </div>
          ) : <Badge ton="bon">Fonds suffisant au rythme actuel</Badge>}
          {fonds.BesoinEcheance !== null && <p className="cs-note">{`Besoin estimé jusqu'à l'échéance : ${francs(fonds.BesoinEcheance)} (${fonds.MoisRestants} mois de dépenses au rythme moyen et honoraires restant dus).`}</p>}
        </Carte>
        <div className="cs-tuiles">
          <Tuile libelle="Cotisations de l'exercice" icone={Coins} valeur={francsCourts(budget.Cotisations)}
            detail={reel && fonds.BudgetReel ? "Sur l'effectif du gestionnaire" : actifs.length ? 'Familles de la convention, après incorporations et retraits' : 'Familles de la convention'} />
          <Tuile libelle="Enveloppe des sinistres" icone={ShieldCheck} valeur={francsCourts(budget.Enveloppe)} detail={`${pct(taux, 0)} consommés`} />
          <Tuile libelle="Projection à l'échéance" icone={TrendingUp} valeur={francsCourts(fonds.Projection)} detail={`Rythme ${francsCourts(fonds.Rythme)} par mois sur ${fonds.MoisAvecDonnees} mois`} />
          <Tuile libelle={`Honoraires du gestionnaire, ${tauxFr(ex.taux_honoraires)}`} icone={Building2} valeur={francsCourts(budget.Honoraires)} detail={`Émis ${francsCourts(fonds.HonorairesEmis.GESTIONNAIRE)}, réglés ${francsCourts(fonds.HonorairesRegles.GESTIONNAIRE)}`} />
          <Tuile libelle={`Commission du cabinet, ${tauxFr(ex.taux_commission)}`} icone={HandCoins} valeur={francsCourts(budget.Commission)} ton="accent" detail={`Facturée ${francsCourts(fonds.HonorairesEmis.COURTIER)}, encaissée ${francsCourts(fonds.HonorairesRegles.COURTIER)}`} />
          <Tuile libelle="Versements du souscripteur" icone={Wallet} valeur={francsCourts(fonds.Versements)} detail={`${fonds.Appels.length} appel${fonds.Appels.length > 1 ? 's' : ''} de fonds`} />
        </div>
      </div>

      <div className="cs-deux">
        <Carte titre="Dépenses cumulées et enveloppe" sousTitre="Dépenses remboursées cumulées mois par mois, face à l'enveloppe des sinistres répartie sur l'exercice.">
          <Cadre legende={[{ libelle: 'Dépenses cumulées', couleur: 'var(--cs-viz-1)', forme: 'ligne' }, { libelle: 'Enveloppe au prorata', couleur: 'var(--cs-attenue)', forme: 'repere' }]}
            tableau={{ entetes: ['Mois', 'Dépenses', 'Cumul', 'Enveloppe au prorata'], lignes: serie.map((m) => [m.Libelle, francs(m.Depenses), francs(m.Cumul), francs(m.Prorata)]) }}>
            <Courbes etiquettes={serie.map((m) => ({ cle: m.Mois, libelle: m.Libelle, libelleCourt: m.LibelleCourt, libelleLong: m.Libelle }))} libelleAria="Dépenses cumulées et enveloppe au prorata"
              series={[{ cle: 'cumul', libelle: 'Dépenses cumulées', valeurs: serie.map((m) => m.Cumul), couleur: 'var(--cs-viz-1)', style: 'plein', aire: true },
                { cle: 'prorata', libelle: 'Enveloppe au prorata', valeurs: serie.map((m) => m.Prorata), couleur: 'var(--cs-attenue)', style: 'repere', libelleFin: 'enveloppe' }]} />
          </Cadre>
        </Carte>
        <Carte titre="Cotisations par collège" sousTitre="Familles de la convention et familles de l'effectif du gestionnaire (adhérents distincts, sortis exclus).">
          <Tableau compact colonnes={[
            { cle: 'Libelle', libelle: 'Collège' },
            { cle: 'Cotisation', libelle: 'Par famille', nombre: true, rendu: (c) => francs(c.Cotisation) },
            { cle: 'Familles', libelle: 'Familles : convention', nombre: true },
            ...(actifs.length ? [{ cle: 'FamillesApresMouvements', libelle: 'après mouvements', nombre: true }] : []),
            { cle: 'FamillesReelles', libelle: 'effectif', nombre: true, rendu: (c) => (c.FamillesReelles === null ? '-' : entier(c.FamillesReelles)) },
            { cle: 'Budget', libelle: 'Cotisations', nombre: true, rendu: (c) => francs(reel && c.BudgetReel !== null ? c.BudgetReel : c.Budget + ajustement(c.Code)) },
          ]} lignes={fonds.Colleges}
            pied={{ Libelle: 'Total', Familles: fonds.Colleges.reduce((s, c) => s + c.Familles, 0),
              FamillesApresMouvements: fonds.Colleges.reduce((s, c) => s + (c.FamillesApresMouvements || 0), 0),
              FamillesReelles: fonds.BudgetReel ? fonds.Colleges.reduce((s, c) => s + (c.FamillesReelles || 0), 0) : null, Cotisation: null, Budget: budget.Cotisations, BudgetReel: budget.Cotisations, Code: '' }} />
          {fonds.FamillesNonRattachees > 0 && <p className="cs-note">{`${entier(fonds.FamillesNonRattachees)} familles de l'effectif relèvent de collèges du gestionnaire non rattachés : onglet Fichiers du gestionnaire.`}</p>}
        </Carte>
      </div>

      <Carte titre="Incorporations et retraits" sousTitre="Familles entrées dans un collège ou sorties en cours d'exercice : elles ajustent les cotisations, les honoraires et la commission."
        actions={peut && fonds.Colleges.length > 0 && <>
          <button type="button" className="btn btn-secondary rafas-bouton" onClick={() => setFenetre({ type: 'mouvement', nature: 'RETRAIT' })}><UserMinus size={15} /> Retirer des familles</button>
          <button type="button" className="btn btn-primary rafas-bouton" onClick={() => setFenetre({ type: 'mouvement', nature: 'INCORPORATION' })}><UserPlus size={15} /> Incorporer des familles</button>
        </>}>
        <Tableau vide="Aucune incorporation ni aucun retrait sur cet exercice." colonnes={[
          { cle: 'Numero', libelle: 'Avenant', rendu: (m) => <span className="rafas-facture"><strong>{m.Numero}</strong><span>{m.Operateur || ''}</span></span> },
          { cle: 'Nature', libelle: 'Mouvement', rendu: (m) => (
            <span className="rafas-facture">
              <Badge ton={m.Annule ? 'neutre' : m.Nature === 'INCORPORATION' ? 'bon' : 'attention'}>{m.Libelle}</Badge>
              {m.Annule && <span title={m.MotifAnnulation}>{`Annulé : ${m.MotifAnnulation}`}</span>}
            </span>
          ) },
          { cle: 'DateEffet', libelle: 'Effet', rendu: (m) => dateFr(m.DateEffet) },
          { cle: 'College', libelle: 'Collège' },
          { cle: 'Familles', libelle: 'Familles', nombre: true, rendu: (m) => <span className="rafas-facture droite"><strong>{entier(m.Familles)}</strong>{m.Personnes ? <span>{`${entier(m.Personnes)} personnes`}</span> : null}</span> },
          { cle: 'Adherents', libelle: 'Adhérents', rendu: (m) => (m.Adherents.length
            ? <span title={m.Adherents.map((a) => a.Nom).join(', ')}>{m.Adherents.slice(0, 3).map((a) => a.Nom).join(', ')}{m.Adherents.length > 3 ? `, et ${m.Adherents.length - 3} autres` : ''}</span>
            : <span className="cs-muet">-</span>) },
          { cle: 'Montant', libelle: 'Cotisations', nombre: true, rendu: (m) => (
            <span className={`rafas-facture droite${m.Annule ? ' cs-muet' : ''}`}>
              <strong>{`${Number(m.Montant) >= 0 ? '+' : '-'} ${francs(Math.abs(Number(m.Montant)))}`}</strong>
              <span>{m.Prorata ? `au prorata, ${pct(Number(m.Fraction), 0)}` : 'cotisation annuelle'}</span>
            </span>
          ) },
          { cle: 'actions', libelle: '', rendu: (m) => (
            <div className="rafas-actions-ligne">
              <button type="button" className="rafas-icone-bouton" title="Imprimer l'avenant" onClick={() => imprimerMouvement(conv, fonds, m)}><Printer size={15} /></button>
              {peut && !m.Annule && <button type="button" className="rafas-icone-bouton danger" title="Annuler" onClick={() => annulerMouvement(m)}><Ban size={15} /></button>}
            </div>
          ) },
        ]} lignes={fonds.Mouvements || []} />
      </Carte>

      <Carte titre="Appels de fonds et versements" sousTitre="La provision demandée au souscripteur en début d'année, puis ajustée selon les dépenses."
        actions={peut && <>
          <button type="button" className="btn btn-secondary rafas-bouton" onClick={() => setFenetre({ type: 'versement' })}><Banknote size={15} /> Versement reçu</button>
          <button type="button" className="btn btn-primary rafas-bouton" onClick={() => setFenetre({ type: 'appel' })}><Plus size={15} /> Appel de fonds</button>
        </>}>
        <Tableau vide="Aucun appel de fonds sur cet exercice." colonnes={[
          { cle: 'numero', libelle: 'Numéro' }, { cle: 'date_appel', libelle: 'Date', rendu: (x) => dateFr(x.date_appel) }, { cle: 'objet', libelle: 'Objet' },
          { cle: 'montant', libelle: 'Montant', nombre: true, rendu: (x) => francs(x.montant) }, { cle: 'verse', libelle: 'Versé', nombre: true, rendu: (x) => francs(x.verse) },
          { cle: 'reste', libelle: 'Reste', nombre: true, rendu: (x) => (x.reste > 0 ? <strong>{francs(x.reste)}</strong> : <Badge ton="bon">Soldé</Badge>) },
          { cle: 'actions', libelle: '', rendu: (x) => (
            <div className="rafas-actions-ligne">
              <button type="button" className="rafas-icone-bouton" title="Imprimer la lettre d'appel" onClick={() => imprimerAppel(conv, fonds, x)}><Printer size={15} /></button>
              {peut && x.reste > 0 && <button type="button" className="rafas-icone-bouton" title="Enregistrer le versement" onClick={() => setFenetre({ type: 'versement', appel: x })}><Banknote size={15} /></button>}
              {peut && !Number(x.verse) && <button type="button" className="rafas-icone-bouton danger" title="Supprimer" onClick={() => supprimer(`Supprimer l'appel ${x.numero} ?`, () => rafasApi.supprimerAppel(x.idappel), 'Appel de fonds supprimé.')}><Trash2 size={15} /></button>}
            </div>
          ) },
        ]} lignes={fonds.Appels} />
        {fonds.ListeVersements.length > 0 && (
          <>
            <h3 className="rafas-sous-titre">Versements reçus</h3>
            <Tableau compact colonnes={[
              { cle: 'date_versement', libelle: 'Date', rendu: (v) => dateFr(v.date_versement) }, { cle: 'montant', libelle: 'Montant', nombre: true, rendu: (v) => francs(v.montant) },
              { cle: 'mode', libelle: 'Mode', rendu: (v) => libelleMode(v.mode) }, { cle: 'reference', libelle: 'Référence' }, { cle: 'banque', libelle: 'Banque' },
              { cle: 'numero_appel', libelle: 'Appel', rendu: (v) => v.numero_appel || '-' },
              { cle: 'actions', libelle: '', rendu: (v) => peut && <button type="button" className="rafas-icone-bouton danger" title="Supprimer" onClick={() => supprimer('Supprimer ce versement ?', () => rafasApi.supprimerVersement(v.idversement), 'Versement supprimé.')}><Trash2 size={15} /></button> },
            ]} lignes={fonds.ListeVersements} />
          </>
        )}
      </Carte>

      <div className="cs-deux">
        <Carte titre={`Commission du cabinet, ${tauxFr(ex.taux_commission)}`} sousTitre="Chiffre d'affaires : comptée au tableau de bord de la direction à la date d'émission, perçue à la date de règlement."
          actions={peut && <button type="button" className="btn btn-primary rafas-bouton" onClick={() => setFenetre({ type: 'facture', beneficiaire: 'COURTIER' })}><ReceiptText size={15} /> Facturer</button>}>
          <Tableau vide="Aucune facture de commission sur cet exercice." colonnes={colonnesFactures} lignes={factures('COURTIER')} />
        </Carte>
        <Carte titre={`Honoraires du gestionnaire, ${tauxFr(ex.taux_honoraires)}`} sousTitre={`${conv.gestionnaire} : honoraires de gestion réglés sur le fonds du régime.`}
          actions={peut && <button type="button" className="btn btn-secondary rafas-bouton" onClick={() => setFenetre({ type: 'facture', beneficiaire: 'GESTIONNAIRE' })}><Plus size={15} /> Enregistrer</button>}>
          <Tableau vide="Aucuns honoraires enregistrés sur cet exercice." colonnes={colonnesFactures} lignes={factures('GESTIONNAIRE')} />
        </Carte>
      </div>

      <FormulaireAppel fonds={fonds} ouvert={fenetre?.type === 'appel'} onFermer={() => setFenetre(null)}
        onValider={async (d) => { const r = await action(() => rafasApi.creerAppel(ex.idexercice, d), 'Appel de fonds émis.'); if (r?.Numero) { const appel = r.Appels.find((x) => x.idappel === r.IdAppel); if (appel) imprimerAppel(conv, r, appel); } }} />
      <FormulaireVersement fonds={fonds} appel={fenetre?.appel} ouvert={fenetre?.type === 'versement'} onFermer={() => setFenetre(null)}
        onValider={(d) => action(() => rafasApi.creerVersement(ex.idexercice, d), 'Versement enregistré.')} />
      <FormulaireFacture fonds={fonds} beneficiaire={fenetre?.beneficiaire} ouvert={fenetre?.type === 'facture'} onFermer={() => setFenetre(null)}
        onValider={(d) => action(() => rafasApi.creerHonoraire(ex.idexercice, d), d.beneficiaire === 'COURTIER' ? 'Facture de commission enregistrée.' : 'Honoraires enregistrés.')} />
      <FormulaireMouvement fonds={fonds} nature={fenetre?.nature} ouvert={fenetre?.type === 'mouvement'} onFermer={() => setFenetre(null)}
        onValider={async (d) => {
          const r = await action(() => rafasApi.creerMouvement(ex.idexercice, d), d.nature === 'INCORPORATION' ? 'Familles incorporées.' : 'Familles retirées.');
          const m = r?.Mouvements?.find((x) => x.IdMouvement === r.IdMouvement);
          if (m) imprimerMouvement(conv, r, m);
        }} />
      <FormulaireReglement facture={fenetre?.type === 'reglement' ? fenetre.facture : null} onFermer={() => setFenetre(null)}
        onValider={(d) => action(() => rafasApi.reglerHonoraire(fenetre.facture.idhonoraire, d), 'Règlement enregistré.')} />
      {envoi && <div className="rafas-voile" aria-live="polite"><Loader2 size={22} className="spin" /></div>}
    </div>
  );
};

export default OngletFonds;
