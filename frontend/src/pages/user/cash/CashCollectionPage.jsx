import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { cashApi, mineneApi, oreoleApi, settingsApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { CreditCard, Clock, PencilLine, Receipt, FileSpreadsheet, FileText, ListChecks, Repeat, Search, X, Wallet } from 'lucide-react';
import { CorrectionEncaissement } from '../../../components/cash/CorrectionEncaissement';
import { GuichetEncaissement, champsRecherche, construireLignes, fcfa } from '../../../components/cash/GuichetEncaissement';
import { aLeDroit } from '../../../utils/droits';
import { formatDate } from '../../../utils/dateUtils';
import { exportToExcel, exportToPdf, printRecuEncaissement, printRecuReglementCommun } from '../../../utils/exportUtils';
import { ouvrirApercuImpression } from '../../../utils/apercuImpression';
import { correspondRecherche } from '../../../utils/financeUtils';

/* =========================================================================
   ENCAISSEMENT DES PRIMES
   - Onglet « Encaisser » : le guichet en quatre étapes (components/cash/GuichetEncaissement.jsx) : client, quittances,
     règlement, vérification, puis le reçu.
   - Onglet « Primes à encaisser » : toutes les quittances non soldées (GET caisse/a-encaisser/, sans la limite des 200
     contrats de l'ancienne liste), filtres et exports ; « Encaisser » ouvre le guichet sur le client, quittance cochée.
   - « Vos encaissements d'aujourd'hui » : une erreur se corrige aussitôt (CorrectionEncaissement).
   ========================================================================= */

// Aperçu du reçu ouvert au clic, rempli une fois l'encaissement retrouvé
const ouvrirFenetreRecu = (message) => {
  const fenetre = ouvrirApercuImpression();
  if (fenetre) fenetre.document.write(`<p style="font-family:Arial;padding:20px;">${message}</p>`);
  return fenetre;
};

const FILTRES_VIDES = { du: '', au: '', compagnie: '', etat: '', recherche: '' };

export const CashCollectionPage = () => {
  const { error: toastError } = useToast();
  const [onglet, setOnglet] = useState('guichet');
  const [quittances, setQuittances] = useState([]);
  const [packages, setPackages] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreurChargement, setErreurChargement] = useState('');
  const [modes, setModes] = useState([]);
  const [banques, setBanques] = useState([]);
  const [filtres, setFiltres] = useState(FILTRES_VIDES);
  // Ouverture du guichet sur un client : { cleLigne, jeton } (le jeton rouvre la même ligne deux fois de suite)
  const [demande, setDemande] = useState(null);

  // Lien « Encaisser » de la fiche d'un contrat Oreole Santé ou MINENE : ouvre directement le règlement du package
  const [parametres, setParametres] = useSearchParams();
  const packageDemande = useRef(parametres.get('oreole') ? `oreole-${parametres.get('oreole')}`
    : parametres.get('minene') ? `minene-${parametres.get('minene')}` : null);
  // « Réutiliser » d'un chèque annulé (Portefeuille des règlements) : le chèque est proposé au règlement
  const chequeDemande = useRef(parametres.get('cheque'));
  const [chequeAReutiliser, setChequeAReutiliser] = useState(null);
  useEffect(() => {
    if (parametres.get('oreole') || parametres.get('minene') || parametres.get('cheque')) setParametres({}, { replace: true });
    const id = chequeDemande.current;
    if (!id) return;
    chequeDemande.current = null;
    cashApi.getChequeStatus({ id })
      .then((r) => {
        if (r?.existe && r.annule) setChequeAReutiliser(r);
        else toastError('Ce chèque n\'est pas annulé : il se réutilise directement à la caisse par son numéro.');
      })
      .catch(() => toastError('Chèque introuvable.'));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const charger = async () => {
    setChargement(true);
    setErreurChargement('');
    try {
      const [liste, oreole, minene] = await Promise.all([
        cashApi.quittancesAEncaisser(),
        oreoleApi.caisse().catch((err) => {
          console.error('Packages Oreole Santé indisponibles :', err);
          return { Packages: [] };
        }),
        mineneApi.caisse().catch((err) => {
          console.error('Packages MINENE indisponibles :', err);
          return { Packages: [] };
        }),
      ]);
      setQuittances(liste?.Quittances || []);
      setPackages([...(oreole?.Packages || []), ...(minene?.Packages || [])]);
    } catch (err) {
      console.error('Erreur chargement des quittances à encaisser :', err);
      setErreurChargement(err.response?.data?.erreur || 'Les quittances à encaisser n\'ont pas pu être chargées.');
    } finally {
      setChargement(false);
    }
  };

  const lignes = useMemo(() => construireLignes(quittances, packages), [quittances, packages]);

  // Encaissements saisis aujourd'hui (les siens ; toute la caisse pour un responsable) : une erreur se corrige aussitôt
  const responsable = aLeDroit('encaissements.cancel');
  const [duJour, setDuJour] = useState([]);
  const [toutLaCaisse, setToutLaCaisse] = useState(false);
  const [aCorriger, setACorriger] = useState(null);
  const chargerDuJour = (tous = toutLaCaisse) => cashApi.encaissementsDuJour(tous)
    .then((r) => setDuJour(r.Encaissements || []))
    .catch(() => setDuJour([]));
  useEffect(() => { chargerDuJour(); }, [toutLaCaisse]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    charger();
    Promise.all([settingsApi.getModesEncaissement(), settingsApi.getBanques()])
      .then(([listeModes, listeBanques]) => {
        setModes(Array.isArray(listeModes) ? listeModes : []);
        setBanques(Array.isArray(listeBanques) ? listeBanques : []);
      })
      .catch((err) => console.error('Erreur chargement modes de paiement / banques :', err));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Package demandé depuis une fiche contrat : guichet ouvert dès que la liste est là
  useEffect(() => {
    if (!packageDemande.current || chargement) return;
    const cle = packageDemande.current;
    packageDemande.current = null;
    if (lignes.some((l) => l.cle === cle)) setDemande({ cleLigne: cle, jeton: Date.now() });
    else toastError('Ce package n\'a plus rien à encaisser.');
  }, [chargement, lignes]); // eslint-disable-line react-hooks/exhaustive-deps

  const encaisserLigne = (ligne) => {
    setOnglet('guichet');
    setDemande({ cleLigne: ligne.cle, jeton: Date.now() });
  };

  const apresEncaissement = (reponse, reglement) => {
    charger();
    chargerDuJour();
    // Chèque réutilisé : il reste proposé tant qu'il garde un solde (il peut régler plusieurs quittances)
    if (chequeAReutiliser && String(reglement?.numero) === String(chequeAReutiliser.numero_cheque)) {
      const solde = Number(reponse?.solde_restant_cheque);
      setChequeAReutiliser(solde > 0 ? { ...chequeAReutiliser, solde_disponible: solde, annule: false } : null);
    }
  };

  // Réimpression du reçu du dernier règlement de la quittance
  const reimprimer = async (ligne) => {
    const fenetre = ouvrirFenetreRecu('Préparation de la quittance…');
    if (ligne.package) {
      await printRecuReglementCommun(ligne.package.DernierEncaissement, fenetre);
      return;
    }
    try {
      const reglement = await cashApi.getDernierReglementQuittance(ligne.numeroQuittance);
      await printRecuEncaissement(reglement?.iddetailencaissement, fenetre);
    } catch (err) {
      console.error('Erreur recherche du dernier règlement :', err);
      if (fenetre) fenetre.close();
      toastError('Le dernier règlement de cette quittance est introuvable.');
    }
  };

  /* ---------------------------------------------------------------- liste des primes à encaisser */
  const compagnies = useMemo(
    () => [...new Set(lignes.flatMap((l) => l.compagnies))].sort((a, b) => a.localeCompare(b, 'fr')),
    [lignes],
  );
  const lignesFiltrees = useMemo(() => lignes.filter((l) => {
    const emission = String(l.dateEmission || '').slice(0, 10);
    if (filtres.du && (!emission || emission < filtres.du)) return false;
    if (filtres.au && (!emission || emission > filtres.au)) return false;
    if (filtres.compagnie && !l.compagnies.includes(filtres.compagnie)) return false;
    if (filtres.etat === 'rien' && l.encaisse > 0) return false;
    if (filtres.etat === 'acompte' && !(l.encaisse > 0)) return false;
    return correspondRecherche(filtres.recherche, [...champsRecherche(l), l.prime, l.reste]);
  }), [lignes, filtres]);

  const exporterEtat = (format) => {
    const somme = (cle) => lignesFiltrees.reduce((total, l) => total + (Number(l[cle]) || 0), 0);
    const periode = filtres.du || filtres.au
      ? `Du ${filtres.du ? formatDate(filtres.du) : 'début'} au ${filtres.au ? formatDate(filtres.au) : 'aujourd’hui'}`
      : 'Toutes les dates';
    const charge = {
      filename: 'Etat_Encaissement_Primes',
      title: 'ÉTAT DES PRIMES À ENCAISSER',
      subtitle: `${periode} - ${filtres.compagnie || 'Toutes les compagnies'}`,
      metadata: {
        'Compagnie': filtres.compagnie || 'Toutes les compagnies',
        'État': filtres.etat === 'rien' ? 'Rien encaissé' : filtres.etat === 'acompte' ? 'Acompte versé' : 'Tous',
        'Recherche': filtres.recherche || 'Aucune',
        'Nombre de quittances': String(lignesFiltrees.length),
      },
      headers: ['N° police', 'Souscripteur', 'Compagnie', "Date d'émission", 'N° quittance', 'Prime totale', 'Déjà encaissé', 'Reste à encaisser'],
      rows: lignesFiltrees.map((l) => [
        l.numeroPolice, l.client, l.compagnie, l.dateEmission ? formatDate(l.dateEmission) : '', l.numeroQuittance,
        `${fcfa(l.prime)} F`, `${fcfa(l.encaisse)} F`, `${fcfa(l.reste)} F`,
      ]),
      totals: ['TOTAL', '', '', '', '', `${fcfa(somme('prime'))} F`, `${fcfa(somme('encaisse'))} F`, `${fcfa(somme('reste'))} F`],
    };
    if (format === 'excel') exportToExcel(charge);
    else exportToPdf(charge);
  };

  const champFiltre = (cle) => (e) => setFiltres((actuels) => ({ ...actuels, [cle]: e.target.value }));

  const colonnes = [
    {
      header: 'N° Police',
      accessor: 'numeroPolice',
      render: (l) => (
        <>
          <strong style={{ color: 'var(--accent-emerald)', fontFamily: 'var(--font-mono)' }}>{l.numeroPolice}</strong>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            {l.package ? `${l.produit} : ${l.package.Quittances.length} polices` : `Quittance ${l.numeroQuittance}`}
          </div>
        </>
      ),
    },
    { header: 'Souscripteur', accessor: 'client' },
    { header: 'Compagnie', accessor: 'compagnie' },
    { header: "Date d'émission", render: (l) => (l.dateEmission ? formatDate(l.dateEmission) : '-') },
    { header: 'Prime Totale', render: (l) => <span>{fcfa(l.prime)} F</span> },
    { header: 'Déjà Encaissé', render: (l) => <span style={{ color: 'var(--accent-emerald)' }}>{fcfa(l.encaisse)} F</span> },
    {
      header: 'Reste à Encaisser',
      render: (l) => <strong style={{ color: 'var(--accent-rose)', fontFamily: 'var(--font-mono)' }}>{fcfa(l.reste)} F</strong>,
    },
    {
      header: 'État',
      render: (l) => <StatusBadge label={l.encaisse > 0 ? 'Acompte versé' : 'À encaisser'} color={l.encaisse > 0 ? 'blue' : 'amber'} />,
    },
    {
      header: 'Action',
      render: (l) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button className="btn btn-primary" style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }} onClick={() => encaisserLigne(l)}>
            <CreditCard size={14} /> Encaisser
          </button>
          {l.encaisse > 0 && (
            <button className="btn btn-secondary" style={{ padding: '0.35rem 0.55rem', fontSize: '0.75rem' }}
              title="Réimprimer la quittance du dernier règlement" onClick={() => reimprimer(l)}>
              <Receipt size={14} /> Quittance
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <CreditCard size={26} color="#10b981" />
            Encaissement des Primes
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Enregistrement des règlements (espèces, chèques, virements, Wave / Orange Money DistriPay) et émission des quittances.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link to="/user/cash/etat" className="btn btn-secondary" title="Consulter l'état détaillé des encaissements">
            <ListChecks size={15} /> États
          </Link>
          <Link to="/user/cash/recherche" className="btn btn-secondary" title="Retrouver à quoi a servi un chèque ou un autre règlement">
            <Search size={15} /> Rechercher un règlement
          </Link>
        </div>
      </div>

      {/* CIMA Article 13 Rule Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(59, 130, 246, 0.08) 100%)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: 'var(--radius-lg)',
          padding: '1rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'rgba(16, 185, 129, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#34d399',
            }}
          >
            <Receipt size={22} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
              Dispositif Réglementaire – Article 13 du Code CIMA
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
              <strong>« Pas de prime, pas d'assurance »</strong> : La prise d'effet des garanties et la délivrance des attestations sont subordonnées au paiement préalable effectif.
            </div>
          </div>
        </div>
        <span className="badge badge-success" style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}>
          Conformité CIMA 100% Active
        </span>
      </div>

      {chequeAReutiliser && (
        <div className="cheque-reutilise" role="status">
          <Repeat size={20} aria-hidden="true" />
          <div>
            <strong>Réutilisation du chèque n° {chequeAReutiliser.numero_cheque} - {chequeAReutiliser.nom_banque}</strong>
            <span>
              {chequeAReutiliser.annule
                ? `Annulé${chequeAReutiliser.date_annulation ? ` le ${formatDate(chequeAReutiliser.date_annulation)}` : ''}${chequeAReutiliser.motif_annulation ? ` (« ${chequeAReutiliser.motif_annulation} »)` : ''}. `
                : 'De nouveau en service. '}
              Disponible : {fcfa(chequeAReutiliser.solde_disponible)} F.
              {' '}Choisissez le client et ses quittances : le chèque sera proposé au règlement.
            </span>
          </div>
          <button type="button" className="btn btn-secondary" onClick={() => setChequeAReutiliser(null)}>
            <X size={14} /> Terminer
          </button>
        </div>
      )}

      {(duJour.length > 0 || toutLaCaisse) && (
        <details className="glass-panel caisse-du-jour" style={{ padding: '0.9rem 1.25rem' }}>
          <summary>
            <Clock size={17} color="#10b981" />
            {toutLaCaisse ? 'Encaissements de la caisse aujourd\'hui' : 'Vos encaissements d\'aujourd\'hui'} ({duJour.length})
            <span style={{ fontWeight: 400, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              - une erreur de client, de chèque ou de référence ? Corrigez-la ici
            </span>
            {responsable && (
              <label style={{ marginLeft: 'auto', display: 'inline-flex', gap: '0.35rem', alignItems: 'center', fontWeight: 500, fontSize: '0.8rem' }}
                onClick={(e) => e.stopPropagation()}>
                <input type="checkbox" checked={toutLaCaisse} onChange={(e) => setToutLaCaisse(e.target.checked)} /> Toute la caisse
              </label>
            )}
          </summary>
          <div style={{ marginTop: '0.5rem' }}>
            {duJour.map((e) => (
              <div key={e.IdEncaissement} className="caisse-du-jour-ligne">
                <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{e.Heure}</span>
                <span><strong>{e.Clients || '-'}</strong><div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Quittance {e.Quittances}</div></span>
                <span>{e.Mode}{e.Reference ? ` - ${e.Reference}` : ''}{toutLaCaisse && e.Operateur ? <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{e.Operateur}</div> : null}</span>
                <strong style={{ fontFamily: 'var(--font-mono)' }}>{fcfa(e.Montant)} F</strong>
                <button type="button" className="btn btn-secondary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }} onClick={() => setACorriger(e.IdEncaissement)}
                  title={`Corriger la pièce ${e.NumeroPiece}`}>
                  <PencilLine size={14} /> Corriger
                </button>
              </div>
            ))}
            {!duJour.length && <div style={{ color: 'var(--text-muted)', fontSize: '0.84rem' }}>Aucun encaissement aujourd'hui.</div>}
          </div>
        </details>
      )}
      {aCorriger && (
        <CorrectionEncaissement idEncaissement={aCorriger} onClose={() => setACorriger(null)}
          onCorrige={() => { charger(); chargerDuJour(); }} />
      )}

      <div className="cs-onglets-boutons" role="tablist" aria-label="Encaissement des primes" style={{ alignSelf: 'flex-start' }}>
        <button type="button" role="tab" aria-selected={onglet === 'guichet'} className={`cs-onglet${onglet === 'guichet' ? ' actif' : ''}`} onClick={() => setOnglet('guichet')}>
          <Wallet size={15} aria-hidden="true" /> Encaisser
        </button>
        <button type="button" role="tab" aria-selected={onglet === 'liste'} className={`cs-onglet${onglet === 'liste' ? ' actif' : ''}`} onClick={() => setOnglet('liste')}>
          <ListChecks size={15} aria-hidden="true" /> Primes à encaisser{chargement ? '' : ` (${lignes.length})`}
        </button>
      </div>

      {/* Le guichet reste monté pendant la consultation de la liste : une saisie commencée n'est pas perdue */}
      <div className="glass-panel" style={{ padding: '1.25rem 1.5rem', display: onglet === 'guichet' ? undefined : 'none' }}>
        <GuichetEncaissement
          lignes={lignes}
          chargement={chargement}
          erreurChargement={erreurChargement}
          onRecharger={charger}
          modes={modes}
          banques={banques}
          onBanqueCreee={(banque) => setBanques((liste) => [...liste, banque])}
          demande={demande}
          chequeAReutiliser={chequeAReutiliser}
          onEnregistre={apresEncaissement}
        />
      </div>

      {onglet === 'liste' && (
        <div className="glass-panel cs-contenu" style={{ padding: '1.25rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 170px), 1fr))', gap: '0.75rem', alignItems: 'end' }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" htmlFor="encaissement-du">Émission du</label>
              <input id="encaissement-du" type="date" className="form-control" value={filtres.du} onChange={champFiltre('du')} />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" htmlFor="encaissement-au">Émission au</label>
              <input id="encaissement-au" type="date" className="form-control" value={filtres.au} onChange={champFiltre('au')} />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" htmlFor="encaissement-compagnie">Compagnie</label>
              <select id="encaissement-compagnie" className="form-control" value={filtres.compagnie} onChange={champFiltre('compagnie')}>
                <option value="">Toutes les compagnies</option>
                {compagnies.map((compagnie) => <option key={compagnie} value={compagnie}>{compagnie}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" htmlFor="encaissement-etat">État</label>
              <select id="encaissement-etat" className="form-control" value={filtres.etat} onChange={champFiltre('etat')}>
                <option value="">Tous</option>
                <option value="rien">Rien encaissé</option>
                <option value="acompte">Acompte versé</option>
              </select>
            </div>
            <div style={{ position: 'relative' }}>
              <label className="form-label" htmlFor="encaissement-recherche">Recherche</label>
              <Search size={15} style={{ position: 'absolute', left: 10, bottom: 11, color: 'var(--text-muted)' }} />
              <input id="encaissement-recherche" type="search" className="form-control" style={{ paddingLeft: '2rem' }}
                value={filtres.recherche} onChange={champFiltre('recherche')} placeholder="Police, client, quittance…" />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setFiltres(FILTRES_VIDES)} title="Effacer les filtres">
                <X size={15} /> Réinitialiser
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => exporterEtat('excel')} disabled={!lignesFiltrees.length}
                title="Exporter les résultats filtrés en Excel">
                <FileSpreadsheet size={15} /> Excel
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => exporterEtat('pdf')} disabled={!lignesFiltrees.length}
                title="Exporter les résultats filtrés en PDF">
                <FileText size={15} /> PDF
              </button>
            </div>
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            {chargement ? 'Chargement…' : `${lignesFiltrees.length} quittance(s) affichée(s) sur ${lignes.length} ; les exports reprennent cette sélection.`}
          </div>
          <DataTable columns={colonnes} data={lignesFiltrees} searchable={false} />
        </div>
      )}
    </div>
  );
};

export default CashCollectionPage;
