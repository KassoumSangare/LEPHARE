import React, { useState, useEffect, useMemo } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { DeleteConfirmModal } from '../../../components/common/DeleteConfirmModal';
import {
  Shield,
  Plus,
  Edit2,
  Trash2,
  Layers,
  Search,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  FolderTree,
  Filter
} from 'lucide-react';
import { settingsApi } from '../../../api/endpoints';
import { dataStore } from '../../../api/dataStore';
import { useToast } from '../../../context/ToastContext';

export const ParametrageGarantiesPage = () => {
  const { success, error: toastError } = useToast();
  const [activeTab, setActiveTab] = useState('garanties'); // 'garanties' | 'sousgaranties'

  // Données
  const [garanties, setGaranties] = useState(() => dataStore.getGuarantees());
  const [sousGaranties, setSousGaranties] = useState([]);
  const [products, setProducts] = useState(() => dataStore.getProducts());
  const [loading, setLoading] = useState(false);
  const [selectedBranche, setSelectedBranche] = useState('ALL');

  // Modals
  const [isGarantieModalOpen, setIsGarantieModalOpen] = useState(false);
  const [isSousGarantieModalOpen, setIsSousGarantieModalOpen] = useState(false);
  const [editingGarantie, setEditingGarantie] = useState(null);
  const [editingSousGarantie, setEditingSousGarantie] = useState(null);
  const [deletingItem, setDeletingItem] = useState(null);
  const [deleteType, setDeleteType] = useState('garantie');

  // Formulaires
  const [garantieForm, setGarantieForm] = useState({
    code: '',
    libelle: '',
    branche: 'Automobile',
    type: 'Obligatoire CIMA',
    tarification: 'Barème Règlementaire',
    taxe_cima: '14.5%',
    fga: true,
  });

  const [sousGarantieForm, setSousGarantieForm] = useState({
    id_garantie: 1,
    code: '',
    libelle: '',
    capital_defaut: 10000000,
    franchise_defaut: '10% (Min 50 000 FCFA)',
    prime_base: 25000,
    active: true,
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [garRes, sgRes] = await Promise.all([
        settingsApi.getGuarantees().catch(() => []),
        settingsApi.getSousGaranties().catch(() => []),
      ]);
      if (Array.isArray(garRes) && garRes.length > 0) {
        const mapped = garRes.map((g) => ({
          id: g.IdGarantie || g.id,
          code: g.CodeGarantie || g.code || `GAR-${g.IdGarantie}`,
          libelle: g.LibelleGarantie || g.libelle,
          branche: g.SaisieAuto ? 'Automobile' : g.SaisieRd ? 'Incendie & Risques Divers' : g.SaisieSante ? 'Santé' : g.SaisieTransport ? 'Transport' : 'Général',
          type: g.Active ? 'Obligatoire CIMA' : 'Optionnelle',
          tarification: 'Barème Réglementaire',
          taxe_cima: '14.5%',
          fga: Boolean(g.SaisieAuto),
          active: Boolean(g.Active),
        }));
        setGaranties(mapped);
      }
      if (Array.isArray(sgRes) && sgRes.length > 0) {
        setSousGaranties(sgRes);
      } else {
        // Fallback sous-garanties réalistes
        setSousGaranties([
          { id: 1, IdSousGarantie: 1, IdGarantie: 1, LibelleSousGarantie: 'Dommages Corporels aux Tiers', CodeSousGarantie: 'RC_CORP', Capital: 500000000, Franchise: 'Sans', Prime: 45000 },
          { id: 2, IdSousGarantie: 2, IdGarantie: 1, LibelleSousGarantie: 'Dommages Matériels aux Tiers', CodeSousGarantie: 'RC_MAT', Capital: 100000000, Franchise: 'Sans', Prime: 35000 },
          { id: 3, IdSousGarantie: 3, IdGarantie: 3, LibelleSousGarantie: 'Tierce Collision avec Tiers Identifié', CodeSousGarantie: 'DOMM_TIERCE', Capital: 25000000, Franchise: '10% Min 50 000', Prime: 85000 },
          { id: 4, IdSousGarantie: 4, IdGarantie: 4, LibelleSousGarantie: 'Incendie Véhicule & Explosion', CodeSousGarantie: 'INC_BASE', Capital: 20000000, Franchise: 'Sans', Prime: 25000 },
          { id: 5, IdSousGarantie: 5, IdGarantie: 5, LibelleSousGarantie: 'Vol Total avec Effraction', CodeSousGarantie: 'VOL_TOTAL', Capital: 20000000, Franchise: '10% Min 100 000', Prime: 40000 },
          { id: 6, IdSousGarantie: 6, IdGarantie: 6, LibelleSousGarantie: 'Pare-Brise et Vitres Latérales', CodeSousGarantie: 'BG_VITRES', Capital: 1000000, Franchise: 'Sans franchise', Prime: 18000 },
          { id: 7, IdSousGarantie: 7, IdGarantie: 7, LibelleSousGarantie: 'Décès Conducteur & Passagers', CodeSousGarantie: 'SEC_DECES', Capital: 5000000, Franchise: 'Sans', Prime: 12000 },
        ]);
      }
    } catch {
      toastError('Erreur de chargement des référentiels.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filtrage par branche
  const filteredGaranties = useMemo(() => {
    if (selectedBranche === 'ALL') return garanties;
    return garanties.filter((g) => g.branche.toLowerCase().includes(selectedBranche.toLowerCase()));
  }, [garanties, selectedBranche]);

  // Handlers Garantie
  const handleSaveGarantie = async (e) => {
    e.preventDefault();
    if (!garantieForm.code || !garantieForm.libelle) return;
    if (editingGarantie) {
      dataStore.updateGuarantee(editingGarantie.id, garantieForm);
      success(`Garantie "${garantieForm.libelle}" mise à jour.`);
    } else {
      dataStore.saveGuarantee(garantieForm);
      success(`Garantie "${garantieForm.libelle}" créée avec succès.`);
    }
    setGaranties(dataStore.getGuarantees());
    setIsGarantieModalOpen(false);
  };

  // Handlers Sous-Garantie
  const handleSaveSousGarantie = async (e) => {
    e.preventDefault();
    if (!sousGarantieForm.libelle) return;
    const newSg = {
      id: editingSousGarantie ? editingSousGarantie.id : Date.now(),
      IdSousGarantie: editingSousGarantie ? editingSousGarantie.IdSousGarantie : Date.now(),
      IdGarantie: Number(sousGarantieForm.id_garantie),
      LibelleSousGarantie: sousGarantieForm.libelle,
      CodeSousGarantie: sousGarantieForm.code || `SG_${Date.now()}`,
      Capital: Number(sousGarantieForm.capital_defaut),
      Franchise: sousGarantieForm.franchise_defaut,
      Prime: Number(sousGarantieForm.prime_base),
    };
    if (editingSousGarantie) {
      setSousGaranties(prev => prev.map(s => s.id === editingSousGarantie.id ? newSg : s));
      success(`Sous-garantie "${newSg.LibelleSousGarantie}" modifiée.`);
    } else {
      setSousGaranties(prev => [newSg, ...prev]);
      success(`Sous-garantie "${newSg.LibelleSousGarantie}" créée avec succès.`);
    }
    try {
      await settingsApi.createSousGarantie?.(newSg);
    } catch {}
    setIsSousGarantieModalOpen(false);
  };

  const garantieColumns = [
    {
      header: 'Code & Libellé',
      render: (r) => (
        <div>
          <strong style={{ color: 'var(--text-primary)', display: 'block' }}>{r.libelle}</strong>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#60a5fa' }}>{r.code}</span>
        </div>
      )
    },
    {
      header: 'Branche',
      accessor: 'branche',
      render: (r) => <span className="badge badge-purple">{r.branche}</span>
    },
    {
      header: 'Caractère',
      render: (r) => (
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: r.type?.includes('Obligatoire') ? '#f43f5e' : 'var(--text-secondary)' }}>
          {r.type}
        </span>
      )
    },
    {
      header: 'Tarification',
      accessor: 'tarification',
      render: (r) => <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{r.tarification}</span>
    },
    {
      header: 'Taxe CIMA',
      accessor: 'taxe_cima',
      render: (r) => <span style={{ fontWeight: 700, color: '#fbbf24' }}>{r.taxe_cima}</span>
    },
    {
      header: 'FGA',
      render: (r) => (
        <span style={{ color: r.fga ? '#34d399' : 'var(--text-muted)', fontWeight: 600, fontSize: '0.8rem' }}>
          {r.fga ? 'Oui' : 'Non'}
        </span>
      )
    },
    {
      header: 'Actions',
      render: (r) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
            onClick={() => {
              setEditingGarantie(r);
              setGarantieForm({
                code: r.code,
                libelle: r.libelle,
                branche: r.branche,
                type: r.type,
                tarification: r.tarification,
                taxe_cima: r.taxe_cima,
                fga: r.fga,
              });
              setIsGarantieModalOpen(true);
            }}
          >
            Modifier
          </button>
          <button
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.45rem', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)' }}
            onClick={() => {
              setDeleteType('garantie');
              setDeletingItem(r);
            }}
          >
            <Trash2 size={13} />
          </button>
        </div>
      )
    }
  ];

  const sousGarantieColumns = [
    {
      header: 'Sous-Garantie',
      render: (r) => (
        <div>
          <strong style={{ color: 'var(--text-primary)', display: 'block' }}>{r.LibelleSousGarantie}</strong>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#38bdf8' }}>{r.CodeSousGarantie || `SG-${r.IdSousGarantie}`}</span>
        </div>
      )
    },
    {
      header: 'Garantie Parente',
      render: (r) => {
        const parent = garanties.find(g => g.id === r.IdGarantie);
        return <span style={{ fontSize: '0.8rem', color: '#60a5fa', fontWeight: 600 }}>{parent ? parent.libelle : `Garantie #${r.IdGarantie}`}</span>;
      }
    },
    {
      header: 'Capital Garanti',
      render: (r) => (
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
          {Number(r.Capital || 0).toLocaleString()} FCFA
        </span>
      )
    },
    {
      header: 'Franchise par Défaut',
      render: (r) => <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{r.Franchise || 'Sans'}</span>
    },
    {
      header: 'Prime de Base',
      render: (r) => (
        <span style={{ color: '#34d399', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
          {Number(r.Prime || 0).toLocaleString()} FCFA
        </span>
      )
    },
    {
      header: 'Actions',
      render: (r) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
            onClick={() => {
              setEditingSousGarantie(r);
              setSousGarantieForm({
                id_garantie: r.IdGarantie,
                code: r.CodeSousGarantie || '',
                libelle: r.LibelleSousGarantie,
                capital_defaut: r.Capital || 0,
                franchise_defaut: r.Franchise || '',
                prime_base: r.Prime || 0,
                active: true,
              });
              setIsSousGarantieModalOpen(true);
            }}
          >
            Modifier
          </button>
          <button
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.45rem', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)' }}
            onClick={() => {
              setDeleteType('sous-garantie');
              setDeletingItem(r);
            }}
          >
            <Trash2 size={13} />
          </button>
        </div>
      )
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '1280px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Shield size={28} color="#3b82f6" />
            Paramétrage des Garanties & Sous-Garanties (OREOLE)
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Gestion du référentiel central des garanties et sous-garanties assurantielles : règles CIMA, capitaux, franchises et assujettissements.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {activeTab === 'garanties' ? (
            <button
              className="btn btn-primary"
              onClick={() => {
                setEditingGarantie(null);
                setGarantieForm({
                  code: '',
                  libelle: '',
                  branche: 'Automobile',
                  type: 'Obligatoire CIMA',
                  tarification: 'Barème Règlementaire',
                  taxe_cima: '14.5%',
                  fga: true,
                });
                setIsGarantieModalOpen(true);
              }}
            >
              <Plus size={16} /> Nouvelle Garantie
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={() => {
                setEditingSousGarantie(null);
                setSousGarantieForm({
                  id_garantie: garanties[0]?.id || 1,
                  code: '',
                  libelle: '',
                  capital_defaut: 10000000,
                  franchise_defaut: '10% (Min 50 000 FCFA)',
                  prime_base: 25000,
                  active: true,
                });
                setIsSousGarantieModalOpen(true);
              }}
            >
              <Plus size={16} /> Nouvelle Sous-Garantie
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
        <button
          type="button"
          onClick={() => setActiveTab('garanties')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.6rem 1.2rem',
            borderRadius: 'var(--radius-md)',
            border: 'none',
            fontSize: '0.875rem',
            fontWeight: activeTab === 'garanties' ? 700 : 500,
            cursor: 'pointer',
            background: activeTab === 'garanties' ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
            color: activeTab === 'garanties' ? '#60a5fa' : 'var(--text-muted)',
            borderBottom: activeTab === 'garanties' ? '2px solid #3b82f6' : '2px solid transparent',
          }}
        >
          <Shield size={16} />
          <span>Garanties Principales ({garanties.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('sousgaranties')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.6rem 1.2rem',
            borderRadius: 'var(--radius-md)',
            border: 'none',
            fontSize: '0.875rem',
            fontWeight: activeTab === 'sousgaranties' ? 700 : 500,
            cursor: 'pointer',
            background: activeTab === 'sousgaranties' ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
            color: activeTab === 'sousgaranties' ? '#60a5fa' : 'var(--text-muted)',
            borderBottom: activeTab === 'sousgaranties' ? '2px solid #3b82f6' : '2px solid transparent',
          }}
        >
          <Layers size={16} />
          <span>Sous-Garanties Granulaires ({sousGaranties.length})</span>
        </button>
      </div>

      {/* Main Table Panel */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        {activeTab === 'garanties' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Filtrer par Branche :</span>
            {['ALL', 'Automobile', 'Incendie', 'Santé', 'Transport', 'Voyage', 'Accidents'].map((b) => (
              <button
                key={b}
                type="button"
                onClick={() => setSelectedBranche(b)}
                style={{
                  padding: '0.3rem 0.75rem',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  border: selectedBranche === b ? '1px solid #3b82f6' : '1px solid var(--border-subtle)',
                  background: selectedBranche === b ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
                  color: selectedBranche === b ? '#60a5fa' : 'var(--text-muted)',
                }}
              >
                {b === 'ALL' ? 'Toutes les Branches' : b}
              </button>
            ))}
          </div>
        )}

        <DataTable
          columns={activeTab === 'garanties' ? garantieColumns : sousGarantieColumns}
          data={activeTab === 'garanties' ? filteredGaranties : sousGaranties}
          searchPlaceholder={activeTab === 'garanties' ? 'Rechercher une garantie...' : 'Rechercher une sous-garantie...'}
        />
      </div>

      {/* Modal Garantie */}
      <Modal
        isOpen={isGarantieModalOpen}
        onClose={() => setIsGarantieModalOpen(false)}
        title={editingGarantie ? 'Modifier la Garantie CIMA' : 'Créer une Garantie CIMA'}
      >
        <form onSubmit={handleSaveGarantie} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Libellé de la Garantie (* requis)</label>
            <input
              type="text"
              className="form-control"
              value={garantieForm.libelle}
              onChange={(e) => setGarantieForm({ ...garantieForm, libelle: e.target.value })}
              required
              placeholder="Ex: Responsabilité Civile Chef de Famille"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Code Technique</label>
              <input
                type="text"
                className="form-control"
                value={garantieForm.code}
                onChange={(e) => setGarantieForm({ ...garantieForm, code: e.target.value.toUpperCase() })}
                required
                placeholder="Ex: RC_CHEF"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Branche Métier</label>
              <select
                className="form-control"
                value={garantieForm.branche}
                onChange={(e) => setGarantieForm({ ...garantieForm, branche: e.target.value })}
              >
                <option value="Automobile">Automobile</option>
                <option value="Incendie & Risques Divers">Incendie & Risques Divers (MRH)</option>
                <option value="Santé">Santé & Maladie</option>
                <option value="Transport">Transport & Facultés</option>
                <option value="Voyage">Voyage & Schengen</option>
                <option value="Accidents Corporels">Accidents Corporels (IA)</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Caractère / Statut Légal</label>
              <select
                className="form-control"
                value={garantieForm.type}
                onChange={(e) => setGarantieForm({ ...garantieForm, type: e.target.value })}
              >
                <option value="Obligatoire CIMA">Obligatoire CIMA</option>
                <option value="Optionnelle">Optionnelle</option>
                <option value="Complémentaire">Complémentaire</option>
                <option value="Pack Assistance">Pack Assistance</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Taux Taxe CIMA</label>
              <input
                type="text"
                className="form-control"
                value={garantieForm.taxe_cima}
                onChange={(e) => setGarantieForm({ ...garantieForm, taxe_cima: e.target.value })}
              />
            </div>
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={garantieForm.fga}
                onChange={(e) => setGarantieForm({ ...garantieForm, fga: e.target.checked })}
              />
              <span style={{ fontSize: '0.85rem' }}>Assujetti au Fonds de Garantie Automobile (FGA)</span>
            </label>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsGarantieModalOpen(false)}>Annuler</button>
            <button type="submit" className="btn btn-primary">Enregistrer</button>
          </div>
        </form>
      </Modal>

      {/* Modal Sous-Garantie */}
      <Modal
        isOpen={isSousGarantieModalOpen}
        onClose={() => setIsSousGarantieModalOpen(false)}
        title={editingSousGarantie ? 'Modifier la Sous-Garantie' : 'Créer une Sous-Garantie'}
      >
        <form onSubmit={handleSaveSousGarantie} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Garantie Parente (* requis)</label>
            <select
              className="form-control"
              value={sousGarantieForm.id_garantie}
              onChange={(e) => setSousGarantieForm({ ...sousGarantieForm, id_garantie: Number(e.target.value) })}
            >
              {garanties.map((g) => (
                <option key={g.id} value={g.id}>{g.libelle} ({g.branche})</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Libellé de la Sous-Garantie (* requis)</label>
            <input
              type="text"
              className="form-control"
              value={sousGarantieForm.libelle}
              onChange={(e) => setSousGarantieForm({ ...sousGarantieForm, libelle: e.target.value })}
              required
              placeholder="Ex: Dommages aux appareils électriques"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Code Sous-Garantie</label>
              <input
                type="text"
                className="form-control"
                value={sousGarantieForm.code}
                onChange={(e) => setSousGarantieForm({ ...sousGarantieForm, code: e.target.value.toUpperCase() })}
                placeholder="Ex: SG_ELEC"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Capital Garanti (FCFA)</label>
              <input
                type="number"
                className="form-control"
                value={sousGarantieForm.capital_defaut}
                onChange={(e) => setSousGarantieForm({ ...sousGarantieForm, capital_defaut: Number(e.target.value) })}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Franchise par Défaut</label>
              <input
                type="text"
                className="form-control"
                value={sousGarantieForm.franchise_defaut}
                onChange={(e) => setSousGarantieForm({ ...sousGarantieForm, franchise_defaut: e.target.value })}
                placeholder="Ex: 10% Min 50 000 FCFA"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Prime Annuelle de Base (FCFA)</label>
              <input
                type="number"
                className="form-control"
                value={sousGarantieForm.prime_base}
                onChange={(e) => setSousGarantieForm({ ...sousGarantieForm, prime_base: Number(e.target.value) })}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsSousGarantieModalOpen(false)}>Annuler</button>
            <button type="submit" className="btn btn-primary">Enregistrer</button>
          </div>
        </form>
      </Modal>

      {/* Delete confirm */}
      <DeleteConfirmModal
        isOpen={!!deletingItem}
        onClose={() => setDeletingItem(null)}
        itemType={deleteType}
        itemName={deletingItem?.libelle || deletingItem?.LibelleSousGarantie}
        itemCode={deletingItem?.code || deletingItem?.CodeSousGarantie}
        validation={{ allowed: true }}
        onConfirm={() => {
          if (deleteType === 'garantie' && deletingItem) {
            dataStore.deleteGuarantee(deletingItem.id);
            setGaranties(dataStore.getGuarantees());
            success(`Garantie supprimée.`);
          } else if (deletingItem) {
            setSousGaranties(prev => prev.filter(s => s.id !== deletingItem.id));
            success(`Sous-garantie supprimée.`);
          }
          setDeletingItem(null);
        }}
      />
    </div>
  );
};

export default ParametrageGarantiesPage;
