import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable } from '../../../components/common/DataTable';
import { isRegistryQuote } from '../../../utils/quoteRegistry';
import { LoadingSpinner } from '../../../components/common/LoadingSpinner';
import { RowActions } from '../../../components/common/RowActions';
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
  RefreshCw,
} from 'lucide-react';

const formatDateTime = (value) => {
  if (!value) return '-';
  const d = new Date(value);
  if (isNaN(d.getTime())) return String(value);
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
};

// Seuls les devis émis durant les 3 dernières années sont affichés
const isWithinLastThreeYears = (q) => {
  const d = new Date(q.date_emission || q.dateemission);
  if (isNaN(d.getTime())) return true;
  const limit = new Date();
  limit.setFullYear(limit.getFullYear() - 3);
  return d >= limit;
};

export const QuoteListPage = () => {
  const { user } = useAuth();
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBranchFilter, setSelectedBranchFilter] = useState('ALL');
  // Décompte du registre par branche, calculé sur les devis à confirmer réellement chargés
  const [stats, setStats] = useState(() => {
    return { ALL: 0, AUTO: 0, VOYAGE: 0, TRANSPORT: 0, MRH: 0, SANTE: 0, IA: 0, AUTRES: 0, CONSOLIDATED: 0 };
  });
  const [selectedQuote, setSelectedQuote] = useState(null);
  const [viewingQuote, setViewingQuote] = useState(null);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [editingQuote, setEditingQuote] = useState(null);
  const [deletingQuote, setDeletingQuote] = useState(null);
  const [deleteValidation, setDeleteValidation] = useState({ allowed: true });
  const [selectedForConsolidation, setSelectedForConsolidation] = useState([]);
  const [consolidating, setConsolidating] = useState(false);
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const isEligibleForConsolidation = (q) =>
    !q.flotte && !q.confirme && !q.archive && !q.devis_consolide;

  const toggleConsolidationSelection = (quote) => {
    setSelectedForConsolidation((prev) => {
      const exists = prev.some((q) => q.iddevis === quote.iddevis);
      if (exists) return prev.filter((q) => q.iddevis !== quote.iddevis);
      return [...prev, quote];
    });
  };

  const handleConsolidateSelected = async () => {
    if (selectedForConsolidation.length < 2) {
      toastError('Sélectionnez au moins 2 devis Mono du même client à consolider.');
      return;
    }
    setConsolidating(true);
    try {
      const payload = selectedForConsolidation.map((q) => ({ iddevis: q.iddevis }));
      const res = await quoteApi.consolidateQuote(payload);
      const newId = res?.data?.iddevis;
      success(
        `${selectedForConsolidation.length} devis consolidés avec succès` +
          (newId ? ` (nouveau devis n°${newId})` : '') +
          ' !'
      );
      setSelectedForConsolidation([]);
      await loadQuotes();
      await loadStats();
    } catch (err) {
      const apiError = err.response?.data?.erreur || err.response?.data?.detail;
      toastError(apiError || 'Erreur lors de la consolidation des devis.');
    } finally {
      setConsolidating(false);
    }
  };

  // Un seul chargement du registre complet (non archivés, non confirmés) : le serveur ne sait pas
  // filtrer les devis expirés ni compter par branche, donc tout est calculé ici pour que
  // compteurs, onglets et liste soient toujours identiques.
  const [registry, setRegistry] = useState(null);

  const getBranchOf = (q) => {
    const p = q.raw?.produit;
    const id = Number(p && typeof p === 'object' ? (p.id_produit ?? p.IdProduit ?? p.idproduit) : (q.raw?.idproduit ?? p));
    if (id === 1) return 'AUTO';
    if (id === 2) return 'IA';
    if (id === 3) return 'VOYAGE';
    if ([4, 7, 9].includes(id)) return 'MRH';
    if ([5, 10].includes(id)) return 'SANTE';
    if (id === 6) return 'TRANSPORT';
    return 'AUTRES';
  };

  const sortRecent = (list) => [...list].sort((a, b) => {
    const dateA = new Date(a.dateemission || a.date_emission || a.dateeffet || 0).getTime();
    const dateB = new Date(b.dateemission || b.date_emission || b.dateeffet || 0).getTime();
    return dateB - dateA || (b.iddevis || b.id || 0) - (a.iddevis || a.id || 0);
  });

  const loadQuotes = async () => {
    setLoading(true);
    try {
      const all = await quoteApi.getAllQuotes({ archive: 'false', confirme: 'false' });
      setRegistry(sortRecent(all.filter(isRegistryQuote).filter(isWithinLastThreeYears)));
    } catch (err) {
      console.error('Erreur chargement devis Django:', err);
      setRegistry(sortRecent((dataStore.getQuotes() || []).filter(isRegistryQuote).filter(isWithinLastThreeYears)));
    } finally {
      setLoading(false);
    }
  };

  const loadStats = () => {};

  useEffect(() => {
    loadQuotes();
  }, []);

  // Liste affichée + compteurs, tous dérivés du même registre
  useEffect(() => {
    if (!registry) return;
    const counts = { ALL: registry.length, AUTO: 0, VOYAGE: 0, TRANSPORT: 0, MRH: 0, SANTE: 0, IA: 0, AUTRES: 0, CONSOLIDATED: 0 };
    registry.forEach((q) => {
      counts[getBranchOf(q)] += 1;
      if (q.devis_consolide) counts.CONSOLIDATED += 1;
    });
    setStats(counts);
    setQuotes(
      selectedBranchFilter === 'ALL' ? registry
        : selectedBranchFilter === 'CONSOLIDATED' ? registry.filter((q) => q.devis_consolide)
        : registry.filter((q) => getBranchOf(q) === selectedBranchFilter)
    );
  }, [registry, selectedBranchFilter]);

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

  // Dynamic KPI Metrics
  const totalDevis = quotes.length;
  const totalPrimesCotees = quotes.reduce((acc, q) => acc + Number(q.prime_totale || 0), 0);
  // Registre = devis à confirmer uniquement (les confirmés vont dans les contrats, les archivés sont masqués).
  // En attente de validation = devis en attente du visa de la Direction (circuit d'approbation).
  const totalEnAttente = quotes.filter(
    (q) => q.circuit_approbation && q.circuit_approbation.statut_validation === 'EN_ATTENTE_DIRECTION'
  ).length;

  const countByBranch = stats;
  const totalConsolides = countByBranch.CONSOLIDATED;

  const getTabLabel = (filter) => {
    switch (filter) {
      case 'AUTO': return 'Auto';
      case 'VOYAGE': return 'Voyage';
      case 'TRANSPORT': return 'Transport';
      case 'MRH': return 'MRH';
      case 'SANTE': return 'Santé';
      case 'IA': return 'IA';
      case 'CONSOLIDATED': return 'Consolidés';
      case 'ARCHIVED': return 'Archivés';
      default: return 'Tous';
    }
  };

  const handlePrintQuotes = (specificBranch = null) => {
    const branchToUse = specificBranch || selectedBranchFilter;
    let listToPrint = quotes;

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
        'Périmètre': `Filtre actif : ${tabName}`,
        'Volume coté': `${listToPrint.length} propositions (${Number(countByBranch[branchToUse] || listToPrint.length).toLocaleString()} en base)`,
        'Total Primes TTC': `${totalMontant.toLocaleString()} FCFA`,
      },
      headers,
      rows,
      tableSummary: {
        'Nombre total de devis cotés': String(listToPrint.length),
        'Montant global des primes TTC': `${totalMontant.toLocaleString()} FCFA`,
      },
    });
  };

  const columns = [
    {
      header: 'Réf. Proposition / Devis',
      accessor: 'numerodevis',
      render: (row) => {
        const eligible = isEligibleForConsolidation(row);
        const isSelected = selectedForConsolidation.some((q) => q.iddevis === row.iddevis);
        const isConsolidated = !!row.devis_consolide;
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            {eligible && selectedBranchFilter !== 'ARCHIVED' && (
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => toggleConsolidationSelection(row)}
                title="Cocher pour fusionner/consolider ce devis mono (sp_consolidation_devis)"
                style={{ cursor: 'pointer', accentColor: '#3b82f6', width: '15px', height: '15px' }}
              />
            )}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <strong style={{ color: '#fff', fontFamily: 'var(--font-mono)' }}>{row.numerodevis || `DEV-${row.id}`}</strong>
                {isConsolidated && (
                  <span
                    style={{
                      fontSize: '0.65rem',
                      padding: '0.1rem 0.35rem',
                      borderRadius: '4px',
                      background: 'rgba(59, 130, 246, 0.2)',
                      color: '#60a5fa',
                      border: '1px solid rgba(59, 130, 246, 0.4)',
                      fontWeight: 700,
                    }}
                    title="Devis multi-risques issu de la consolidation de plusieurs devis mono"
                  >
                    Consolidé #{row.devis_consolide}
                  </span>
                )}
                {row.archive && (
                  <span
                    style={{
                      fontSize: '0.65rem',
                      padding: '0.1rem 0.35rem',
                      borderRadius: '4px',
                      background: 'rgba(239, 68, 68, 0.2)',
                      color: '#f87171',
                      border: '1px solid rgba(239, 68, 68, 0.4)',
                      fontWeight: 700,
                    }}
                  >
                    Archivé
                  </span>
                )}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {row.client_nom || row.nomcomplet || 'Client Inconnu'}
              </div>
            </div>
          </div>
        );
      },
    },
    {
      header: 'Branche / Produit',
      accessor: 'produit',
      render: (row) => (
        <div>
          <span style={{ fontWeight: 600, color: '#e2e8f0' }}>{row.branche ? row.branche.toUpperCase() : 'AUTOMOBILE'}</span>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{row.produit || 'Auto Standard'}</div>
        </div>
      ),
    },
    {
      header: 'Compagnie',
      accessor: 'compagnie',
      render: (row) => <div style={{ fontSize: '0.85rem' }}>{row.compagnie || 'NSIA ASSURANCES'}</div>,
    },
    {
      header: 'Émission',
      accessor: 'date_emission',
      render: (row) => <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{formatDateTime(row.date_emission)}</div>,
    },
    {
      header: 'Prime Totale TTC',
      accessor: 'prime_totale',
      render: (row) => (
        <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>
          {Number(row.prime_totale || 0).toLocaleString()} FCFA
        </strong>
      ),
    },
    {
      header: 'Statut',
      accessor: 'statut',
      render: (row) => {
        let color = 'amber';
        const s = (row.statut || '').toLowerCase();
        if (row.archive) color = 'slate';
        else if (s.includes('confirm') || s.includes('contrat') || row.confirme) color = 'emerald';
        else if (s.includes('consolid')) color = 'blue';
        else if (s.includes('expir')) color = 'red';
        const label = color === 'emerald' ? 'Confirmé' : (color === 'blue' ? (row.statut || 'Consolidé') : (color === 'red' ? (row.statut || 'Expiré') : 'Attente'));
        return <StatusBadge label={label} color={color} />;
      },
    },
    {
      header: 'Actions',
      render: (row) => {
        const canEdit = canUser(user, 'edit', 'quotes');
        const canDelete = canUser(user, 'delete', 'quotes');
        const isConsolidated = !!row.devis_consolide;
        const todayStr = new Date().toISOString().split('T')[0];
        const isExpired = row.date_expiration ? new Date(row.date_expiration) < new Date(todayStr) : false;
        const isPendingApproval = row.circuit_approbation && row.circuit_approbation.statut_validation === 'EN_ATTENTE_DIRECTION';

        return (
          <RowActions
            onView={() => setViewingQuote(row)}
            viewTitle="Consulter l'intégralité du devis et imprimer la proposition"
            showConfirm={!isConsolidated}
            confirmLabel={isExpired ? 'Expiré' : isPendingApproval ? 'En Visa' : 'Confirmer'}
            confirmDisabled={isExpired || isPendingApproval}
            confirmTitle={
              isExpired
                ? 'Devis expiré : conversion bloquée (CA-07.3)'
                : isPendingApproval
                ? 'Visa Direction Requis avant confirmation (CA-07.4)'
                : 'Confirmer le devis et générer le contrat (E08)'
            }
            onConfirm={() => handleConvertContract(row)}
            onEdit={() => setEditingQuote(row)}
            editDisabled={isConsolidated || !canEdit}
            editTitle={
              isConsolidated
                ? 'Devis consolidé scellé (non modifiable)'
                : (canEdit ? 'Ajuster le devis' : 'Non habilité pour la modification')
            }
            onArchive={() => {
              const check = validateBusinessRule('delete', 'quotes', row, dataStore);
              setDeleteValidation(check);
              setDeletingQuote(row);
            }}
            archiveDisabled={!canDelete}
            archiveTitle={canDelete ? 'Archiver la proposition (Conformité CIMA)' : "Non habilité pour l'archivage"}
          />
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
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/quotes/auto')}>
            <Car size={16} />
            <span>Devis Auto</span>
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/quotes/voyage')}>
            <Plane size={16} />
            <span>Devis Voyage</span>
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/quotes/transport')}>
            <Ship size={16} />
            <span>Devis Transport</span>
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/quotes/mrh')}>
            <Home size={16} />
            <span>Devis MRH</span>
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/quotes/sante')}>
            <HeartPulse size={16} />
            <span>Devis Santé</span>
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/user/quotes/ia')}>
            <UserPlus size={16} />
            <span>Devis IA</span>
          </button>
        </div>
      </div>

      {/* KPI Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <div className="glass-panel" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Layers size={20} color="#3b82f6" />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Total Devis Actifs</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', fontFamily: 'var(--font-mono)' }}>{countByBranch.ALL.toLocaleString()}</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <TrendingUp size={20} color="#10b981" />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Primes Totales Cotées (Page)</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#34d399', fontFamily: 'var(--font-mono)' }}>{totalPrimesCotees.toLocaleString()} F</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'rgba(245, 158, 11, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Clock size={20} color="#f59e0b" />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>En Attente Validation (Page)</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>{totalEnAttente}</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <CheckCheck size={20} color="#818cf8" />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Consolidés en Contrat</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#a5b4fc', fontFamily: 'var(--font-mono)' }}>{totalConsolides.toLocaleString()}</div>
          </div>
        </div>
      </div>

      {/* Branch Filter Tabs with Direct Print Button on Each Tab */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {[
          { id: 'ALL', label: 'Tous', count: countByBranch.ALL, icon: null },
          { id: 'AUTO', label: 'Auto', count: countByBranch.AUTO, icon: <Car size={13} /> },
          { id: 'VOYAGE', label: 'Voyage', count: countByBranch.VOYAGE, icon: <Plane size={13} color="#60a5fa" /> },
          { id: 'TRANSPORT', label: 'Transport', count: countByBranch.TRANSPORT, icon: <Ship size={13} color="#38bdf8" /> },
          { id: 'MRH', label: 'MRH', count: countByBranch.MRH, icon: <Home size={13} /> },
          { id: 'SANTE', label: 'Santé', count: countByBranch.SANTE, icon: <HeartPulse size={13} /> },
          { id: 'IA', label: 'IA', count: countByBranch.IA, icon: <UserPlus size={13} /> },
          { id: 'AUTRES', label: 'Autres', count: countByBranch.AUTRES, icon: <Layers size={13} /> },
          { id: 'CONSOLIDATED', label: 'Consolidés', count: countByBranch.CONSOLIDATED, icon: <CheckCircle size={13} color="#34d399" /> },
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
                <span>{tab.label}</span>
                <span
                  style={{
                    fontSize: '0.72rem',
                    padding: '0.1rem 0.35rem',
                    borderRadius: '999px',
                    background: isActive ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.08)',
                    color: isActive ? '#fff' : 'var(--text-muted)',
                    marginLeft: '0.2rem',
                  }}
                >
                  {Number(tab.count || 0).toLocaleString()}
                </span>
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handlePrintQuotes(tab.id);
                }}
                title={`Imprimer directement la liste : ${tab.label}`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '0.4rem 0.45rem',
                  border: 'none',
                  borderLeft: isActive ? '1px solid rgba(255,255,255,0.2)' : '1px solid var(--border-subtle)',
                  background: 'transparent',
                  color: isActive ? '#fff' : 'var(--text-muted)',
                  cursor: 'pointer',
                }}
              >
                <Printer size={12} />
              </button>
            </div>
          );
        })}
      </div>

      {/* Consolidation Action Bar (si des devis sont sélectionnés) */}
      {selectedForConsolidation.length > 0 && (
        <div
          className="glass-panel"
          style={{
            padding: '0.75rem 1.25rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(16, 185, 129, 0.15))',
            border: '1px solid rgba(59, 130, 246, 0.4)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Layers size={20} color="#60a5fa" />
            <div>
              <strong style={{ color: '#fff', fontSize: '0.9rem' }}>
                {selectedForConsolidation.length} devis sélectionné(s) pour consolidation
              </strong>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Fusion multi-risques vers un devis consolidé unique (sp_consolidation_devis)
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setSelectedForConsolidation([])}
              style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
            >
              Annuler
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={selectedForConsolidation.length < 2 || consolidating}
              onClick={handleConsolidateSelected}
              style={{ fontSize: '0.8rem', padding: '0.35rem 0.9rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <CheckCircle size={14} />
              <span>{consolidating ? 'Consolidation en cours...' : `Consolider (${selectedForConsolidation.length})`}</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Table Card */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Affichage des {quotes.length} devis à confirmer ({getTabLabel(selectedBranchFilter)}) sur un total de <strong>{countByBranch[selectedBranchFilter]?.toLocaleString()}</strong> dans le registre
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              loadStats();
              loadQuotes(selectedBranchFilter);
            }}
            title="Actualiser la liste"
            style={{ fontSize: '0.78rem', padding: '0.3rem 0.65rem' }}
          >
            <RefreshCw size={13} />
            <span>Actualiser</span>
          </button>
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : (
          <DataTable
            columns={columns}
            data={quotes}
            searchPlaceholder="Rechercher par n° devis, assuré, compagnie ou branche..."
          />
        )}
      </div>

      {/* Modal Consultation Devis */}
      {viewingQuote && (
        <ViewQuoteModal
          isOpen={!!viewingQuote}
          onClose={() => setViewingQuote(null)}
          quote={viewingQuote}
        />
      )}

      {/* Modal Modification Devis */}
      {editingQuote && (
        <EditQuoteModal
          isOpen={!!editingQuote}
          onClose={() => setEditingQuote(null)}
          quote={editingQuote}
          onSuccess={() => {
            loadQuotes();
            loadStats();
          }}
        />
      )}

      {/* Modal Confirmation Conversion en Contrat */}
      <Modal
        isOpen={isConfirmModalOpen}
        onClose={() => setIsConfirmModalOpen(false)}
        title="Confirmation de la Transformation en Contrat CIMA"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
            Êtes-vous sûr de vouloir valider et transformer la proposition{' '}
            <strong style={{ color: '#fff' }}>{selectedQuote?.numerodevis}</strong> ({selectedQuote?.client_nom}) en contrat d'assurance définitif ?
          </p>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsConfirmModalOpen(false)}>
              Annuler
            </button>
            <button type="button" className="btn btn-primary" onClick={confirmConversion}>
              Confirmer & Émettre Police
            </button>
          </div>
        </div>
      </Modal>

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
              loadStats();
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
