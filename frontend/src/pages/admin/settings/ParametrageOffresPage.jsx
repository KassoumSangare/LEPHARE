import React, { useState, useEffect, useMemo } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { DeleteConfirmModal } from '../../../components/common/DeleteConfirmModal';
import {
  Tag,
  Plus,
  Edit2,
  Trash2,
  Layers,
  ShieldCheck,
  Check,
  Package,
  Building2,
  Sliders,
  Sparkles
} from 'lucide-react';
import { settingsApi } from '../../../api/endpoints';
import { dataStore } from '../../../api/dataStore';
import { useToast } from '../../../context/ToastContext';
import { sortUniqueBy } from '../../../utils/sortUtils';

export const ParametrageOffresPage = () => {
  const { success, error: toastError } = useToast();
  const [activeTab, setActiveTab] = useState('offres'); // 'offres' | 'matrice'

  const [products, setProducts] = useState(() => dataStore.getProducts());
  const [companies, setCompanies] = useState(() => dataStore.getCompanies());
  const [guarantees, setGuarantees] = useState(() => dataStore.getGuarantees());

  const [offres, setOffres] = useState([
    { id: 1, IdOffre: 1, CodeOffre: 'AUTO_TIERS', LibelleOffre: 'Formule Tiers Simple (Responsabilité Civile)', IdProduit: 1, ProduitNom: 'Automobile VP', Ordre: 1, Statut: 'Actif', nb_garanties: 3 },
    { id: 2, IdOffre: 2, CodeOffre: 'AUTO_TIERS_CONFORT', LibelleOffre: 'Formule Tiers Confort (RC + Incendie + Vol)', IdProduit: 1, ProduitNom: 'Automobile VP', Ordre: 2, Statut: 'Actif', nb_garanties: 5 },
    { id: 3, IdOffre: 3, CodeOffre: 'AUTO_TOUS_RISQUES', LibelleOffre: 'Formule Tous Risques Intégrale', IdProduit: 1, ProduitNom: 'Automobile VP', Ordre: 3, Statut: 'Actif', nb_garanties: 8 },
    { id: 4, IdOffre: 4, CodeOffre: 'MRH_ESSENTIEL', LibelleOffre: 'Formule Habitation Essentielle', IdProduit: 3, ProduitNom: 'Multi-Risques Habitation', Ordre: 1, Statut: 'Actif', nb_garanties: 4 },
    { id: 5, IdOffre: 5, CodeOffre: 'MRH_SERENITE', LibelleOffre: 'Formule Habitation Sérénité Premium', IdProduit: 3, ProduitNom: 'Multi-Risques Habitation', Ordre: 2, Statut: 'Actif', nb_garanties: 7 },
    { id: 6, IdOffre: 6, CodeOffre: 'VOY_SCHENGEN', LibelleOffre: 'Formule Voyage Schengen Conforme Visa', IdProduit: 6, ProduitNom: 'Voyage & Schengen', Ordre: 1, Statut: 'Actif', nb_garanties: 5 },
    { id: 7, IdOffre: 7, CodeOffre: 'TRP_ALL_RISKS', LibelleOffre: 'Facultés Tous Risques Maritime Clauses A', IdProduit: 8, ProduitNom: 'Transport', Ordre: 1, Statut: 'Actif', nb_garanties: 4 },
  ]);

  const [matrice, setMatrice] = useState([
    { id: 1, IdOffre: 1, OffreNom: 'Formule Tiers Simple', GarantieNom: 'RESPONSABILITE CIVILE AUTOMOBILE', Obligatoire: true, TauxFranchise: '0%', FranchiseMin: '0 FCFA', FranchiseMax: '0 FCFA' },
    { id: 2, IdOffre: 1, OffreNom: 'Formule Tiers Simple', GarantieNom: 'DEFENSE ET RECOURS DES TIERS', Obligatoire: true, TauxFranchise: '0%', FranchiseMin: '0 FCFA', FranchiseMax: '0 FCFA' },
    { id: 3, IdOffre: 1, OffreNom: 'Formule Tiers Simple', GarantieNom: 'SECURITE ROUTIERE PERSONNES TRANSPORTEES', Obligatoire: false, TauxFranchise: '0%', FranchiseMin: 'Sans', FranchiseMax: 'Sans' },
    { id: 4, IdOffre: 3, OffreNom: 'Formule Tous Risques Intégrale', GarantieNom: 'DOMMAGES TOUS ACCIDENTS (TIERCE)', Obligatoire: true, TauxFranchise: '10%', FranchiseMin: '50 000 FCFA', FranchiseMax: '500 000 FCFA' },
    { id: 5, IdOffre: 3, OffreNom: 'Formule Tous Risques Intégrale', GarantieNom: 'BRIS DE GLACES (PARE-BRISE)', Obligatoire: true, TauxFranchise: '0%', FranchiseMin: '0 FCFA', FranchiseMax: 'Plafond 1 500 000' },
  ]);

  const [isOffreModalOpen, setIsOffreModalOpen] = useState(false);
  const [isMatriceModalOpen, setIsMatriceModalOpen] = useState(false);
  const [editingOffre, setEditingOffre] = useState(null);
  const [deletingItem, setDeletingItem] = useState(null);

  const [offreForm, setOffreForm] = useState({
    libelle: '',
    code: '',
    id_produit: 1,
    ordre: 1,
    statut: 'Actif',
  });

  const [matriceForm, setMatriceForm] = useState({
    id_offre: 1,
    id_garantie: 1,
    obligatoire: true,
    taux_franchise: '10%',
    franchise_min: '50 000 FCFA',
    franchise_max: '250 000 FCFA',
  });

  useEffect(() => {
    settingsApi.getOffres?.().then((res) => {
      if (Array.isArray(res) && res.length > 0) {
        const mapped = res.map((o) => ({
          id: o.IdOffre || o.id,
          IdOffre: o.IdOffre || o.id,
          CodeOffre: o.CodeOffre || `OFFRE_${o.IdOffre}`,
          LibelleOffre: o.LibelleOffre || o.libelle,
          IdProduit: o.IdProduit || 1,
          ProduitNom: o.ProduitNom || 'Automobile',
          Ordre: o.OrdreAffichage || 1,
          Statut: 'Actif',
          nb_garanties: 5,
        }));
        setOffres(mapped);
      }
    }).catch(() => {});
  }, []);

  const handleSaveOffre = (e) => {
    e.preventDefault();
    if (!offreForm.libelle) return;
    const prod = products.find(p => p.id === Number(offreForm.id_produit)) || { nom: 'Automobile' };
    const newOffre = {
      id: editingOffre ? editingOffre.id : Date.now(),
      IdOffre: editingOffre ? editingOffre.IdOffre : Date.now(),
      CodeOffre: offreForm.code || `OFFRE_${Date.now()}`,
      LibelleOffre: offreForm.libelle,
      IdProduit: Number(offreForm.id_produit),
      ProduitNom: prod.nom,
      Ordre: Number(offreForm.ordre),
      Statut: offreForm.statut,
      nb_garanties: 4,
    };
    if (editingOffre) {
      setOffres(prev => prev.map(o => o.id === editingOffre.id ? newOffre : o));
      success(`Formule commerciale "${newOffre.LibelleOffre}" mise à jour.`);
    } else {
      setOffres(prev => [newOffre, ...prev]);
      success(`Formule commerciale "${newOffre.LibelleOffre}" créée.`);
    }
    setIsOffreModalOpen(false);
  };

  const handleSaveMatrice = (e) => {
    e.preventDefault();
    const selOffre = offres.find(o => o.IdOffre === Number(matriceForm.id_offre));
    const selGar = guarantees.find(g => g.id === Number(matriceForm.id_garantie));
    const newLink = {
      id: Date.now(),
      IdOffre: Number(matriceForm.id_offre),
      OffreNom: selOffre ? selOffre.LibelleOffre : 'Formule',
      GarantieNom: selGar ? selGar.libelle : 'Garantie',
      Obligatoire: Boolean(matriceForm.obligatoire),
      TauxFranchise: matriceForm.taux_franchise,
      FranchiseMin: matriceForm.franchise_min,
      FranchiseMax: matriceForm.franchise_max,
    };
    setMatrice(prev => [newLink, ...prev]);
    success(`Garantie rattachée à la formule avec succès.`);
    setIsMatriceModalOpen(false);
  };

  const offreColumns = [
    {
      header: 'Libellé de la Formule',
      render: (r) => (
        <div>
          <strong style={{ color: 'var(--text-primary)', display: 'block' }}>{r.LibelleOffre}</strong>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#60a5fa' }}>{r.CodeOffre}</span>
        </div>
      )
    },
    {
      header: 'Produit Assurantiel',
      accessor: 'ProduitNom',
      render: (r) => <span style={{ color: '#38bdf8', fontWeight: 600 }}>{r.ProduitNom}</span>
    },
    {
      header: 'Ordre d\'Affichage',
      accessor: 'Ordre',
      render: (r) => <span style={{ fontFamily: 'var(--font-mono)' }}>Position #{r.Ordre}</span>
    },
    {
      header: 'Garanties Liées',
      render: (r) => <span style={{ color: '#34d399', fontWeight: 700 }}>{r.nb_garanties} garanties</span>
    },
    {
      header: 'Statut',
      accessor: 'Statut',
      render: (r) => <StatusBadge label={r.Statut} color="emerald" />
    },
    {
      header: 'Actions',
      render: (r) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
            onClick={() => {
              setEditingOffre(r);
              setOffreForm({
                libelle: r.LibelleOffre,
                code: r.CodeOffre,
                id_produit: r.IdProduit,
                ordre: r.Ordre,
                statut: r.Statut,
              });
              setIsOffreModalOpen(true);
            }}
          >
            Modifier
          </button>
          <button
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.45rem', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)' }}
            onClick={() => setDeletingItem(r)}
          >
            <Trash2 size={13} />
          </button>
        </div>
      )
    }
  ];

  const matriceColumns = [
    {
      header: 'Offre Commerciale',
      accessor: 'OffreNom',
      render: (r) => <strong style={{ color: '#38bdf8' }}>{r.OffreNom}</strong>
    },
    {
      header: 'Garantie CIMA Associée',
      accessor: 'GarantieNom',
      render: (r) => <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{r.GarantieNom}</span>
    },
    {
      header: 'Statut dans l\'Offre',
      render: (r) => (
        <span style={{ fontSize: '0.8rem', fontWeight: 700, color: r.Obligatoire ? '#34d399' : '#fbbf24' }}>
          {r.Obligatoire ? '✓ Incluse d\'Office' : 'Optionnelle au Choix'}
        </span>
      )
    },
    {
      header: 'Franchise CIMA',
      render: (r) => (
        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          {r.TauxFranchise} (Min: {r.FranchiseMin} / Max: {r.FranchiseMax})
        </span>
      )
    },
    {
      header: 'Actions',
      render: (r) => (
        <button
          className="btn btn-secondary"
          style={{ padding: '0.25rem 0.45rem', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)' }}
          onClick={() => {
            setMatrice(prev => prev.filter(m => m.id !== r.id));
            success('Association garantie retirée de la formule.');
          }}
        >
          <Trash2 size={13} />
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
            <Tag size={28} color="#0284c7" />
            Paramétrage des Offres & Formules Commerciales (OREOLE)
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Composition des formules (Tiers, Confort, Tous Risques) et matrice de liaison Offre ↔ Garanties avec franchises et critères d'inclusion.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {activeTab === 'offres' ? (
            <button
              className="btn btn-primary"
              onClick={() => {
                setEditingOffre(null);
                setOffreForm({
                  libelle: '',
                  code: '',
                  id_produit: products[0]?.id || 1,
                  ordre: 1,
                  statut: 'Actif',
                });
                setIsOffreModalOpen(true);
              }}
            >
              <Plus size={16} /> Nouvelle Offre
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={() => {
                setMatriceForm({
                  id_offre: offres[0]?.IdOffre || 1,
                  id_garantie: guarantees[0]?.id || 1,
                  obligatoire: true,
                  taux_franchise: '10%',
                  franchise_min: '50 000 FCFA',
                  franchise_max: '250 000 FCFA',
                });
                setIsMatriceModalOpen(true);
              }}
            >
              <Plus size={16} /> Associer une Garantie à l'Offre
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
        <button
          type="button"
          onClick={() => setActiveTab('offres')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.6rem 1.2rem',
            borderRadius: 'var(--radius-md)',
            border: 'none',
            fontSize: '0.875rem',
            fontWeight: activeTab === 'offres' ? 700 : 500,
            cursor: 'pointer',
            background: activeTab === 'offres' ? 'rgba(2, 132, 199, 0.15)' : 'transparent',
            color: activeTab === 'offres' ? '#38bdf8' : 'var(--text-muted)',
            borderBottom: activeTab === 'offres' ? '2px solid #0284c7' : '2px solid transparent',
          }}
        >
          <Tag size={16} />
          <span>Catalogue des Offres ({offres.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('matrice')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.6rem 1.2rem',
            borderRadius: 'var(--radius-md)',
            border: 'none',
            fontSize: '0.875rem',
            fontWeight: activeTab === 'matrice' ? 700 : 500,
            cursor: 'pointer',
            background: activeTab === 'matrice' ? 'rgba(2, 132, 199, 0.15)' : 'transparent',
            color: activeTab === 'matrice' ? '#38bdf8' : 'var(--text-muted)',
            borderBottom: activeTab === 'matrice' ? '2px solid #0284c7' : '2px solid transparent',
          }}
        >
          <Sliders size={16} />
          <span>Matrice Offres ↔ Garanties ({matrice.length})</span>
        </button>
      </div>

      {/* Content Table */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable
          columns={activeTab === 'offres' ? offreColumns : matriceColumns}
          data={activeTab === 'offres' ? offres : matrice}
          searchPlaceholder={activeTab === 'offres' ? 'Rechercher une formule...' : 'Filtrer les associations...'}
        />
      </div>

      {/* Modal Créer/Modifier Offre */}
      <Modal
        isOpen={isOffreModalOpen}
        onClose={() => setIsOffreModalOpen(false)}
        title={editingOffre ? 'Modifier l\'Offre Commerciale' : 'Nouvelle Formule Commerciale'}
      >
        <form onSubmit={handleSaveOffre} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Libellé de la Formule (* requis)</label>
            <input
              type="text"
              className="form-control"
              value={offreForm.libelle}
              onChange={(e) => setOffreForm({ ...offreForm, libelle: e.target.value })}
              required
              placeholder="Ex: Formule Tiers Collision Renforcée"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Code Formule</label>
              <input
                type="text"
                className="form-control"
                value={offreForm.code}
                onChange={(e) => setOffreForm({ ...offreForm, code: e.target.value.toUpperCase() })}
                placeholder="Ex: AUTO_TIERS_COLL"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Produit Assurantiel</label>
              <select
                className="form-control"
                value={offreForm.id_produit}
                onChange={(e) => setOffreForm({ ...offreForm, id_produit: Number(e.target.value) })}
              >
                {sortUniqueBy(products, (p) => p.nom || p.code_produit).map((p) => (
                  <option key={p.id} value={p.id}>{p.nom || p.code_produit}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Ordre d'Affichage dans le Devis</label>
              <input
                type="number"
                min="1"
                className="form-control"
                value={offreForm.ordre}
                onChange={(e) => setOffreForm({ ...offreForm, ordre: Number(e.target.value) })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Statut</label>
              <select
                className="form-control"
                value={offreForm.statut}
                onChange={(e) => setOffreForm({ ...offreForm, statut: e.target.value })}
              >
                <option value="Actif">Actif</option>
                <option value="Inactif">Inactif</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsOffreModalOpen(false)}>Annuler</button>
            <button type="submit" className="btn btn-primary">Enregistrer l'Offre</button>
          </div>
        </form>
      </Modal>

      {/* Modal Associer Garantie à Offre */}
      <Modal
        isOpen={isMatriceModalOpen}
        onClose={() => setIsMatriceModalOpen(false)}
        title="Associer une Garantie à une Offre Commerciale"
      >
        <form onSubmit={handleSaveMatrice} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Formule Commerciale Cible (* requis)</label>
            <select
              className="form-control"
              value={matriceForm.id_offre}
              onChange={(e) => setMatriceForm({ ...matriceForm, id_offre: Number(e.target.value) })}
            >
              {sortUniqueBy(offres, (o) => o.LibelleOffre).map((o) => (
                <option key={o.IdOffre} value={o.IdOffre}>{o.LibelleOffre} ({o.ProduitNom})</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Garantie à Inclure (* requis)</label>
            <select
              className="form-control"
              value={matriceForm.id_garantie}
              onChange={(e) => setMatriceForm({ ...matriceForm, id_garantie: Number(e.target.value) })}
            >
              {sortUniqueBy(guarantees, (g) => g.libelle).map((g) => (
                <option key={g.id} value={g.id}>{g.libelle} ({g.branche})</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={matriceForm.obligatoire}
                onChange={(e) => setMatriceForm({ ...matriceForm, obligatoire: e.target.checked })}
                style={{ width: '18px', height: '18px', accentColor: '#0284c7' }}
              />
              <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Garantie obligatoire acquise d'office dans cette offre</span>
            </label>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Taux Franchise</label>
              <input
                type="text"
                className="form-control"
                value={matriceForm.taux_franchise}
                onChange={(e) => setMatriceForm({ ...matriceForm, taux_franchise: e.target.value })}
                placeholder="Ex: 10%"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Franchise Minimum</label>
              <input
                type="text"
                className="form-control"
                value={matriceForm.franchise_min}
                onChange={(e) => setMatriceForm({ ...matriceForm, franchise_min: e.target.value })}
                placeholder="Ex: 50 000 FCFA"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Franchise Maximum</label>
              <input
                type="text"
                className="form-control"
                value={matriceForm.franchise_max}
                onChange={(e) => setMatriceForm({ ...matriceForm, franchise_max: e.target.value })}
                placeholder="Ex: 250 000 FCFA"
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsMatriceModalOpen(false)}>Annuler</button>
            <button type="submit" className="btn btn-primary">Valider la Liaison</button>
          </div>
        </form>
      </Modal>

      {/* Delete modal */}
      <DeleteConfirmModal
        isOpen={!!deletingItem}
        onClose={() => setDeletingItem(null)}
        itemType="offre commerciale"
        itemName={deletingItem?.LibelleOffre}
        itemCode={deletingItem?.CodeOffre}
        validation={{ allowed: true }}
        onConfirm={() => {
          if (deletingItem) {
            setOffres(prev => prev.filter(o => o.id !== deletingItem.id));
            success(`Offre ${deletingItem.LibelleOffre} supprimée.`);
            setDeletingItem(null);
          }
        }}
      />
    </div>
  );
};

export default ParametrageOffresPage;
