import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { DeleteConfirmModal } from '../../../components/common/DeleteConfirmModal';
import { PolicyMovementModal } from './PolicyMovementModal';
import { dataStore } from '../../../api/dataStore';
import { contractApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { useAuth } from '../../../context/AuthContext';
import { canUser, validateBusinessRule } from '../../../utils/rbac';
import {
  ShieldCheck,
  Eye,
  RefreshCw,
  Car,
  Plus,
  ArrowRight,
  FileCheck,
  Home,
  HeartPulse,
  Activity,
  Layers,
  ShieldAlert,
  Ban,
  Trash2,
  Archive,
  FileText,
  Sparkles,
  Calendar,
  AlertCircle,
} from 'lucide-react';

export const ContractListPage = () => {
  const { user } = useAuth();
  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [quotes, setQuotes] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [actionContract, setActionContract] = useState(null);
  const [movementModalTab, setMovementModalTab] = useState('renouvellement');
  const [filterTab, setFilterTab] = useState('all');
  const [deletingContract, setDeletingContract] = useState(null);
  const [deleteValidation, setDeleteValidation] = useState({ allowed: true });
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const loadContractsData = async () => {
    try {
      const [backendList, quotesList] = await Promise.all([
        contractApi.getContracts(),
        quoteApi.getQuotes(),
      ]);
      if (Array.isArray(backendList)) setContracts(backendList);
      if (Array.isArray(quotesList)) setQuotes(quotesList);
    } catch (err) {
      console.error('Erreur chargement contrats Django:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContractsData();
  }, []);

  const validatedQuotes = quotes.filter((q) => q.statut !== 'Consolidé');

  const isExpiredOrDue = (dateStr) => {
    if (!dateStr) return false;
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return false;
    const now = new Date();
    const diffDays = (d - now) / (1000 * 60 * 60 * 24);
    return diffDays <= 30; // Expired or expiring in 30 days
  };

  const filteredContracts = contracts.filter((c) => {
    if (filterTab === 'active') return c.statut_contrat === 'En cours' || c.statut === 'En cours';
    if (filterTab === 'renewable') return isExpiredOrDue(c.date_expiration);
    if (filterTab === 'terminated') return c.statut_contrat === 'Résilié' || c.statut === 'Résilié' || c.statut_contrat?.includes('Annulé');
    return true;
  });

  const activeCount = contracts.filter((c) => c.statut_contrat === 'En cours' || c.statut === 'En cours').length;
  const renewableCount = contracts.filter((c) => isExpiredOrDue(c.date_expiration)).length;
  const terminatedCount = contracts.filter((c) => c.statut_contrat === 'Résilié' || c.statut === 'Résilié' || c.statut_contrat?.includes('Annulé')).length;

  const columns = [
    {
      header: 'N° Police',
      accessor: 'numeropolice',
      render: (row) => (
        <div>
          <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{row.numeropolice}</strong>
          {row.dernier_avenant && (
            <div style={{ fontSize: '0.7rem', color: '#60a5fa' }}>{row.dernier_avenant}</div>
          )}
        </div>
      ),
    },
    {
      header: 'Souscripteur',
      accessor: 'client_nom',
      render: (row) => <div style={{ fontWeight: 600, color: '#fff' }}>{row.client_nom}</div>,
    },
    { header: 'Produit', accessor: 'produit' },
    { header: 'Compagnie', accessor: 'compagnie' },
    {
      header: 'Période de Validité',
      render: (row) => {
        const isNearDue = isExpiredOrDue(row.date_expiration);
        return (
          <div style={{ fontSize: '0.8rem' }}>
            Du {row.date_effet} au{' '}
            <span style={{ color: isNearDue ? '#f59e0b' : '#60a5fa', fontWeight: isNearDue ? 700 : 400 }}>
              {row.date_expiration}
            </span>
            {isNearDue && (
              <span
                style={{
                  display: 'inline-block',
                  marginLeft: '0.35rem',
                  padding: '0.1rem 0.35rem',
                  fontSize: '0.65rem',
                  borderRadius: '4px',
                  background: 'rgba(245, 158, 11, 0.15)',
                  color: '#f59e0b',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                }}
              >
                Échéance
              </span>
            )}
          </div>
        );
      },
    },
    {
      header: 'Prime Totale',
      render: (row) => <strong style={{ color: '#fff' }}>{row.prime_totale.toLocaleString()} F</strong>,
    },
    {
      header: 'Règlement',
      accessor: 'statut_encaissement',
      render: (row) => <StatusBadge label={row.statut_encaissement} color={row.statut_encaissement === 'Soldé' ? 'emerald' : 'amber'} />,
    },
    {
      header: 'Actions Mouvements & Police',
      render: (row) => {
        const canTerminate = canUser(user, 'terminate', 'contracts');
        const canDelete = canUser(user, 'delete', 'contracts');
        const isResilie = row.statut_contrat === 'Résilié' || row.statut === 'Résilié';

        return (
          <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center', flexWrap: 'wrap' }}>
            {/* 1. RENOUVELER (Action mise en avant selon demande utilisateur) */}
            <button
              className="btn"
              style={{
                padding: '0.3rem 0.6rem',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                background: 'linear-gradient(135deg, #059669, #10b981)',
                color: '#ffffff',
                border: 'none',
                fontWeight: 600,
                borderRadius: 'var(--radius-sm)',
                boxShadow: '0 2px 6px rgba(16, 185, 129, 0.3)',
                cursor: 'pointer',
              }}
              onClick={() => {
                setActionContract(row);
                setMovementModalTab('renouvellement');
              }}
              title="Renouveler la police, proroger la période et imprimer le certificat officiel CIMA"
            >
              <RefreshCw size={13} />
              <span>Renouveler</span>
            </button>

            {/* 2. AVENANT */}
            <button
              className="btn btn-secondary"
              style={{
                padding: '0.3rem 0.55rem',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                color: '#60a5fa',
                borderColor: 'rgba(96, 165, 250, 0.3)',
              }}
              onClick={() => {
                setActionContract(row);
                setMovementModalTab('avenant');
              }}
              title="Émettre un avenant (changement plaque, garanties, adjonction)"
            >
              <FileText size={13} />
              <span>Avenant</span>
            </button>

            {/* 3. TRANSFORMATION */}
            <button
              className="btn btn-secondary"
              style={{
                padding: '0.3rem 0.5rem',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                color: '#c084fc',
                borderColor: 'rgba(192, 132, 252, 0.3)',
              }}
              onClick={() => {
                setActionContract(row);
                setMovementModalTab('transformation');
              }}
              title="Transformer la police (surclassement formule, changement compagnie)"
            >
              <Sparkles size={13} />
              <span>Transf.</span>
            </button>

            {/* 4. FICHE POLICE & QUITTANCES */}
            <button
              className="btn btn-secondary"
              style={{ padding: '0.3rem 0.55rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
              onClick={() => navigate(`/user/contracts/${row.id}`)}
              title="Consulter la fiche police, quittance et historique"
            >
              <Eye size={13} />
              <span>Fiche</span>
            </button>

            {/* 5. RESILIATION */}
            <button
              className="btn btn-secondary"
              disabled={isResilie || !canTerminate}
              style={{
                padding: '0.3rem 0.55rem',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                color: isResilie ? 'var(--text-muted)' : '#f59e0b',
                borderColor: isResilie ? 'var(--border-subtle)' : 'rgba(245, 158, 11, 0.3)',
                opacity: (!isResilie && canTerminate) ? 1 : 0.45,
                cursor: (!isResilie && canTerminate) ? 'pointer' : 'not-allowed',
              }}
              onClick={() => {
                setActionContract(row);
                setMovementModalTab('resiliation');
              }}
              title={isResilie ? 'Police déjà résiliée' : (canTerminate ? 'Résilier la police (Art. 13 CIMA)' : 'Non habilité')}
            >
              <Ban size={13} />
              <span>{isResilie ? 'Résilié' : 'Résilier'}</span>
            </button>

            {/* 6. ARCHIVAGE / CONTRÔLE CIMA */}
            <button
              className="btn btn-secondary"
              style={{
                padding: '0.3rem 0.55rem',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                color: '#38bdf8',
                borderColor: 'rgba(56, 189, 248, 0.25)',
              }}
              onClick={() => {
                const check = validateBusinessRule('delete', 'contracts', row, dataStore);
                setDeleteValidation(check);
                setDeletingContract(row);
              }}
              title="Archiver / Contrôle CIMA de la police"
            >
              <Archive size={13} />
              <span>Archiver</span>
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div className="responsive-header">
        <div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <ShieldCheck size={26} color="#10b981" />
            Portefeuille des Contrats & Polices Actives
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Renouvellements avec impression de certificat CIMA, avenants, transformations et suivi des échéances.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/user/endorsements')}>
            <FileText size={16} color="#60a5fa" />
            <span>Registre des Avenants</span>
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/user/asaci')}>
            <Car size={16} />
            <span>Attestations ASACI</span>
          </button>
          <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
            <Plus size={16} />
            <span>Émettre un Contrat</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>TOTAL POLICES EN COURS</span>
            <ShieldCheck size={18} color="#10b981" />
          </div>
          <div className="metric-value">{contracts.length}</div>
          <span style={{ fontSize: '0.75rem', color: '#34d399' }}>{activeCount} polices actuellement actives</span>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>À RENOUVELER / ÉCHÉANCES</span>
            <RefreshCw size={18} color="#f59e0b" />
          </div>
          <div className="metric-value" style={{ color: '#f59e0b' }}>{renewableCount}</div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Échues ou échéance dans les 30 jours</span>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>VOLUME PRIMES ÉMISES</span>
            <Layers size={18} color="#3b82f6" />
          </div>
          <div className="metric-value">
            {(contracts.reduce((acc, c) => acc + (c.prime_totale || 0), 0) / 1000000).toFixed(1)} M FCFA
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Chiffre d'affaires portefeuille</span>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>DEVIS PRÊTS À ÉMETTRE</span>
            <FileCheck size={18} color="#10b981" />
          </div>
          <div className="metric-value">{validatedQuotes.length}</div>
          <span style={{ fontSize: '0.75rem', color: '#34d399' }}>En attente de confirmation</span>
        </div>
      </div>

      {/* Main Table with Filter Tabs */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        {/* Quick Filter Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.75rem' }}>
          <button
            type="button"
            className={`btn ${filterTab === 'all' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.8rem', padding: '0.35rem 0.85rem' }}
            onClick={() => setFilterTab('all')}
          >
            Toutes ({contracts.length})
          </button>
          <button
            type="button"
            className={`btn ${filterTab === 'active' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.8rem', padding: '0.35rem 0.85rem' }}
            onClick={() => setFilterTab('active')}
          >
            En cours ({activeCount})
          </button>
          <button
            type="button"
            className={`btn ${filterTab === 'renewable' ? 'btn-primary' : 'btn-secondary'}`}
            style={{
              fontSize: '0.8rem',
              padding: '0.35rem 0.85rem',
              borderColor: filterTab === 'renewable' ? '#f59e0b' : 'rgba(245, 158, 11, 0.4)',
              color: filterTab === 'renewable' ? '#fff' : '#f59e0b',
              background: filterTab === 'renewable' ? '#d97706' : '',
            }}
            onClick={() => setFilterTab('renewable')}
          >
            À Renouveler / Échues ({renewableCount})
          </button>
          <button
            type="button"
            className={`btn ${filterTab === 'terminated' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.8rem', padding: '0.35rem 0.85rem' }}
            onClick={() => setFilterTab('terminated')}
          >
            Résiliées ({terminatedCount})
          </button>
        </div>

        <DataTable
          columns={columns}
          data={filteredContracts}
          searchPlaceholder="Rechercher par n° police, souscripteur, produit ou compagnie..."
        />
      </div>

      {/* Modal Émettre un Contrat */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Émission d'une Nouvelle Police d'Assurance">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Option A: Convert existing quote */}
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#60a5fa', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileCheck size={18} />
              Option 1 : Émettre depuis un Devis Validé ({validatedQuotes.length} en attente)
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
              Transformez instantanément une proposition d'assurance validée en contrat définitif.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '180px', overflowY: 'auto' }}>
              {validatedQuotes.slice(0, 3).map((q) => (
                <div
                  key={q.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.75rem 1rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.85rem' }}>{q.numerodevis} - {q.client_nom}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{q.produit} ({q.compagnie}) • <strong style={{ color: '#34d399' }}>{q.prime_totale.toLocaleString()} F</strong></div>
                  </div>
                  <button
                    className="btn btn-primary"
                    style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
                    onClick={() => {
                      const { contract } = dataStore.convertQuoteToContract(q);
                      setContracts(dataStore.getContracts());
                      setQuotes(dataStore.getQuotes());
                      setIsModalOpen(false);
                      success(`Police N° ${contract.numeropolice} émise pour ${contract.client_nom} !`);
                    }}
                  >
                    <span>Émettre Police</span>
                    <ArrowRight size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)' }}></div>

          {/* Option B: New quotation */}
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#34d399', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Plus size={18} />
              Option 2 : Saisir une Nouvelle Souscription (Simulateurs)
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
              Créez une nouvelle affaire directe selon la branche du risque :
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem' }}>
              <button
                className="btn btn-secondary"
                style={{ display: 'flex', flexDirection: 'column', padding: '1rem', height: 'auto', gap: '0.5rem', textAlign: 'center' }}
                onClick={() => {
                  setIsModalOpen(false);
                  navigate('/user/quotes/auto');
                }}
              >
                <Car size={22} color="#3b82f6" />
                <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Automobile</span>
              </button>

              <button
                className="btn btn-secondary"
                style={{ display: 'flex', flexDirection: 'column', padding: '1rem', height: 'auto', gap: '0.5rem', textAlign: 'center' }}
                onClick={() => {
                  setIsModalOpen(false);
                  navigate('/user/quotes/mrh');
                }}
              >
                <Home size={22} color="#0ea5e9" />
                <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Habitation MRH</span>
              </button>

              <button
                className="btn btn-secondary"
                style={{ display: 'flex', flexDirection: 'column', padding: '1rem', height: 'auto', gap: '0.5rem', textAlign: 'center' }}
                onClick={() => {
                  setIsModalOpen(false);
                  navigate('/user/quotes/sante');
                }}
              >
                <HeartPulse size={22} color="#f43f5e" />
                <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Santé Groupe</span>
              </button>

              <button
                className="btn btn-secondary"
                style={{ display: 'flex', flexDirection: 'column', padding: '1rem', height: 'auto', gap: '0.5rem', textAlign: 'center' }}
                onClick={() => {
                  setIsModalOpen(false);
                  navigate('/user/quotes/ia');
                }}
              >
                <Activity size={22} color="#a855f7" />
                <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Individuelle IA</span>
              </button>
            </div>
          </div>
        </div>
      </Modal>

      {/* Modal Mouvements de Police CIMA (Renouvellement, Avenant, Transformation, Résiliation) */}
      <PolicyMovementModal
        isOpen={!!actionContract}
        onClose={() => setActionContract(null)}
        contract={actionContract}
        initialTab={movementModalTab}
        onSuccess={(updated) => {
          setContracts(dataStore.getContracts());
        }}
      />

      {/* Modal Alerte Suppression CIMA */}
      <DeleteConfirmModal
        isOpen={!!deletingContract}
        onClose={() => setDeletingContract(null)}
        itemType="contrat"
        itemName={`Police d'assurance ${deletingContract?.numeropolice} (${deletingContract?.client_nom})`}
        itemCode={deletingContract?.numeropolice}
        validation={deleteValidation}
        alternativeLabel="Résilier la Police (Art. 13)"
        onAlternativeAction={() => {
          if (deletingContract) {
            const target = deletingContract;
            setDeletingContract(null);
            setActionContract(target);
          }
        }}
        onConfirm={() => {
          if (deletingContract) {
            try {
              dataStore.deleteContract(deletingContract.id);
            } catch (err) {
              toastError(err.message);
            }
          }
        }}
      />
    </div>
  );
};

export default ContractListPage;
