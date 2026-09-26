import React, { useState, useEffect } from 'react';
import { conventionsApi } from '../../../api/endpoints';
import { dataStore } from '../../../api/dataStore';
import { MetricCard } from '../../../components/common/MetricCard';
import { Modal } from '../../../components/common/Modal';
import { DeleteConfirmModal } from '../../../components/common/DeleteConfirmModal';
import { validateBusinessRule } from '../../../utils/rbac';
import { useToast } from '../../../context/ToastContext';
import {
  FileCheck,
  Building,
  ShieldCheck,
  Calendar,
  Percent,
  Plus,
  Edit2,
  Clock,
  Banknote,
  Layers,
  CheckCircle,
  HelpCircle,
  Trash2,
} from 'lucide-react';

export const ConventionsEnginePage = () => {
  const { success, error: toastError } = useToast();
  const [conventions, setConventions] = useState(() => dataStore.getConventions());
  const [deletingConvention, setDeletingConvention] = useState(null);
  const [deleteValidation, setDeleteValidation] = useState({ allowed: true });
  const [selectedConvention, setSelectedConvention] = useState(() => dataStore.getConventions()[0] || null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showProtocolModal, setShowProtocolModal] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      try {
        const data = await conventionsApi.getConventions();
        if (isMounted && data && Array.isArray(data) && data.length > 0) {
          setConventions(data);
          setSelectedConvention(data[0]);
        }
      } catch (err) {
        console.error('Erreur conventions Django:', err);
      }
    };
    loadData();
    return () => { isMounted = false; };
  }, []);
  const [editForm, setEditForm] = useState({
    plafond_delegation_sinistre: 5000000,
    delai_reversement_jours: 30,
    encaissement_delegue: true,
  });

  const handleOpenEdit = (cnv) => {
    setSelectedConvention(cnv);
    setEditForm({
      plafond_delegation_sinistre: cnv.plafond_delegation_sinistre || 5000000,
      delai_reversement_jours: cnv.delai_reversement_jours || 30,
      encaissement_delegue: cnv.encaissement_delegue ?? true,
    });
    setShowEditModal(true);
  };

  const handleSaveEdit = () => {
    if (!selectedConvention) return;
    const updated = dataStore.updateConvention(selectedConvention.id, {
      plafond_delegation_sinistre: Number(editForm.plafond_delegation_sinistre),
      delai_reversement_jours: Number(editForm.delai_reversement_jours),
      encaissement_delegue: Boolean(editForm.encaissement_delegue),
    });
    setConventions(dataStore.getConventions());
    setSelectedConvention(updated || selectedConvention);
    setShowEditModal(false);
    success(`Modifications contractuelles enregistrées pour ${selectedConvention.compagnie}.`);
  };

  useEffect(() => {
    const unsub = dataStore.subscribe(() => {
      const list = dataStore.getConventions();
      setConventions(list);
      if (selectedConvention) {
        const found = list.find((c) => c.id === selectedConvention.id);
        if (found) setSelectedConvention(found);
      }
    });
    return unsub;
  }, [selectedConvention]);

  // New convention form
  const [newCnv, setNewCnv] = useState({
    compagnie: '',
    code_partenaire: '',
    delai_reversement_jours: 30,
    plafond_delegation_sinistre: 5000000,
    encaissement_delegue: true,
    participation_beneficiaire: { active: true, taux: '15%', seuil_sp: '60%' },
  });

  const handleCreateConvention = async (e) => {
    e.preventDefault();
    const payload = {
      code_convention: `CNV-2026-${String(conventions.length + 1).padStart(3, '0')}`,
      ...newCnv,
      delai_reversement_jours: Number(newCnv.delai_reversement_jours),
      plafond_delegation_sinistre: Number(newCnv.plafond_delegation_sinistre),
      date_effet: '2026-01-01',
      date_renouvellement: '2026-12-31',
      statut: 'Actif',
      commissions_branches: {
        automobile: 12.5,
        mrh: 15.0,
        sante: 10.0,
        rc: 14.0,
      },
    };

    const saved = dataStore.saveConvention(payload);
    try {
      await conventionsApi.createConvention(payload);
    } catch (err) {
      console.warn('Fallback convention creation');
    }

    setConventions(dataStore.getConventions());
    setSelectedConvention(saved);
    setShowAddModal(false);
    success(`Convention avec ${payload.compagnie} paramétrée avec succès.`);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <span className="badge badge-primary">Module I – Conventions & Partenaires</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Moteur Multi-Compagnies</span>
          </div>
          <h1 className="title-xl">Conventions avec les compagnies</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Les accords signés avec chaque compagnie : mandat d'encaissement, délais de reversement, plafonds de délégation.
          </p>
        </div>

        <button
          className="btn btn-primary"
          onClick={() => setShowAddModal(true)}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <Plus size={16} />
          <span>Nouvelle Convention</span>
        </button>
      </div>

      {/* KPI Overview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <MetricCard
          title="Conventions Actives"
          value={conventions.length}
          subtitle="Partenaires agréés"
          icon={<Building size={22} color="#60a5fa" />}
        />
        <MetricCard
          title="Délai Reversement Légal"
          value="30 Jours"
          subtitle="Strictement conforme CIMA Livre V"
          icon={<Clock size={22} color="#34d399" />}
        />
        <MetricCard
          title="Mandat Délégation Max"
          value="15 M FCFA"
          subtitle="Plafond C3MEDICAL Santé / Évacuation"
          icon={<ShieldCheck size={22} color="#818cf8" />}
        />
        <MetricCard
          title="Participation Bénéficiaire"
          value="4 Partenaires"
          subtitle="Accords de PB négociés"
          icon={<Percent size={22} color="#fbbf24" />}
        />
      </div>

      {/* Conventions Grid & Detailed Config */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
        {conventions.map((cnv) => (
          <div
            key={cnv.id}
            className="glass-panel"
            style={{
              padding: '1.5rem',
              borderRadius: 'var(--radius-xl)',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              borderTop: '4px solid #2563eb',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#60a5fa', fontWeight: 600 }}>{cnv.id}</span>
                <h2 className="title-md" style={{ margin: '0.2rem 0' }}>
                  {cnv.compagnie}
                </h2>
                <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
                  {cnv.statut}
                </span>
              </div>
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '10px',
                  background: 'rgba(37,99,235,0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#60a5fa',
                }}
              >
                <Building size={20} />
              </div>
            </div>

            {/* Key parameters */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.6rem',
                background: 'var(--bg-surface)',
                padding: '1rem',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.85rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Pouvoir Encaissement :</span>
                <strong style={{ color: cnv.encaissement_delegue ? '#34d399' : '#fbbf24' }}>
                  {cnv.encaissement_delegue ? 'Délégué (Quittance LE PHARE)' : 'Direct Assureur'}
                </strong>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Délai Reversement CIMA :</span>
                <strong>{cnv.delai_reversement_jours} jours calendaires</strong>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Plafond Gestion Sinistres :</span>
                <strong style={{ color: '#60a5fa' }}>
                  {Number(cnv.plafond_delegation_sinistre || 0).toLocaleString('fr-FR')} FCFA
                </strong>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Participation Bénéficiaire :</span>
                <span>
                  {cnv.participation_beneficiaire?.active
                    ? `${cnv.participation_beneficiaire.taux} (seuil S/P ${cnv.participation_beneficiaire.seuil_sp})`
                    : 'Non applicable'}
                </span>
              </div>
            </div>

            {/* Commission rates by branch */}
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                Barème de Commissions LE PHARE
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                {Object.entries(cnv.commissions_branches || {}).map(([branche, taux]) => (
                  <div
                    key={branche}
                    style={{
                      background: 'rgba(255,255,255,0.03)',
                      padding: '0.4rem 0.6rem',
                      borderRadius: '6px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '0.8rem',
                    }}
                  >
                    <span style={{ textTransform: 'capitalize', color: 'var(--text-secondary)' }}>{branche} :</span>
                    <strong style={{ color: '#34d399' }}>{taux} %</strong>
                  </div>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto', paddingTop: '0.5rem' }}>
              <button
                className="btn btn-secondary"
                style={{ flex: 1, fontSize: '0.75rem', padding: '0.4rem' }}
                onClick={() => {
                  setSelectedConvention(cnv);
                  setShowProtocolModal(true);
                }}
              >
                <FileCheck size={13} style={{ marginRight: '0.35rem' }} /> Accord & Mandat
              </button>
              <button
                className="btn btn-primary"
                style={{ flex: 1, fontSize: '0.75rem', padding: '0.4rem' }}
                onClick={() => handleOpenEdit(cnv)}
              >
                <Edit2 size={13} style={{ marginRight: '0.35rem' }} /> Modifier
              </button>
              <button
                className="btn btn-secondary"
                style={{ padding: '0.4rem 0.6rem', fontSize: '0.75rem', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.25)' }}
                onClick={() => {
                  const check = validateBusinessRule('delete', 'conventions', cnv, dataStore);
                  setDeleteValidation(check);
                  setDeletingConvention(cnv);
                }}
                title="Supprimer la convention"
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal: New convention */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Ajouter une Convention Assureur"
        subtitle="Paramétrage des règles de gestion déléguée, plafonds et délais CIMA."
        maxWidth="560px"
      >
        <form onSubmit={handleCreateConvention} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Raison Sociale Compagnie Assureur *</label>
            <input
              type="text"
              className="form-control"
              required
              placeholder="ex: SANLAM ASSURANCES CI"
              value={newCnv.compagnie}
              onChange={(e) => setNewCnv({ ...newCnv, compagnie: e.target.value })}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Délai Reversement (Jours CIMA)</label>
              <input
                type="number"
                className="form-control"
                value={newCnv.delai_reversement_jours}
                onChange={(e) => setNewCnv({ ...newCnv, delai_reversement_jours: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Plafond Délégation Sinistre (FCFA)</label>
              <input
                type="number"
                className="form-control"
                value={newCnv.plafond_delegation_sinistre}
                onChange={(e) => setNewCnv({ ...newCnv, plafond_delegation_sinistre: e.target.value })}
              />
            </div>
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}>
              <input
                type="checkbox"
                checked={newCnv.encaissement_delegue}
                onChange={(e) => setNewCnv({ ...newCnv, encaissement_delegue: e.target.checked })}
              />
              <span>Mandat d'encaissement délégué avec émission de quittance LE PHARE</span>
            </label>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
              Annuler
            </button>
            <button type="submit" className="btn btn-primary">
              Créer la Convention
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit convention */}
      {selectedConvention && (
        <Modal
          isOpen={showEditModal}
          onClose={() => setShowEditModal(false)}
          title={`Paramètres Convention – ${selectedConvention.compagnie}`}
          subtitle="Ajustement contractuel du plafond et des délais de reversement."
          maxWidth="560px"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Plafond de gestion déléguée des sinistres (FCFA)</label>
              <input
                type="number"
                className="form-control"
                value={editForm.plafond_delegation_sinistre}
                onChange={(e) => setEditForm({ ...editForm, plafond_delegation_sinistre: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Délai contractuel de reversement (jours CIMA)</label>
              <input
                type="number"
                className="form-control"
                value={editForm.delai_reversement_jours}
                onChange={(e) => setEditForm({ ...editForm, delai_reversement_jours: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}>
                <input
                  type="checkbox"
                  checked={editForm.encaissement_delegue}
                  onChange={(e) => setEditForm({ ...editForm, encaissement_delegue: e.target.checked })}
                />
                <span>Mandat d'encaissement délégué actif</span>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                Fermer
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleSaveEdit}
              >
                Sauvegarder
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: View Convention Protocol & Mandate Certificate */}
      {selectedConvention && (
        <Modal
          isOpen={showProtocolModal}
          onClose={() => setShowProtocolModal(false)}
          title={`Accord & Protocole de Convention – ${selectedConvention.compagnie}`}
          subtitle={`Référence Convention : ${selectedConvention.id} • Conforme Code des Assurances CIMA`}
          maxWidth="640px"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div
              style={{
                background: 'rgba(37,99,235,0.06)',
                border: '1px solid rgba(37,99,235,0.2)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Partenaire Porteur de Risque</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#fff' }}>{selectedConvention.compagnie}</div>
                <div style={{ fontSize: '0.75rem', color: '#60a5fa' }}>Mandat de Courtage & Délégation de Gestion</div>
              </div>
              <span className="badge badge-success" style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}>
                Convention Active 2026
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.825rem' }}>
              <div style={{ padding: '0.75rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>POUVOIR D'ENCAISSEMENT (ART. 13)</span>
                <strong style={{ color: selectedConvention.encaissement_delegue ? '#34d399' : '#fbbf24' }}>
                  {selectedConvention.encaissement_delegue ? 'Délégué avec quittance LE PHARE' : 'Direct Compagnie'}
                </strong>
              </div>
              <div style={{ padding: '0.75rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>DÉLAI DE REVERSEMENT (ART. 544)</span>
                <strong style={{ color: '#fff' }}>{selectedConvention.delai_reversement_jours} Jours Calendaires</strong>
              </div>
              <div style={{ padding: '0.75rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>PLAFOND RÈGLEMENT SINISTRES (ART. 54)</span>
                <strong style={{ color: '#60a5fa' }}>{Number(selectedConvention.plafond_delegation_sinistre || 0).toLocaleString('fr-FR')} FCFA</strong>
              </div>
              <div style={{ padding: '0.75rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>PARTICIPATION BÉNÉFICIAIRE</span>
                <strong style={{ color: '#fbbf24' }}>
                  {selectedConvention.participation_beneficiaire?.active
                    ? `${selectedConvention.participation_beneficiaire.taux} (S/P ${selectedConvention.participation_beneficiaire.seuil_sp})`
                    : 'Non applicable'}
                </strong>
              </div>
            </div>

            <div>
              <div style={{ fontWeight: 700, fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                Taux de Commissions Contractuels par Branche CIMA
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
                {Object.entries(selectedConvention.commissions_branches || {}).map(([b, t]) => (
                  <div key={b} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0.75rem', background: 'var(--bg-surface)', borderRadius: '4px', border: '1px solid var(--border-subtle)', fontSize: '0.8rem' }}>
                    <span style={{ textTransform: 'capitalize' }}>{b}</span>
                    <strong style={{ color: '#34d399' }}>{t} %</strong>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowProtocolModal(false)}>
                Fermer
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  window.print();
                  success('Impression du protocole de convention lancée.');
                }}
              >
                Imprimer le Protocole
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal Suppression Convention */}
      <DeleteConfirmModal
        isOpen={!!deletingConvention}
        onClose={() => setDeletingConvention(null)}
        itemType="convention assureur"
        itemName={`Convention ${deletingConvention?.code} (${deletingConvention?.compagnie})`}
        itemCode={deletingConvention?.code}
        validation={deleteValidation}
        onConfirm={() => {
          if (deletingConvention) {
            try {
              dataStore.deleteConvention(deletingConvention.id);
              setConventions(dataStore.getConventions());
              success(`Convention ${deletingConvention.code} supprimée.`);
              setDeletingConvention(null);
            } catch (err) {
              toastError(err.message);
            }
          }
        }}
      />
    </div>
  );
};

export default ConventionsEnginePage;
