import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Banknote,
  BarChart3,
  Building2,
  CalendarDays,
  CheckCheck,
  CheckCircle2,
  Coins,
  HandCoins,
  Info,
  Landmark,
  Layers,
  Percent,
  PiggyBank,
  PieChart,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  Wallet,
} from 'lucide-react';

import {
  AIDE_CHIFFRE_AFFAIRES, aideResteAPercevoir, Anime, BoutonVoir, Detail, Evolution, francs, heureMaj, Jauge, lignesResteAPercevoir, nombre,
  partsChiffreAffaires, pluriel, pourcent, Repartition, Section, Segments, SYNONYMES_CHIFFRE_AFFAIRES, Tuile,
} from '../../components/common/Cockpit';
import { GraphiqueMensuel } from '../../components/common/GraphiqueMensuel';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { cockpitApi } from '../../api/endpoints';
import { useAuth } from '../../context/AuthContext';
import { formatDate, formatDateLisible } from '../../utils/dateUtils';
import { useActualisationAuto } from '../../utils/useActualisationAuto';

// Tableau de bord de la direction : chiffres réels d'un exercice (GET /api/tableau-de-bord/), alertes de conformité au jour.
// Chaque bloc n'est envoyé par le serveur qu'avec son droit (« Bloc … » du groupe Tableau de bord d'Administration > Rôles) :
// « Blocs » de la réponse. OREOLE est courtier : son chiffre d'affaires, ce sont ses commissions et accessoires, pas les primes,
// qui reviennent aux compagnies (production/chiffre_affaires.py).
const ICONES_ALERTE = {
  reversements_retard: Banknote,
  cheques_echus: Landmark,
  impayes: Wallet,
  reclamations_anciennes: HandCoins,
  derogations: CheckCheck,
  commissions_a_reclamer: HandCoins,
};

// Sommes perçues par le cabinet, dans l'ordre de la réponse du serveur
const SOURCES_PERCU = [
  ['Compagnies', 'Règlements des compagnies'],
  ['FraisCourtiers', 'Honoraires et frais courtiers Oreole Santé'],
  ['Reprises', 'Affaires antérieures'],
  ['Rafas', 'Commission RAFAS'],
];

const majuscule = (texte) => texte.replace(/^./, (c) => c.toUpperCase());
const enumeration = (parties) => parties.filter(Boolean).join(', ').replace(/, ([^,]*)$/, ' et $1');

export const AdminDashboard = () => {
  const navigate = useNavigate();
  const { peut } = useAuth();
  const [exercice, setExercice] = useState(null);
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState('');
  const [majLe, setMajLe] = useState(null);
  const lecture = useRef(0);

  // silencieux : relecture automatique, sans atténuer les chiffres ; en échec, ils restent en place. Une réponse arrivée
  // après un changement d'exercice est écartée.
  const charger = useCallback(async (annee, { silencieux = false } = {}) => {
    const numero = ++lecture.current;
    if (!silencieux) {
      setChargement(true);
      setErreur('');
    }
    try {
      const resultat = await cockpitApi.tableauDeBord(annee);
      if (numero !== lecture.current) return;
      setDonnees(resultat);
      setMajLe(Date.now());
      setErreur('');
    } catch (err) {
      console.error('Erreur chargement du tableau de bord :', err);
      if (!silencieux && numero === lecture.current) {
        setErreur(err?.response?.data?.detail || 'Les chiffres du tableau de bord n\'ont pas pu être chargés : le serveur ou la base de données ne répond pas.');
      }
    } finally {
      if (numero === lecture.current) setChargement(false);
    }
  }, []);

  useEffect(() => { charger(exercice); }, [charger, exercice]);
  // Chiffres relus chaque minute tant que l'écran est affiché, et au retour sur l'onglet
  useActualisationAuto(() => charger(exercice, { silencieux: true }), majLe);

  const d = donnees;
  const n = d?.Exercice;
  const blocs = new Set(d?.Blocs || []);
  const voit = (bloc) => blocs.has(bloc);
  const production = d?.Production;
  const encaissements = d?.Encaissements;
  const ca = d?.ChiffreAffaires;
  const situation = d?.Situation;
  const periode = d && (d.EnCours
    ? `du 1er janvier au ${formatDate(d.Au)}, comparés à la même période de ${n - 1}`
    : `de l'exercice ${n} complet, comparés à ${n - 1}`);

  // Blocs reçus (le serveur n'envoie que ceux que les droits de l'utilisateur accordent)
  const blocCa = voit('chiffre_affaires') && ca?.Total !== undefined;
  const blocPercu = voit('percu') && Boolean(ca?.Percu);
  const blocReste = voit('reste_a_percevoir') && Boolean(ca?.EnAttente);
  const blocPrimes = voit('primes') && Boolean(production);
  const blocEncaisse = voit('encaisse') && encaissements?.Total !== undefined;
  const blocRecouvrement = voit('recouvrement') && encaissements?.TauxRecouvrement !== undefined;
  const alertes = voit('alertes') ? d?.Alertes : undefined;
  // Colonnes de chiffre d'affaires dans la synthèse par branche et le tableau par compagnie
  const caListes = voit('ca_listes');

  // Part de chaque compagnie : dans le chiffre d'affaires quand il est accordé, sinon dans les primes
  const mesureCompagnie = caListes ? 'ChiffreAffaires' : 'PrimeTtc';
  const totalCompagnies = (d?.ParCompagnie || []).reduce((s, c) => s + Math.max(c[mesureCompagnie] || 0, 0), 0);
  const branches = d?.ParBranche || [];
  const alertesVisibles = (alertes || []).filter((alerte) => peut(alerte.Droit));
  const total = (cle) => branches.reduce((s, b) => s + (b[cle] || 0), 0);
  const tauxTotal = (part, base) => (base ? (part * 100) / base : null);
  const sourcesPercues = blocPercu ? SOURCES_PERCU.filter(([cle]) => ca.Percu[cle]) : [];
  const rienAVoir = d && blocs.size === 0;
  // Introduction de l'en-tête : seulement ce que les blocs accordés montrent
  const contenuVisible = majuscule(enumeration([
    (blocCa || blocPercu || blocReste || voit('ca_par_mois')) && 'chiffre d\'affaires du cabinet',
    (blocPrimes || voit('primes_par_mois') || voit('compagnies') || voit('branches')) && 'primes',
    (blocEncaisse || blocRecouvrement || voit('primes_par_mois') || voit('branches')) && 'encaissements',
  ]));

  return (
    <div className="cockpit">
      {/* En-tête : exercice et raccourcis */}
      <div className="glass-panel cockpit-entete">
        <div>
          <span className="cockpit-surtitre">
            <CalendarDays size={13} aria-hidden="true" />
            {d
              ? `Direction · alertes au ${formatDateLisible(d.Jour, { moisLong: true, jourSemaine: true })}${majLe ? ` · à jour à ${heureMaj(majLe)}` : ''}`
              : 'Direction'}
          </span>
          <h1 className="title-xl">Tableau de bord</h1>
          <p>
            {!d && 'Chiffre d\'affaires du cabinet, primes, encaissements et alertes de conformité.'}
            {d && contenuVisible && `${contenuVisible} ${periode}.`}
            {d && !contenuVisible && alertes && `Alertes de conformité au ${formatDate(d.Jour)}.`}
          </p>
        </div>
        <div className="cockpit-raccourcis">
          {d && <Segments options={d.Exercices} valeur={n} onChange={setExercice} libelle="Exercice affiché" />}
          {peut('commissions.view') && (
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/admin/commissions')}>
              <HandCoins size={16} /><span>Commissions</span>
            </button>
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
          {rienAVoir && (
            <div className="cockpit-rien"><ShieldCheck size={18} aria-hidden="true" /><span>Aucun bloc du tableau de bord n'est accordé à votre profil.</span></div>
          )}

          {/* Revenu du cabinet : ce qui fait son chiffre d'affaires */}
          {(blocCa || blocPercu || blocReste) && (
            <>
              <p className="cockpit-bande">Chiffre d'affaires du cabinet</p>
              <div className="cockpit-tuiles">
                {blocCa && (
                  <Tuile
                    vedette
                    titre={`Chiffre d'affaires ${n}`}
                    valeur={<Anime valeur={ca.Total} format={francs} />}
                    icone={Coins}
                    couleur="emerald"
                    vers={peut('commissions.view') ? '/admin/commissions' : undefined}
                    aide={AIDE_CHIFFRE_AFFAIRES}
                    evolution={<Evolution actuel={ca.Total} precedent={ca.Precedent} au={d.AuPrecedent} />}
                  >
                    <Repartition libelle="Composition du chiffre d'affaires (commissions)" parts={partsChiffreAffaires(ca)} />
                    <dl className="cockpit-chiffres-cles">
                      <div><dt>Taux moyen</dt><dd>{pourcent(ca.TauxMoyen)}</dd><dd className="aide">de la prime nette</dd></div>
                      <div><dt>Part des primes</dt><dd>{pourcent(ca.PartDesPrimes)}</dd><dd className="aide">des primes TTC émises</dd></div>
                      {ca.Apporteurs?.Total > 0 ? (
                        <div><dt>Après les apporteurs</dt><dd>{francs(ca.Net)}</dd><dd className="aide">{francs(ca.Apporteurs.Total)} leur reviennent</dd></div>
                      ) : (
                        <div><dt>Actes</dt><dd>{nombre(ca.Nombre)}</dd><dd className="aide">émis sur la période</dd></div>
                      )}
                    </dl>
                  </Tuile>
                )}
                {blocPercu && (
                  <Tuile
                    titre={`Perçu en ${n}`}
                    valeur={<Anime valeur={ca.Percu.Total} format={francs} />}
                    icone={PiggyBank}
                    couleur="blue"
                    vers={peut('commissions.view') ? '/admin/commissions' : undefined}
                    aide="Sommes reçues par le cabinet sur la période : règlements des compagnies, frais courtiers gardés à l'encaissement, affaires antérieures déjà réglées, RAFAS"
                    evolution={<Evolution actuel={ca.Percu.Total} precedent={ca.PercuPrecedent} au={d.AuPrecedent} />}
                    lignes={sourcesPercues.length
                      ? sourcesPercues.map(([cle, libelle]) => <Detail libelle={libelle} valeur={francs(ca.Percu[cle])} />)
                      : ['Aucun règlement de commission saisi sur la période']}
                  />
                )}
                {blocReste && (
                  <Tuile
                    titre={`Reste à percevoir ${n}`}
                    valeur={<Anime valeur={ca.ResteAPercevoir?.Total ?? ca.EnAttente.Total} format={francs} />}
                    icone={HandCoins}
                    couleur="amber"
                    vers={(peut('reversements.view') && '/admin/remittances') || (peut('commissions.view') && '/admin/commissions') || undefined}
                    aide={aideResteAPercevoir(n)}
                    lignes={lignesResteAPercevoir(ca, n)}
                  />
                )}
              </div>
            </>
          )}

          {/* Primes placées pour le compte des compagnies */}
          {(blocPrimes || blocEncaisse || blocRecouvrement) && (
            <>
              <p className="cockpit-bande">Primes pour le compte des compagnies</p>
              <div className="cockpit-tuiles">
                {blocPrimes && (
                  <Tuile
                    titre={`Primes émises ${n}`}
                    valeur={<Anime valeur={production.PrimeTtc} format={francs} />}
                    icone={TrendingUp}
                    couleur="purple"
                    vers={peut('contrats.view') ? '/user/contracts' : undefined}
                    aide="Primes TTC des actes émis sur la période, contrats annulés exclus : elles reviennent aux compagnies"
                    evolution={<Evolution actuel={production.PrimeTtc} precedent={production.Precedent.PrimeTtc} au={d.AuPrecedent} />}
                    lignes={[
                      `${pluriel(production.Nombre, 'acte', 'actes')} : ${nombre(production.AffairesNouvelles)} affaires nouvelles, ${nombre(production.Renouvellements)} renouvellements, ${pluriel(production.Avenants, 'autre avenant', 'autres avenants')}`,
                    ]}
                  />
                )}
                {blocEncaisse && (
                  <Tuile
                    titre={`Encaissé en ${n}`}
                    valeur={<Anime valeur={encaissements.Total} format={francs} />}
                    icone={Wallet}
                    couleur="emerald"
                    vers={peut('encaissements.view') ? '/user/cash/etat' : undefined}
                    aide="Encaissements saisis sur la période, pièces annulées exclues, décaissements déduits"
                    lignes={[
                      <Detail libelle={`Primes de ${n}`} valeur={francs(encaissements.SurExercice)} />,
                      <Detail libelle="Exercices antérieurs" valeur={francs(encaissements.SurAnterieurs)} />,
                    ]}
                  />
                )}
                {blocRecouvrement && (
                  <Tuile
                    titre="Recouvrement des émissions"
                    valeur={<Anime valeur={encaissements.TauxRecouvrement} format={pourcent} entier={false} />}
                    icone={Percent}
                    couleur="blue"
                    aide={`Part des primes émises en ${n} déjà encaissée à ce jour : la commission ne se perçoit qu'après l'encaissement et le reversement de la prime`}
                    lignes={[
                      <Jauge taux={encaissements.TauxRecouvrement} libelle="Taux de recouvrement" />,
                      <Detail libelle="Encaissé sur les émissions" valeur={francs(encaissements.EncaisseSurEmissions)} />,
                      <Detail libelle={`Reste à encaisser, ${pluriel(encaissements.QuittancesImpayees, 'quittance', 'quittances')}`} valeur={francs(encaissements.ResteAEncaisser)} />,
                    ]}
                  />
                )}
              </div>
            </>
          )}

          {voit('ca_par_mois') && (
            <Section
              icone={BarChart3}
              titre="Chiffre d'affaires par mois"
              sousTitre={`Commissions du cabinet (au taux et sur les accessoires) des actes émis en ${n} et en ${n - 1}, sommes perçues en ${n}, en francs CFA`}
            >
              <GraphiqueMensuel
                mois={d.ParMois}
                exercice={n}
                titre="Chiffre d'affaires par mois"
                series={[
                  { cle: 'ChiffreAffaires', libelle: `Chiffre d'affaires ${n}`, classe: 'n', forme: 'barre' },
                  { cle: 'ChiffreAffairesPrecedent', libelle: `Chiffre d'affaires ${n - 1}`, classe: 'n1', forme: 'barre' },
                  { cle: 'Percu', libelle: `Perçu en ${n}`, classe: 'enc', forme: 'ligne' },
                ]}
              />
            </Section>
          )}

          {(alertes || voit('compagnies')) && (
            // Deux colonnes seulement si les deux blocs sont accordés, sinon le bloc prend toute la largeur
            <div className={alertes && voit('compagnies') ? 'cockpit-colonnes' : 'cockpit'}>
              {/* Alertes de conformité : situation au jour, quel que soit l'exercice ; chacune selon le droit de son module */}
              {alertes && (
                <Section
                  icone={ShieldAlert}
                  titre="Alertes de conformité"
                  sousTitre={`Situation au ${formatDate(d.Jour)}, d'après la base`}
                >
                  {alertesVisibles.length === 0 ? (
                    <div className="cockpit-rien">
                      <CheckCircle2 size={18} aria-hidden="true" />
                      <span>Aucune alerte : reversements, chèques, primes et commissions à jour.</span>
                    </div>
                  ) : (
                    <ul className="cockpit-a-traiter">
                      {alertesVisibles.map((a) => {
                        const Icone = ICONES_ALERTE[a.Code] || (a.Ton === 'critique' ? ShieldAlert : Info);
                        return (
                          <li key={a.Code}>
                            <button
                              type="button"
                              className={`ton-${a.Ton}`}
                              onClick={() => navigate(a.Vers)}
                            >
                              <Icone size={16} aria-hidden="true" />
                              <span>
                                {a.Libelle}
                                {a.Nombre !== null && <> : {nombre(a.Nombre)}</>}
                              </span>
                              {a.Montant !== null && <span className="montant-alerte">{francs(a.Montant)}</span>}
                              <ArrowRight size={14} aria-hidden="true" className="fleche" />
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                  {(situation?.Reversements || situation?.Commissions) && (
                    <p className="cockpit-note">
                      {situation.Reversements && (
                        <>
                          Primes à reverser : {francs(situation.Reversements.Montant)}, {pluriel(situation.Reversements.Nombre, 'encaissement', 'encaissements')}
                          {situation.Reversements.PlusAncien && <>, le plus ancien du {formatDate(situation.Reversements.PlusAncien)}</>}.
                          {' '}
                        </>
                      )}
                      {situation.Commissions && (
                        <>Commissions en attente de règlement : {francs(situation.Commissions.AReclamer + situation.Commissions.Reclamees)}.</>
                      )}
                    </p>
                  )}
                </Section>
              )}

              {/* Par compagnie : une seule mesure pour la part (chiffre d'affaires s'il est accordé, sinon primes), une seule teinte */}
              {voit('compagnies') && (
                <Section
                  icone={Building2}
                  titre={caListes ? `Chiffre d'affaires ${n} par compagnie` : `Primes ${n} par compagnie`}
                  sousTitre={caListes
                    ? 'Commissions du cabinet (au taux et sur les accessoires), avec les primes TTC placées'
                    : 'Primes TTC placées pour le compte des compagnies'}
                >
                  {d.ParCompagnie.length === 0 ? (
                    <div className="cockpit-rien"><span>Aucun acte émis sur la période.</span></div>
                  ) : (
                    <div className="table-wrapper">
                      <table className="cockpit-branches">
                        <thead>
                          <tr>
                            <th>Compagnie</th>
                            {caListes && <th className="nombre">Chiffre d'affaires</th>}
                            <th className="nombre">Primes TTC</th>
                            <th>{caListes ? 'Part du CA' : 'Part des primes'}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {d.ParCompagnie.map((c, i) => {
                            const part = totalCompagnies ? (Math.max(c[mesureCompagnie] || 0, 0) * 100) / totalCompagnies : 0;
                            return (
                              <tr key={c.IdCompagnie ?? c.Compagnie} title={`${c.Compagnie} : ${caListes ? `${francs(c.ChiffreAffaires)} de chiffre d'affaires, ` : ''}${francs(c.PrimeTtc)} de primes, ${pluriel(c.Nombre, 'acte', 'actes')}`}>
                                <td>
                                  <div className="avec-rang">
                                    <span className="cockpit-rang" aria-hidden="true">{i + 1}</span>
                                    <div>{c.Compagnie}<span className="secondaire">{pluriel(c.Nombre, 'acte', 'actes')}</span></div>
                                  </div>
                                </td>
                                {caListes && (
                                  <td className="nombre montant">
                                    {francs(c.ChiffreAffaires)}
                                    {c.ChiffreAffairesPercu > 0 && <span className="secondaire">perçu {francs(c.ChiffreAffairesPercu)}</span>}
                                  </td>
                                )}
                                <td className="nombre montant">{francs(c.PrimeTtc)}</td>
                                <td className="part">
                                  <div className="cockpit-barre" aria-hidden="true"><span style={{ width: `${part}%` }} /></div>
                                  <span>{part.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %</span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Section>
              )}
            </div>
          )}

          {voit('primes_par_mois') && (
            <Section
              icone={TrendingUp}
              titre="Primes et encaissements par mois"
              sousTitre={`Primes TTC émises pour les compagnies en ${n} et en ${n - 1}, encaissements saisis en ${n}, en francs CFA`}
            >
              <GraphiqueMensuel mois={d.ParMois} exercice={n} />
            </Section>
          )}

          {voit('branches') && (
            <Section
              icone={Layers}
              titre={`Synthèse ${n} par branche`}
              sousTitre={`${caListes ? 'Chiffre d\'affaires du cabinet, primes' : 'Primes'} émises et encaissements, avec la catégorie des états réglementaires CIMA`}
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
                        {caListes && <th className="nombre">Chiffre d'affaires</th>}
                        {caListes && <th className="nombre">Perçu</th>}
                        <th className="nombre">Primes TTC émises</th>
                        <th className="nombre">Encaissé en {n}</th>
                        <th className="nombre">Recouvrement</th>
                      </tr>
                    </thead>
                    <tbody>
                      {branches.map((b, i) => (
                        <tr key={b.IdProduit ?? b.Branche}>
                          <td>
                            <div className="avec-rang">
                              <span className="cockpit-rang" aria-hidden="true">{i + 1}</span>
                              <div>
                                {b.Branche}
                                {b.CategorieCima.toLowerCase() !== b.Branche.toLowerCase() && <span className="secondaire">{b.CategorieCima}</span>}
                              </div>
                            </div>
                          </td>
                          <td className="nombre">{nombre(b.Nombre)}</td>
                          {caListes && (
                            <td className="nombre montant">
                              {francs(b.ChiffreAffaires)}
                              {b.TauxCommission !== null && b.TauxCommission !== undefined && <span className="secondaire">{pourcent(b.TauxCommission)} {b.LibelleBase || 'de la prime nette'}</span>}
                              {b.Accessoires > 0 && <span className="secondaire">dont commission sur accessoires {francs(b.Accessoires)}</span>}
                            </td>
                          )}
                          {caListes && <td className="nombre montant">{francs(b.ChiffreAffairesPercu)}</td>}
                          <td className="nombre montant">{francs(b.PrimeTtc)}</td>
                          <td className="nombre montant">
                            {francs(b.EncaisseExercice + b.EncaisseAnterieur)}
                            {b.EncaisseAnterieur > 0 && <span className="secondaire">dont {francs(b.EncaisseAnterieur)} antérieurs</span>}
                          </td>
                          <td className="nombre">
                            {pourcent(b.TauxRecouvrement)}
                            {b.ResteAEncaisser > 0 && <span className="secondaire">reste {francs(b.ResteAEncaisser)}</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td>Ensemble</td>
                        <td className="nombre">{nombre(total('Nombre'))}</td>
                        {caListes && <td className="nombre montant">{francs(total('ChiffreAffaires'))}</td>}
                        {caListes && <td className="nombre montant">{francs(total('ChiffreAffairesPercu'))}</td>}
                        <td className="nombre montant">{francs(total('PrimeTtc'))}</td>
                        <td className="nombre montant">{francs(total('EncaisseExercice') + total('EncaisseAnterieur'))}</td>
                        <td className="nombre">{pourcent(tauxTotal(total('EncaisseSurEmissions'), total('PrimeEmiseQuittancee')))}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}
              <p className="cockpit-note">
                {caListes && (
                  <>
                    Chiffre d'affaires : commission du cabinet sur chaque acte émis sur la période, au taux de la compagnie et sur les
                    accessoires (accessoire courtier ; en Oreole Santé, frais courtiers et honoraires OREOLE). Les termes {SYNONYMES_CHIFFRE_AFFAIRES} désignent
                    tous ce chiffre d'affaires. Perçu : règlements des compagnies saisis dans LE PHARE, frais courtiers gardés à
                    l'encaissement des cotisations, affaires antérieures déjà réglées et commission RAFAS réglée.
                    {' '}
                  </>
                )}
                Recouvrement : part des primes émises sur la période déjà encaissée à ce jour.
              </p>
            </Section>
          )}
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
