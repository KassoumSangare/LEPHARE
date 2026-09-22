import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MetricCard } from '../../components/common/MetricCard';
import { DataTable } from '../../components/common/DataTable';
import { StatusBadge } from '../../components/common/StatusBadge';
import { approvalApi, remittanceApi } from '../../api/endpoints';
import { dataStore } from '../../api/dataStore';
import {
  BarChart3,
  TrendingUp,
  Building2,
  Coins,
  ShieldCheck,
  CheckCheck,
  ArrowUpRight,
  PieChart,
} from 'lucide-react';

export const AdminDashboard = () => {
  const navigate = useNavigate();

  const [derogations, setDerogations] = useState(() => dataStore.getDerogations());
  const [remittances, setRemittances] = useState(() => dataStore.getRemittances());

  useEffect(() => {
    let isMounted = true;
    const loadRealData = async () => {
      try {
        const [demList, remList] = await Promise.all([
          approvalApi.getDemandes().catch(() => []),
          remittanceApi.getPendingRemittances().catch(() => []),
        ]);
        if (isMounted) {
          if (demList && Array.isArray(demList) && demList.length > 0) {
            setDerogations(demList);
          }
          if (remList && Array.isArray(remList) && remList.length > 0) {
            setRemittances(remList);
          }
        }
      } catch (e) {
        console.error('Erreur dashboard admin Django:', e);
      }
    };
    loadRealData();
    return () => { isMounted = false; };
  }, []);

  const pendingApprovals = derogations.filter((d) => d.statut === 'PENDING');
  const pendingRemittances = remittances.filter((r) => r.statut !== 'Validé');

  const cimaColumns = [
    { header: 'Code CIMA', accessor: 'code_branche', render: (r) => <strong style={{ color: '#60a5fa' }}>{r.code_branche}</strong> },
    { header: 'Branche Réglementaire', accessor: 'branche' },
    { header: 'Émissions Brutes (FCFA)', render: (r) => <strong>{Number(r.emissions || 0).toLocaleString('fr-FR')} F</strong> },
    { header: 'Encaissements (FCFA)', render: (r) => <span style={{ color: '#34d399' }}>{Number(r.encaissements || 0).toLocaleString('fr-FR')} F</span> },
    { header: 'Commissions Dues (FCFA)', render: (r) => <span style={{ color: '#fbbf24' }}>{Number(r.commissions || 0).toLocaleString('fr-FR')} F</span> },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Top Banner */}
      <div
        className="glass-panel"
        style={{
          padding: '1.75rem 2rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1.25rem',
          background: 'linear-gradient(135deg, rgba(88, 28, 135, 0.4) 0%, rgba(15, 23, 42, 0.95) 100%)',
          border: '1px solid rgba(139, 92, 246, 0.3)',
        }}
      >
        <div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <BarChart3 size={28} color="#c084fc" />
            Direction & Pilotage Stratégique
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.35rem' }}>
            Supervision globale, conformité CIMA, autorisations hiérarchiques et pilotage des résultats financiers.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={() => navigate('/admin/approvals')} style={{ background: 'linear-gradient(135deg, #8b5cf6, #6d28d9)' }}>
            <CheckCheck size={16} />
            <span>Valider Dérogations ({pendingApprovals.length})</span>
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/admin/reporting/cima')}>
            <PieChart size={16} />
            <span>États CIMA</span>
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/admin/remittances')}>
            <Building2 size={16} />
            <span>Reversements</span>
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/user/contracts')}>
            <ShieldCheck size={16} />
            <span>Portefeuille Polices</span>
          </button>
        </div>
      </div>

      {/* KPI Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
        <MetricCard
          title="Chiffre d'Affaires Global"
          value="— FCFA"
          subtext="Volume d'affaires émis"
          trend="+22.4% vs N-1"
          icon={TrendingUp}
          color="emerald"
        />
        <MetricCard
          title="Taux de Recouvrement"
          value="—%"
          subtext="Efficience de caisse"
          trend="+3.1 points"
          icon={Coins}
          color="blue"
        />
        <MetricCard
          title="Reversements à Valider"
          value={`${pendingRemittances.length} bordereaux`}
          subtext="En attente transfert compagnies"
          trend="Délai légal 30j CIMA"
          icon={Building2}
          color="amber"
        />
        <MetricCard
          title="Demandes en Attente"
          value={`${pendingApprovals.length} requêtes`}
          subtext="Approbation dérogations"
          trend="À traiter d'urgence"
          icon={CheckCheck}
          color="purple"
        />
      </div>

      {/* CIMA Regulatory Breakdown Table */}
      <div className="glass-panel" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div>
            <h2 className="title-md" style={{ color: '#fff' }}>Synthèse Réglementaire CIMA par Branche (État E1)</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Ventilation des émissions, encaissements et commissions par branche d'assurance</p>
          </div>
          <button className="btn btn-secondary" style={{ fontSize: '0.75rem' }} onClick={() => navigate('/admin/reporting/cima')}>
            Détail des états CIMA <ArrowUpRight size={14} />
          </button>
        </div>
        <DataTable columns={cimaColumns} data={[]} searchable={false} itemsPerPage={5} emptyMessage="Connectez le backend CIMA pour afficher les données réglementaires." />
      </div>
    </div>
  );
};

export default AdminDashboard;
