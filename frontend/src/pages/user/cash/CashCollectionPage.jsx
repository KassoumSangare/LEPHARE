import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { cashApi, contractApi, settingsApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { CreditCard, Check, Receipt, FileSpreadsheet, FileText, ListChecks, Search, X } from 'lucide-react';
import { formatDate } from '../../../utils/dateUtils';
import { exportToExcel, exportToPdf, printRecuEncaissement } from '../../../utils/exportUtils';
import { ouvrirApercuImpression } from '../../../utils/apercuImpression';
import { correspondRecherche } from '../../../utils/financeUtils';
import {
  actionReglement,
  ChampsReglement,
  champsReglementApi,
  modesProposes,
  natureMode,
  reglementVide,
} from '../../../components/cash/ChampsReglement';

// Date du jour au format du champ date (AAAA-MM-JJ), en heure locale
const aujourdhui = () => {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

// Quittance générée à la confirmation du devis (sp_confirmation_devis → sp_generation_quittance)
const numeroQuittance = (contract) => contract?.raw?.idquittance?.numeroquittance || '';
const dateEmission = (contract) => contract?.raw
  ? contract.raw.dateemission || contract.raw.date_emission || ''
  : contract?.date_emission || '';
const montantFormate = (montant) => Math.round(Number(montant) || 0).toLocaleString('fr-FR');
const resteAEncaisser = (contract) => {
  const reste = (Number(contract?.prime_totale) || 0) - (Number(contract?.montant_encaisse) || 0);
  return reste <= 4 ? 0 : reste;
};

// Aperçu du reçu ouvert au clic, rempli une fois l'encaissement enregistré
const ouvrirFenetreRecu = (message) => {
  const fenetre = ouvrirApercuImpression();
  if (fenetre) fenetre.document.write(`<p style="font-family:Arial;padding:20px;">${message}</p>`);
  return fenetre;
};

// Message d'erreur de /api/enregistrementencaissement : { erreur, details } ou erreurs de validation
const messageErreurEncaissement = (err) => {
  const d = err.response?.data;
  if (d?.erreur) return d.details ? `${d.erreur} ${d.details}` : d.erreur;
  if (d?.detail) return d.detail;
  if (d && typeof d === 'object') {
    const premier = Object.values(d).flat()[0];
    if (typeof premier === 'string') return premier;
  }
  return "L'encaissement n'a pas pu être enregistré. Veuillez réessayer.";
};

export const CashCollectionPage = () => {
  const [contracts, setContracts] = useState([]);
  const [selectedContract, setSelectedContract] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modes, setModes] = useState([]);
  const [banques, setBanques] = useState([]);
  const [filtres, setFiltres] = useState({ du: '', au: '', compagnie: '', statut: '', recherche: '' });
  const { success, error: toastError } = useToast();

  const loadContracts = async () => {
    try {
      // Contrats dont la quittance reste à encaisser, derniers confirmés en tête
      const data = await contractApi.getContracts({ a_encaisser: 1 });
      if (Array.isArray(data)) {
        setContracts(data);
      }
    } catch (err) {
      console.error('Erreur chargement contrats caisse Django:', err);
    }
  };

  useEffect(() => {
    loadContracts();
    Promise.all([settingsApi.getModesEncaissement(), settingsApi.getBanques()])
      .then(([listeModes, listeBanques]) => {
        setModes(modesProposes(listeModes));
        setBanques(Array.isArray(listeBanques) ? listeBanques : []);
      })
      .catch((err) => console.error('Erreur chargement modes de paiement / banques :', err));
  }, []);

  // Payment Form State
  const [montantEncaisse, setMontantEncaisse] = useState(0);
  const [reglement, setReglement] = useState(reglementVide());
  const [enregistrement, setEnregistrement] = useState(false);
  const changerReglement = (champ, valeur) => setReglement((prev) => ({ ...prev, [champ]: valeur }));
  // Titre et bouton du formulaire selon le mode choisi (décaissement, annulation, compensation…)
  const action = actionReglement(modes.find((m) => String(m.idmodeencaissement) === String(reglement.idMode)));

  const handleOpenPayment = (contract) => {
    setSelectedContract(contract);
    const reste = resteAEncaisser(contract);
    setMontantEncaisse(reste);
    const especes = modes.find((m) => natureMode(m).especes);
    setReglement({
      ...reglementVide(String(contract.client_nom || '').slice(0, 50)),
      idMode: String((especes || modes[0])?.idmodeencaissement || ''),
    });
    setIsModalOpen(true);
  };

  // Réimpression du reçu du dernier règlement de la quittance
  const handleShowQuittance = async (contract) => {
    const fenetre = ouvrirFenetreRecu('Préparation de la quittance…');
    try {
      const reglement = await cashApi.getDernierReglementQuittance(numeroQuittance(contract));
      await printRecuEncaissement(reglement?.iddetailencaissement, fenetre);
    } catch (err) {
      console.error('Erreur recherche du dernier règlement :', err);
      if (fenetre) fenetre.close();
      toastError('Le dernier règlement de cette quittance est introuvable.');
    }
  };

  const handleSavePayment = async (e) => {
    e.preventDefault();
    if (!selectedContract || enregistrement) return;
    const quittance = numeroQuittance(selectedContract);
    if (!quittance) {
      toastError("Ce contrat n'a pas de quittance : encaissement impossible.");
      return;
    }

    const fenetre = ouvrirFenetreRecu("Enregistrement de l'encaissement…");
    setEnregistrement(true);
    try {
      // Date de saisie : toujours la date du jour (non modifiable, imposée aussi par le serveur)
      const [annee, mois, jour] = aujourdhui().split('-');
      const mode = modes.find((m) => String(m.idmodeencaissement) === String(reglement.idMode));
      const res = await cashApi.collectPremium({
        ...champsReglementApi(reglement, mode),
        date_encaissement: `${jour}-${mois}-${annee}`,
        montant_total: Number(montantEncaisse),
        liste_quittance: [{ numero_quittance: quittance, montant_encaissement: Number(montantEncaisse) }],
      });
      setIsModalOpen(false);
      loadContracts();
      success(res.data?.message || `Règlement de ${Number(montantEncaisse).toLocaleString('fr-FR')} FCFA enregistré.`);
      const [ligne] = await cashApi.getDetailsEncaissement(res.data?.id_encaissement);
      await printRecuEncaissement(ligne?.iddetailencaissement, fenetre);
    } catch (err) {
      console.error('Erreur encaissement :', err.response?.data || err);
      if (fenetre) fenetre.close();
      toastError(messageErreurEncaissement(err));
    } finally {
      setEnregistrement(false);
    }
  };

  const compagnies = useMemo(
    () => [...new Set(contracts.map((contract) => contract.compagnie).filter(Boolean))]
      .sort((a, b) => a.localeCompare(b, 'fr')),
    [contracts],
  );
  const contratsFiltres = useMemo(() => contracts.filter((contract) => {
    const emission = String(dateEmission(contract)).slice(0, 10);
    if (filtres.du && (!emission || emission < filtres.du)) return false;
    if (filtres.au && (!emission || emission > filtres.au)) return false;
    if (filtres.compagnie && contract.compagnie !== filtres.compagnie) return false;
    if (filtres.statut && contract.statut_encaissement !== filtres.statut) return false;
    return correspondRecherche(filtres.recherche, [
      contract.numeropolice, contract.client_nom, contract.compagnie, contract.produit,
      contract.statut_encaissement, dateEmission(contract), numeroQuittance(contract),
      contract.prime_totale, contract.montant_encaisse,
    ]);
  }), [contracts, filtres]);

  const exporterEtat = (format) => {
    const totalPrimes = contratsFiltres.reduce((total, contract) => total + (Number(contract.prime_totale) || 0), 0);
    const totalEncaisse = contratsFiltres.reduce((total, contract) => total + (Number(contract.montant_encaisse) || 0), 0);
    const totalRestant = contratsFiltres.reduce(
      (total, contract) => total + resteAEncaisser(contract),
      0,
    );
    const periode = filtres.du || filtres.au
      ? `Du ${filtres.du ? formatDate(filtres.du) : 'début'} au ${filtres.au ? formatDate(filtres.au) : 'aujourd’hui'}`
      : 'Toutes les dates';
    const statut = filtres.statut || 'Tous les statuts';
    const charge = {
      filename: 'Etat_Encaissement_Primes',
      title: 'ÉTAT DES PRIMES À ENCAISSER',
      subtitle: `${periode} - ${filtres.compagnie || 'Toutes les compagnies'}`,
      metadata: {
        'Compagnie': filtres.compagnie || 'Toutes les compagnies',
        'Statut': statut,
        'Recherche': filtres.recherche || 'Aucune',
        'Nombre de contrats': String(contratsFiltres.length),
      },
      headers: ['N° police', 'Souscripteur', 'Compagnie', "Date d'émission", 'N° quittance', 'Prime totale', 'Déjà encaissé', 'Reste à encaisser', 'Statut'],
      rows: contratsFiltres.map((contract) => [
        contract.numeropolice,
        contract.client_nom,
        contract.compagnie,
        dateEmission(contract) ? formatDate(dateEmission(contract)) : '',
        numeroQuittance(contract),
        `${montantFormate(contract.prime_totale)} F`,
        `${montantFormate(contract.montant_encaisse)} F`,
        `${montantFormate(resteAEncaisser(contract))} F`,
        contract.statut_encaissement,
      ]),
      totals: ['TOTAL', '', '', '', '', `${montantFormate(totalPrimes)} F`, `${montantFormate(totalEncaisse)} F`, `${montantFormate(totalRestant)} F`, ''],
    };
    if (format === 'excel') exportToExcel(charge);
    else exportToPdf(charge);
  };

  const champFiltre = (cle) => (e) => setFiltres((actuels) => ({ ...actuels, [cle]: e.target.value }));
  const reinitialiserFiltres = () => setFiltres({ du: '', au: '', compagnie: '', statut: '', recherche: '' });

  const columns = [
    {
      header: 'N° Police',
      accessor: 'numeropolice',
      render: (row) => <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{row.numeropolice}</strong>,
    },
    { header: 'Souscripteur', accessor: 'client_nom' },
    { header: 'Compagnie', accessor: 'compagnie' },
    {
      // Date réelle du contrat en base : normalizeContrat met le 01/01/2026 quand elle manque
      header: "Date d'émission",
      render: (row) => formatDate(row.raw ? (row.raw.dateemission || row.raw.date_emission) : row.date_emission),
    },
    {
      header: 'Prime Totale',
      render: (row) => <span>{row.prime_totale.toLocaleString('fr-FR')} F</span>,
    },
    {
      header: 'Déjà Encaissé',
      render: (row) => <span style={{ color: '#34d399' }}>{row.montant_encaisse.toLocaleString('fr-FR')} F</span>,
    },
    {
      header: 'Reste à Encaisser',
      render: (row) => {
        const reste = resteAEncaisser(row);
        return (
          <strong style={{ color: reste > 0 ? '#fb7185' : '#34d399', fontFamily: 'var(--font-mono)' }}>
            {reste.toLocaleString('fr-FR')} F
          </strong>
        );
      },
    },
    {
      header: 'Statut',
      accessor: 'statut_encaissement',
      render: (row) => <StatusBadge label={row.statut_encaissement} color={row.statut_encaissement === 'Soldé' ? 'emerald' : 'amber'} />,
    },
    {
      header: 'Action',
      render: (row) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button
            className="btn btn-primary"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
            onClick={() => handleOpenPayment(row)}
          >
            <CreditCard size={14} /> Encaisser
          </button>
          {row.montant_encaisse > 0 && (
            <button
              className="btn btn-secondary"
              style={{ padding: '0.35rem 0.55rem', fontSize: '0.75rem' }}
              title="Réimprimer la quittance du dernier règlement"
              onClick={() => handleShowQuittance(row)}
            >
              <Receipt size={14} /> Quittance
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <CreditCard size={26} color="#10b981" />
          Encaissement des Primes
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Enregistrement des règlements (espèces, chèques, virements, Wave / Orange Money DistriPay) et émission des quittances.
        </p>
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

      <div className="glass-panel" style={{ padding: '1.25rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
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
            <label className="form-label" htmlFor="encaissement-statut">Statut</label>
            <select id="encaissement-statut" className="form-control" value={filtres.statut} onChange={champFiltre('statut')}>
              <option value="">Tous les statuts</option>
              <option value="À Encaisser">À encaisser</option>
              <option value="Soldé">Soldé</option>
            </select>
          </div>
          <div style={{ position: 'relative' }}>
            <label className="form-label" htmlFor="encaissement-recherche">Recherche</label>
            <Search size={15} style={{ position: 'absolute', left: 10, bottom: 11, color: 'var(--text-muted)' }} />
            <input id="encaissement-recherche" type="search" className="form-control" style={{ paddingLeft: '2rem' }}
              value={filtres.recherche} onChange={champFiltre('recherche')} placeholder="Police, client, quittance…" />
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-secondary" onClick={reinitialiserFiltres} title="Effacer les filtres">
              <X size={15} /> Réinitialiser
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => exporterEtat('excel')} disabled={!contratsFiltres.length}
              title="Exporter les résultats filtrés en Excel">
              <FileSpreadsheet size={15} /> Excel
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => exporterEtat('pdf')} disabled={!contratsFiltres.length}
              title="Exporter les résultats filtrés en PDF">
              <FileText size={15} /> PDF
            </button>
            <Link to="/user/cash/etat" className="btn btn-primary" title="Consulter l'état détaillé des encaissements">
              <ListChecks size={15} /> États
            </Link>
          </div>
        </div>
        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          {contratsFiltres.length} contrat(s) affiché(s) sur {contracts.length} ; les exports reprennent cette sélection.
        </div>
        <DataTable
          columns={columns}
          data={contratsFiltres}
          searchable={false}
        />
      </div>

      {/* Payment Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={action.titre}>
        {selectedContract && (
          <form onSubmit={handleSavePayment}>
            <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', background: 'rgba(30, 41, 59, 0.6)', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                <span>Police: <strong>{selectedContract.numeropolice}</strong></span>
                <span>Assuré: <strong>{selectedContract.client_nom}</strong></span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', marginTop: '0.35rem' }}>
                <span>Quittance: <strong>{numeroQuittance(selectedContract) || '-'}</strong></span>
                <span>Prime globale: {selectedContract.prime_totale.toLocaleString('fr-FR')} F</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', fontSize: '0.875rem', marginTop: '0.35rem' }}>
                <span>Reste dû: <strong style={{ color: '#fb7185' }}>{resteAEncaisser(selectedContract).toLocaleString('fr-FR')} F</strong></span>
              </div>
            </div>

            <div className="responsive-form-row">
              <div className="form-group">
                <label className="form-label">Montant perçu (FCFA)</label>
                <input
                  type="number"
                  className="form-control"
                  required
                  min="1"
                  value={montantEncaisse}
                  onChange={(e) => setMontantEncaisse(parseInt(e.target.value) || 0)}
                />
              </div>
            </div>

            <ChampsReglement modes={modes} banques={banques} valeurs={reglement} onChange={changerReglement} montantAEncaisser={montantEncaisse} />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                Annuler
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={enregistrement}
                style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}
              >
                <Check size={18} /> {enregistrement ? 'Enregistrement…' : action.bouton}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
};

export default CashCollectionPage;
