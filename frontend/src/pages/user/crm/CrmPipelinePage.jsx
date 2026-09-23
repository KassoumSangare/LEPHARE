import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MetricCard } from '../../../components/common/MetricCard';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { crmApi } from '../../../api/endpoints';
import { dataStore } from '../../../api/dataStore';
import { useToast } from '../../../context/ToastContext';
import {
  Users,
  TrendingUp,
  Plus,
  Search,
  Filter,
  Calendar,
  Banknote,
  CheckCircle,
  Phone,
  Mail,
  ArrowRight,
  ChevronRight,
  Briefcase,
  Layers,
  FileCheck,
  UserCheck,
  Edit2,
  Trash2,
} from 'lucide-react';
import { DeleteConfirmModal } from '../../../components/common/DeleteConfirmModal';
import { EditLeadModal } from './EditLeadModal';
import { canUser, getCurrentUser, validateBusinessRule } from '../../../utils/rbac';

const STAGES = [
  { id: 'Nouveau', label: 'Prospects Entrants', color: '#60a5fa', bg: 'rgba(96, 165, 250, 0.1)' },
  { id: 'Qualifié', label: 'Besoins Qualifiés', color: '#818cf8', bg: 'rgba(129, 140, 248, 0.1)' },
  { id: 'Proposition', label: 'Proposition Émise', color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.1)' },
  { id: 'Négociation', label: 'Négociation & Clôture', color: '#f97316', bg: 'rgba(249, 115, 22, 0.1)' },
  { id: 'Gagné', label: 'Affaires Gagnées', color: '#34d399', bg: 'rgba(52, 211, 153, 0.1)' },
];

const parseAmount = (val) => {
  if (typeof val === 'number') return isNaN(val) ? 0 : val;
  if (!val) return 0;
  const cleaned = String(val).replace(/[^\d.-]/g, '');
  const num = parseFloat(cleaned);
  return isNaN(num) ? 0 : num;
};

const normalizeLead = (l) => {
  let statut = l.statut;
  if (!statut) {
    const etape = (l.etape || '').toLowerCase();
    if (etape.includes('nouv') || etape.includes('entrant')) statut = 'Nouveau';
    else if (etape.includes('qualif')) statut = 'Qualifié';
    else if (etape.includes('prop')) statut = 'Proposition';
    else if (etape.includes('négoc') || etape.includes('negoc')) statut = 'Négociation';
    else if (etape.includes('gagn') || etape.includes('conclu')) statut = 'Gagné';
    else statut = 'Nouveau';
  }

  let branche = l.branche || l.produit_cible || 'Automobile';
  if (branche.toLowerCase().includes('auto') || branche.toLowerCase().includes('flotte')) branche = 'Automobile';
  else if (branche.toLowerCase().includes('sant')) branche = 'Santé';
  else if (branche.toLowerCase().includes('multi') || branche.toLowerCase().includes('mrp') || branche.toLowerCase().includes('incendie') || branche.toLowerCase().includes('rd')) branche = 'IARD';
  else if (branche.toLowerCase().includes('vie') || branche.toLowerCase().includes('retraite')) branche = 'Vie';
  else if (branche.toLowerCase().includes('transport')) branche = 'Transport';

  return {
    id: l.id || l.id_lead || Date.now(),
    id_lead: l.id_lead || `PROSP-2026-${String(l.id || 1).padStart(3, '0')}`,
    nom_prospect: l.nom_prospect || l.nom || l.societe || 'Prospect Anonyme',
    contact: l.contact || l.nom_contact || l.interlocuteur || 'Direction Générale',
    telephone: l.telephone || '+225 07 00 00 00',
    email: l.email || 'contact@prospect.ci',
    branche: branche,
    prime_estimee: parseAmount(l.prime_estimee || l.montant_estime || 0),
    statut: statut,
    commercial_attribue: l.commercial_attribue || l.commercial_assigne || 'Koffi Serge',
    prochaine_action: l.prochaine_action || l.notes || 'Relance commerciale',
    date_action: l.date_action || l.prochaine_relance || '15/09/2026',
    probabilite: l.probabilite || 50,
  };
};

export const CrmPipelinePage = () => {
  const navigate = useNavigate();
  const { success } = useToast();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('ALL');
  const [viewMode, setViewMode] = useState('kanban'); // 'kanban' or 'list'
  const [showAddModal, setShowAddModal] = useState(false);
  const [currentUser, setCurrentUser] = useState(() => getCurrentUser());
  const [editingLead, setEditingLead] = useState(null);
  const [deletingLead, setDeletingLead] = useState(null);

  const loadLeads = async () => {
    setLoading(true);
    try {
      const data = await crmApi.getLeads();
      if (Array.isArray(data)) {
        setLeads(data.map(normalizeLead));
      }
    } catch (err) {
      console.error('Erreur chargement leads Django:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLeads();
  }, []);

  // New lead form state
  const [newLead, setNewLead] = useState({
    nom_prospect: '',
    contact: '',
    telephone: '',
    email: '',
    branche: 'Automobile',
    prime_estimee: 500000,
    statut: 'Nouveau',
    commercial_attribue: 'Koffi Serge',
    prochaine_action: 'Premier rendez-vous et qualification du besoin',
    date_action: '2026-09-15',
  });

  const handleAddLead = async (e) => {
    e.preventDefault();
    const leadPayload = {
      id_lead: `PROSP-2026-${String(leads.length + 1).padStart(3, '0')}`,
      ...newLead,
      prime_estimee: parseAmount(newLead.prime_estimee),
      historique_echanges: [
        { date: new Date().toISOString().split('T')[0], auteur: newLead.commercial_attribue, action: 'Création de l opportunité dans le CRM' },
      ],
    };
    
    dataStore.saveLead(leadPayload);
    try {
      await crmApi.createLead(leadPayload);
    } catch (err) {
      console.warn('API create lead fallback');
    }

    setLeads(dataStore.getLeads().map(normalizeLead));
    setShowAddModal(false);
    success(`Le prospect ${newLead.nom_prospect} a été enregistré dans le pipeline commercial.`);
  };

  const handleMoveStage = async (leadId, nextStage) => {
    dataStore.updateLead(leadId, { statut: nextStage });
    setLeads(dataStore.getLeads().map(normalizeLead));
    try {
      await crmApi.updateLeadStage(leadId, nextStage);
    } catch (err) {
      console.warn('Erreur synchro transition', err);
    }
    success(`Statut mis à jour vers "${nextStage}".`);
  };

  const handleSaveLeadEdits = (leadId, updates) => {
    dataStore.updateLead(leadId, updates);
    setLeads(dataStore.getLeads().map(normalizeLead));
    success(`Prospect ${updates.nom_prospect || leadId} mis à jour avec succès.`);
  };

  const handleConfirmDeleteLead = (lead) => {
    dataStore.deleteLead(lead.id || lead.id_lead);
    setLeads(dataStore.getLeads().map(normalizeLead));
    setDeletingLead(null);
    success(`L'opportunité ${lead.nom_prospect} a été supprimée du CRM.`);
  };

  // Filtered leads
  const filteredLeads = leads.filter((l) => {
    const nom = (l.nom_prospect || '').toLowerCase();
    const comm = (l.commercial_attribue || '').toLowerCase();
    const br = (l.branche || '').toLowerCase();
    const q = (searchTerm || '').toLowerCase();
    const matchSearch = !q || nom.includes(q) || comm.includes(q) || br.includes(q);
    const matchBranch = selectedBranch === 'ALL' || l.branche === selectedBranch;
    return matchSearch && matchBranch;
  });

  // Pipeline metrics
  const totalPipelineVal = filteredLeads.reduce((acc, l) => acc + parseAmount(l.prime_estimee), 0);
  const wonLeads = filteredLeads.filter((l) => l.statut === 'Gagné');
  const wonVal = wonLeads.reduce((acc, l) => acc + parseAmount(l.prime_estimee), 0);
  const conversionRate = filteredLeads.length > 0 ? Math.round((wonLeads.length / filteredLeads.length) * 100) : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <span className="badge badge-info">Module C – CRM & Pipeline</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>LE PHARE V2</span>
          </div>
          <h1 className="title-xl">Prospection & Pipeline Commercial</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Suivi 360° du cycle d'acquisition, transformation de leads et relances commerciales.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button
            className="btn btn-secondary"
            onClick={() => navigate('/user/crm/360')}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <UserCheck size={16} />
            <span>Vue 360° Client</span>
          </button>
          <button
            className="btn btn-primary"
            onClick={() => setShowAddModal(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <Plus size={16} />
            <span>Nouveau Prospect</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <MetricCard
          title="Opportunités Actives"
          value={filteredLeads.length}
          subtitle="En portefeuille commercial"
          icon={<Briefcase size={22} color="#60a5fa" />}
        />
        <MetricCard
          title="Volume Pipeline Estimé"
          value={`${((totalPipelineVal || 0) / 1000000).toFixed(1)} M FCFA`}
          subtitle="Primes annuelles potentielles"
          icon={<Banknote size={22} color="#fbbf24" />}
        />
        <MetricCard
          title="Affaires Clôturées (Gagnées)"
          value={`${((wonVal || 0) / 1000000).toFixed(1)} M FCFA`}
          subtitle={`${wonLeads.length} dossiers transformés`}
          icon={<CheckCircle size={22} color="#34d399" />}
        />
        <MetricCard
          title="Taux de Transformation"
          value={`${conversionRate} %`}
          subtitle="Cible CIMA institutionnelle ≥ 25%"
          icon={<TrendingUp size={22} color="#818cf8" />}
        />
      </div>

      {/* Filters & Mode Switcher */}
      <div className="glass-panel" style={{ padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: '280px' }}>
          <div style={{ position: 'relative', flex: 1, maxWidth: '340px' }}>
            <Search size={16} style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="form-control"
              style={{ paddingLeft: '2.5rem', fontSize: '0.875rem' }}
              placeholder="Rechercher prospect, contact, chargé..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Filter size={15} color="var(--text-muted)" />
            <select
              className="form-control"
              style={{ fontSize: '0.85rem', width: '160px' }}
              value={selectedBranch}
              onChange={(e) => setSelectedBranch(e.target.value)}
            >
              <option value="ALL">Toutes branches</option>
              <option value="Automobile">Automobile</option>
              <option value="Flotte Auto">Flotte Auto</option>
              <option value="Santé Groupe">Santé Groupe</option>
              <option value="Multirisque Habitation">MRH</option>
              <option value="Multirisque Entreprise">Entreprise</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className={`btn ${viewMode === 'kanban' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
            onClick={() => setViewMode('kanban')}
          >
            <Layers size={14} style={{ marginRight: '0.35rem' }} /> Kanban
          </button>
          <button
            className={`btn ${viewMode === 'list' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
            onClick={() => setViewMode('list')}
          >
            <Users size={14} style={{ marginRight: '0.35rem' }} /> Liste
          </button>
        </div>
      </div>

      {/* Kanban Board */}
      {viewMode === 'kanban' ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(270px, 1fr))',
            gap: '1.25rem',
            alignItems: 'start',
          }}
        >
          {STAGES.map((stage) => {
            const stageLeads = filteredLeads.filter((l) => l.statut === stage.id);
            const stageTotal = stageLeads.reduce((acc, l) => acc + parseAmount(l.prime_estimee), 0);

            return (
              <div
                key={stage.id}
                className="glass-panel"
                style={{
                  padding: '1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.85rem',
                  borderRadius: 'var(--radius-lg)',
                  borderTop: `3px solid ${stage.color}`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)' }}>{stage.label}</span>
                    <span
                      style={{
                        background: stage.bg,
                        color: stage.color,
                        padding: '0.15rem 0.5rem',
                        borderRadius: '12px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                      }}
                    >
                      {stageLeads.length}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                    {(stageTotal / 1000).toLocaleString('fr-FR')} k
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', minHeight: '300px' }}>
                  {stageLeads.length === 0 ? (
                    <div
                      style={{
                        padding: '2rem 1rem',
                        textAlign: 'center',
                        color: 'var(--text-muted)',
                        fontSize: '0.8rem',
                        fontStyle: 'italic',
                        border: '1px dashed var(--border-color)',
                        borderRadius: 'var(--radius-md)',
                      }}
                    >
                      Aucune affaire dans cette étape
                    </div>
                  ) : (
                    stageLeads.map((lead) => (
                      <div
                        key={lead.id}
                        style={{
                          background: 'var(--bg-surface)',
                          padding: '1rem',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid var(--border-color)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.5rem',
                          boxShadow: 'var(--shadow-sm)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <span style={{ fontSize: '0.75rem', color: '#60a5fa', fontWeight: 600 }}>{lead.id}</span>
                          <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
                            {lead.branche}
                          </span>
                        </div>

                        <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                          {lead.nom_prospect}
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          <Users size={13} />
                          <span>{lead.contact}</span>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.25rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                          <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Prime</div>
                            <div style={{ fontWeight: 700, color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                              {parseAmount(lead.prime_estimee).toLocaleString('fr-FR')} FCFA
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Commercial</div>
                            <div style={{ fontSize: '0.75rem', fontWeight: 600 }}>{lead.commercial_attribue}</div>
                          </div>
                        </div>

                        {lead.prochaine_action && (
                          <div
                            style={{
                              fontSize: '0.75rem',
                              background: 'rgba(255,255,255,0.03)',
                              padding: '0.4rem 0.6rem',
                              borderRadius: '4px',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.4rem',
                              color: 'var(--text-muted)',
                            }}
                          >
                            <Calendar size={12} color="#fbbf24" />
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {lead.prochaine_action}
                            </span>
                          </div>
                        )}

                        {/* Fast stage advancement buttons */}
                        <div style={{ display: 'flex', gap: '0.35rem', marginTop: '0.5rem' }}>
                          {stage.id !== 'Gagné' && (
                            <button
                              className="btn btn-secondary"
                              style={{ flex: 1, padding: '0.25rem 0.4rem', fontSize: '0.7rem', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.25rem' }}
                              onClick={() => {
                                const currentIndex = STAGES.findIndex((s) => s.id === stage.id);
                                if (currentIndex < STAGES.length - 1) {
                                  handleMoveStage(lead.id, STAGES[currentIndex + 1].id);
                                }
                              }}
                            >
                              <span>Étape suivante</span>
                              <ChevronRight size={13} />
                            </button>
                          )}
                          <button
                            className="btn btn-primary"
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.7rem' }}
                            title="Créer un devis formel"
                            onClick={() => navigate('/user/quotes')}
                          >
                            Devis
                          </button>
                        </div>

                        {/* Edit & Delete Action Buttons (RBAC governed) */}
                        <div style={{ display: 'flex', gap: '0.35rem', justifyContent: 'flex-end', paddingTop: '0.35rem', borderTop: '1px dashed var(--border-color)' }}>
                          {canUser(currentUser, 'edit', 'leads') && (
                            <button
                              className="btn btn-secondary"
                              style={{ padding: '0.2rem 0.45rem', fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                              title="Modifier ce prospect"
                              onClick={() => setEditingLead(lead)}
                            >
                              <Edit2 size={11} />
                              <span>Modifier</span>
                            </button>
                          )}
                          {canUser(currentUser, 'delete', 'leads') && (
                            <button
                              className="btn btn-secondary"
                              style={{ padding: '0.2rem 0.45rem', fontSize: '0.7rem', color: '#f87171' }}
                              title="Supprimer ce prospect"
                              onClick={() => setDeletingLead(lead)}
                            >
                              <Trash2 size={11} />
                            </button>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* List Mode */
        <div className="glass-panel" style={{ padding: '1rem' }}>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Réf Prospect</th>
                  <th>Nom Prospect / Société</th>
                  <th>Contact Principal</th>
                  <th>Branche</th>
                  <th>Prime Estimée</th>
                  <th>Étape Pipeline</th>
                  <th>Commercial</th>
                  <th>Prochaine Relance</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredLeads.map((lead) => (
                  <tr key={lead.id}>
                    <td><strong style={{ color: '#60a5fa' }}>{lead.id}</strong></td>
                    <td><strong style={{ color: 'var(--text-primary)' }}>{lead.nom_prospect}</strong></td>
                    <td>
                      <div>{lead.contact}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{lead.telephone}</div>
                    </td>
                    <td><span className="badge badge-neutral">{lead.branche}</span></td>
                    <td><strong>{lead.prime_estimee.toLocaleString('fr-FR')} FCFA</strong></td>
                    <td>
                      <span className={`badge ${lead.statut === 'Gagné' ? 'badge-success' : lead.statut === 'Proposition' ? 'badge-warning' : 'badge-info'}`}>
                        {lead.statut}
                      </span>
                    </td>
                    <td>{lead.commercial_attribue}</td>
                    <td>
                      <span style={{ fontSize: '0.8rem', color: '#fbbf24' }}>{lead.date_action || 'Non définie'}</span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                          onClick={() => navigate('/user/crm/360')}
                        >
                          Fiche 360°
                        </button>
                        <button
                          className="btn btn-primary"
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                          onClick={() => navigate('/user/quotes')}
                        >
                          Devis
                        </button>
                        {canUser(currentUser, 'edit', 'leads') && (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.25rem 0.45rem', fontSize: '0.75rem' }}
                            title="Modifier l'opportunité"
                            onClick={() => setEditingLead(lead)}
                          >
                            <Edit2 size={13} />
                          </button>
                        )}
                        {canUser(currentUser, 'delete', 'leads') && (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.25rem 0.45rem', fontSize: '0.75rem', color: '#f87171' }}
                            title="Supprimer l'opportunité"
                            onClick={() => setDeletingLead(lead)}
                          >
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal: New Lead */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Créer une Nouvelle Opportunité / Prospect"
        subtitle="Enregistrement dans le CRM de LE PHARE avec attribution commerciale immédiate."
        maxWidth="580px"
      >
        <form onSubmit={handleAddLead} style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
          <div className="form-group">
            <label className="form-label">Nom Prospect / Entreprise *</label>
            <input
              type="text"
              className="form-control"
              placeholder="ex: IVOIRE LOGISTIQUE SARL"
              required
              value={newLead.nom_prospect}
              onChange={(e) => setNewLead({ ...newLead, nom_prospect: e.target.value })}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Contact / Interlocuteur</label>
              <input
                type="text"
                className="form-control"
                placeholder="M. Touré Amadou"
                value={newLead.contact}
                onChange={(e) => setNewLead({ ...newLead, contact: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Téléphone</label>
              <input
                type="text"
                className="form-control"
                placeholder="+225 07 00 11 22 33"
                value={newLead.telephone}
                onChange={(e) => setNewLead({ ...newLead, telephone: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Branche Ciblée</label>
              <select
                className="form-control"
                value={newLead.branche}
                onChange={(e) => setNewLead({ ...newLead, branche: e.target.value })}
              >
                <option value="Automobile">Automobile</option>
                <option value="Flotte Auto">Flotte Auto</option>
                <option value="Santé Groupe">Santé Groupe</option>
                <option value="Multirisque Habitation">Multirisque Habitation</option>
                <option value="Multirisque Entreprise">Multirisque Entreprise</option>
                <option value="Responsabilité Civile">Responsabilité Civile</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Prime Estimée (FCFA)</label>
              <input
                type="number"
                className="form-control"
                value={newLead.prime_estimee}
                onChange={(e) => setNewLead({ ...newLead, prime_estimee: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Commercial Attribué</label>
              <select
                className="form-control"
                value={newLead.commercial_attribue}
                onChange={(e) => setNewLead({ ...newLead, commercial_attribue: e.target.value })}
              >
                <option value="Koffi Serge">Koffi Serge (Direct)</option>
                <option value="Yao Marc">Yao Marc (Grand Comptes)</option>
                <option value="Kouadio Estelle">Kouadio Estelle (Courtage)</option>
                <option value="Cabinet Alpha Courtage">Cabinet Alpha (Apporteur)</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Date Prochaine Relance</label>
              <input
                type="date"
                className="form-control"
                value={newLead.date_action}
                onChange={(e) => setNewLead({ ...newLead, date_action: e.target.value })}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Prochaine Action Prévue</label>
            <input
              type="text"
              className="form-control"
              placeholder="ex: Transmission offre tarifaire et recueil RCCM"
              value={newLead.prochaine_action}
              onChange={(e) => setNewLead({ ...newLead, prochaine_action: e.target.value })}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
              Annuler
            </button>
            <button type="submit" className="btn btn-primary">
              Enregistrer l'Opportunité
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Lead */}
      <EditLeadModal
        isOpen={Boolean(editingLead)}
        onClose={() => setEditingLead(null)}
        lead={editingLead}
        onSave={handleSaveLeadEdits}
      />

      {/* Modal: Delete Lead Confirmation */}
      {deletingLead && (
        <DeleteConfirmModal
          isOpen={Boolean(deletingLead)}
          onClose={() => setDeletingLead(null)}
          title={`Supprimer l'opportunité [${deletingLead.nom_prospect}]`}
          resourceName="l'opportunité CRM"
          entity={deletingLead}
          validation={validateBusinessRule('delete', 'leads', deletingLead, dataStore)}
          onConfirm={() => handleConfirmDeleteLead(deletingLead)}
        />
      )}
    </div>
  );
};

export default CrmPipelinePage;
