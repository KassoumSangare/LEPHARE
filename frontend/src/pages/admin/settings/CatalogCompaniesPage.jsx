import React, { useState, useEffect } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { DeleteConfirmModal } from '../../../components/common/DeleteConfirmModal';
import { Building2, Plus, Phone, Mail, Check, FileText, Trash2 } from 'lucide-react';
import { settingsApi } from '../../../api/endpoints';
import { dataStore } from '../../../api/dataStore';
import { validateBusinessRule } from '../../../utils/rbac';
import { useToast } from '../../../context/ToastContext';
import { useNavigate } from 'react-router-dom';

export const CatalogCompaniesPage = () => {
  const { success } = useToast();
  const navigate = useNavigate();

  const [companies, setCompanies] = useState(() => dataStore.getCompanies());

  useEffect(() => {
    // Charger les compagnies réelles de la base Django (30 compagnies en BDD)
    settingsApi.getCompanies().then((res) => {
      if (Array.isArray(res) && res.length > 0) {
        const mapped = res.map((c) => ({
          id: c.IdCompagnie || c.id,
          code: c.CodeAsaci || c.code || `CIE-${c.IdCompagnie || c.id}`,
          nom: c.RaisonSociale || c.nom,
          code_asaci: c.CodeAsaci || c.code_asaci || 'N/A',
          telephone: c.Telephone || c.telephone || '+225 27 20 00 00',
          email: c.Email || c.email || 'contact@assurance.ci',
          branches: c.branches || 'Auto, Santé, MRH, IA, Transport, Voyage',
          statut: c.statut || 'Partenaire Actif',
          statut_badge: 'emerald',
          raw: c,
        }));
        setCompanies(mapped);
      }
    }).catch(() => {});

    const unsub = dataStore.subscribe(() => {
      setCompanies(dataStore.getCompanies());
    });
    return unsub;
  }, []);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [deletingCompany, setDeletingCompany] = useState(null);
  const [deleteValidation, setDeleteValidation] = useState({ allowed: true });

  const [newCompany, setNewCompany] = useState({
    code: '',
    nom: '',
    code_asaci: '',
    telephone: '+225 ',
    email: '',
    branches: 'Auto, MRH, Santé',
    statut: 'Partenaire Actif',
  });

  const handleCreate = (e) => {
    e.preventDefault();
    const item = dataStore.saveCompany({
      ...newCompany,
      code: newCompany.code.toUpperCase(),
      code_asaci: newCompany.code_asaci.toUpperCase() || `ASACI_${newCompany.code.toUpperCase()}`,
    });
    setCompanies(dataStore.getCompanies());
    setIsCreateModalOpen(false);
    success(`Compagnie partenaire "${item.nom}" ajoutée avec succès.`);
  };

  const handleSaveEdit = (e) => {
    e.preventDefault();
    if (!selectedCompany) return;
    dataStore.updateCompany(selectedCompany.id, selectedCompany);
    setCompanies(dataStore.getCompanies());
    setIsEditModalOpen(false);
    success(`Données de ${selectedCompany.nom} mises à jour.`);
  };

  const columns = [
    { header: 'Code', accessor: 'code', render: (r) => <strong style={{ color: '#60a5fa' }}>{r.code}</strong> },
    { header: 'Raison Sociale de la Compagnie', accessor: 'nom', render: (r) => <div style={{ fontWeight: 600, color: '#fff' }}>{r.nom}</div> },
    { header: 'Code ASACI', accessor: 'code_asaci', render: (r) => <span style={{ fontFamily: 'var(--font-mono)', color: '#34d399' }}>{r.code_asaci}</span> },
    { header: 'Téléphone', accessor: 'telephone' },
    { header: 'Email Contact', accessor: 'email' },
    { header: 'Branches Agréées', accessor: 'branches' },
    { header: 'Statut', accessor: 'statut', render: (r) => <StatusBadge label={r.statut} color="emerald" /> },
    {
      header: 'Actions',
      render: (r) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem' }}
            onClick={() => {
              setSelectedCompany(r);
              setIsDetailModalOpen(true);
            }}
          >
            Fiche
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem' }}
            onClick={() => {
              setSelectedCompany({ ...r });
              setIsEditModalOpen(true);
            }}
          >
            Modifier
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.25rem 0.45rem', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.25)' }}
            onClick={() => {
              const check = validateBusinessRule('delete', 'conventions', r, dataStore);
              setDeleteValidation(check);
              setDeletingCompany(r);
            }}
            title="Supprimer la compagnie partenaire"
          >
            <Trash2 size={13} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Building2 size={26} color="#3b82f6" />
            Compagnies partenaires
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Les assureurs avec qui le cabinet travaille : agréments, codes ASACI, modalités de reversement.
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setIsCreateModalOpen(true)}>
          <Plus size={16} /> Nouvelle Compagnie
        </button>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable columns={columns} data={companies} searchPlaceholder="Filtrer une compagnie d'assurance..." />
      </div>

      {/* Modal Créer Compagnie */}
      <Modal isOpen={isCreateModalOpen} onClose={() => setIsCreateModalOpen(false)} title="Enregistrer une Compagnie Partenaire">
        <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="responsive-form-row">
            <div className="form-group">
              <label className="form-label">Code Compagnie (Court) *</label>
              <input
                type="text"
                className="form-control"
                required
                placeholder="Ex: SANLAM ou WAFA"
                value={newCompany.code}
                onChange={(e) => setNewCompany({ ...newCompany, code: e.target.value.toUpperCase() })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Code Passerelle ASACI</label>
              <input
                type="text"
                className="form-control"
                placeholder="Ex: ASACI_SANLAM"
                value={newCompany.code_asaci}
                onChange={(e) => setNewCompany({ ...newCompany, code_asaci: e.target.value })}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Dénomination Sociale Complète *</label>
            <input
              type="text"
              className="form-control"
              required
              placeholder="Ex: SANLAM Assurances Côte d'Ivoire"
              value={newCompany.nom}
              onChange={(e) => setNewCompany({ ...newCompany, nom: e.target.value })}
            />
          </div>

          <div className="responsive-form-row">
            <div className="form-group">
              <label className="form-label">Téléphone Direct</label>
              <input
                type="text"
                className="form-control"
                value={newCompany.telephone}
                onChange={(e) => setNewCompany({ ...newCompany, telephone: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Email Professionnel</label>
              <input
                type="email"
                className="form-control"
                value={newCompany.email}
                onChange={(e) => setNewCompany({ ...newCompany, email: e.target.value })}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Branches Agréées</label>
            <input
              type="text"
              className="form-control"
              placeholder="Ex: Auto, MRH, Santé, Transport, Responsabilité Civile"
              value={newCompany.branches}
              onChange={(e) => setNewCompany({ ...newCompany, branches: e.target.value })}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsCreateModalOpen(false)}>
              Annuler
            </button>
            <button type="submit" className="btn btn-primary">
              <Check size={16} /> Enregistrer la Compagnie
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Modifier Compagnie */}
      {selectedCompany && (
        <Modal isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)} title={`Modifier Partenaire – ${selectedCompany.code}`}>
          <form onSubmit={handleSaveEdit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Raison Sociale</label>
              <input
                type="text"
                className="form-control"
                value={selectedCompany.nom}
                onChange={(e) => setSelectedCompany({ ...selectedCompany, nom: e.target.value })}
              />
            </div>

            <div className="responsive-form-row">
              <div className="form-group">
                <label className="form-label">Code ASACI</label>
                <input
                  type="text"
                  className="form-control"
                  value={selectedCompany.code_asaci}
                  onChange={(e) => setSelectedCompany({ ...selectedCompany, code_asaci: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Statut</label>
                <select
                  className="form-control"
                  value={selectedCompany.statut}
                  onChange={(e) => setSelectedCompany({ ...selectedCompany, statut: e.target.value })}
                >
                  <option value="En Révision Convention">En Révision Convention</option>
                  <option value="Partenaire Actif">Partenaire Actif</option>
                  <option value="Suspendu">Suspendu</option>
                </select>
              </div>
            </div>

            <div className="responsive-form-row">
              <div className="form-group">
                <label className="form-label">Téléphone</label>
                <input
                  type="text"
                  className="form-control"
                  value={selectedCompany.telephone}
                  onChange={(e) => setSelectedCompany({ ...selectedCompany, telephone: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input
                  type="email"
                  className="form-control"
                  value={selectedCompany.email}
                  onChange={(e) => setSelectedCompany({ ...selectedCompany, email: e.target.value })}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Branches Agréées</label>
              <input
                type="text"
                className="form-control"
                value={selectedCompany.branches}
                onChange={(e) => setSelectedCompany({ ...selectedCompany, branches: e.target.value })}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setIsEditModalOpen(false)}>
                Annuler
              </button>
              <button type="submit" className="btn btn-primary">
                Sauvegarder
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal Fiche Compagnie & Passerelle */}
      {selectedCompany && (
        <Modal isOpen={isDetailModalOpen} onClose={() => setIsDetailModalOpen(false)} title={`Fiche Partenaire – ${selectedCompany.nom}`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ background: 'rgba(37,99,235,0.08)', padding: '0.85rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(37,99,235,0.2)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Porteur de Risque Agréé</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#fff' }}>{selectedCompany.nom}</div>
              <div style={{ fontSize: '0.75rem', color: '#60a5fa', fontFamily: 'var(--font-mono)' }}>Identifiant Code : {selectedCompany.code}</div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.825rem' }}>
              <div style={{ padding: '0.65rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>CODE ASACI OCI</span>
                <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{selectedCompany.code_asaci}</strong>
              </div>
              <div style={{ padding: '0.65rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>STATUT CONVENTION</span>
                <strong style={{ color: '#60a5fa' }}>{selectedCompany.statut}</strong>
              </div>
              <div style={{ padding: '0.65rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>CONTACT TÉLÉPHONIQUE</span>
                <div>{selectedCompany.telephone}</div>
              </div>
              <div style={{ padding: '0.65rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>EMAIL GESTION</span>
                <div>{selectedCompany.email}</div>
              </div>
            </div>

            <div style={{ padding: '0.75rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '0.8rem' }}>
              <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>BRANCHES COUVERTES</span>
              <div>{selectedCompany.branches}</div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setIsDetailModalOpen(false);
                  navigate('/admin/conventions');
                }}
              >
                Voir Convention & Plafonds
              </button>
              <button type="button" className="btn btn-primary" onClick={() => setIsDetailModalOpen(false)}>
                Fermer
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal Suppression Compagnie */}
      <DeleteConfirmModal
        isOpen={!!deletingCompany}
        onClose={() => setDeletingCompany(null)}
        itemType="compagnie partenaire"
        itemName={deletingCompany?.nom}
        itemCode={deletingCompany?.code}
        validation={deleteValidation}
        onConfirm={() => {
          if (deletingCompany) {
            try {
              dataStore.deleteCompany(deletingCompany.id);
              setCompanies(dataStore.getCompanies());
              success(`Compagnie ${deletingCompany.nom} supprimée.`);
              setDeletingCompany(null);
            } catch (err) {
              toastError(err.message);
            }
          }
        }}
      />
    </div>
  );
};

export default CatalogCompaniesPage;
