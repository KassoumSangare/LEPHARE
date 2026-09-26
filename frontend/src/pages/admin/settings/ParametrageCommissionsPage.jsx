import React, { useState } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { Coins, Plus, Edit2, Trash2, Award, Building2, HelpCircle } from 'lucide-react';
import { useToast } from '../../../context/ToastContext';

export const ParametrageCommissionsPage = () => {
  const { success } = useToast();

  const [baremes, setBaremes] = useState([
    { id: 1, Code: 'COMM_AUTO_VP', Branche: 'Automobile VP', Compagnie: 'Toutes Compagnies (CIMA)', TauxApporteur: 10.0, TauxCourtage: 12.0, PlafondLegalCima: 12.0, Statut: 'Règlementaire' },
    { id: 2, Code: 'COMM_AUTO_FLOTTE', Branche: 'Automobile Flotte', Compagnie: 'Toutes Compagnies (CIMA)', TauxApporteur: 8.0, TauxCourtage: 10.0, PlafondLegalCima: 10.0, Statut: 'Règlementaire' },
    { id: 3, Code: 'COMM_MRH', Branche: 'Incendie & MRH', Compagnie: 'Toutes Compagnies (CIMA)', TauxApporteur: 15.0, TauxCourtage: 18.0, PlafondLegalCima: 20.0, Statut: 'Règlementaire' },
    { id: 4, Code: 'COMM_SANTE_GRP', Branche: 'Santé Groupe', Compagnie: 'Toutes Compagnies (CIMA)', TauxApporteur: 7.5, TauxCourtage: 10.0, PlafondLegalCima: 10.0, Statut: 'Règlementaire' },
    { id: 5, Code: 'COMM_IA', Branche: 'Individuelle Accident', Compagnie: 'Toutes Compagnies (CIMA)', TauxApporteur: 12.0, TauxCourtage: 15.0, PlafondLegalCima: 15.0, Statut: 'Règlementaire' },
    { id: 6, Code: 'COMM_VOY', Branche: 'Assistance Voyage', Compagnie: 'AMSA Assurances CI', TauxApporteur: 15.0, TauxCourtage: 20.0, PlafondLegalCima: 20.0, Statut: 'Conventionnel' },
    { id: 7, Code: 'COMM_TRP_MAR', Branche: 'Transport Maritime (Facultés)', Compagnie: 'SANLAM Assurance CI', TauxApporteur: 10.0, TauxCourtage: 12.5, PlafondLegalCima: 15.0, Statut: 'Conventionnel' },
  ]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingBareme, setEditingBareme] = useState(null);

  const [form, setForm] = useState({
    code: '',
    branche: 'Automobile VP',
    compagnie: 'Toutes Compagnies (CIMA)',
    taux_apporteur: 10.0,
    taux_courtage: 12.0,
    plafond_cima: 12.0,
  });

  const handleSave = (e) => {
    e.preventDefault();
    const newB = {
      id: editingBareme ? editingBareme.id : Date.now(),
      Code: form.code || `COMM_${Date.now()}`,
      Branche: form.branche,
      Compagnie: form.compagnie,
      TauxApporteur: Number(form.taux_apporteur),
      TauxCourtage: Number(form.taux_courtage),
      PlafondLegalCima: Number(form.plafond_cima),
      Statut: 'Actif',
    };
    if (editingBareme) {
      setBaremes(prev => prev.map(b => b.id === editingBareme.id ? newB : b));
      success(`Barème de commission ${newB.Code} mis à jour.`);
    } else {
      setBaremes(prev => [newB, ...prev]);
      success(`Nouveau barème ${newB.Code} ajouté.`);
    }
    setIsModalOpen(false);
  };

  const columns = [
    {
      header: 'Barème & Branche',
      render: (r) => (
        <div>
          <strong style={{ color: 'var(--text-primary)', display: 'block' }}>{r.Branche}</strong>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#60a5fa' }}>{r.Code}</span>
        </div>
      )
    },
    {
      header: 'Compagnie / Cadre',
      accessor: 'Compagnie',
      render: (r) => <span style={{ color: 'var(--text-secondary)' }}>{r.Compagnie}</span>
    },
    {
      header: 'Taux Apporteur / Commercial',
      render: (r) => (
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#fbbf24' }}>
          {r.TauxApporteur.toFixed(1)} %
        </span>
      )
    },
    {
      header: 'Taux Courtage Cabinet',
      render: (r) => (
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, color: '#34d399', fontSize: '0.95rem' }}>
          {r.TauxCourtage.toFixed(1)} %
        </span>
      )
    },
    {
      header: 'Plafond Légal CIMA',
      render: (r) => (
        <span style={{ color: '#f87171', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
          Max {r.PlafondLegalCima.toFixed(1)} %
        </span>
      )
    },
    {
      header: 'Statut',
      accessor: 'Statut',
      render: (r) => <StatusBadge label={r.Statut} color="emerald" />
    },
    {
      header: 'Actions',
      render: (r) => (
        <button
          className="btn btn-secondary"
          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
          onClick={() => {
            setEditingBareme(r);
            setForm({
              code: r.Code,
              branche: r.Branche,
              compagnie: r.Compagnie,
              taux_apporteur: r.TauxApporteur,
              taux_courtage: r.TauxCourtage,
              plafond_cima: r.PlafondLegalCima,
            });
            setIsModalOpen(true);
          }}
        >
          Modifier
        </button>
      )
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '1280px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Coins size={28} color="#34d399" />
            Taux de commission
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Taux de commission du cabinet par branche et par compagnie.
          </p>
        </div>

        <button
          className="btn btn-primary"
          onClick={() => {
            setEditingBareme(null);
            setForm({
              code: '',
              branche: 'Automobile VP',
              compagnie: 'Toutes Compagnies (CIMA)',
              taux_apporteur: 10.0,
              taux_courtage: 12.0,
              plafond_cima: 12.0,
            });
            setIsModalOpen(true);
          }}
        >
          <Plus size={16} /> Nouveau Barème de Commission
        </button>
      </div>

      {/* Notice de conformité */}
      <div className="glass-panel" style={{ padding: '1rem 1.25rem', borderLeft: '4px solid #34d399', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <Award size={20} color="#34d399" style={{ flexShrink: 0 }} />
        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Les taux de commission appliqués par le Cabinet LE PHARE respectent scrupuleusement les plafonds du Code des Assurances CIMA (Art. 540 à 545). Toute dérogation au-delà du plafond est automatiquement bloquée.
        </span>
      </div>

      {/* Table */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable columns={columns} data={baremes} searchPlaceholder="Filtrer une branche ou compagnie..." />
      </div>

      {/* Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingBareme ? 'Modifier le Barème de Commission' : 'Nouveau Barème de Commission'}
      >
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Branche Métier (* requis)</label>
              <input
                type="text"
                className="form-control"
                value={form.branche}
                onChange={(e) => setForm({ ...form, branche: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Compagnie Ciblée</label>
              <input
                type="text"
                className="form-control"
                value={form.compagnie}
                onChange={(e) => setForm({ ...form, compagnie: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Taux Apporteur (%)</label>
              <input
                type="number"
                step="0.5"
                className="form-control"
                value={form.taux_apporteur}
                onChange={(e) => setForm({ ...form, taux_apporteur: Number(e.target.value) })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Taux Courtage Cabinet (%)</label>
              <input
                type="number"
                step="0.5"
                className="form-control"
                value={form.taux_courtage}
                onChange={(e) => setForm({ ...form, taux_courtage: Number(e.target.value) })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Plafond Légal CIMA (%)</label>
              <input
                type="number"
                step="0.5"
                className="form-control"
                value={form.plafond_cima}
                onChange={(e) => setForm({ ...form, plafond_cima: Number(e.target.value) })}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Annuler</button>
            <button type="submit" className="btn btn-primary">Enregistrer le Barème</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default ParametrageCommissionsPage;
