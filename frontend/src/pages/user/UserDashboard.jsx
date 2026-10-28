import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Banknote,
  CalendarClock,
  CalendarX,
  CheckCircle2,
  ClipboardList,
  CreditCard,
  FilePlus,
  FileText,
  HandCoins,
  History,
  Landmark,
  Percent,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  UserPlus,
  Wallet,
} from 'lucide-react';

import { DataTable } from '../../components/common/DataTable';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { StatusBadge } from '../../components/common/StatusBadge';
import { cockpitApi } from '../../api/endpoints';
import { useAuth } from '../../context/AuthContext';
import { formatDate, formatDateLisible } from '../../utils/dateUtils';
import { moduleDuProduit, moduleOuvert } from '../../utils/parametrage';
import { MODULES_EDITION_COMPLETE } from '../../utils/quoteRegistry';

// Cockpit opérationnel : chiffres réels de la base (GET /api/cockpit/), chaque bloc selon les droits de l'utilisateur
const francs = (n) => `${Math.round(Number(n) || 0).toLocaleString('fr-FR')} F`;
const nombre = (n) => Number(n || 0).toLocaleString('fr-FR');
const pluriel = (n, un, plusieurs) => `${nombre(n)} ${Number(n) > 1 ? plusieurs : un}`;

const COULEURS_ICONE = {
  blue: { fond: 'rgba(59, 130, 246, 0.15)', texte: '#60a5fa', bord: 'rgba(59, 130, 246, 0.25)' },
  emerald: { fond: 'rgba(16, 185, 129, 0.15)', texte: '#34d399', bord: 'rgba(16, 185, 129, 0.25)' },
  amber: { fond: 'rgba(245, 158, 11, 0.15)', texte: '#fbbf24', bord: 'rgba(245, 158, 11, 0.25)' },
  purple: { fond: 'rgba(139, 92, 246, 0.15)', texte: '#c084fc', bord: 'rgba(139, 92, 246, 0.25)' },
  rose: { fond: 'rgba(244, 63, 94, 0.15)', texte: '#fb7185', bord: 'rgba(244, 63, 94, 0.25)' },
};

// Tuile d'indicateur : ouvre l'écran détaillé quand une destination est donnée
const Tuile = ({ titre, valeur, icone: Icone, couleur = 'blue', lignes = [], vers, aide }) => {
  const navigate = useNavigate();
  const c = COULEURS_ICONE[couleur] || COULEURS_ICONE.blue;
  const ouvrir = vers ? () => navigate(vers) : undefined;
  return (
    <div
      className={`metric-card cockpit-tuile${vers ? ' cliquable' : ''}`}
      role={vers ? 'link' : undefined}
      tabIndex={vers ? 0 : undefined}
      onClick={ouvrir}
      onKeyDown={vers ? (e) => { if (e.key === 'Enter') ouvrir(); } : undefined}
      title={aide}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
        <span style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)' }}>{titre}</span>
        <div className="metric-card-icon" style={{ background: c.fond, color: c.texte, border: `1px solid ${c.bord}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icone size={20} />
        </div>
      </div>
      <div className="metric-value">{valeur}</div>
      {lignes.filter(Boolean).map((ligne, i) => (
        <div key={i} className="cockpit-tuile-ligne">{ligne}</div>
      ))}
    </div>
  );
};

// Évolution par rapport à la même date de l'an dernier : flèche + libellé, jamais la couleur seule
const Evolution = ({ actuel, precedent, au }) => {
  if (!precedent) return null;
  const taux = ((actuel - precedent) * 100) / precedent;
  const hausse = taux >= 0;
  const Fleche = hausse ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={`cockpit-evolution ${hausse ? 'hausse' : 'baisse'}`}>
      <Fleche size={13} aria-hidden="true" />
      <strong>{hausse ? '+' : '−'}{Math.abs(taux).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %</strong>
      <span>{hausse ? 'en hausse' : 'en baisse'} par rapport au {formatDate(au)} ({francs(precedent)})</span>
    </span>
  );
};

const Section = ({ titre, sousTitre, action, children }) => (
  <section className="glass-panel cockpit-section">
    <div className="cockpit-section-entete">
      <div>
        <h2 className="title-md">{titre}</h2>
        {sousTitre && <p>{sousTitre}</p>}
      </div>
      {action}
    </div>
    {children}
  </section>
);

const BoutonVoir = ({ libelle, vers }) => {
  const navigate = useNavigate();
  return (
    <button type="button" className="btn btn-secondary cockpit-voir" onClick={() => navigate(vers)}>
      {libelle}
      <ArrowRight size={14} />
    </button>
  );
};

export const UserDashboard = () => {
  const navigate = useNavigate();
  const { peut, isDirectorOrAdmin } = useAuth();
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState('');

  const charger = useCallback(async () => {
    setChargement(true);
    setErreur('');
    try {
      setDonnees(await cockpitApi.lire());
    } catch (err) {
      console.error('Erreur chargement du cockpit :', err);
      setErreur('Les chiffres du cockpit n\'ont pas pu être chargés : le serveur ou la base de données ne répond pas.');
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => { charger(); }, [charger]);

  const production = donnees?.Production;
  const devis = donnees?.Devis;
  const caisse = donnees?.Caisse;
  const reversements = donnees?.Reversements;
  const commissions = donnees?.Commissions;
  const exercice = donnees?.Exercice || new Date().getFullYear();

  // Devis : formulaire du produit rouvert s'il sait le faire, sinon registre des devis
  const ouvrirDevis = (d) => {
    const module = moduleDuProduit(Number(d.IdProduit));
    if (MODULES_EDITION_COMPLETE.includes(module) && moduleOuvert(module)) navigate(`/user/quotes/${module}?edit=${d.IdDevis}`);
    else navigate('/user/quotes');
  };

  // Points en attente : seulement ceux qui comptent au moins un élément
  const aTraiter = [
    production?.Echeances?.Echues > 0 && {
      icone: CalendarX, ton: 'critique', vers: '/user/contracts?statut=echu',
      libelle: `${pluriel(production.Echeances.Echues, 'police échue', 'polices échues')} depuis moins de 30 jours, sans renouvellement`,
    },
    production?.Echeances?.AEchoir > 0 && {
      icone: CalendarClock, ton: 'attention', vers: '/user/contracts?statut=a_renouveler',
      libelle: `${pluriel(production.Echeances.AEchoir, 'police arrive', 'polices arrivent')} à échéance dans les 30 jours`,
    },
    devis?.Expires > 0 && {
      icone: FileText, ton: 'attention', vers: '/user/quotes?onglet=EXPIRED',
      libelle: `${pluriel(devis.Expires, 'devis expiré', 'devis expirés')} depuis le ${formatDate(devis.ExpiresDepuis)} à relancer ou modifier`,
    },
    caisse?.Cheques?.ADeposer > 0 && {
      icone: Landmark, ton: caisse.Cheques.Echus > 0 ? 'critique' : 'attention', vers: '/user/cheques',
      libelle: `${pluriel(caisse.Cheques.ADeposer, 'chèque', 'chèques')} à déposer d'ici un mois pour ${francs(caisse.Cheques.Montant)}${caisse.Cheques.Echus > 0 ? `, dont ${nombre(caisse.Cheques.Echus)} en retard` : ''}`,
    },
    reversements?.Nombre > 0 && isDirectorOrAdmin && {
      icone: Banknote, ton: 'info', vers: '/admin/remittances',
      libelle: `${francs(reversements.Montant)} de primes encaissées à reverser à ${pluriel(reversements.Compagnies, 'compagnie', 'compagnies')}`,
    },
    commissions?.AReclamer > 0 && isDirectorOrAdmin && {
      icone: HandCoins, ton: 'info', vers: '/admin/commissions',
      libelle: `${francs(commissions.AReclamer)} de commissions à réclamer aux compagnies`,
    },
    donnees?.Sinistres?.Ouverts > 0 && {
      icone: AlertTriangle, ton: 'attention', vers: '/user/claims',
      libelle: `${pluriel(donnees.Sinistres.Ouverts, 'sinistre en cours', 'sinistres en cours')} de traitement, ${francs(donnees.Sinistres.MontantReclame)} réclamés`,
    },
    donnees?.Questionnaires?.ATraiter > 0 && {
      icone: ClipboardList, ton: 'info', vers: '/user/crm/questionnaires',
      libelle: `${pluriel(donnees.Questionnaires.ATraiter, 'questionnaire prospect', 'questionnaires prospects')} en attente de devis`,
    },
  ].filter(Boolean);

  const totalBranches = (production?.ParBranche || []).reduce((s, b) => s + Math.max(b.PrimeTtc, 0), 0);

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
    {
      header: 'Action',
      render: (e) => (e.DevisEnCours
        ? <button type="button" className="btn btn-secondary cockpit-bouton-ligne" onClick={() => navigate('/user/quotes')}>Devis préparé</button>
        : <button type="button" className="btn btn-primary cockpit-bouton-ligne" onClick={() => navigate(`/user/contracts/${e.IdContrat}/renouvellement`)}>Renouveler</button>),
    },
  ];

  const colonnesDevis = [
    { header: 'N° Devis', accessor: 'NumeroDevis', render: (d) => <strong style={{ fontFamily: 'var(--font-mono)' }}>{d.NumeroDevis}</strong> },
    { header: 'Client', accessor: 'Client', render: (d) => d.Client || '-' },
    { header: 'Branche', accessor: 'Produit' },
    { header: 'Valable jusqu\'au', accessor: 'DateExpiration', render: (d) => formatDate(d.DateExpiration) },
    { header: 'Prime TTC', accessor: 'PrimeTtc', render: (d) => <span style={{ fontFamily: 'var(--font-mono)' }}>{francs(d.PrimeTtc)}</span> },
    { header: 'Action', render: (d) => <button type="button" className="btn btn-secondary cockpit-bouton-ligne" onClick={() => ouvrirDevis(d)}>Ouvrir</button> },
  ];

  const colonnesContrats = [
    { header: 'N° Police', accessor: 'NumeroPolice', render: (c) => <strong style={{ fontFamily: 'var(--font-mono)' }}>{c.NumeroPolice}</strong> },
    { header: 'Client', accessor: 'Client' },
    { header: 'Branche', accessor: 'Produit' },
    { header: 'Émis le', accessor: 'DateEmission', render: (c) => formatDate(c.DateEmission) },
    { header: 'Prime TTC', accessor: 'PrimeTtc', render: (c) => <span style={{ fontFamily: 'var(--font-mono)' }}>{francs(c.PrimeTtc)}</span> },
    {
      header: 'Règlement', accessor: 'Reste',
      render: (c) => (c.Reste > 0
        ? <StatusBadge label={`Reste ${francs(c.Reste)}`} color="amber" />
        : <StatusBadge label="Soldé" color="emerald" />),
    },
    { header: 'Action', render: (c) => <button type="button" className="btn btn-secondary cockpit-bouton-ligne" onClick={() => navigate(`/user/contracts/${c.IdContrat}`)}>Ouvrir</button> },
  ];

  return (
    <div className="cockpit">
      {/* En-tête et raccourcis */}
      <div className="glass-panel cockpit-entete">
        <div>
          <h1 className="title-xl">Cockpit opérationnel</h1>
          <p>
            {donnees
              ? `Situation au ${formatDateLisible(donnees.Jour, { moisLong: true, jourSemaine: true })}, exercice ${exercice}.`
              : 'Production, devis, caisse et échéances du cabinet.'}
          </p>
        </div>
        <div className="cockpit-raccourcis">
          {peut('devis.create') && (
            <button type="button" className="btn btn-primary" onClick={() => navigate('/user/quotes')}>
              <FilePlus size={16} /><span>Nouveau devis</span>
            </button>
          )}
          {peut('clients.create') && (
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/clients')}>
              <UserPlus size={16} /><span>Nouveau client</span>
            </button>
          )}
          {peut('encaissements.create') && (
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/cash')}>
              <CreditCard size={16} /><span>Encaisser une prime</span>
            </button>
          )}
          {peut('contrats.reprise') && (
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/reprises')}>
              <History size={16} /><span>Affaires antérieures</span>
            </button>
          )}
          <button type="button" className="btn btn-secondary" onClick={charger} aria-busy={chargement} title="Recalculer les chiffres">
            <RefreshCw size={16} /><span>Actualiser</span>
          </button>
        </div>
      </div>

      {erreur && (
        <div className="cockpit-erreur" role="alert">
          <AlertTriangle size={18} aria-hidden="true" />
          <span>{erreur}</span>
          <button type="button" className="btn btn-secondary" onClick={charger}>Réessayer</button>
        </div>
      )}

      {!donnees && chargement && <LoadingSpinner text="Calcul des chiffres du cabinet…" />}

      {donnees && (
        <>
          {/* Production et devis */}
          {(production || devis) && (
            <div className="cockpit-tuiles">
              {production && (
                <Tuile
                  titre={`Production ${exercice}`}
                  valeur={francs(production.Annee.PrimeTtc)}
                  icone={TrendingUp}
                  couleur="purple"
                  vers="/user/contracts"
                  aide="Primes TTC des actes émis depuis le 1er janvier, contrats annulés exclus"
                  lignes={[
                    `${pluriel(production.Annee.Nombre, 'acte', 'actes')} : ${nombre(production.Annee.AffairesNouvelles)} affaires nouvelles, ${nombre(production.Annee.Renouvellements)} renouvellements`,
                    `Ce mois-ci : ${francs(production.Mois.PrimeTtc)}, ${pluriel(production.Mois.Nombre, 'acte', 'actes')}`,
                    <Evolution actuel={production.Annee.PrimeTtc} precedent={production.AnneePrecedente.PrimeTtc} au={production.AnneePrecedente.Au} />,
                  ]}
                />
              )}
              {production && (
                <Tuile
                  titre="Polices en vigueur"
                  valeur={nombre(production.PolicesEnVigueur)}
                  icone={ShieldCheck}
                  couleur="emerald"
                  vers="/user/contracts?statut=en_cours"
                  aide="Polices dont la période d'affaire nouvelle ou de renouvellement couvre aujourd'hui, résiliations exclues"
                  lignes={[
                    `${pluriel(production.Echeances.AEchoir, 'échéance', 'échéances')} dans les 30 jours`,
                    `${pluriel(production.Echeances.Echues, 'police échue', 'polices échues')} depuis moins de 30 jours`,
                  ]}
                />
              )}
              {devis && (
                <Tuile
                  titre="Devis en cours"
                  valeur={nombre(devis.EnCours)}
                  icone={FileText}
                  couleur="blue"
                  vers="/user/quotes"
                  aide="Devis ni confirmés ni archivés, encore valables"
                  lignes={[
                    `${francs(devis.PrimeTtcEnCours)} de primes proposées`,
                    `${pluriel(devis.Expires, 'devis expiré', 'devis expirés')} depuis le ${formatDate(devis.ExpiresDepuis)}`,
                  ]}
                />
              )}
              {devis && (
                <Tuile
                  titre={`Transformation ${exercice}`}
                  valeur={`${Number(devis.TauxTransformation).toLocaleString('fr-FR')} %`}
                  icone={Percent}
                  couleur="amber"
                  vers="/user/quotes"
                  aide="Devis émis depuis le 1er janvier et déjà confirmés en contrat"
                  lignes={[
                    `${nombre(devis.ConfirmesAnnee)} devis confirmés sur ${nombre(devis.EmisAnnee)} émis`,
                    <div className="cockpit-jauge" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={devis.TauxTransformation} aria-label="Taux de transformation">
                      <span style={{ width: `${Math.min(100, devis.TauxTransformation)}%` }} />
                    </div>,
                  ]}
                />
              )}
            </div>
          )}

          {/* Caisse et flux financiers */}
          {(caisse || reversements || commissions) && (
            <div className="cockpit-tuiles">
              {caisse && (
                <Tuile
                  titre={`Encaissé en ${exercice}`}
                  valeur={francs(caisse.Annee.Montant)}
                  icone={Wallet}
                  couleur="emerald"
                  vers="/user/cash/etat"
                  aide="Encaissements saisis depuis le 1er janvier, pièces annulées exclues, décaissements déduits"
                  lignes={[
                    `${pluriel(caisse.Annee.Pieces, 'pièce de caisse', 'pièces de caisse')}`,
                    `Ce mois-ci : ${francs(caisse.Mois.Montant)}, ${pluriel(caisse.Mois.Pieces, 'pièce', 'pièces')}`,
                  ]}
                />
              )}
              {caisse && (
                <Tuile
                  titre="Reste à encaisser"
                  valeur={francs(caisse.ResteAEncaisser.Montant)}
                  icone={CreditCard}
                  couleur="rose"
                  vers="/user/cash"
                  aide="Quittances non soldées des contrats en vigueur ou échus, émises depuis le 1er janvier"
                  lignes={[
                    `${pluriel(caisse.ResteAEncaisser.Nombre, 'quittance', 'quittances')} de l'exercice`,
                    caisse.ResteAEncaisser.NombreAnterieur > 0
                      && `Années antérieures : ${francs(caisse.ResteAEncaisser.MontantAnterieur)}, ${pluriel(caisse.ResteAEncaisser.NombreAnterieur, 'quittance', 'quittances')}`,
                  ]}
                />
              )}
              {reversements && (
                <Tuile
                  titre="À reverser aux compagnies"
                  valeur={francs(reversements.Montant)}
                  icone={Banknote}
                  couleur="blue"
                  vers={isDirectorOrAdmin ? '/admin/remittances' : undefined}
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
                  valeur={francs(commissions.AReclamer + commissions.Reclamees)}
                  icone={HandCoins}
                  couleur="purple"
                  vers={isDirectorOrAdmin ? '/admin/commissions' : undefined}
                  aide="Commissions des primes reversées pas encore payées par les compagnies"
                  lignes={[
                    `À réclamer : ${francs(commissions.AReclamer)}`,
                    `Réclamées non payées : ${francs(commissions.Reclamees)}${commissions.BordereauxEnAttente ? `, ${pluriel(commissions.BordereauxEnAttente, 'bordereau', 'bordereaux')}` : ''}`,
                  ]}
                />
              )}
            </div>
          )}

          <div className="cockpit-colonnes">
            {/* Points en attente */}
            <Section titre="À traiter" sousTitre="Ce qui attend une action, d'après la base">
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

            {/* Production par branche : une seule mesure, une seule teinte */}
            {production && (
              <Section titre={`Production ${exercice} par branche`} sousTitre="Primes TTC émises depuis le 1er janvier">
                {production.ParBranche.length === 0 ? (
                  <div className="cockpit-rien"><span>Aucun acte émis cette année.</span></div>
                ) : (
                  <table className="cockpit-branches">
                    <thead>
                      <tr><th>Branche</th><th>Actes</th><th>Prime TTC</th><th>Part</th></tr>
                    </thead>
                    <tbody>
                      {production.ParBranche.map((b) => {
                        const part = totalBranches ? (Math.max(b.PrimeTtc, 0) * 100) / totalBranches : 0;
                        return (
                          <tr key={b.IdProduit ?? b.Branche} title={`${b.Branche} : ${francs(b.PrimeTtc)}, ${pluriel(b.Nombre, 'acte', 'actes')}`}>
                            <td>{b.Branche}</td>
                            <td>{nombre(b.Nombre)}</td>
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
                )}
              </Section>
            )}
          </div>

          {production && (
            <Section
              titre="Échéances à suivre"
              sousTitre="Polices échues depuis moins de 30 jours ou à échoir dans les 30 jours, sans renouvellement enregistré"
              action={<BoutonVoir libelle="Toutes les échéances" vers="/user/contracts?statut=a_renouveler" />}
            >
              {production.Echeances.Lignes.length === 0
                ? <div className="cockpit-rien"><CheckCircle2 size={18} aria-hidden="true" /><span>Aucune échéance à suivre.</span></div>
                : <DataTable columns={colonnesEcheances} data={production.Echeances.Lignes} searchable={false} itemsPerPage={8} />}
            </Section>
          )}

          {devis && (
            <Section
              titre="Derniers devis en cours"
              sousTitre="Devis encore valables, à confirmer en contrat"
              action={<BoutonVoir libelle="Tous les devis" vers="/user/quotes" />}
            >
              {devis.Derniers.length === 0
                ? <div className="cockpit-rien"><span>Aucun devis en cours.</span></div>
                : <DataTable columns={colonnesDevis} data={devis.Derniers} searchable={false} itemsPerPage={8} />}
            </Section>
          )}

          {production && (
            <Section
              titre="Derniers contrats émis"
              sousTitre="Polices et avenants les plus récents, avec leur règlement"
              action={<BoutonVoir libelle="Tous les contrats" vers="/user/contracts" />}
            >
              <DataTable columns={colonnesContrats} data={production.Derniers} searchable={false} itemsPerPage={8} />
            </Section>
          )}

          {!production && !devis && !caisse && !reversements && !commissions && (
            <div className="cockpit-rien"><span>Vos droits ne donnent accès à aucun chiffre du cockpit.</span></div>
          )}
        </>
      )}
    </div>
  );
};

export default UserDashboard;
