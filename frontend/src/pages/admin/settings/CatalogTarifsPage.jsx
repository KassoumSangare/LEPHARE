import React, { useState, useEffect } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { DeleteConfirmModal } from '../../../components/common/DeleteConfirmModal';
import { Sliders, Plus, Edit2, FileText, Check, Trash2 } from 'lucide-react';
import { useToast } from '../../../context/ToastContext';
import { dataStore } from '../../../api/dataStore';
import { settingsApi } from '../../../api/endpoints';
import { formatDate } from '../../../utils/dateUtils';

export const CatalogTarifsPage = () => {
  const { success } = useToast();

  const [tarifs, setTarifs] = useState(() => dataStore.getTarifs());
  const [products, setProducts] = useState(() => dataStore.getProducts());

  useEffect(() => {
    // Charger les 26 tarifs réels de Django configuration_api/tarif/
    settingsApi.getTarifs().then((res) => {
      if (Array.isArray(res) && res.length > 0) {
        const mapped = res.map((t) => ({
          id: t.IdTarif || t.id,
          libelle: t.Libelle || t.libelle,
          produit: t.CodeCategorie ? `Catégorie ${t.CodeCategorie}` : (t.produit || 'Automobile VP'),
          taux_taxe: t.NatAccessoires ? '14.5% + Accessoires' : '14.5%',
          frais_accessoires: t.NatAccessoires ? 'Inclus CIMA' : '15 000 FCFA',
          date_effet: '2024-01-01',
          statut: 'Vigueur',
          base_calcul: `Usage ${t.CodeUsage || 'N/A'} - Réf: ${t.Reference || 'Standard CIMA'}`,
          raw: t,
        }));
        setTarifs(mapped);
      }
    }).catch(() => {});

    const unsub = dataStore.subscribe(() => {
      setTarifs(dataStore.getTarifs());
      setProducts(dataStore.getProducts());
    });
    return unsub;
  }, []);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedTarif, setSelectedTarif] = useState(null);
  const [deletingTarif, setDeletingTarif] = useState(null);

  const [newTarif, setNewTarif] = useState({
    libelle: '',
    produit: 'Automobile VP',
    taux_taxe: '14.5%',
    frais_accessoires: '15 000 FCFA',
    date_effet: '2026-01-01',
    statut: 'Vigueur',
    base_calcul: 'Tarification barème officiel CIMA',
  });

  const handleCreate = (e) => {
    e.preventDefault();
    const item = dataStore.saveTarif(newTarif);
    setTarifs(dataStore.getTarifs());
    setIsCreateModalOpen(false);
    success(`Nouvelle grille tarifaire "${item.libelle}" ajoutée.`);
  };

  const handleSaveEdit = (e) => {
    e.preventDefault();
    if (!selectedTarif) return;
    dataStore.updateTarif(selectedTarif.id, selectedTarif);
    setTarifs(dataStore.getTarifs());
    setIsEditModalOpen(false);
    success(`Grille tarifaire "${selectedTarif.libelle}" mise à jour.`);
  };

  const columns = [
    { header: 'Libellé de la Grille', accessor: 'libelle', render: (r) => <strong style={{ color: '#fff' }}>{r.libelle}</strong> },
    { header: 'Produit Assurantiel', accessor: 'produit', render: (r) => <span style={{ color: '#60a5fa' }}>{r.produit}</span> },
    { header: 'Taux Taxe Assurance', accessor: 'taux_taxe', render: (r) => <span style={{ fontFamily: 'var(--font-mono)' }}>{r.taux_taxe}</span> },
    { header: 'Accessoires Courtier', accessor: 'frais_accessoires', render: (r) => <span style={{ color: '#34d399' }}>{r.frais_accessoires}</span> },
    { header: 'Date Application', accessor: 'date_effet', render: (r) => formatDate(r.date_effet) },
    { header: 'Statut', accessor: 'statut', render: (r) => <StatusBadge label={r.statut} color="emerald" /> },
    {
      header: 'Actions',
      render: (r) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem' }}
            onClick={() => {
              setSelectedTarif(r);
              setIsDetailModalOpen(true);
            }}
          >
            Détails
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem' }}
            onClick={() => {
              setSelectedTarif({ ...r });
              setIsEditModalOpen(true);
            }}
          >
            Modifier
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.25rem 0.45rem', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.25)' }}
            onClick={() => setDeletingTarif(r)}
            title="Supprimer la grille tarifaire"
          >
            <Trash2 size={13} />
          </button>
        </div>
      ),
    },
  ];

  const standardProducts = [
    'Automobile VP',
    'Auto Flotte',
    'MRH',
    'Santé Groupe',
    'IA Standard',
    'Voyage & Schengen',
    'Transport Facultés',
  ];

  const allProductOptions = Array.from(
    new Set([
      ...standardProducts,
      ...products.map((p) => p.nom || p.code_produit),
    ])
  ).sort((a, b) => String(a).localeCompare(String(b), 'fr-FR', { sensitivity: 'base' }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Sliders size={26} color="#fbbf24" />
            Grilles Tarifaires, Accessoires & Taxes
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Paramétrage des barèmes de calcul, coefficients de durée, frais de gestion et taxes CIMA.
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setIsCreateModalOpen(true)}>
          <Plus size={16} /> Nouvelle Grille Tarifaire
        </button>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable columns={columns} data={tarifs} searchPlaceholder="Filtrer une grille ou barème..." />
      </div>

      {/* Modal Créer Grille */}
      <Modal isOpen={isCreateModalOpen} onClose={() => setIsCreateModalOpen(false)} title="Nouvelle Grille Tarifaire">
        <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Libellé de la Grille *</label>
            <input
              type="text"
              className="form-control"
              required
              placeholder="Ex: Barème Automobile 2026 Zone 1"
              value={newTarif.libelle}
              onChange={(e) => setNewTarif({ ...newTarif, libelle: e.target.value })}
            />
          </div>

          <div className="responsive-form-row">
            <div className="form-group">
              <label className="form-label">Produit Assurantiel</label>
              <select
                className="form-control"
                value={newTarif.produit}
                onChange={(e) => setNewTarif({ ...newTarif, produit: e.target.value })}
              >
                {allProductOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Taux Taxe Assurance CIMA</label>
              <input
                type="text"
                className="form-control"
                value={newTarif.taux_taxe}
                onChange={(e) => setNewTarif({ ...newTarif, taux_taxe: e.target.value })}
              />
            </div>
          </div>

          <div className="responsive-form-row">
            <div className="form-group">
              <label className="form-label">Frais Accessoires Courtier</label>
              <input
                type="text"
                className="form-control"
                value={newTarif.frais_accessoires}
                onChange={(e) => setNewTarif({ ...newTarif, frais_accessoires: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Date d'Application</label>
              <input
                type="date"
                className="form-control"
                value={newTarif.date_effet}
                onChange={(e) => setNewTarif({ ...newTarif, date_effet: e.target.value })}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Base de Calcul / Formule</label>
            <input
              type="text"
              className="form-control"
              value={newTarif.base_calcul}
              onChange={(e) => setNewTarif({ ...newTarif, base_calcul: e.target.value })}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsCreateModalOpen(false)}>
              Annuler
            </button>
            <button type="submit" className="btn btn-primary">
              <Check size={16} /> Enregistrer la Grille
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Modifier Grille */}
      {selectedTarif && (
        <Modal isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)} title={`Modifier Grille – ${selectedTarif.libelle}`}>
          <form onSubmit={handleSaveEdit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="responsive-form-row">
              <div className="form-group">
                <label className="form-label">Libellé</label>
                <input
                  type="text"
                  className="form-control"
                  value={selectedTarif.libelle}
                  onChange={(e) => setSelectedTarif({ ...selectedTarif, libelle: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Produit Assurantiel</label>
                <select
                  className="form-control"
                  value={selectedTarif.produit}
                  onChange={(e) => setSelectedTarif({ ...selectedTarif, produit: e.target.value })}
                >
                  {allProductOptions.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="responsive-form-row">
              <div className="form-group">
                <label className="form-label">Taux Taxe CIMA</label>
                <input
                  type="text"
                  className="form-control"
                  value={selectedTarif.taux_taxe}
                  onChange={(e) => setSelectedTarif({ ...selectedTarif, taux_taxe: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Frais Accessoires</label>
                <input
                  type="text"
                  className="form-control"
                  value={selectedTarif.frais_accessoires}
                  onChange={(e) => setSelectedTarif({ ...selectedTarif, frais_accessoires: e.target.value })}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Base de Calcul / Formule</label>
              <input
                type="text"
                className="form-control"
                value={selectedTarif.base_calcul}
                onChange={(e) => setSelectedTarif({ ...selectedTarif, base_calcul: e.target.value })}
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

      {/* Modal Détails Grille */}
      {selectedTarif && (
        <Modal isOpen={isDetailModalOpen} onClose={() => setIsDetailModalOpen(false)} title={`Barème Tarifaire – ${selectedTarif.libelle}`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ background: 'rgba(251,191,36,0.08)', padding: '0.85rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(251,191,36,0.2)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Produit Associé</div>
              <div style={{ fontSize: '1rem', fontWeight: 800, color: '#fff' }}>{selectedTarif.produit}</div>
              <div style={{ fontSize: '0.75rem', color: '#fbbf24', marginTop: '2px' }}>En vigueur depuis le {selectedTarif.date_effet}</div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.825rem' }}>
              <div style={{ padding: '0.65rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>TAXE D'ASSURANCE CIMA</span>
                <strong style={{ color: '#fbbf24' }}>{selectedTarif.taux_taxe}</strong>
              </div>
              <div style={{ padding: '0.65rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>ACCESSOIRES COURTIER</span>
                <strong style={{ color: '#34d399' }}>{selectedTarif.frais_accessoires}</strong>
              </div>
            </div>

            <div style={{ padding: '0.75rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '0.8rem' }}>
              <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>RÈGLE ET PARAMÈTRE DE CALCUL</span>
              <div>{selectedTarif.base_calcul}</div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setIsDetailModalOpen(false)}>
                Fermer
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  window.print();
                  success('Impression de la grille tarifaire lancée.');
                }}
              >
                Imprimer
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal Suppression Grille */}
      <DeleteConfirmModal
        isOpen={!!deletingTarif}
        onClose={() => setDeletingTarif(null)}
        itemType="grille tarifaire"
        itemName={deletingTarif?.libelle}
        itemCode={deletingTarif?.produit}
        validation={{ allowed: true }}
        onConfirm={() => {
          if (deletingTarif) {
            dataStore.deleteTarif(deletingTarif.id);
            setTarifs(dataStore.getTarifs());
            success(`Grille tarifaire ${deletingTarif.libelle} supprimée.`);
            setDeletingTarif(null);
          }
        }}
      />
    </div>
  );
};

export default CatalogTarifsPage;
