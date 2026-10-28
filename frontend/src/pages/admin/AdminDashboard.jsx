import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Banknote,
  CheckCheck,
  CheckCircle2,
  HandCoins,
  Info,
  Landmark,
  Percent,
  PieChart,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  Wallet,
} from 'lucide-react';

import {
  BoutonVoir, Evolution, francs, Jauge, nombre, pluriel, pourcent, Section, Tuile,
} from '../../components/common/Cockpit';
import { GraphiqueMensuel } from '../../components/common/GraphiqueMensuel';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { cockpitApi } from '../../api/endpoints';
import { useAuth } from '../../context/AuthContext';
import { formatDate, formatDateLisible } from '../../utils/dateUtils';

// Tableau de bord de la direction : chiffres réels d'un exercice (GET /api/tableau-de-bord/), alertes de conformité au jour
const ICONES_ALERTE = {
  reversements_retard: Banknote,
  cheques_echus: Landmark,
  impayes: Wallet,
  reclamations_anciennes: HandCoins,
  derogations: CheckCheck,
  commissions_a_reclamer: HandCoins,
};

export const AdminDashboard = () => {
  const navigate = useNavigate();
  const { peut } = useAuth();
  const [exercice, setExercice] = useState(null);
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState('');

  const charger = useCallback(async (annee) => {
    setChargement(true);
    setErreur('');
    try {
      setDonnees(await cockpitApi.tableauDeBord(annee));
    } catch (err) {
      console.error('Erreur chargement du tableau de bord :', err);
      setErreur(err?.response?.data?.detail || 'Les chiffres du tableau de bord n\'ont pas pu être chargés : le serveur ou la base de données ne répond pas.');
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => { charger(exercice); }, [charger, exercice]);

  const d = donnees;
  const production = d?.Production;
  const encaissements = d?.Encaissements;
  const resultats = d?.Resultats;
  const situation = d?.Situation;
  const n = d?.Exercice;
  const periode = d && (d.EnCours
    ? `du 1er janvier au ${formatDate(d.Au)}, comparé à la même période de ${n - 1}`
    : `exercice ${n} complet, comparé à ${n - 1}`);

  const totalCompagnies = (d?.ParCompagnie || []).reduce((s, c) => s + Math.max(c.PrimeTtc, 0), 0);
  const branches = d?.ParBranche || [];
  const total = (cle) => branches.reduce((s, b) => s + (b[cle] || 0), 0);
  const tauxTotal = (part, base) => (base ? (part * 100) / base : null);

  return (
    <div className="cockpit">
      {/* En-tête : exercice et raccourcis */}
      <div className="glass-panel cockpit-entete">
        <div>
          <h1 className="title-xl">Tableau de bord</h1>
          <p>
            {d
              ? `Production, encaissements et résultats ${periode}. Alertes au ${formatDateLisible(d.Jour, { moisLong: true, jourSemaine: true })}.`
              : 'Production, encaissements, résultats et alertes de conformité du cabinet.'}
          </p>
        </div>
        <div className="cockpit-raccourcis">
          {d && (
            <label className="cockpit-exercice">
              <span>Exercice</span>
              <select
                className="form-control"
                value={n}
                onChange={(e) => setExercice(Number(e.target.value))}
                aria-label="Exercice affiché"
              >
                {d.Exercices.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            </label>
          )}
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/admin/reporting/cima')}>
            <PieChart size={16} /><span>États CIMA</span>
          </button>
          {peut('reversements.view') && (
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/admin/remittances')}>
              <Banknote size={16} /><span>Reversements</span>
            </button>
          )}
          <button type="button" className="btn btn-secondary" onClick={() => charger(exercice)} aria-busy={chargement} title="Recalculer les chiffres">
            <RefreshCw size={16} /><span>Actualiser</span>
          </button>
        </div>
      </div>

      {erreur && (
        <div className="cockpit-erreur" role="alert">
          <AlertTriangle size={18} aria-hidden="true" />
          <span>{erreur}</span>
          <button type="button" className="btn btn-secondary" onClick={() => charger(exercice)}>Réessayer</button>
        </div>
      )}

      {!d && chargement && <LoadingSpinner text="Calcul des chiffres de l'exercice…" />}

      {d && (
        // Changement d'exercice : les chiffres affichés restent en place, atténués, jusqu'aux nouveaux
        <div className={`cockpit${chargement ? ' cockpit-chargement' : ''}`} aria-busy={chargement}>
          <div className="cockpit-tuiles">
            <Tuile
              titre={`Production ${n}`}
              valeur={francs(production.PrimeTtc)}
              icone={TrendingUp}
              couleur="purple"
              vers={peut('contrats.view') ? '/user/contracts' : undefined}
              aide="Primes TTC des actes émis sur la période, contrats annulés exclus"
              lignes={[
                `${pluriel(production.Nombre, 'acte', 'actes')} : ${nombre(production.AffairesNouvelles)} affaires nouvelles, ${nombre(production.Renouvellements)} renouvellements, ${pluriel(production.Avenants, 'autre avenant', 'autres avenants')}`,
                <Evolution actuel={production.PrimeTtc} precedent={production.Precedent.PrimeTtc} au={d.AuPrecedent} />,
              ]}
            />
            <Tuile
              titre={`Encaissé en ${n}`}
              valeur={francs(encaissements.Total)}
              icone={Wallet}
              couleur="emerald"
              vers={peut('encaissements.view') ? '/user/cash/etat' : undefined}
              aide="Encaissements saisis sur la période, pièces annulées exclues, décaissements déduits"
              lignes={[
                `Primes de ${n} : ${francs(encaissements.SurExercice)}`,
                `Primes des exercices antérieurs : ${francs(encaissements.SurAnterieurs)}`,
              ]}
            />
            <Tuile
              titre="Recouvrement des émissions"
              valeur={pourcent(encaissements.TauxRecouvrement)}
              icone={Percent}
              couleur="blue"
              aide={`Part des primes émises en ${n} déjà encaissée à ce jour (quittances des contrats)`}
              lignes={[
                `${francs(encaissements.EncaisseSurEmissions)} encaissés sur ${francs(encaissements.PrimeEmise)} émis`,
                <Jauge taux={encaissements.TauxRecouvrement} libelle="Taux de recouvrement" />,
                `Reste à encaisser : ${francs(encaissements.ResteAEncaisser)}, ${pluriel(encaissements.QuittancesImpayees, 'quittance', 'quittances')}`,
              ]}
            />
            <Tuile
              titre={`Commissions ${n}`}
              valeur={francs(resultats.CommissionsAcquises)}
              icone={HandCoins}
              couleur="amber"
              vers={peut('commissions.view') ? '/admin/commissions' : undefined}
              aide="Commissions du cabinet sur les actes émis de la période (prime hors taxes et accessoires)"
              lignes={[
                `Taux moyen : ${pourcent(resultats.TauxMoyen)} de la prime nette`,
                `Perçues sur la période : ${francs(resultats.CommissionsPercues)}`,
                <Evolution actuel={resultats.CommissionsAcquises} precedent={resultats.CommissionsAcquisesPrecedent} au={d.AuPrecedent} />,
              ]}
            />
          </div>

          <div className="cockpit-colonnes">
            {/* Alertes de conformité : situation au jour, quel que soit l'exercice */}
            <Section
              titre="Alertes de conformité"
              sousTitre={`Situation au ${formatDate(d.Jour)}, d'après la base`}
            >
              {d.Alertes.length === 0 ? (
                <div className="cockpit-rien">
                  <CheckCircle2 size={18} aria-hidden="true" />
                  <span>Aucune alerte : reversements, chèques, primes et commissions à jour.</span>
                </div>
              ) : (
                <ul className="cockpit-a-traiter">
                  {d.Alertes.map((a) => {
                    const Icone = ICONES_ALERTE[a.Code] || (a.Ton === 'critique' ? ShieldAlert : Info);
                    const autorise = peut(a.Droit);
                    return (
                      <li key={a.Code}>
                        <button
                          type="button"
                          className={`ton-${a.Ton}`}
                          disabled={!autorise}
                          onClick={() => navigate(a.Vers)}
                          title={autorise ? undefined : 'Écran réservé à un autre droit'}
                        >
                          <Icone size={16} aria-hidden="true" />
                          <span>
                            {a.Libelle}
                            {a.Nombre !== null && <> : {nombre(a.Nombre)}</>}
                          </span>
                          {a.Montant !== null && <span className="montant-alerte">{francs(a.Montant)}</span>}
                          {autorise && <ArrowRight size={14} aria-hidden="true" className="fleche" />}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
              <p className="cockpit-note">
                Primes à reverser : {francs(situation.Reversements.Montant)}, {pluriel(situation.Reversements.Nombre, 'encaissement', 'encaissements')}
                {situation.Reversements.PlusAncien && <>, le plus ancien du {formatDate(situation.Reversements.PlusAncien)}</>}.
                {' '}Commissions en attente de règlement : {francs(situation.Commissions.AReclamer + situation.Commissions.Reclamees)}.
              </p>
            </Section>

            {/* Production par compagnie : une seule mesure, une seule teinte */}
            <Section titre={`Production ${n} par compagnie`} sousTitre="Primes TTC émises et commissions du cabinet">
              {d.ParCompagnie.length === 0 ? (
                <div className="cockpit-rien"><span>Aucun acte émis sur la période.</span></div>
              ) : (
                <table className="cockpit-branches">
                  <thead>
                    <tr><th>Compagnie</th><th className="nombre">Prime TTC</th><th className="nombre">Commission</th><th>Part</th></tr>
                  </thead>
                  <tbody>
                    {d.ParCompagnie.map((c) => {
                      const part = totalCompagnies ? (Math.max(c.PrimeTtc, 0) * 100) / totalCompagnies : 0;
                      return (
                        <tr key={c.IdCompagnie ?? c.Compagnie} title={`${c.Compagnie} : ${francs(c.PrimeTtc)}, ${pluriel(c.Nombre, 'acte', 'actes')}`}>
                          <td>{c.Compagnie}<span className="secondaire">{pluriel(c.Nombre, 'acte', 'actes')}</span></td>
                          <td className="nombre montant">{francs(c.PrimeTtc)}</td>
                          <td className="nombre montant">{francs(c.Commission)}</td>
                          <td className="part">
                            <div className="cockpit-barre" aria-hidden="true"><span style={{ width: `${part}%` }} /></div>
                            <span>{part.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </Section>
          </div>

          <Section
            titre="Production et encaissements par mois"
            sousTitre={`Primes TTC émises en ${n} et en ${n - 1}, encaissements saisis en ${n}, en francs CFA`}
          >
            <GraphiqueMensuel mois={d.ParMois} exercice={n} />
          </Section>

          <Section
            titre={`Synthèse ${n} par branche`}
            sousTitre="Émissions, encaissements et commissions, avec la catégorie des états réglementaires CIMA"
            action={<BoutonVoir libelle="États CIMA" vers="/admin/reporting/cima" />}
          >
            {branches.length === 0 ? (
              <div className="cockpit-rien"><span>Aucun mouvement sur la période.</span></div>
            ) : (
              <div className="table-wrapper">
                <table className="cockpit-branches">
                  <thead>
                    <tr>
                      <th>Branche</th>
                      <th className="nombre">Actes</th>
                      <th className="nombre">Primes TTC émises</th>
                      <th className="nombre">Commissions</th>
                      <th className="nombre">Encaissé en {n}</th>
                      <th className="nombre">Recouvrement</th>
                      <th className="nombre">Commissions perçues</th>
                    </tr>
                  </thead>
                  <tbody>
                    {branches.map((b) => (
                      <tr key={b.IdProduit ?? b.Branche}>
                        <td>
                          {b.Branche}
                          {b.CategorieCima.toLowerCase() !== b.Branche.toLowerCase() && <span className="secondaire">{b.CategorieCima}</span>}
                        </td>
                        <td className="nombre">{nombre(b.Nombre)}</td>
                        <td className="nombre montant">{francs(b.PrimeTtc)}</td>
                        <td className="nombre montant">
                          {francs(b.Commission)}
                          {b.TauxCommission !== null && <span className="secondaire">{pourcent(b.TauxCommission)} de la prime nette</span>}
                        </td>
                        <td className="nombre montant">
                          {francs(b.EncaisseExercice + b.EncaisseAnterieur)}
                          {b.EncaisseAnterieur > 0 && <span className="secondaire">dont {francs(b.EncaisseAnterieur)} antérieurs</span>}
                        </td>
                        <td className="nombre">
                          {pourcent(b.TauxRecouvrement)}
                          {b.ResteAEncaisser > 0 && <span className="secondaire">reste {francs(b.ResteAEncaisser)}</span>}
                        </td>
                        <td className="nombre montant">{francs(b.CommissionPercue + b.CommissionReprise)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td>Ensemble</td>
                      <td className="nombre">{nombre(total('Nombre'))}</td>
                      <td className="nombre montant">{francs(total('PrimeTtc'))}</td>
                      <td className="nombre montant">{francs(total('Commission'))}</td>
                      <td className="nombre montant">{francs(total('EncaisseExercice') + total('EncaisseAnterieur'))}</td>
                      <td className="nombre">{pourcent(tauxTotal(total('EncaisseSurEmissions'), total('PrimeEmiseQuittancee')))}</td>
                      <td className="nombre montant">{francs(total('CommissionPercue') + total('CommissionReprise'))}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
            <p className="cockpit-note">
              Commissions perçues : règlements des compagnies saisis dans LE PHARE sur la période
              ({francs(resultats.PercuesReglements)}) et affaires antérieures soldées ({francs(resultats.PercuesReprises)}).
              Recouvrement : part des primes émises sur la période déjà encaissée à ce jour.
            </p>
          </Section>

          {!peut('contrats.view') && !peut('encaissements.view') && (
            <div className="cockpit-rien"><ShieldCheck size={18} aria-hidden="true" /><span>Chiffres consolidés : le détail des contrats et de la caisse relève d'autres droits.</span></div>
          )}
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
