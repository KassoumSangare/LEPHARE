import React, { useState } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { Layers, Plus, Edit2, Trash2, CheckCircle2, TrendingDown } from 'lucide-react';
import { useToast } from '../../../context/ToastContext';

export const ParametrageFlottePage = () => {
  const { success } = useToast();

  const [tranches, setTranches] = useState([
    { id: 1, Code: 'FLOTTE_T1', TrancheVehicules: '2 à 5 véhicules', MinVehicules: 2, MaxVehicules: 5, TauxReductionRC: 5.0, TauxReductionDommages: 10.0, Condition: 'Appartenant à la même personne morale/physique', Statut: 'Actif' },
    { id: 2, Code: 'FLOTTE_T2', TrancheVehicules: '6 à 10 véhicules', MinVehicules: 6, MaxVehicules: 10, TauxReductionRC: 10.0, TauxReductionDommages: 15.0, Condition: 'Parc homogène immatriculé au siège', Statut: 'Actif' },
    { id: 3, Code: 'FLOTTE_T3', TrancheVehicules: '11 à 20 véhicules', MinVehicules: 11, MaxVehicules: 20, TauxReductionRC: 15.0, TauxReductionDommages: 20.0, Condition: 'Suivi de sinistralité S/P < 60%', Statut: 'Actif' },
    { id: 4, Code: 'FLOTTE_T4', TrancheVehicules: '21 à 50 véhicules', MinVehicules: 21, MaxVehicules: 50, TauxReductionRC: 20.0, TauxReductionDommages: 25.0, Condition: 'Gestionnaire de parc dédié + Télématique', Statut: 'Actif' },
    { id: 5, Code: 'FLOTTE_T5', TrancheVehicules: 'Plus de 50 véhicules', MinVehicules: 51, MaxVehicules: 999, TauxReductionRC: 25.0, TauxReductionDommages: 30.0, Condition: 'Grand Compte Entreprise / Accord Direction', Statut: 'Actif' },
  ]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTranche, setEditingTranche] = useState(null);

  const [form, setForm] = useState({
    code: '',
    tranche: '',
    min: 2,
    max: 5,
    reduc_rc: 5.0,
    reduc_domm: 10.0,
    condition: '',
  });

  const handleSave = (e) => {
    e.preventDefault();
    const newT = {
      id: editingTranche ? editingTranche.id : Date.now(),
      Code: form.code || `FLOTTE_${Date.now()}`,
      TrancheVehicules: form.tranche || `${form.min} à ${form.max} véhicules`,
      MinVehicules: Number(form.min),
      MaxVehicules: Number(form.max),
      TauxReductionRC: Number(form.reduc_rc),
      TauxReductionDommages: Number(form.reduc_domm),
      Condition: form.condition || 'Accord standard',
      Statut: 'Actif',
    };

    if (editingTranche) {
      setTranches(prev => prev.map(t => t.id === editingTranche.id ? newT : t));
      success(`Palier de réduction ${newT.Code} mis à jour.`);
    } else {
      setTranches(prev => [...prev, newT]);
      success(`Nouveau palier flotte ${newT.Code} ajouté.`);
    }
    setIsModalOpen(false);
  };

  const columns = [
    {
      header: 'Palier Flotte',
      render: (r) => (
        <div>
          <strong style={{ color: 'var(--text-primary)', display: 'block' }}>{r.TrancheVehicules}</strong>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#60a5fa' }}>{r.Code}</span>
        </div>
      )
    },
    {
      header: 'Fourchette Volume',
      render: (r) => <span style={{ fontFamily: 'var(--font-mono)' }}>{r.MinVehicules} - {r.MaxVehicules === 999 ? '∞' : r.MaxVehicules} véhicules</span>
    },
    {
      header: 'Réduction RC Auto',
      render: (r) => (
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, color: '#38bdf8' }}>
          -{r.TauxReductionRC.toFixed(1)} %
        </span>
      )
    },
    {
      header: 'Réduction Dommages / Tierce',
      render: (r) => (
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, color: '#34d399' }}>
          -{r.TauxReductionDommages.toFixed(1)} %
        </span>
      )
    },
    {
      header: 'Conditions d\'Éligibilité',
      accessor: 'Condition',
      render: (r) => <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{r.Condition}</span>
    },
    {
      header: 'Actions',
      render: (r) => (
        <button
          className="btn btn-secondary"
          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
          onClick={() => {
            setEditingTranche(r);
            setForm({
              code: r.Code,
              tranche: r.TrancheVehicules,
              min: r.MinVehicules,
              max: r.MaxVehicules,
              reduc_rc: r.TauxReductionRC,
              reduc_domm: r.TauxReductionDommages,
              condition: r.Condition,
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
            <TrendingDown size={28} color="#38bdf8" />
            Réductions flotte
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Remise accordée automatiquement selon le nombre de véhicules d'un même client.
          </p>
        </div>

        <button
          className="btn btn-primary"
          onClick={() => {
            setEditingTranche(null);
            setForm({
              code: '',
              tranche: '',
              min: 2,
              max: 5,
              reduc_rc: 5.0,
              reduc_domm: 10.0,
              condition: '',
            });
            setIsModalOpen(true);
          }}
        >
          <Plus size={16} /> Nouveau Palier Flotte
        </button>
      </div>

      {/* Table */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable columns={columns} data={tranches} searchPlaceholder="Filtrer une tranche ou réduction..." />
      </div>

      {/* Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingTranche ? 'Modifier le Palier Flotte' : 'Nouveau Palier de Réduction Flotte'}
      >
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Désignation du Palier (* requis)</label>
            <input
              type="text"
              className="form-control"
              value={form.tranche}
              onChange={(e) => setForm({ ...form, tranche: e.target.value })}
              required
              placeholder="Ex: 6 à 10 véhicules"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Nombre Min Véhicules</label>
              <input
                type="number"
                min="2"
                className="form-control"
                value={form.min}
                onChange={(e) => setForm({ ...form, min: Number(e.target.value) })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Nombre Max Véhicules</label>
              <input
                type="number"
                min="2"
                className="form-control"
                value={form.max}
                onChange={(e) => setForm({ ...form, max: Number(e.target.value) })}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Réduction RC Auto (%)</label>
              <input
                type="number"
                step="0.5"
                className="form-control"
                value={form.reduc_rc}
                onChange={(e) => setForm({ ...form, reduc_rc: Number(e.target.value) })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Réduction Dommages / Tierce (%)</label>
              <input
                type="number"
                step="0.5"
                className="form-control"
                value={form.reduc_domm}
                onChange={(e) => setForm({ ...form, reduc_domm: Number(e.target.value) })}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Condition Particulière</label>
            <input
              type="text"
              className="form-control"
              value={form.condition}
              onChange={(e) => setForm({ ...form, condition: e.target.value })}
              placeholder="Ex: Carte grise au nom de la même entité juridique"
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Annuler</button>
            <button type="submit" className="btn btn-primary">Enregistrer le Palier</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default ParametrageFlottePage;
