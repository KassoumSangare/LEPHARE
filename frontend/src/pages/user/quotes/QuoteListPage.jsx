import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { DeleteConfirmModal } from '../../../components/common/DeleteConfirmModal';
import { EditQuoteModal } from './EditQuoteModal';
import { ViewQuoteModal } from './ViewQuoteModal';
import { SubscriptionIssuanceModal } from './SubscriptionIssuanceModal';
import { dataStore } from '../../../api/dataStore';
import { quoteApi, contractApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { useAuth } from '../../../context/AuthContext';
import { canUser, validateBusinessRule } from '../../../utils/rbac';
import { exportToPdf } from '../../../utils/exportUtils';
import {
  FileText,
  Plus,
  CheckCircle,
  Car,
  Home,
  HeartPulse,
  Edit2,
  Trash2,
  Archive,
  Plane,
  Ship,
  UserPlus,
  Eye,
  TrendingUp,
  Layers,
  Clock,
  CheckCheck,
  Printer,
} from 'lucide-react';

const formatDateTime = (value) => {
  if (!value) return '-';
  const d = new Date(value);
  if (isNaN(d.getTime())) return String(value);
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}:${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

export const QuoteListPage = () => {
  const { user } = useAuth();
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBranchFilter, setSelectedBranchFilter] = useState('ALL');
  const [selectedQuote, setSelectedQuote] = useState(null);
  const [viewingQuote, setViewingQuote] = useState(null);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [editingQuote, setEditingQuote] = useState(null);
  const [deletingQuote, setDeletingQuote] = useState(null);
  const [deleteValidation, setDeleteValidation] = useState({ allowed: true });
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const loadQuotes = async () => {
    setLoading(true);
    try {
      const backendQuotes = await quoteApi.getQuotes();
      if (Array.isArray(backendQuotes) && backendQuotes.length > 0) {
        setQuotes(backendQuotes);
      } else {
        const local = dataStore.getQuotes();
        setQuotes(local || []);
      }
    } catch (err) {
      console.error('Erreur chargement devis Django:', err);
      const local = dataStore.getQuotes();
      setQuotes(local || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuotes();
  }, []);

  const handleConvertContract = (quote) => {
    setSelectedQuote(quote);
    setIsConfirmModalOpen(true);
  };

  const confirmConversion = async () => {
    if (!selectedQuote) return;
    try {
      const res = await contractApi.createContractFromQuote(selectedQuote.id);
      success(`Devis ${selectedQuote.numerodevis} converti avec succès en contrat définitif dans Django !`);
      setIsConfirmModalOpen(false);
      navigate('/user/contracts');
    } catch (err) {
      toastError(err.response?.data?.detail || err.response?.data?.message || 'Erreur lors de la confirmation du devis sur Django');
      setIsConfirmModalOpen(false);
    }
  };

    // Branch and status filtering
  const filteredQuotes = quotes.filter((q) => {
    if (selectedBranchFilter === 'ALL') return true;
    const statutLower = (q.statut || '').toLowerCase();
    if (selectedBranchFilter === 'CONSOLIDATED') return statutLower.includes('consolid') || statutLower.includes('confirm') || q.confirme;
    const b = (q.branche || '').toLowerCase();
    const p = (q.produit || '').toLowerCase();
    if (selectedBranchFilter === 'AUTO') return b.includes('auto') || p.includes('auto');
    if (selectedBranchFilter === 'VOYAGE') return b.includes('voyag') || p.includes('voyag');
    if (selectedBranchFilter === 'TRANSPORT') return b.includes('transp') || p.includes('transp');
    if (selectedBranchFilter === 'MRH') return b.includes('mrh') || b.includes('habit') || p.includes('mrh') || p.includes('habit') || p.includes('profess');
    if (selectedBranchFilter === 'SANTE') return b.includes('sant') || b.includes('maladie') || p.includes('sant') || p.includes('vie');
    if (selectedBranchFilter === 'IA') return b.includes('ia') || b.includes('accident') || p.includes('ia') || p.includes('accident') || p.includes('civil');
    return true;
  });

  // Dynamic KPI Metrics
  const totalDevis = quotes.length;
  const totalPrimesCotees = quotes.reduce((acc, q) => acc + Number(q.prime_totale || 0), 0);
  const totalConsolides = quotes.filter((q) => {
    const s = (q.statut || '').toLowerCase();
    return s.includes('consolid') || s.includes('confirm') || q.confirme;
  }).length;
  const totalEnAttente = Math.max(0, totalDevis - totalConsolides);
  const tauxConversion = totalDevis > 0 ? Math.round((totalConsolides / totalDevis) * 100) : 0;

  // Counts per branch
  const countByBranch = {
    AUTO: quotes.filter((q) => (q.branche || '').toLowerCase().includes('auto') || (q.produit || '').toLowerCase().includes('auto')).length,
    VOYAGE: quotes.filter((q) => (q.branche || '').toLowerCase().includes('voyag') || (q.produit || '').toLowerCase().includes('voyag')).length,
    TRANSPORT: quotes.filter((q) => (q.branche || '').toLowerCase().includes('transp') || (q.produit || '').toLowerCase().includes('transp')).length,
    MRH: quotes.filter((q) => (q.branche || '').toLowerCase().includes('mrh') || (q.produit || '').toLowerCase().includes('mrh') || (q.produit || '').toLowerCase().includes('habit') || (q.produit || '').toLowerCase().includes('profess')).length,
    SANTE: quotes.filter((q) => (q.branche || '').toLowerCase().includes('sant') || (q.produit || '').toLowerCase().includes('sant') || (q.produit || '').toLowerCase().includes('maladie') || (q.produit || '').toLowerCase().includes('vie')).length,
    IA: quotes.filter((q) => (q.branche || '').toLowerCase().includes('ia') || (q.produit || '').toLowerCase().includes('ia') || (q.produit || '').toLowerCase().includes('accident') || (q.produit || '').toLowerCase().includes('civil')).length,
  };

  const getTabLabel = (filter) => {
    switch (filter) {
      case 'AUTO': return 'Auto';
      case 'VOYAGE': return 'Voyage';
      case 'TRANSPORT': return 'Transport';
      case 'MRH': return 'MRH';
      case 'SANTE': return 'Santé';
      case 'IA': return 'IA';
      case 'CONSOLIDATED': return 'Consolidés';
      default: return 'Tous';
    }
  };

  const handlePrintQuotes = (specificBranch = null) => {
    const branchToUse = specificBranch || selectedBranchFilter;
    let listToPrint = quotes;
    if (branchToUse !== 'ALL') {
      const statutLower = (q) => (q.statut || '').toLowerCase();
      if (branchToUse === 'CONSOLIDATED') {
        listToPrint = quotes.filter((q) => statutLower(q).includes('consolid') || statutLower(q).includes('confirm') || q.confirme);
      } else {
        listToPrint = quotes.filter((q) => {
          const b = (q.branche || '').toLowerCase();
          const p = (q.produit || '').toLowerCase();
          if (branchToUse === 'AUTO') return b.includes('auto') || p.includes('auto');
          if (branchToUse === 'VOYAGE') return b.includes('voyag') || p.includes('voyag');
          if (branchToUse === 'TRANSPORT') return b.includes('transp') || p.includes('transp');
          if (branchToUse === 'MRH') return b.includes('mrh') || b.includes('habit') || p.includes('mrh') || p.includes('habit') || p.includes('profess');
          if (branchToUse === 'SANTE') return b.includes('sant') || b.includes('maladie') || p.includes('sant') || p.includes('vie');
          if (branchToUse === 'IA') return b.includes('ia') || b.includes('accident') || p.includes('ia') || p.includes('accident') || p.includes('civil');
          return true;
        });
      }
    }

    if (!listToPrint || listToPrint.length === 0) {
      toastError(`Aucun devis à imprimer pour ${getTabLabel(branchToUse)}.`);
      return;
    }

    const today = new Date().toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });

    // Colonnes utiles épurées : N° Devis, Client, Branche / Produit, Compagnie, Date Émission, Prime Totale TTC, Statut
    const headers = [
      'N° Devis',
      'Client / Souscripteur',
      'Branche / Produit',
      'Compagnie',
      'Date Émission',
      'Prime Totale TTC',
      'Statut',
    ];

    const rows = listToPrint.map((q) => {
      const branchProd = [q.branche, q.produit].filter(Boolean).join(' - ') || (q.produit || 'Auto');
      const prime = `${Number(q.prime_totale || 0).toLocaleString()} FCFA`;
      return [
        q.numerodevis || `DEV-${q.id}`,
        q.client_nom || q.nomcomplet || 'Client Particulier',
        branchProd,
        q.compagnie || 'LE PHARE',
        formatDateTime(q.date_emission),
        prime,
        q.statut || 'En cours',
      ];
    });

    const totalMontant = listToPrint.reduce((acc, q) => acc + Number(q.prime_totale || 0), 0);
    const tabName = getTabLabel(branchToUse);

    exportToPdf({
      filename: `Registre_Devis_${tabName}_LE_PHARE_${new Date().toISOString().slice(0, 10)}.pdf`,
      title: `REGISTRE OFFICIEL DES DEVIS & PROPOSITIONS [${tabName.toUpperCase()}]`,
      subtitle: branchToUse !== 'ALL' ? `Branche / Catégorie : ${tabName} — Conforme aux normes d'audit CIMA` : 'État global de souscription conforme aux normes CIMA',
      metadata: {
        'Date d\'édition': today,
        'Édité par': user?.nom ? `${user.nom} (${user.email || ''})` : (user?.email || 'Gestionnaire'),
        'Catégorie': tabName,
        'Nombre de devis': `${listToPrint.length} propositions`,
        'Total Primes Cotées': `${totalMontant.toLocaleString()} FCFA`,
        'Base de données': 'LE PHARE Assurances',
      },
      headers,
      rows,
      totals: [
        'TOTAL GLOBAL',
        `${listToPrint.length} Devis`,
        '-',
        '-',
        '-',
        `${totalMontant.toLocaleString()} FCFA`,
        '-',
      ],
    });
  };

  const columns = [
    {
      header: 'N° Devis',
      accessor: 'numerodevis',
      sortable: true,
      render: (row) => (
        <span
          style={{ color: '#60a5fa', fontFamily: 'var(--font-mono)', fontWeight: 700, cursor: 'pointer' }}
          onClick={() => setViewingQuote(row)}
          title="Cliquer pour afficher la fiche complète"
        >
          {row.numerodevis}
        </span>
      ),
    },
    {
      header: 'Assuré / Souscripteur',
      accessor: 'client_nom',
      sortable: true,
      render: (row) => <div style={{ fontWeight: 600, color: '#fff' }}>{row.client_nom}</div>,
    },
    {
      header: 'Branche / Produit',
      accessor: 'produit',
      sortable: true,
      sortAccessor: (row) => row.branche || row.produit || '',
      render: (row) => {
        const b = String(row.branche || '').toLowerCase();
        let color = '#3b82f6';
        let bg = 'rgba(59, 130, 246, 0.12)';
        let label = row.branche || 'Auto';
        if (b.includes('voyag')) { color = '#38bdf8'; bg = 'rgba(56, 189, 248, 0.12)'; label = 'Voyage'; }
        else if (b.includes('transp')) { color = '#0284c7'; bg = 'rgba(2, 132, 199, 0.12)'; label = 'Transport'; }
        else if (b.includes('mrh') || b.includes('habit')) { color = '#0ea5e9'; bg = 'rgba(14, 165, 233, 0.12)'; label = 'MRH'; }
        else if (b.includes('sant')) { color = '#f43f5e'; bg = 'rgba(244, 63, 94, 0.12)'; label = 'Santé'; }
        else if (b.includes('ia') || b.includes('accident')) { color = '#8b5cf6'; bg = 'rgba(139, 92, 246, 0.12)'; label = 'IA'; }

        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.85rem' }}>{row.produit}</span>
            <span
              style={{
                width: 'fit-content',
                fontSize: '0.7rem',
                fontWeight: 600,
                color,
                background: bg,
                padding: '0.1rem 0.45rem',
                borderRadius: '4px',
                border: `1px solid ${color}33`,
              }}
            >
              {label}
            </span>
          </div>
        );
      },
    },
    { header: 'Compagnie', accessor: 'compagnie', sortable: true },
    {
      header: 'Émission',
      accessor: 'date_emission',
      sortable: true,
      sortAccessor: (row) => {
        const t = row.date_emission ? new Date(row.date_emission).getTime() : NaN;
        return isNaN(t) ? row.date_emission || '' : t;
      },
      render: (row) => <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{formatDateTime(row.date_emission)}</span>,
    },
    {
      header: 'Prime Totale TTC',
      accessor: 'prime_totale',
      render: (row) => <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{Number(row.prime_totale || 0).toLocaleString()} FCFA</strong>,
    },
    {
      header: 'Statut',
      accessor: 'statut',
      render: (row) => <StatusBadge label={row.statut} color={row.statut_badge} />,
    },
    {
      header: 'Actions',
      render: (row) => {
        const canEdit = canUser(user, 'edit', 'quotes');
        const canDelete = canUser(user, 'delete', 'quotes');
        const isConsolidated = row.statut === 'Consolidé';

        return (
          <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
            {/* View / Print Full Sheet */}
            <button
              type="button"
              className="btn btn-secondary"
              style={{
                padding: '0.3rem 0.55rem',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                color: '#38bdf8',
                borderColor: 'rgba(56, 189, 248, 0.3)',
              }}
              onClick={() => setViewingQuote(row)}
              title="Consulter l'intégralité du devis et imprimer la proposition"
            >
              <Eye size={13} />
              <span>Consulter</span>
            </button>

            {!isConsolidated && (() => {
              const todayStr = new Date().toISOString().split('T')[0];
              const isExpired = row.date_expiration ? new Date(row.date_expiration) < new Date(todayStr) : false;
              const isPendingApproval = row.circuit_approbation && row.circuit_approbation.statut_validation === 'EN_ATTENTE_DIRECTION';

              return (
                <button
                  className="btn btn-primary"
                  disabled={isExpired || isPendingApproval}
                  style={{
                    padding: '0.3rem 0.6rem',
                    fontSize: '0.75rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                    background: (isExpired || isPendingApproval) ? '#475569' : '#059669',
                    borderColor: (isExpired || isPendingApproval) ? '#475569' : '#059669',
                    cursor: (isExpired || isPendingApproval) ? 'not-allowed' : 'pointer',
                  }}
                  onClick={() => handleConvertContract(row)}
                  title={
                    isExpired
                      ? 'Devis expiré : conversion bloquée (CA-07.3)'
                      : isPendingApproval
                      ? 'Visa Direction Requis avant émission (CA-07.4)'
                      : 'Souscrire & Émettre la police définitive (E08)'
                  }
                >
                  <CheckCircle size={13} />
                  <span>{isExpired ? 'Expiré' : isPendingApproval ? 'En Visa' : 'Émettre'}</span>
                </button>
              );
            })()}

            <button
              className="btn btn-secondary"
              disabled={isConsolidated || !canEdit}
              style={{
                padding: '0.3rem 0.55rem',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                opacity: (!isConsolidated && canEdit) ? 1 : 0.45,
                cursor: (!isConsolidated && canEdit) ? 'pointer' : 'not-allowed',
              }}
              onClick={() => setEditingQuote(row)}
              title={
                isConsolidated
                  ? 'Devis consolidé scellé (non modifiable)'
                  : (canEdit ? 'Ajuster le devis' : 'Non habilité pour la modification')
              }
            >
              <Edit2 size={13} color="#60a5fa" />
              <span>Ajuster</span>
            </button>

            <button
              className="btn btn-secondary"
              disabled={!canDelete}
              style={{
                padding: '0.3rem 0.55rem',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                color: canDelete ? '#38bdf8' : 'var(--text-muted)',
                borderColor: canDelete ? 'rgba(56, 189, 248, 0.3)' : 'var(--border-subtle)',
                opacity: canDelete ? 1 : 0.45,
                cursor: canDelete ? 'pointer' : 'not-allowed',
              }}
              onClick={() => {
                const check = validateBusinessRule('delete', 'quotes', row, dataStore);
                setDeleteValidation(check);
                setDeletingQuote(row);
              }}
              title={canDelete ? 'Archiver la proposition (Conformité CIMA)' : "Non habilité pour l'archivage"}
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
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <FileText size={26} color="#3b82f6" />
            Gestion des Devis & Propositions
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Centralisation, consultation et transformation des devis toutes branches (Auto, Voyage, Transport, MRH, Santé, IA).
          </p>
        </div>

        {/* Quick Branch Creator Buttons & Print */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handlePrintQuotes}
            disabled={loading || quotes.length === 0}
            title="Imprimer le registre officiel des devis & propositions"
            style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}
          >
            <Printer size={16} />
            <span>Imprimer la Liste</span>
          </button>
          <button className="btn btn-primary" onClick={() => navigate('/user/quotes/auto')} title="Assurance Automobile">
            <Car size={15} /> Devis Auto
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/user/quotes/voyage')} title="Assurance Voyage & Schengen" style={{ borderColor: 'rgba(59, 130, 246, 0.4)' }}>
            <Plane size={15} color="#60a5fa" /> Devis Voyage
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/user/quotes/transport')} title="Assurance Transport & Facultés" style={{ borderColor: 'rgba(2, 132, 199, 0.4)' }}>
            <Ship size={15} color="#38bdf8" /> Devis Transport
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/user/quotes/mrh')} title="Multirisque Habitation">
            <Home size={15} /> Devis MRH
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/user/quotes/sante')} title="Santé Groupe">
            <HeartPulse size={15} /> Devis Santé
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/user/quotes/ia')} title="Individuelle Accident">
            <UserPlus size={15} /> Devis IA
          </button>
        </div>
      </div>

      {/* KPI Metrics Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <div className="glass-panel" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Layers size={20} color="#3b82f6" />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Total Devis Émis</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', fontFamily: 'var(--font-mono)' }}>{totalDevis}</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <TrendingUp size={20} color="#10b981" />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Primes Totales Cotées</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#34d399', fontFamily: 'var(--font-mono)' }}>{totalPrimesCotees.toLocaleString()} F</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'rgba(245, 158, 11, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Clock size={20} color="#f59e0b" />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>En Attente Validation</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>{totalEnAttente}</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <CheckCheck size={20} color="#818cf8" />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Consolidés en Contrat</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#a5b4fc', fontFamily: 'var(--font-mono)' }}>{totalConsolides} ({tauxConversion}%)</div>
          </div>
        </div>
      </div>

      {/* Branch Filter Tabs with Direct Print Button on Each Tab */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {[
          { id: 'ALL', label: 'Tous', count: totalDevis, icon: null },
          { id: 'AUTO', label: 'Auto', count: countByBranch.AUTO, icon: <Car size={13} /> },
          { id: 'VOYAGE', label: 'Voyage', count: countByBranch.VOYAGE, icon: <Plane size={13} color="#60a5fa" /> },
          { id: 'TRANSPORT', label: 'Transport', count: countByBranch.TRANSPORT, icon: <Ship size={13} color="#38bdf8" /> },
          { id: 'MRH', label: 'MRH', count: countByBranch.MRH, icon: <Home size={13} /> },
          { id: 'SANTE', label: 'Santé', count: countByBranch.SANTE, icon: <HeartPulse size={13} /> },
          { id: 'IA', label: 'IA', count: countByBranch.IA, icon: <UserPlus size={13} /> },
          { id: 'CONSOLIDATED', label: 'Consolidés', count: totalConsolides, icon: <CheckCircle size={13} color="#34d399" /> },
        ].map((tab) => {
          const isActive = selectedBranchFilter === tab.id;
          return (
            <div
              key={tab.id}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                borderRadius: 'var(--radius-md)',
                overflow: 'hidden',
                border: isActive ? '1px solid #3b82f6' : '1px solid var(--border-subtle)',
                background: isActive ? 'var(--primary)' : 'var(--surface-sunken)',
                boxShadow: isActive ? '0 0 12px rgba(59, 130, 246, 0.3)' : 'none',
                transition: 'all 0.2s ease',
              }}
            >
              <button
                type="button"
                onClick={() => setSelectedBranchFilter(tab.id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  padding: '0.4rem 0.65rem',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  border: 'none',
                  background: 'transparent',
                  color: isActive ? '#fff' : 'var(--text-secondary)',
                  cursor: 'pointer',
                }}
                title={`Afficher les devis : ${tab.label}`}
              >
                {tab.icon}
                <span>{tab.label} ({tab.count})</span>
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handlePrintQuotes(tab.id);
                }}
                disabled={loading || tab.count === 0}
                title={`Imprimer immédiatement la liste : ${tab.label} (${tab.count} devis)`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '0.4rem 0.55rem',
                  border: 'none',
                  borderLeft: isActive ? '1px solid rgba(255, 255, 255, 0.25)' : '1px solid var(--border-subtle)',
                  background: isActive ? 'rgba(0, 0, 0, 0.18)' : 'rgba(255, 255, 255, 0.03)',
                  color: isActive ? '#fff' : (tab.count > 0 ? '#38bdf8' : 'var(--text-muted)'),
                  cursor: tab.count > 0 ? 'pointer' : 'not-allowed',
                  opacity: tab.count === 0 ? 0.4 : 1,
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => {
                  if (tab.count > 0) e.currentTarget.style.background = isActive ? 'rgba(0, 0, 0, 0.35)' : 'rgba(56, 189, 248, 0.2)';
                }}
                onMouseLeave={(e) => {
                  if (tab.count > 0) e.currentTarget.style.background = isActive ? 'rgba(0, 0, 0, 0.18)' : 'rgba(255, 255, 255, 0.03)';
                }}
              >
                <Printer size={13} />
              </button>
            </div>
          );
        })}
      </div>

      {/* Table */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable
          columns={columns}
          data={filteredQuotes}
          loading={loading}
          loadingText="Chargement des devis..." 
          searchPlaceholder="Rechercher par n° devis, assuré, compagnie ou branche..."
          actions={
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => handlePrintQuotes()}
              disabled={loading || filteredQuotes.length === 0}
              title={`Imprimer les propositions de l'onglet actif (${getTabLabel(selectedBranchFilter)})`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                padding: '0.45rem 0.9rem',
                fontSize: '0.82rem',
                fontWeight: 600,
                color: '#38bdf8',
                borderColor: 'rgba(56, 189, 248, 0.4)',
                background: 'rgba(56, 189, 248, 0.1)',
                whiteSpace: 'nowrap',
              }}
            >
              <Printer size={15} />
              <span>Imprimer {getTabLabel(selectedBranchFilter)} ({filteredQuotes.length})</span>
            </button>
          }
        />
      </div>

      {/* Modal Consultation & Impression Devis */}
      <ViewQuoteModal
        isOpen={!!viewingQuote}
        onClose={() => setViewingQuote(null)}
        quote={viewingQuote}
        onConvertToContract={(q) => {
          setViewingQuote(null);
          handleConvertContract(q);
        }}
      />

      {/* Modal Souscription / Émission de Police (E08 & CA-08.1 à CA-08.4) */}
      <SubscriptionIssuanceModal
        isOpen={isConfirmModalOpen}
        onClose={() => {
          setIsConfirmModalOpen(false);
          loadQuotes();
        }}
        quote={selectedQuote}
        onConfirmSuccess={async ({ quote, dateEffet, duree, auditLog }) => {
          try {
            await contractApi.createContractFromQuote(quote.id).catch(() => null);
          } catch (e) {
            console.warn('Django fallback');
          }
          const newContract = dataStore.convertQuoteToContract(quote);
          if (newContract) {
            newContract.date_effet = dateEffet;
            newContract.audit_emission = auditLog;
            newContract.convention_version = auditLog.convention_utilisee;
          }
          loadQuotes();
          return newContract;
        }}
      />

      {/* Modal Modification Devis */}
      <EditQuoteModal
        isOpen={!!editingQuote}
        onClose={() => setEditingQuote(null)}
        quote={editingQuote}
        onSave={(id, updates) => {
          dataStore.updateQuote(id, updates);
          setQuotes(dataStore.getQuotes());
          success(`Devis ${editingQuote.numerodevis} ajusté avec succès !`);
        }}
      />

      {/* Modal Suppression Sécurisée / Contrôle CIMA */}
      <DeleteConfirmModal
        isOpen={!!deletingQuote}
        onClose={() => setDeletingQuote(null)}
        itemType="devis"
        itemName={`Proposition ${deletingQuote?.numerodevis} (${deletingQuote?.client_nom})`}
        itemCode={deletingQuote?.numerodevis}
        validation={deleteValidation}
        onConfirm={async () => {
          if (deletingQuote) {
            try {
              await quoteApi.archiveQuote(deletingQuote.id);
              success(`Devis ${deletingQuote.numerodevis} archivé avec succès.`);
              setDeletingQuote(null);
              loadQuotes();
            } catch (err) {
              toastError(err.response?.data?.message || err.message || 'Erreur lors de l\'archivage sur Django');
            }
          }
        }}
      />
    </div>
  );
};

export default QuoteListPage;
