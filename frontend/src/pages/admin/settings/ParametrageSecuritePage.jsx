import React, { useState } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { ShieldCheck, Plus, Edit2, Trash2, HeartHandshake, Banknote, Users } from 'lucide-react';
import { useToast } from '../../../context/ToastContext';

export const ParametrageSecuritePage = () => {
  const { success } = useToast();

  const [formules, setFormules] = useState([
    { id: 1, Code: 'SEC_STD_NSIA', LibelleFormule: 'Sécurité Routière Standard 5 Places', Compagnie: 'NSIA ASSURANCES CI', CapitalDeces: 1000000, CapitalInvalidite: 1000000, FraisMedicaux: 100000, PrimeParPlace: 2500, PrimeTotaleAnnuelle: 12500, Statut: 'Actif' },
    { id: 2, Code: 'SEC_CONF_NSIA', LibelleFormule: 'Sécurité Routière Confort Renforcée', Compagnie: 'NSIA ASSURANCES CI', CapitalDeces: 2500000, CapitalInvalidite: 2500000, FraisMedicaux: 250000, PrimeParPlace: 5000, PrimeTotaleAnnuelle: 25000, Statut: 'Actif' },
    { id: 3, Code: 'SEC_ELITE_SANLAM', LibelleFormule: 'Pack Sécurité Prestige Conducteur & Passagers', Compagnie: 'SANLAM ASSURANCE CI', CapitalDeces: 5000000, CapitalInvalidite: 5000000, FraisMedicaux: 500000, PrimeParPlace: 8500, PrimeTotaleAnnuelle: 42500, Statut: 'Actif' },
    { id: 4, Code: 'SEC_AMSA_MINI', LibelleFormule: 'Sécurité Routière Économique Passagers', Compagnie: 'AMSA ASSURANCES CI', CapitalDeces: 500000, CapitalInvalidite: 500000, FraisMedicaux: 50000, PrimeParPlace: 1500, PrimeTotaleAnnuelle: 7500, Statut: 'Actif' },
    { id: 5, Code: 'SEC_SUNU_PRO', LibelleFormule: 'Sécurité Routière Transport Professionnel & Salariés', Compagnie: 'SUNU ASSURANCES CI', CapitalDeces: 3000000, CapitalInvalidite: 3000000, FraisMedicaux: 300000, PrimeParPlace: 6000, PrimeTotaleAnnuelle: 30000, Statut: 'Actif' },
  ]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingFormule, setEditingFormule] = useState(null);

  const [form, setForm] = useState({
    code: '',
    libelle: '',
    compagnie: 'NSIA ASSURANCES CI',
    capital_deces: 1000000,
    capital_invalidite: 1000000,
    frais_medicaux: 100000,
    prime_place: 2500,
  });

  const handleSave = (e) => {
    e.preventDefault();
    const newF = {
      id: editingFormule ? editingFormule.id : Date.now(),
      Code: form.code || `SEC_${Date.now()}`,
      LibelleFormule: form.libelle,
      Compagnie: form.compagnie,
      CapitalDeces: Number(form.capital_deces),
      CapitalInvalidite: Number(form.capital_invalidite),
      FraisMedicaux: Number(form.frais_medicaux),
      PrimeParPlace: Number(form.prime_place),
      PrimeTotaleAnnuelle: Number(form.prime_place) * 5,
      Statut: 'Actif',
    };

    if (editingFormule) {
      setFormules(prev => prev.map(f => f.id === editingFormule.id ? newF : f));
      success(`Formule de sécurité routière ${newF.Code} mise à jour.`);
    } else {
      setFormules(prev => [...prev, newF]);
      success(`Nouvelle formule de sécurité routière ${newF.Code} créée.`);
    }
    setIsModalOpen(false);
  };

  const columns = [
    {
      header: 'Formule Sécurité Routière',
      render: (r) => (
        <div>
          <strong style={{ color: 'var(--text-primary)', display: 'block' }}>{r.LibelleFormule}</strong>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#38bdf8' }}>{r.Code}</span>
        </div>
      )
    },
    {
      header: 'Compagnie Partenaire',
      accessor: 'Compagnie',
      render: (r) => <span style={{ color: '#60a5fa', fontWeight: 600 }}>{r.Compagnie}</span>
    },
    {
      header: 'Capital Décès / Invalidité',
      render: (r) => (
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
          {Number(r.CapitalDeces).toLocaleString('fr-FR')} FCFA
        </span>
      )
    },
    {
      header: 'Frais Médicaux Plafond',
      render: (r) => (
        <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
          {Number(r.FraisMedicaux).toLocaleString('fr-FR')} FCFA
        </span>
      )
    },
    {
      header: 'Prime / Place / An',
      render: (r) => (
        <span style={{ color: '#34d399', fontFamily: 'var(--font-mono)', fontWeight: 800 }}>
          {Number(r.PrimeParPlace).toLocaleString('fr-FR')} FCFA
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
            setEditingFormule(r);
            setForm({
              code: r.Code,
              libelle: r.LibelleFormule,
              compagnie: r.Compagnie,
              capital_deces: r.CapitalDeces,
              capital_invalidite: r.CapitalInvalidite,
              frais_medicaux: r.FraisMedicaux,
              prime_place: r.PrimeParPlace,
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
            <ShieldCheck size={28} color="#34d399" />
            Sécurité routière
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Formules de la garantie des personnes transportées : capitaux et prime par place.
          </p>
        </div>

        <button
          className="btn btn-primary"
          onClick={() => {
            setEditingFormule(null);
            setForm({
              code: '',
              libelle: '',
              compagnie: 'NSIA ASSURANCES CI',
              capital_deces: 1000000,
              capital_invalidite: 1000000,
              frais_medicaux: 100000,
              prime_place: 2500,
            });
            setIsModalOpen(true);
          }}
        >
          <Plus size={16} /> Nouvelle Formule Sécurité
        </button>
      </div>

      {/* Table */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable columns={columns} data={formules} searchPlaceholder="Filtrer une formule ou compagnie..." />
      </div>

      {/* Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingFormule ? 'Modifier la Formule Sécurité' : 'Nouvelle Formule de Sécurité Routière'}
      >
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Libellé de la Formule (* requis)</label>
            <input
              type="text"
              className="form-control"
              value={form.libelle}
              onChange={(e) => setForm({ ...form, libelle: e.target.value })}
              required
              placeholder="Ex: Sécurité Routière Standard"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Code Formule</label>
              <input
                type="text"
                className="form-control"
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                placeholder="Ex: SEC_STD"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Compagnie Partenaire</label>
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
              <label className="form-label">Capital Décès (FCFA)</label>
              <input
                type="number"
                className="form-control"
                value={form.capital_deces}
                onChange={(e) => setForm({ ...form, capital_deces: Number(e.target.value) })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Capital Invalidité (FCFA)</label>
              <input
                type="number"
                className="form-control"
                value={form.capital_invalidite}
                onChange={(e) => setForm({ ...form, capital_invalidite: Number(e.target.value) })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Frais Médicaux (FCFA)</label>
              <input
                type="number"
                className="form-control"
                value={form.frais_medicaux}
                onChange={(e) => setForm({ ...form, frais_medicaux: Number(e.target.value) })}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Prime par Place Assurée / An (FCFA)</label>
            <input
              type="number"
              className="form-control"
              value={form.prime_place}
              onChange={(e) => setForm({ ...form, prime_place: Number(e.target.value) })}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Annuler</button>
            <button type="submit" className="btn btn-primary">Enregistrer la Formule</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default ParametrageSecuritePage;
