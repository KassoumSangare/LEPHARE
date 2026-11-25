import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Banknote,
  CalendarClock,
  CalendarDays,
  CalendarX,
  CheckCircle2,
  ClipboardList,
  Coins,
  CreditCard,
  FilePlus,
  FileText,
  HandCoins,
  History,
  Landmark,
  Layers,
  ListChecks,
  Percent,
  PiggyBank,
  Receipt,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  UserPlus,
  Wallet,
} from 'lucide-react';

import {
  AIDE_CHIFFRE_AFFAIRES, aideResteAPercevoir, Anime, BoutonVoir, cheminDevis, Detail, Evolution, francs, heureMaj, Jauge, lignesResteAPercevoir,
  MiniBarres, nombre, partsChiffreAffaires, pluriel, pourcent, Repartition, Section, Tuile,
} from '../../components/common/Cockpit';
import { DataTable } from '../../components/common/DataTable';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { StatusBadge } from '../../components/common/StatusBadge';
import { cockpitApi } from '../../api/endpoints';
import { useAuth } from '../../context/AuthContext';
import { formatDate, formatDateLisible } from '../../utils/dateUtils';
import { DROIT_TABLEAU } from '../../utils/droits';
import { useActualisationAuto } from '../../utils/useActualisationAuto';

// Cockpit opérationnel : chiffres réels de la base (GET /api/cockpit/). Chaque bloc n'est envoyé par le serveur qu'avec son
// droit (« Bloc … » du groupe Cockpit opérationnel d'Administration > Rôles) : un bloc s'affiche s'il a reçu ses chiffres.
// OREOLE est courtier : son chiffre d'affaires, ce sont ses commissions et accessoires, les primes reviennent aux compagnies.
const SOURCES_PERCU = [
  ['Compagnies', 'Règlements des compagnies'],
  ['FraisCourtiers', 'Honoraires et frais courtiers Oreole Santé'],
  ['Reprises', 'Affaires antérieures'],
  ['Rafas', 'RAFAS'],
];
const MOIS = Array.from({ length: 12 }, (_, i) => new Date(2026, i, 1).toLocaleDateString('fr-FR', { month: 'long' }));

export const UserDashboard = () => {
  const navigate = useNavigate();
  const { peut, isDirectorOrAdmin, user } = useAuth();
  const prenom = String(user?.first_name || user?.name || '').trim().split(/\s+/)[0];
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState('');
  const [majLe, setMajLe] = useState(null);
  const lecture = useRef(0);

  // silencieux : relecture automatique, sans indicateur de chargement ; en échec, les chiffres affichés restent en place
  // (l'heure de mise à jour de l'en-tête ne bouge plus)
  const charger = useCallback(async ({ silencieux = false } = {}) => {
    const numero = ++lecture.current;
    if (!silencieux) {
      setChargement(true);
      setErreur('');
    }
    try {
      const resultat = await cockpitApi.lire();
      if (numero !== lecture.current) return;
      setDonnees(resultat);
      setMajLe(Date.now());
      setErreur('');
    } catch (err) {
      console.error('Erreur chargement du cockpit :', err);
      if (!silencieux && numero === lecture.current) {
        setErreur('Les chiffres du cockpit n\'ont pas pu être chargés : le serveur ou la base de données ne répond pas.');
      }
    } finally {
      if (numero === lecture.current) setChargement(false);
    }
  }, []);

  useEffect(() => { charger(); }, [charger]);
  // Chiffres relus chaque minute tant que l'écran est affiché, et au retour sur l'onglet
  useActualisationAuto(() => charger({ silencieux: true }), majLe);

  const d = donnees || {};
  const exercice = d.Exercice || new Date().getFullYear();
  // Blocs reçus (le serveur n'envoie que ceux que les droits de l'utilisateur accordent)
  const ca = d.ChiffreAffaires;
  const blocCa = ca?.Total !== undefined;
  const blocPercu = Boolean(ca?.Percu);
  const blocReste = Boolean(ca?.EnAttente);
  const { Primes: primes, Polices: polices, Devis: devis, Transformation: transformation, Encaisse: encaisse } = d;
  const { ResteAEncaisser: resteAEncaisser, Reversements: reversements, Commissions: commissions, ATraiter: aTraiterRecu } = d;
  // Colonnes de chiffre d'affaires dans les autres blocs (droit « Chiffre d'affaires dans les autres blocs »)
  const caListes = (d.Blocs || []).includes('commissions_listes');
  const sourcesPercues = blocPercu ? SOURCES_PERCU.filter(([cle]) => ca.Percu[cle]) : [];
  const tuilesCa = blocCa || blocPercu || blocReste;
  // Reste à percevoir : ouvre l'écran des reversements, dont il reprend les étapes, sinon l'état des commissions
  const versReste = !isDirectorOrAdmin ? undefined
    : (peut('reversements.view') && '/admin/remittances') || (peut('commissions.view') && '/admin/commissions') || undefined;
  const tuilesProduction = Boolean(primes || polices || devis || transformation);
  const tuilesCaisse = Boolean(encaisse || resteAEncaisser || reversements || commissions);
  const aucunBloc = donnees && (d.Blocs || []).length === 0;

  const ouvrirDevis = (ligne) => navigate(cheminDevis(ligne.IdProduit, ligne.IdDevis));

  // Bloc « À traiter » : seulement les points qui comptent au moins un élément ; chacun exige le droit de consulter son module
  const t = aTraiterRecu || {};
  const aTraiter = [
    peut('contrats.view') && t.Polices?.Echues > 0 && {
      icone: CalendarX, ton: 'critique', vers: '/user/contracts?statut=echu',
      libelle: `${pluriel(t.Polices.Echues, 'police échue', 'polices échues')} depuis moins de 30 jours, sans renouvellement`,
    },
    peut('contrats.view') && t.Polices?.AEchoir > 0 && {
      icone: CalendarClock, ton: 'attention', vers: '/user/contracts?statut=a_renouveler',
      libelle: `${pluriel(t.Polices.AEchoir, 'police arrive', 'polices arrivent')} à échéance dans les 30 jours`,
    },
    peut('devis.view') && t.Devis?.Expires > 0 && {
      icone: FileText, ton: 'attention', vers: '/user/quotes?onglet=EXPIRED',
      libelle: `${pluriel(t.Devis.Expires, 'devis expiré', 'devis expirés')} depuis le ${formatDate(t.Devis.ExpiresDepuis)} à relancer ou modifier`,
    },
    peut('encaissements.view') && t.Cheques?.ADeposer > 0 && {
      icone: Landmark, ton: t.Cheques.Echus > 0 ? 'critique' : 'attention', vers: '/user/cheques',
      libelle: `${pluriel(t.Cheques.ADeposer, 'chèque', 'chèques')} à déposer d'ici un mois pour ${francs(t.Cheques.Montant)}${t.Cheques.Echus > 0 ? `, dont ${nombre(t.Cheques.Echus)} en retard` : ''}`,
    },
    t.Reversements?.Nombre > 0 && isDirectorOrAdmin && peut('reversements.view') && {
      icone: Banknote, ton: 'info', vers: '/admin/remittances',
      libelle: `${francs(t.Reversements.Montant)} de primes encaissées à reverser à ${pluriel(t.Reversements.Compagnies, 'compagnie', 'compagnies')}`,
    },
    t.CommissionsAReclamer > 0 && isDirectorOrAdmin && peut('commissions.view') && {
      icone: HandCoins, ton: 'info', vers: '/admin/commissions',
      libelle: `${francs(t.CommissionsAReclamer)} de commissions à réclamer aux compagnies`,
    },
    peut('sinistres.view') && t.Sinistres?.Ouverts > 0 && {
      icone: AlertTriangle, ton: 'attention', vers: '/user/claims',
      libelle: `${pluriel(t.Sinistres.Ouverts, 'sinistre en cours', 'sinistres en cours')} de traitement, ${francs(t.Sinistres.MontantReclame)} réclamés`,
    },
    peut('crm.view') && t.Questionnaires > 0 && {
      icone: ClipboardList, ton: 'info', vers: '/user/crm/questionnaires',
      libelle: `${pluriel(t.Questionnaires, 'questionnaire prospect', 'questionnaires prospects')} en attente de devis`,
    },
  ].filter(Boolean);

  // Part de chaque branche : dans le chiffre d'affaires quand ses colonnes sont accordées, sinon dans les primes
  const mesurePart = caListes ? 'ChiffreAffaires' : 'PrimeTtc';
  const totalBranches = (d.ParBranche || []).reduce((s, b) => s + Math.max(b[mesurePart] || 0, 0), 0);
  const colonneCa = (libelle) => (caListes ? [{
    header: libelle, accessor: 'ChiffreAffaires',
    render: (l) => <span style={{ fontFamily: 'var(--font-mono)' }}>{francs(l.ChiffreAffaires)}</span>,
  }] : []);

  const colonnesEcheances = [
    { header: 'N° Police', accessor: 'NumeroPolice', render: (e) => <strong style={{ fontFamily: 'var(--font-mono)' }}>{e.NumeroPolice}</strong> },
    { header: 'Client', accessor: 'Client' },
    { header: 'Branche', accessor: 'Produit' },
    { header: 'Compagnie', accessor: 'Compagnie' },
    {
      header: 'Échéance', accessor: 'DateExpiration',
      render: (e) => (
        <div>
          <div>{formatDate(e.DateExpiration)}</div>
          <StatusBadge
            label={e.Jours < 0 ? `Échue depuis ${pluriel(-e.Jours, 'jour', 'jours')}` : e.Jours === 0 ? 'Échéance aujourd\'hui' : `Dans ${pluriel(e.Jours, 'jour', 'jours')}`}
            color={e.Jours < 0 ? 'red' : 'amber'}
          />
        </div>
      ),
    },
    { header: 'Prime TTC', accessor: 'PrimeTtc', render: (e) => <span style={{ fontFamily: 'var(--font-mono)' }}>{francs(e.PrimeTtc)}</span> },
    ...colonneCa('Commission en jeu'),
    {
      header: 'Action',
      render: (e) => (e.DevisEnCours
        ? peut('devis.view') && <button type="button" className="btn btn-secondary cockpit-bouton-ligne" onClick={() => navigate('/user/quotes')}>Devis préparé</button>
        : peut('contrats.view') && peut('contrats.avenant') && <button type="button" className="btn btn-primary cockpit-bouton-ligne" onClick={() => navigate(`/user/contracts/${e.IdContrat}/renouvellement`)}>Renouveler</button>),
    },
  ];

  const colonnesDevis = [
    { header: 'N° Devis', accessor: 'NumeroDevis', render: (l) => <strong style={{ fontFamily: 'var(--font-mono)' }}>{l.NumeroDevis}</strong> },
    { header: 'Client', accessor: 'Client', render: (l) => l.Client || '-' },
    { header: 'Branche', accessor: 'Produit' },
    { header: 'Valable jusqu\'au', accessor: 'DateExpiration', render: (l) => formatDate(l.DateExpiration) },
    { header: 'Prime TTC', accessor: 'PrimeTtc', render: (l) => <span style={{ fontFamily: 'var(--font-mono)' }}>{francs(l.PrimeTtc)}</span> },
    { header: 'Action', render: (l) => peut(['devis.create', 'devis.update']) && <button type="button" className="btn btn-secondary cockpit-bouton-ligne" onClick={() => ouvrirDevis(l)}>Ouvrir</button> },
  ];

  const colonnesContrats = [
    { header: 'N° Police', accessor: 'NumeroPolice', render: (c) => <strong style={{ fontFamily: 'var(--font-mono)' }}>{c.NumeroPolice}</strong> },
    { header: 'Client', accessor: 'Client' },
    { header: 'Branche', accessor: 'Produit' },
    { header: 'Émis le', accessor: 'DateEmission', render: (c) => formatDate(c.DateEmission) },
    { header: 'Prime TTC', accessor: 'PrimeTtc', render: (c) => <span style={{ fontFamily: 'var(--font-mono)' }}>{francs(c.PrimeTtc)}</span> },
    ...colonneCa('Commission'),
    {
      header: 'Règlement', accessor: 'Reste',
      render: (c) => (c.Reste > 0
        ? <StatusBadge label={`Reste ${francs(c.Reste)}`} color="amber" />
        : <StatusBadge label="Soldé" color="emerald" />),
    },
    { header: 'Action', render: (c) => peut('contrats.view') && <button type="button" className="btn btn-secondary cockpit-bouton-ligne" onClick={() => navigate(`/user/contracts/${c.IdContrat}`)}>Ouvrir</button> },
  ];

  return (
    <div className="cockpit">
      {/* En-tête et raccourcis */}
      <div className="glass-panel cockpit-entete">
        <div>
          <span className="cockpit-surtitre">
            <CalendarDays size={13} aria-hidden="true" />
            {donnees
              ? `${formatDateLisible(d.Jour, { moisLong: true, jourSemaine: true })} · exercice ${exercice}${majLe ? ` · à jour à ${heureMaj(majLe)}` : ''}`
              : 'Exercice en cours'}
          </span>
          <h1 className="title-xl">Cockpit opérationnel</h1>
          <p>{prenom ? `Bonjour ${prenom}.` : 'Bonjour.'}</p>
        </div>
        <div className="cockpit-raccourcis">
          {peut('devis.create') && peut('devis.view') && (
            <button type="button" className="btn btn-primary" onClick={() => navigate('/user/quotes')}>
              <FilePlus size={16} /><span>Nouveau devis</span>
            </button>
          )}
          {peut('clients.create') && peut('clients.view') && (
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/clients')}>
              <UserPlus size={16} /><span>Nouveau client</span>
            </button>
          )}
          {peut('encaissements.create') && peut('encaissements.view') && (
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/cash')}>
              <CreditCard size={16} /><span>Encaisser une prime</span>
            </button>
          )}
          {peut('contrats.reprise') && peut('contrats.view') && (
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/reprises')}>
              <History size={16} /><span>Affaires antérieures</span>
            </button>
          )}
          <button type="button" className="btn btn-secondary" onClick={() => charger()} aria-busy={chargement} title="Recalculer les chiffres">
            <RefreshCw size={16} /><span>Actualiser</span>
          </button>
        </div>
      </div>

      {erreur && (
        <div className="cockpit-erreur" role="alert">
          <AlertTriangle size={18} aria-hidden="true" />
          <span>{erreur}</span>
          <button type="button" className="btn btn-secondary" onClick={() => charger()}>Réessayer</button>
        </div>
      )}

      {!donnees && chargement && <LoadingSpinner text="Calcul des chiffres du cabinet…" />}

      {donnees && (
        <>
          {/* Chiffre d'affaires du cabinet : commissions et accessoires, ce qui fait le revenu du courtier */}
          {tuilesCa && (
            <>
              <p className="cockpit-bande">Chiffre d'affaires du cabinet</p>
              <div className="cockpit-tuiles">
                {blocCa && (
                  <Tuile
                    vedette
                    titre={`Chiffre d'affaires ${exercice}`}
                    valeur={<Anime valeur={ca.Total} format={francs} />}
                    icone={Coins}
                    couleur="emerald"
                    vers={isDirectorOrAdmin && peut(DROIT_TABLEAU) ? '/admin/dashboard' : undefined}
                    aide={`${AIDE_CHIFFRE_AFFAIRES} Depuis le 1er janvier.`}
                    evolution={<Evolution actuel={ca.Total} precedent={ca.Precedent} au={ca.AuPrecedent} />}
                  >
                    <Repartition libelle="Composition du chiffre d'affaires (commissions)" parts={partsChiffreAffaires(ca)} />
                    {ca.Mensuel && (
                      <MiniBarres
                        titre="Chiffre d'affaires"
                        valeurs={ca.Mensuel}
                        libelles={MOIS}
                        actuel={Number(String(d.Jour).slice(5, 7)) - 1}
                      />
                    )}
                    <Detail libelle="Taux moyen sur la prime nette" valeur={pourcent(ca.TauxMoyen)} />
                    {ca.Apporteurs?.Total > 0 && <Detail libelle="Après les apporteurs d'affaires" valeur={francs(ca.Net)} />}
                  </Tuile>
                )}
                {blocPercu && (
                  <Tuile
                    titre={`Perçu en ${exercice}`}
                    valeur={<Anime valeur={ca.Percu.Total} format={francs} />}
                    icone={PiggyBank}
                    couleur="blue"
                    vers={isDirectorOrAdmin && peut('commissions.view') ? '/admin/commissions' : undefined}
                    aide="Sommes reçues par le cabinet depuis le 1er janvier : règlements des compagnies, frais courtiers gardés à l'encaissement, affaires antérieures déjà réglées, RAFAS"
                    lignes={[
                      ...(sourcesPercues.length
                        ? sourcesPercues.map(([cle, libelle]) => <Detail libelle={libelle} valeur={francs(ca.Percu[cle])} />)
                        : ['Aucun règlement de commission saisi cette année']),
                      <Detail libelle="Ce mois-ci" valeur={francs(ca.Mois?.Percu)} />,
                    ]}
                  />
                )}
                {blocReste && (
                  <Tuile
                    titre={`Reste à percevoir ${exercice}`}
                    valeur={<Anime valeur={ca.ResteAPercevoir?.Total ?? ca.EnAttente.Total} format={francs} />}
                    icone={HandCoins}
                    couleur="amber"
                    vers={versReste}
                    aide={aideResteAPercevoir(exercice)}
                    lignes={lignesResteAPercevoir(ca, exercice)}
                  />
                )}
              </div>
            </>
          )}

          {/* Production et devis */}
          {tuilesProduction && tuilesCa && <p className="cockpit-bande">Production et devis</p>}
          {tuilesProduction && (
            <div className="cockpit-tuiles">
              {primes && (
                <Tuile
                  titre={`Primes émises ${exercice}`}
                  valeur={<Anime valeur={primes.Annee.PrimeTtc} format={francs} />}
                  icone={TrendingUp}
                  couleur="purple"
                  vers={peut('contrats.view') ? '/user/contracts' : undefined}
                  aide="Primes TTC des actes émis depuis le 1er janvier, contrats annulés exclus : elles reviennent aux compagnies"
                  evolution={<Evolution actuel={primes.Annee.PrimeTtc} precedent={primes.AnneePrecedente.PrimeTtc} au={primes.AnneePrecedente.Au} />}
                  lignes={[
                    `${pluriel(primes.Annee.Nombre, 'acte', 'actes')} : ${nombre(primes.Annee.AffairesNouvelles)} affaires nouvelles, ${nombre(primes.Annee.Renouvellements)} renouvellements`,
                    <Detail libelle={`Ce mois-ci, ${pluriel(primes.Mois.Nombre, 'acte', 'actes')}`} valeur={francs(primes.Mois.PrimeTtc)} />,
                  ]}
                />
              )}
              {polices && (
                <Tuile
                  titre="Polices en vigueur"
                  valeur={<Anime valeur={polices.EnVigueur} format={nombre} />}
                  icone={ShieldCheck}
                  couleur="emerald"
                  vers={peut('contrats.view') ? '/user/contracts?statut=en_cours' : undefined}
                  aide="Polices dont la période d'affaire nouvelle ou de renouvellement couvre aujourd'hui, résiliations exclues"
                  lignes={[
                    <Detail libelle="Échéances dans les 30 jours" valeur={nombre(polices.AEchoir)} />,
                    <Detail libelle="Échues depuis moins de 30 jours" valeur={nombre(polices.Echues)} />,
                    polices.ChiffreAffaires > 0 && <Detail libelle="Commissions en jeu" valeur={francs(polices.ChiffreAffaires)} />,
                  ]}
                />
              )}
              {devis && (
                <Tuile
                  titre="Devis en cours"
                  valeur={<Anime valeur={devis.EnCours} format={nombre} />}
                  icone={FileText}
                  couleur="blue"
                  vers={peut('devis.view') ? '/user/quotes' : undefined}
                  aide="Devis ni confirmés ni archivés, encore valables"
                  lignes={[
                    <Detail libelle="Primes proposées" valeur={francs(devis.PrimeTtcEnCours)} />,
                    <Detail libelle={`Expirés depuis le ${formatDate(devis.ExpiresDepuis)}`} valeur={nombre(devis.Expires)} />,
                  ]}
                />
              )}
              {transformation && (
                <Tuile
                  titre={`Transformation ${exercice}`}
                  valeur={<Anime valeur={transformation.TauxTransformation} format={pourcent} entier={false} />}
                  icone={Percent}
                  couleur="amber"
                  vers={peut('devis.view') ? '/user/quotes' : undefined}
                  aide="Devis émis depuis le 1er janvier et déjà confirmés en contrat"
                  lignes={[
                    <Jauge taux={transformation.TauxTransformation} libelle="Taux de transformation" />,
                    `${nombre(transformation.ConfirmesAnnee)} devis confirmés sur ${nombre(transformation.EmisAnnee)} émis`,
                  ]}
                />
              )}
            </div>
          )}

          {/* Caisse et flux financiers : primes pour le compte des compagnies */}
          {tuilesCaisse && tuilesCa && <p className="cockpit-bande">Caisse et compagnies</p>}
          {tuilesCaisse && (
            <div className="cockpit-tuiles">
              {encaisse && (
                <Tuile
                  titre={`Encaissé en ${exercice}`}
                  valeur={<Anime valeur={encaisse.Annee.Montant} format={francs} />}
                  icone={Wallet}
                  couleur="emerald"
                  vers={peut('encaissements.view') ? '/user/cash/etat' : undefined}
                  aide="Encaissements saisis depuis le 1er janvier, pièces annulées exclues, décaissements déduits"
                  lignes={[
                    `${pluriel(encaisse.Annee.Pieces, 'pièce de caisse', 'pièces de caisse')}`,
                    <Detail libelle={`Ce mois-ci, ${pluriel(encaisse.Mois.Pieces, 'pièce', 'pièces')}`} valeur={francs(encaisse.Mois.Montant)} />,
                  ]}
                />
              )}
              {resteAEncaisser && (
                <Tuile
                  titre="Reste à encaisser"
                  valeur={<Anime valeur={resteAEncaisser.Montant} format={francs} />}
                  icone={CreditCard}
                  couleur="rose"
                  vers={peut('encaissements.view') ? '/user/cash' : undefined}
                  aide="Quittances non soldées des contrats en vigueur ou échus, émises depuis le 1er janvier"
                  lignes={[
                    `${pluriel(resteAEncaisser.Nombre, 'quittance', 'quittances')} de l'exercice`,
                    resteAEncaisser.NombreAnterieur > 0 && (
                      <Detail
                        libelle={`Années antérieures, ${pluriel(resteAEncaisser.NombreAnterieur, 'quittance', 'quittances')}`}
                        valeur={francs(resteAEncaisser.MontantAnterieur)}
                      />
                    ),
                  ]}
                />
              )}
              {reversements && (
                <Tuile
                  titre="À reverser aux compagnies"
                  valeur={<Anime valeur={reversements.Montant} format={francs} />}
                  icone={Banknote}
                  couleur="blue"
                  vers={isDirectorOrAdmin && peut('reversements.view') ? '/admin/remittances' : undefined}
                  aide="Primes encaissées pas encore reversées, prime entière (Code CIMA)"
                  lignes={[
                    `${pluriel(reversements.Nombre, 'encaissement', 'encaissements')}, ${pluriel(reversements.Compagnies, 'compagnie', 'compagnies')}`,
                    reversements.PlusAncien && `Le plus ancien du ${formatDate(reversements.PlusAncien)}`,
                  ]}
                />
              )}
              {commissions && (
                <Tuile
                  titre="Commissions en attente"
                  valeur={<Anime valeur={commissions.AReclamer + commissions.Reclamees} format={francs} />}
                  icone={HandCoins}
                  couleur="purple"
                  vers={isDirectorOrAdmin && peut('commissions.view') ? '/admin/commissions' : undefined}
                  aide="Commissions des primes reversées pas encore payées par les compagnies"
                  lignes={[
                    <Detail libelle="À réclamer" valeur={francs(commissions.AReclamer)} />,
                    <Detail
                      libelle={`Réclamées non payées${commissions.BordereauxEnAttente ? `, ${pluriel(commissions.BordereauxEnAttente, 'bordereau', 'bordereaux')}` : ''}`}
                      valeur={francs(commissions.Reclamees)}
                    />,
                  ]}
                />
              )}
            </div>
          )}

          {(aTraiterRecu || d.ParBranche) && (
            // Deux colonnes seulement si les deux blocs sont accordés, sinon le bloc prend toute la largeur
            <div className={aTraiterRecu && d.ParBranche ? 'cockpit-colonnes' : 'cockpit'}>
              {/* Points en attente */}
              {aTraiterRecu && (
                <Section icone={ListChecks} titre="À traiter" sousTitre="Ce qui attend une action, d'après la base">
                  {aTraiter.length === 0 ? (
                    <div className="cockpit-rien">
                      <CheckCircle2 size={18} aria-hidden="true" />
                      <span>Rien en attente.</span>
                    </div>
                  ) : (
                    <ul className="cockpit-a-traiter">
                      {aTraiter.map(({ icone: Icone, ton, vers, libelle }) => (
                        <li key={libelle}>
                          <button type="button" className={`ton-${ton}`} onClick={() => navigate(vers)}>
                            <Icone size={16} aria-hidden="true" />
                            <span>{libelle}</span>
                            <ArrowRight size={14} aria-hidden="true" className="fleche" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </Section>
              )}

              {/* Production par branche : une seule mesure pour la part, une seule teinte */}
              {d.ParBranche && (
                <Section
                  icone={Layers}
                  titre={`Production ${exercice} par branche`}
                  sousTitre={caListes
                    ? 'Primes TTC émises et commissions du cabinet (au taux et sur les accessoires) depuis le 1er janvier'
                    : 'Primes TTC émises depuis le 1er janvier'}
                >
                  {d.ParBranche.length === 0 ? (
                    <div className="cockpit-rien"><span>Aucun acte émis cette année.</span></div>
                  ) : (
                    <div className="table-wrapper">
                      <table className="cockpit-branches">
                        <thead>
                          <tr>
                            <th>Branche</th><th>Actes</th>{caListes && <th>Chiffre d'affaires</th>}<th>Prime TTC</th>
                            <th>{caListes ? 'Part du CA' : 'Part'}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {d.ParBranche.map((b, i) => {
                            const part = totalBranches ? (Math.max(b[mesurePart] || 0, 0) * 100) / totalBranches : 0;
                            return (
                              <tr key={b.IdProduit ?? b.Branche} title={`${b.Branche} : ${caListes ? `${francs(b.ChiffreAffaires)} de chiffre d'affaires, ` : ''}${francs(b.PrimeTtc)} de primes, ${pluriel(b.Nombre, 'acte', 'actes')}`}>
                                <td><div className="avec-rang"><span className="cockpit-rang" aria-hidden="true">{i + 1}</span><div>{b.Branche}</div></div></td>
                                <td>{nombre(b.Nombre)}</td>
                                {caListes && <td className="montant">{francs(b.ChiffreAffaires)}</td>}
                                <td className="montant">{francs(b.PrimeTtc)}</td>
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

          {d.Echeances && (
            <Section
              icone={CalendarClock}
              titre="Échéances à suivre"
              sousTitre="Polices échues depuis moins de 30 jours ou à échoir dans les 30 jours, sans renouvellement enregistré"
              action={peut('contrats.view') && <BoutonVoir libelle="Toutes les échéances" vers="/user/contracts?statut=a_renouveler" />}
            >
              {d.Echeances.Lignes.length === 0
                ? <div className="cockpit-rien"><CheckCircle2 size={18} aria-hidden="true" /><span>Aucune échéance à suivre.</span></div>
                : <DataTable columns={colonnesEcheances} data={d.Echeances.Lignes} searchable={false} itemsPerPage={8} />}
            </Section>
          )}

          {d.DerniersDevis && (
            <Section
              icone={FileText}
              titre="Derniers devis en cours"
              sousTitre="Devis encore valables, à confirmer en contrat"
              action={peut('devis.view') && <BoutonVoir libelle="Tous les devis" vers="/user/quotes" />}
            >
              {d.DerniersDevis.length === 0
                ? <div className="cockpit-rien"><span>Aucun devis en cours.</span></div>
                : <DataTable columns={colonnesDevis} data={d.DerniersDevis} searchable={false} itemsPerPage={8} />}
            </Section>
          )}

          {d.DerniersContrats && (
            <Section
              icone={Receipt}
              titre="Derniers contrats émis"
              sousTitre="Polices et avenants les plus récents, avec leur règlement"
              action={peut('contrats.view') && <BoutonVoir libelle="Tous les contrats" vers="/user/contracts" />}
            >
              <DataTable columns={colonnesContrats} data={d.DerniersContrats} searchable={false} itemsPerPage={8} />
            </Section>
          )}

          {aucunBloc && (
            <div className="cockpit-rien"><ShieldCheck size={18} aria-hidden="true" /><span>Aucun bloc du cockpit n'est accordé à votre profil.</span></div>
          )}
        </>
      )}
    </div>
  );
};

export default UserDashboard;
