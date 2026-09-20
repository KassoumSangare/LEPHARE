import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { DeleteConfirmModal } from '../../../components/common/DeleteConfirmModal';
import { PolicyMovementModal } from './PolicyMovementModal';
import { dataStore } from '../../../api/dataStore';
import { contractApi, quoteApi } from '../../../api/endpoints';
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
  Plane,
  Ship,
  Briefcase,
  Printer,
  Scale,
} from 'lucide-react';

export const ContractListPage = () => {
  const { user } = useAuth();
  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [quotes, setQuotes] = useState([]);
  const [selectedBranchFilter, setSelectedBranchFilter] = useState('ALL');
  const [stats, setStats] = useState({
    ALL: 21714,
    AUTO: 4926,
    SANTE: 8758,
    IA: 3939,
    VOYAGE: 1661,
    TRANSPORT: 1032,
    MRH: 894,
    RC: 504,
  });

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [actionContract, setActionContract] = useState(null);
  const [movementModalTab, setMovementModalTab] = useState('renouvellement');
  const [filterTab, setFilterTab] = useState('all');
  const [deletingContract, setDeletingContract] = useState(null);
  const [deleteValidation, setDeleteValidation] = useState({ allowed: true });
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const getBranchParams = (branch) => {
    switch (branch) {
      case 'AUTO': return { idproduit: 1, page_size: 200 };
      case 'IA': return { idproduit: 2, page_size: 200 };
      case 'VOYAGE': return { idproduit: 3, page_size: 200 };
      case 'MRH': return { idproduit: '4,7,9', page_size: 200 };
      case 'SANTE': return { idproduit: '5,10', page_size: 200 };
      case 'TRANSPORT': return { idproduit: 6, page_size: 200 };
      case 'RC': return { idproduit: 8, page_size: 200 };
      default: return { page_size: 200 };
    }
  };

  const loadStats = async () => {
    try {
      const s = await contractApi.getStats();
      if (s && typeof s === 'object') {
        setStats(s);
      }
    } catch (e) {
      console.warn('Erreur chargement stats contrats:', e);
    }
  };

  const loadContractsData = async (branch = selectedBranchFilter) => {
    setLoading(true);
    try {
      const params = getBranchParams(branch);
      const [backendList, quotesList] = await Promise.all([
        contractApi.getContracts(params),
        quoteApi.getQuotes(),
      ]);
      if (Array.isArray(backendList) && backendList.length > 0) {
        setContracts(backendList);
      } else {
        const local = dataStore.getContracts();
        setContracts(local || []);
      }
      if (Array.isArray(quotesList)) setQuotes(quotesList);
    } catch (err) {
      console.error('Erreur chargement contrats Django:', err);
      const local = dataStore.getContracts();
      setContracts(local || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
    loadContractsData(selectedBranchFilter);
  }, []);

  const handleBranchFilterChange = (branch) => {
    setSelectedBranchFilter(branch);
    loadContractsData(branch);
  };

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

  const countByBranch = {
    ALL: stats.ALL || 21714,
    AUTO: stats.AUTO || 4926,
    SANTE: stats.SANTE || 8758,
    IA: stats.IA || 3939,
    VOYAGE: stats.VOYAGE || 1661,
    TRANSPORT: stats.TRANSPORT || 1032,
    MRH: stats.MRH || 894,
    RC: stats.RC || 504,
  };

  const getTabLabel = (filter) => {
    switch (filter) {
      case 'AUTO': return 'Automobile';
      case 'SANTE': return 'Santé & Vie';
      case 'IA': return 'Individuelle Accidents';
      case 'VOYAGE': return 'Voyage';
      case 'TRANSPORT': return 'Transport';
      case 'MRH': return 'Habitation & Pro';
      case 'RC': return 'Resp. Civile';
      default: return 'Tous';
    }
  };

  const handlePrintContracts = () => {
    if (!contracts || contracts.length === 0) {
      toastError(`Aucun contrat à imprimer pour la sélection ${getTabLabel(selectedBranchFilter)}.`);
      return;
    }

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      toastError('Veuillez autoriser les fenêtres pop-up pour imprimer.');
      return;
    }

    const today = new Date().toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });

    const rowsHtml = filteredContracts.map((c) => `
      <tr>
        <td style="padding: 6px; border: 1px solid #ccc; font-weight: bold; font-family: monospace;">${c.numeropolice || '-'}</td>
        <td style="padding: 6px; border: 1px solid #ccc;">${c.client_nom || '-'}</td>
        <td style="padding: 6px; border: 1px solid #ccc;">${c.produit || '-'}</td>
        <td style="padding: 6px; border: 1px solid #ccc;">${c.compagnie || '-'}</td>
        <td style="padding: 6px; border: 1px solid #ccc;">${c.date_effet || '-'} au ${c.date_expiration || '-'}</td>
        <td style="padding: 6px; border: 1px solid #ccc; text-align: right; font-weight: bold;">${Number(c.prime_totale || 0).toLocaleString()} FCFA</td>
        <td style="padding: 6px; border: 1px solid #ccc;">${c.statut_contrat || c.statut || 'En cours'}</td>
      </tr>
    `).join('');

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Portefeuille des Contrats - ${getTabLabel(selectedBranchFilter)}</title>
          <style>
            body { font-family: Arial, sans-serif; padding: 20px; color: #111; }
            h1 { font-size: 18px; margin-bottom: 4px; }
            .subtitle { font-size: 12px; color: #555; margin-bottom: 15px; }
            table { width: 100%; border-collapse: collapse; font-size: 11px; }
            th { background: #f0f0f0; border: 1px solid #ccc; padding: 6px; text-align: left; }
          </style>
        </head>
        <body>
          <h1>LE PHARE ASSURANCES — Portefeuille des Polices & Contrats</h1>
          <div class="subtitle">Branche: <strong>${getTabLabel(selectedBranchFilter)}</strong> | Édité le: ${today} | Total lignes: ${filteredContracts.length} (sur un total base de ${countByBranch[selectedBranchFilter]?.toLocaleString()} contrats)</div>
          <table>
            <thead>
              <tr>
                <th>N° Police</th>
                <th>Souscripteur</th>
                <th>Produit</th>
                <th>Compagnie</th>
                <th>Période de Validité</th>
                <th>Prime Totale TTC</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>
          <script>
            window.onload = function() { window.print(); };
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

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
      render: (row) => <strong style={{ color: '#fff' }}>{Number(row.prime_totale || 0).toLocaleString()} F</strong>,
    },
    {
      header: 'Règlement',
      accessor: 'statut_encaissement',
      render: (row) => <StatusBadge label={row.statut_encaissement || 'Soldé'} color={row.statut_encaissement === 'Soldé' ? 'emerald' : 'amber'} />,
    },
    {
      header: 'Actions Mouvements & Police',
      render: (row) => {
        const canTerminate = canUser(user, 'terminate', 'contracts');
        const canDelete = canUser(user, 'delete', 'contracts');
        const isResilie = row.statut_contrat === 'Résilié' || row.statut === 'Résilié';

        return (
          <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center', flexWrap: 'wrap' }}>
            {/* 1. RENOUVELER */}
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
                borderColor: isResilie ? 'transparent' : 'rgba(245, 158, 11, 0.3)',
                cursor: isResilie || !canTerminate ? 'not-allowed' : 'pointer',
              }}
              onClick={() => {
                setActionContract(row);
                setMovementModalTab('resiliation');
              }}
              title={
                !canTerminate
                  ? 'Permission CIMA insuffisante pour résilier un contrat'
                  : 'Résilier le contrat (Article 13 CIMA)'
              }
            >
              <Ban size={13} />
              <span>Résilier</span>
            </button>

            {/* 6. SUPPRESSION / CONTRÔLE CIMA */}
            <button
              className="btn btn-secondary"
              disabled={!canDelete}
              style={{
                padding: '0.3rem 0.45rem',
                fontSize: '0.75rem',
                color: '#ef4444',
                borderColor: 'rgba(239, 68, 68, 0.3)',
                cursor: !canDelete ? 'not-allowed' : 'pointer',
              }}
              onClick={() => {
                const val = validateBusinessRule('DELETE_CONTRACT', row);
                setDeleteValidation(val);
                setDeletingContract(row);
              }}
              title={
                !canDelete
                  ? 'Permission CIMA insuffisante'
                  : 'Vérifier et supprimer le contrat (Contrôle CIMA)'
              }
            >
              <Trash2 size={13} />
            </button>
          </div>
        );
      },
    },
  ];

  const branchFilters = [
    { key: 'ALL', label: 'Toutes les branches', icon: Layers, count: countByBranch.ALL },
    { key: 'AUTO', label: 'Automobile', icon: Car, count: countByBranch.AUTO },
    { key: 'SANTE', label: 'Santé & Prévoyance', icon: HeartPulse, count: countByBranch.SANTE },
    { key: 'IA', label: 'Individuelle Accidents', icon: Activity, count: countByBranch.IA },
    { key: 'VOYAGE', label: 'Voyage', icon: Plane, count: countByBranch.VOYAGE },
    { key: 'TRANSPORT', label: 'Transport', icon: Ship, count: countByBranch.TRANSPORT },
    { key: 'MRH', label: 'Habitation & Pro', icon: Home, count: countByBranch.MRH },
    { key: 'RC', label: 'Resp. Civile', icon: Scale, count: countByBranch.RC },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <ShieldCheck size={24} color="#34d399" />
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800 }}>Portefeuille des Contrats & Polices Actives</h1>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Gestion intégrale du parc de contrats, avenants, renouvellements et attestations CIMA.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handlePrintContracts}
            title="Imprimer l'état du portefeuille pour cette branche"
          >
            <Printer size={16} />
            <span>Imprimer l'état ({filteredContracts.length})</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              loadStats();
              loadContractsData(selectedBranchFilter);
            }}
            title="Rafraîchir les données depuis la base PostgreSQL"
          >
            <RefreshCw size={16} />
            <span>Actualiser</span>
          </button>

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setIsModalOpen(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <Plus size={16} />
            <span>Émettre Police</span>
          </button>
        </div>
      </div>

      {/* KPI Cards connectées aux vrais chiffres de la base */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <div className="card" style={{ padding: '1.25rem', borderLeft: '4px solid #10b981', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981' }}>
            <ShieldCheck size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Total Polices en BDD</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#10b981' }}>{countByBranch.ALL.toLocaleString()}</div>
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem', borderLeft: '4px solid #3b82f6', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: 'rgba(59, 130, 246, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#3b82f6' }}>
            <Car size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Contrats Automobile</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#3b82f6' }}>{countByBranch.AUTO.toLocaleString()}</div>
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem', borderLeft: '4px solid #ec4899', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: 'rgba(236, 72, 153, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ec4899' }}>
            <HeartPulse size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Santé & Prévoyance</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ec4899' }}>{countByBranch.SANTE.toLocaleString()}</div>
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem', borderLeft: '4px solid #f59e0b', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: 'rgba(245, 158, 11, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f59e0b' }}>
            <Activity size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Autres Risques CIMA</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f59e0b' }}>
              {(countByBranch.ALL - countByBranch.AUTO - countByBranch.SANTE).toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Onglets Filtres par Branche (Directement branchés sur PostgreSQL) */}
      <div
        style={{
          display: 'flex',
          gap: '0.5rem',
          flexWrap: 'wrap',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '0.5rem',
        }}
      >
        {branchFilters.map((tab) => {
          const Icon = tab.icon;
          const isActive = selectedBranchFilter === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => handleBranchFilterChange(tab.key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.5rem 0.85rem',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.82rem',
                fontWeight: isActive ? 700 : 500,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                border: isActive ? '1px solid #3b82f6' : '1px solid transparent',
                background: isActive ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                color: isActive ? '#60a5fa' : 'var(--text-secondary)',
              }}
            >
              <Icon size={15} />
              <span>{tab.label}</span>
              <span
                style={{
                  fontSize: '0.72rem',
                  padding: '0.1rem 0.45rem',
                  borderRadius: '999px',
                  background: isActive ? '#3b82f6' : 'rgba(255, 255, 255, 0.08)',
                  color: isActive ? '#fff' : 'var(--text-muted)',
                  fontWeight: 600,
                }}
              >
                {tab.count?.toLocaleString()}
              </span>
            </button>
          );
        })}
      </div>

      {/* Main Table Card */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className={`btn ${filterTab === 'all' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.8rem', padding: '0.35rem 0.85rem' }}
              onClick={() => setFilterTab('all')}
            >
              Tous les contrats ({filteredContracts.length})
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

          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Affichage des {filteredContracts.length} premiers contrats ({getTabLabel(selectedBranchFilter)})
          </div>
        </div>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <RefreshCw size={24} className="animate-spin" />
            <span style={{ marginLeft: '0.5rem' }}>Chargement des contrats depuis PostgreSQL...</span>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={filteredContracts}
            searchPlaceholder="Rechercher par n° police, souscripteur, produit ou compagnie..."
          />
        )}
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
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{q.produit} ({q.compagnie}) — <strong style={{ color: '#34d399' }}>{q.prime_totale.toLocaleString()} F</strong></div>
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
        onSuccess={() => {
          loadContractsData(selectedBranchFilter);
          loadStats();
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
              loadContractsData(selectedBranchFilter);
              loadStats();
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
