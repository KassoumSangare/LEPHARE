import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertTriangle, ArrowDown, ArrowLeft, ArrowRight, ArrowUp, ArrowUpDown, Car, ChevronLeft, ChevronRight,
  HeartPulse, Home, Layers, Loader2, Pencil, Plane, Search, Save, Shield, Ship, X,
} from 'lucide-react';
import { contractApi } from '../../../api/endpoints';
import { EnTeteParametrage } from '../../../components/admin/EnTeteParametrage';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { SqueletteTableau } from '../../../components/common/Squelette';
import { useToast } from '../../../context/ToastContext';
import { messageErreurApi } from '../../../utils/financeUtils';

const TAILLE_PAGE = 25;
const BRANCHES = [
  { cle: 'ALL', libelle: 'Toutes les branches', icone: Layers, produits: null },
  { cle: 'AUTO', libelle: 'Automobile', icone: Car, produits: [1] },
  { cle: 'SANTE', libelle: 'Santé & Vie', icone: HeartPulse, produits: [5, 10] },
  { cle: 'IA', libelle: 'Individuelle Accidents', icone: Activity, produits: [2] },
  { cle: 'VOYAGE', libelle: 'Voyage', icone: Plane, produits: [3] },
  { cle: 'TRANSPORT', libelle: 'Transport', icone: Ship, produits: [6] },
  { cle: 'MRH', libelle: 'Habitation & Dommages', icone: Home, produits: [4, 7, 9] },
  { cle: 'RC', libelle: 'Responsabilité Civile', icone: Shield, produits: [8] },
];
const STATUTS = {
  en_cours: { libelle: 'En cours', badge: 'emerald' },
  a_renouveler: { libelle: 'À renouveler', badge: 'amber' },
  echu: { libelle: 'Échu', badge: 'slate' },
  renouvele: { libelle: 'Renouvelé', badge: 'blue' },
  resilie: { libelle: 'Résilié', badge: 'rose' },
  annule: { libelle: 'Annulé', badge: 'rose' },
};
const ONGLETS_STATUT = ['tous', ...Object.keys(STATUTS)];
const TAILLES_PAGE = [25, 50, 100];
const dateFr = (valeur) => {
  const match = String(valeur || '').match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : '-';
};
const montant = (valeur) => (valeur === null || valeur === undefined || valeur === ''
  ? '-'
  : `${Math.round(Number(valeur)).toLocaleString('fr-FR')} F`);
const nombre = (valeur) => Number(valeur || 0).toLocaleString('fr-FR');

const LIBELLES = {
  numeropolice: 'Numéro de police',
  numero_police_compagnie: 'Numéro de police compagnie',
  numero_avenant_compagnie: 'Numéro d’avenant compagnie',
  numeroavenant: 'Numéro d’avenant',
  referenceagent: 'Référence agent',
  idclient: 'Identifiant client',
  idassure: 'Identifiant assuré',
  idcompagnie: 'Identifiant compagnie',
  flotte: 'Contrat flotte',
  coassurance: 'Coassurance',
  renouvelable: 'Renouvelable',
  dateeffet: 'Date d’effet',
  dateexpiration: 'Date d’échéance',
  dateemission: 'Date d’émission',
  heuredebut: 'Heure de début',
  nbreche: 'Nombre d’échéances',
  primenette: 'Prime nette',
  primeannuelle: 'Prime annuelle',
  primettc: 'Prime TTC',
  accessoire: 'Accessoires',
  accessoirecompagnie: 'Accessoires compagnie',
  accessoireintermediaire: 'Accessoires intermédiaire',
  accessoiregestionnaire: 'Accessoires gestionnaire',
  commissionintermediaire: 'Commission intermédiaire',
  commissiongestionnaire: 'Commission gestionnaire',
  commissionaperiteur: 'Commission apériteur',
  bonus_malus: 'Bonus-malus',
  taxe: 'Taxe',
  fga: 'FGA',
  cedeao: 'CEDEAO',
  taux_commission: 'Taux de commission',
  assure: 'Nom de l’assuré',
  observation: 'Observation',
  idcontratdetail: 'Identifiant du risque',
  idcontratdetgarantie: 'Identifiant de la garantie',
  idusage: 'Identifiant usage',
  idtypevehicule: 'Identifiant type de véhicule',
  idgenrevehicule: 'Identifiant genre de véhicule',
  idmarque: 'Identifiant marque',
  idgarantie: 'Identifiant garantie',
  matricule: 'Immatriculation',
  numchassis: 'Numéro de châssis',
  nummoteur: 'Numéro de moteur',
  modelevehicule: 'Modèle du véhicule',
  nombreplace: 'Nombre de places',
  puissancefiscale: 'Puissance fiscale',
  chargeutile: 'Charge utile',
  valeurneuve: 'Valeur à neuf',
  valeurvenale: 'Valeur vénale',
  valeuraccessoire: 'Valeur des accessoires',
  conducteur: 'Conducteur',
  datemec: 'Date de première mise en circulation',
  permis: 'Numéro de permis',
  sexe: 'Sexe',
  codeusage: 'Code usage',
  idtarif: 'Identifiant tarif',
  idoffre: 'Identifiant offre',
  acquise: 'Garantie acquise',
  capital: 'Capital garanti',
  franchise: 'Franchise',
  textefranchise: 'Texte de franchise',
  minfranchise: 'Franchise minimum',
  maxfranchise: 'Franchise maximum',
  tauxfranchise: 'Taux de franchise',
  taxeenregistrement: 'Taxe d’enregistrement',
  taux_reduction: 'Taux de réduction',
};

const CLES_BOOLS = new Set([
  'flotte', 'coassurance', 'renouvelable', 'transfere', 'anticipation', 'auteur',
  'prime_imposee', 'remorque', 'extincteur', 'carteverte', 'pc_control', 'cg_control', 'acquise',
]);

const estDate = (cle) => cle.startsWith('date') || cle === 'heuredebut' || cle === 'datemec' || cle === 'datenaicnd';
const estNumerique = (cle, valeur) => (
  typeof valeur === 'number'
  || /^-?\d+([.,]\d+)?$/.test(String(valeur ?? ''))
  || cle.startsWith('id')
  || /^(prime|taxe|fga|cedeao|accessoire|commission|bonus|capital|franchise|taux|valeur|charge|puissance|nombre|nbre|mt_|ipp|deces|hosp)/i.test(cle)
);

const valeurDate = (valeur) => {
  if (!valeur) return '';
  const texte = String(valeur);
  return texte.includes('T') ? texte.slice(0, 16) : `${texte.slice(0, 10)}T00:00`;
};

const libelleChamp = (cle) => LIBELLES[cle] || cle
  .replace(/_/g, ' ')
  .replace(/([a-z])([A-Z])/g, '$1 $2')
  .replace(/\b\w/g, (lettre) => lettre.toUpperCase());

const nomClient = (contrat) => {
  const client = contrat.idclient;
  if (client && typeof client === 'object') {
    return `${client.Nom || ''} ${client.Prenoms || ''}`.trim();
  }
  return contrat.assure || 'Client non renseigné';
};

const champsModifies = (courant, initial, exclus = []) => Object.fromEntries(
  Object.entries(courant || {}).filter(([cle, valeur]) => (
    !exclus.includes(cle) && JSON.stringify(valeur) !== JSON.stringify(initial?.[cle])
  )),
);

const ChampEdition = ({ cle, valeur, onChange }) => {
  if (CLES_BOOLS.has(cle) || typeof valeur === 'boolean') {
    return (
      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minHeight: 40 }}>
        <input type="checkbox" checked={Boolean(valeur)} onChange={(event) => onChange(event.target.checked)} />
        <span>{libelleChamp(cle)}</span>
      </label>
    );
  }

  const date = estDate(cle);
  const numerique = !date && estNumerique(cle, valeur);
  const multiline = ['observation', 'conducteur', 'textefranchise', 'assure'].includes(cle);
  const commonProps = {
    className: 'form-input',
    value: date ? valeurDate(valeur) : (valeur ?? ''),
    type: date ? 'datetime-local' : (numerique ? 'number' : 'text'),
    step: numerique && /prime|taxe|fga|cedeao|accessoire|commission|capital|franchise|taux|valeur|charge|bonus|ipp|deces|hosp/i.test(cle) ? 'any' : undefined,
    onChange: (event) => {
      const value = event.target.value;
      onChange(value === '' && (valeur === null || date || numerique) ? null : value);
    },
  };

  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
      <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>{libelleChamp(cle)}</span>
      {multiline
        ? <textarea {...commonProps} rows={2} />
        : <input {...commonProps} />}
    </label>
  );
};

const ChampsEdition = ({ valeurs, identifiantsMasques = [], onChange }) => (
  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '0.75rem' }}>
    {Object.entries(valeurs || {})
      .filter(([cle]) => !identifiantsMasques.includes(cle) && cle !== 'garanties')
      .map(([cle, valeur]) => (
        <ChampEdition
          key={cle}
          cle={cle}
          valeur={valeur}
          onChange={(nouvelleValeur) => onChange(cle, nouvelleValeur)}
        />
      ))}
  </div>
);

export const AdminContractManagementPage = () => {
  const { success, error: toastError } = useToast();
  const [recherche, setRecherche] = useState('');
  const [rechercheAppliquee, setRechercheAppliquee] = useState('');
  const [page, setPage] = useState(1);
  const [taille, setTaille] = useState(TAILLE_PAGE);
  const [branche, setBranche] = useState('ALL');
  const [statut, setStatut] = useState('tous');
  const [ordre, setOrdre] = useState('');
  const [champPeriode, setChampPeriode] = useState('effet');
  const [du, setDu] = useState('');
  const [au, setAu] = useState('');
  const [liste, setListe] = useState({ results: [], count: 0, par_produit: {}, par_statut: {} });
  const [chargementListe, setChargementListe] = useState(true);
  const [contratEdite, setContratEdite] = useState(null);
  const [valeursInitiales, setValeursInitiales] = useState(null);
  const [chargementContrat, setChargementContrat] = useState(false);
  const [enregistrement, setEnregistrement] = useState(false);

  const chargerListe = useCallback(async () => {
    setChargementListe(true);
    try {
      const filtres = {
        recherche: rechercheAppliquee || undefined,
        idproduit: BRANCHES.find((item) => item.cle === branche)?.produits?.join(','),
        statut: statut === 'tous' ? undefined : statut,
        [`${champPeriode}_du`]: du || undefined,
        [`${champPeriode}_au`]: au || undefined,
        ordre: ordre || undefined,
        page,
        page_size: taille,
      };
      const resultat = await contractApi.getAdministrationContracts(filtres);
      setListe(resultat);
    } catch (error) {
      toastError(`Les contrats n’ont pas pu être chargés : ${messageErreurApi(error)}`);
    } finally {
      setChargementListe(false);
    }
  }, [au, branche, champPeriode, du, ordre, page, rechercheAppliquee, statut, taille, toastError]);

  useEffect(() => {
    chargerListe();
  }, [chargerListe]);

  const ouvrirContrat = async (id) => {
    setChargementContrat(true);
    try {
      const resultat = await contractApi.getAdministrationContract(id);
      setContratEdite(resultat);
      setValeursInitiales(JSON.stringify(resultat));
    } catch (error) {
      toastError(`Le contrat n’a pas pu être ouvert : ${messageErreurApi(error)}`);
    } finally {
      setChargementContrat(false);
    }
  };

  const modifierContrat = (cle, valeur) => {
    setContratEdite((courant) => ({
      ...courant,
      contrat: { ...courant.contrat, [cle]: valeur },
    }));
  };

  const modifierDetail = (index, cle, valeur) => {
    setContratEdite((courant) => ({
      ...courant,
      details: courant.details.map((detail, i) => (
        i === index ? { ...detail, [cle]: valeur } : detail
      )),
    }));
  };

  const modifierGarantie = (indexDetail, indexGarantie, cle, valeur) => {
    setContratEdite((courant) => ({
      ...courant,
      details: courant.details.map((detail, i) => (
        i !== indexDetail
          ? detail
          : {
            ...detail,
            garanties: detail.garanties.map((garantie, j) => (
              j === indexGarantie ? { ...garantie, [cle]: valeur } : garantie
            )),
          }
      )),
    }));
  };

  const modifier = useMemo(
    () => Boolean(contratEdite && JSON.stringify(contratEdite) !== valeursInitiales),
    [contratEdite, valeursInitiales],
  );

  const enregistrer = async () => {
    setEnregistrement(true);
    try {
      const idContrat = Number(contratEdite?.contrat?.idcontrat);
      if (!Number.isSafeInteger(idContrat) || idContrat <= 0) {
        toastError('Le contrat ne possède pas d’identifiant valide. Fermez-le puis ouvrez-le à nouveau.');
        return;
      }
      const initial = JSON.parse(valeursInitiales);
      const detailsModifies = contratEdite.details.flatMap((detail) => {
        const detailInitial = initial.details.find(
          (item) => item.idcontratdetail === detail.idcontratdetail,
        );
        if (!detailInitial) return [];
        const champsDetail = champsModifies(detail, detailInitial, [
          'idcontratdetail', 'idcontrat', 'garanties',
        ]);
        const garantiesModifiees = (detail.garanties || []).flatMap((garantie) => {
          const garantieInitiale = (detailInitial.garanties || []).find(
            (item) => item.idcontratdetgarantie === garantie.idcontratdetgarantie,
          );
          if (!garantieInitiale) return [];
          const champsGarantie = champsModifies(garantie, garantieInitiale, [
            'idcontratdetgarantie', 'idcontratdetail',
          ]);
          return Object.keys(champsGarantie).length
            ? [{ ...champsGarantie, idcontratdetgarantie: garantie.idcontratdetgarantie }]
            : [];
        });
        if (!Object.keys(champsDetail).length && !garantiesModifiees.length) return [];
        return [{
          ...champsDetail,
          idcontratdetail: detail.idcontratdetail,
          garanties: garantiesModifiees,
        }];
      });
      const resultat = await contractApi.updateAdministrationContract(
        idContrat,
        {
          contrat: champsModifies(contratEdite.contrat, initial.contrat, ['idcontrat']),
          details: detailsModifies,
        },
      );
      setContratEdite(resultat);
      setValeursInitiales(JSON.stringify(resultat));
      success('Les modifications du contrat ont été enregistrées et journalisées.');
      await chargerListe();
    } catch (error) {
      toastError(`Les modifications n’ont pas été enregistrées : ${messageErreurApi(error)}`);
    } finally {
      setEnregistrement(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(liste.count / taille));
  const trier = (cle) => {
    const actif = ordre.replace(/^-/, '') === cle ? ordre : null;
    const decroissantDabord = ['effet', 'echeance', 'prime'].includes(cle);
    setOrdre(actif
      ? (actif.startsWith('-') ? cle : `-${cle}`)
      : (decroissantDabord ? `-${cle}` : cle));
    setPage(1);
  };
  const enteteTri = (cle, libelle, alignement = 'left') => {
    const actif = ordre.replace(/^-/, '') === cle;
    const Icone = !actif ? ArrowUpDown : ordre.startsWith('-') ? ArrowDown : ArrowUp;
    return (
      <th className={`triable${alignement === 'right' ? ' droite' : ''}`} aria-sort={actif ? (ordre.startsWith('-') ? 'descending' : 'ascending') : 'none'}>
        <button type="button" className="portefeuille-tri" onClick={() => trier(cle)} title="Trier">
          {libelle}<Icone size={12} style={{ opacity: actif ? 1 : 0.45 }} />
        </button>
      </th>
    );
  };
  const compteBranche = (item) => {
    if (!item.produits) return Object.values(liste.par_produit || {}).reduce((total, valeur) => total + Number(valeur), 0);
    return item.produits.reduce((total, id) => total + Number(liste.par_produit?.[String(id)] || 0), 0);
  };
  const compteStatut = (cle) => {
    if (cle === 'tous') return Object.entries(liste.par_statut || {})
      .filter(([statutCompte]) => statutCompte !== 'annule')
      .reduce((total, [, valeur]) => total + Number(valeur), 0);
    return Number(liste.par_statut?.[cle] || 0);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', padding: '1.5rem' }}>
      <EnTeteParametrage
        icone={Pencil}
        titre="Administration des contrats"
        description="Modification contrôlée des données du contrat, des risques/véhicules et des garanties. Chaque enregistrement exige un motif et conserve les valeurs avant/après dans le journal d’audit."
      />

      <section className="glass-panel portefeuille-filtres" aria-label="Recherche et filtres">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
            setRechercheAppliquee(recherche.trim());
          }}
          className="portefeuille-ligne-recherche"
        >
          <label className="portefeuille-recherche">
            <Search size={17} aria-hidden="true" />
            <input
              type="search"
              className="form-control"
              value={recherche}
              onChange={(event) => setRecherche(event.target.value)}
              placeholder="N° de police, client, produit ou compagnie…"
              aria-label="Rechercher un contrat"
            />
            <button type="submit" className="btn btn-primary" aria-label="Rechercher">
              <Search size={16} />
            </button>
          </label>
          <div className="portefeuille-periode" role="group" aria-label="Période">
            <select className="form-control" value={champPeriode} onChange={(event) => { setChampPeriode(event.target.value); setPage(1); }}>
              <option value="effet">Date d’effet</option>
              <option value="echeance">Date d’échéance</option>
              <option value="emission">Date d’émission</option>
            </select>
            <input type="date" className="form-control" value={du} max={au || undefined} onChange={(event) => { setDu(event.target.value); setPage(1); }} aria-label="Du" />
            <ArrowRight size={14} aria-hidden="true" />
            <input type="date" className="form-control" value={au} min={du || undefined} onChange={(event) => { setAu(event.target.value); setPage(1); }} aria-label="Au" />
          </div>
        </form>

        <div className="portefeuille-branches" role="tablist" aria-label="Branches">
          {BRANCHES.map((item) => {
            const Icone = item.icone;
            const actif = branche === item.cle;
            return (
              <button key={item.cle} type="button" role="tab" aria-selected={actif}
                className={`portefeuille-puce${actif ? ' actif' : ''}`}
                onClick={() => { setBranche(item.cle); setPage(1); }}>
                <Icone size={15} /><span>{item.libelle}</span>
                <span className="portefeuille-compte">{nombre(compteBranche(item))}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="glass-panel portefeuille-liste" aria-label="Contrats">
        <div className="portefeuille-statuts" role="tablist" aria-label="Statut des contrats">
          {ONGLETS_STATUT.map((cle) => (
            <button key={cle} type="button" role="tab" aria-selected={statut === cle}
              className={`portefeuille-statut statut-${cle}${statut === cle ? ' actif' : ''}`}
              onClick={() => { setStatut(cle); setPage(1); }}>
              {cle === 'tous' ? 'Tous' : STATUTS[cle].libelle}
              <span className="portefeuille-compte">{nombre(compteStatut(cle))}</span>
            </button>
          ))}
        </div>
        <div className="portefeuille-resume">
          <span className="portefeuille-volume">{nombre(liste.count)} contrat(s)</span>
        </div>
        {chargementListe ? (
          <SqueletteTableau colonnes={7} lignes={8} libelle="Chargement des contrats…" />
        ) : (
          <>
            <div className="table-wrapper">
              <table className="data-table portefeuille-table">
                <thead>
                  <tr>
                    {enteteTri('police', 'Police')}
                    {enteteTri('client', 'Client')}
                    {enteteTri('produit', 'Produit · Compagnie')}
                    {enteteTri('echeance', 'Effet → Échéance')}
                    {enteteTri('prime', 'Prime TTC', 'right')}
                    <th>Statut</th><th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {liste.results.map((contrat) => (
                    <tr key={contrat.idcontrat}>
                      <td data-label="Police"><span className="portefeuille-police">{contrat.numeropolice || contrat.numero_police_compagnie || `Contrat ${contrat.idcontrat}`}</span></td>
                      <td data-label="Client"><span className="portefeuille-client">{nomClient(contrat)}</span></td>
                      <td data-label="Produit">
                        <div className="portefeuille-principal">{contrat.idproduit?.libelle_produit || '-'}</div>
                        <div className="portefeuille-secondaire">{contrat.idcompagnie?.RaisonSociale || '-'}</div>
                      </td>
                      <td data-label="Période">
                        <div className="portefeuille-periode-cellule"><span>{dateFr(contrat.dateeffet)}</span><ArrowRight size={12} /><span>{dateFr(contrat.dateexpiration)}</span></div>
                      </td>
                      <td data-label="Prime TTC" style={{ textAlign: 'right' }}>
                        <div className="portefeuille-montant">{montant(contrat.primettc)}</div>
                        <div className="portefeuille-secondaire">Nette {montant(contrat.primenette)}</div>
                      </td>
                      <td data-label="Statut">
                        {STATUTS[contrat.statut_portefeuille] ? (
                          <StatusBadge label={STATUTS[contrat.statut_portefeuille].libelle} color={STATUTS[contrat.statut_portefeuille].badge} />
                        ) : '-'}
                      </td>
                      <td data-label="Actions" className="portefeuille-cellule-actions">
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => ouvrirContrat(contrat.idcontrat)}
                          disabled={chargementContrat}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                        >
                          <Pencil size={14} /> Modifier
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!liste.results.length && <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Aucun contrat trouvé.</td></tr>}
                </tbody>
              </table>
            </div>
            <nav className="portefeuille-pagination" aria-label="Pagination">
              <span>{nombre(liste.count)} contrat(s) — page {page} / {totalPages}</span>
              <div className="portefeuille-pages">
                <label>
                  <span>Lignes par page</span>
                  <select className="form-control" value={taille} onChange={(event) => { setTaille(Number(event.target.value)); setPage(1); }}>
                    {TAILLES_PAGE.map((valeur) => <option key={valeur} value={valeur}>{valeur}</option>)}
                  </select>
                </label>
                <button type="button" className="btn btn-secondary" aria-label="Page précédente" disabled={page <= 1} onClick={() => setPage((v) => v - 1)}><ChevronLeft size={16} /></button>
                <button type="button" className="btn btn-secondary" aria-label="Page suivante" disabled={page >= totalPages} onClick={() => setPage((v) => v + 1)}><ChevronRight size={16} /></button>
              </div>
            </nav>
          </>
        )}
      </section>

      {contratEdite && (
        <section className="glass-panel" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Contrat {contratEdite.contrat.numeropolice || `#${contratEdite.contrat.idcontrat}`}</h2>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>Les identifiants de structure et la quittance liée ne sont pas modifiables depuis cet écran.</span>
            </div>
            <button type="button" className="btn btn-secondary" onClick={() => { setContratEdite(null); setValeursInitiales(null); }} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <X size={15} /> Fermer
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem', padding: '0.75rem', borderRadius: 8, background: 'rgba(245,158,11,0.1)', color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
            <AlertTriangle size={17} style={{ flexShrink: 0, color: 'var(--accent-amber)' }} />
            <span>Cette modification administrative ne crée pas d’avenant et ne recalcule pas automatiquement les quittances. Vérifiez les données et le motif avant l’enregistrement.</span>
          </div>

          <details open>
            <summary style={{ cursor: 'pointer', fontWeight: 700, padding: '0.4rem 0' }}>Informations du contrat</summary>
            <ChampsEdition
              valeurs={contratEdite.contrat}
              identifiantsMasques={['idcontrat', 'iddevis', 'idproduit', 'idintermediaire', 'idavenant', 'idquittance', 'piece_jointe', 'idcontratannulation', 'idoperateur', 'auteur', 'idoldhist', 'oldnumerodevis']}
              onChange={modifierContrat}
            />
          </details>

          {contratEdite.details.map((detail, indexDetail) => (
            <details key={detail.idcontratdetail} open={indexDetail === 0}>
              <summary style={{ cursor: 'pointer', fontWeight: 700, padding: '0.4rem 0' }}>
                Risque / véhicule {indexDetail + 1} — {detail.matricule || detail.assure || `#${detail.idcontratdetail}`}
              </summary>
              <ChampsEdition
                valeurs={detail}
                identifiantsMasques={['idcontratdetail', 'idcontrat', 'garanties']}
                onChange={(cle, valeur) => modifierDetail(indexDetail, cle, valeur)}
              />
              {(detail.garanties || []).map((garantie, indexGarantie) => (
                <details key={garantie.idcontratdetgarantie} style={{ margin: '0.7rem 0 0 1rem' }}>
                  <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)', fontSize: '0.85rem', padding: '0.35rem 0' }}>
                    Garantie {indexGarantie + 1} — {garantie.idgarantie}
                  </summary>
                  <ChampsEdition
                    valeurs={garantie}
                    identifiantsMasques={['idcontratdetgarantie', 'idcontratdetail']}
                    onChange={(cle, valeur) => modifierGarantie(indexDetail, indexGarantie, cle, valeur)}
                  />
                </details>
              ))}
            </details>
          ))}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => { setContratEdite(null); setValeursInitiales(null); }} disabled={enregistrement}>
              <ArrowLeft size={15} /> Retour à la liste
            </button>
            <button type="button" className="btn btn-primary" onClick={enregistrer} disabled={!modifier || enregistrement} aria-busy={enregistrement} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
              {enregistrement ? <Loader2 className="spin" size={15} /> : <Save size={15} />}
              Enregistrer les modifications
            </button>
          </div>
        </section>
      )}
    </div>
  );
};

export default AdminContractManagementPage;
