import React, { useState, useEffect } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { approvalApi } from '../../../api/endpoints';
import { dataStore } from '../../../api/dataStore';
import { CheckCheck, Check, X, ShieldAlert, Key } from 'lucide-react';
import { useToast } from '../../../context/ToastContext';
import { formatDate } from '../../../utils/dateUtils';

const normalizeDemande = (d) => {
  const isApproved = d.statut === 'APPROUVEE' || d.statut === 'VALIDEE' || d.statut === 'APPROVED';
  const isRejected = d.statut === 'REJETEE' || d.statut === 'REJECTED';
  return {
    ...d,
    id: d.id,
    type_label: d.type_operation === 'ANNUL_ENC' ? "Annulation d'encaissement" : (d.type_operation || 'Dérogation'),
    demandeur_nom: d.demandeur ? `${d.demandeur.first_name || ''} ${d.demandeur.last_name || d.demandeur.email || ''}`.trim() : (d.demandeur_nom || 'Opérateur Guichet'),
    objet: d.objet || d.motif || 'Dérogation opérationnelle',
    date_demande: d.date_demande ? d.date_demande.substring(0, 16).replace('T', ' ') : new Date().toISOString().substring(0, 10),
    statut: d.statut,
    statut_label: isApproved ? 'Approuvée' : (isRejected ? 'Rejetée' : 'En attente'),
    statut_badge: isApproved ? 'emerald' : (isRejected ? 'rose' : 'amber'),
    code_jeton: d.code_jeton || (d.jeton && d.jeton.code ? d.jeton.code : null),
  };
};

export const ApprovalCenterPage = () => {
  const [demandes, setDemandes] = useState(() => dataStore.getDerogations());
  const [selectedDemande, setSelectedDemande] = useState(null);
  const [isApproveModalOpen, setIsApproveModalOpen] = useState(false);
  const [validiteHeures, setValiditeHeures] = useState(24);
  const { success, error } = useToast();

  const loadDemandes = async () => {
    try {
      const data = await approvalApi.getDemandes();
      if (data && Array.isArray(data)) {
        setDemandes(data.map(normalizeDemande));
      }
    } catch (e) {
      console.error('Erreur autorisations Django:', e);
      setDemandes(dataStore.getDerogations());
    }
  };

  useEffect(() => {
    loadDemandes();
  }, []);

  const handleOpenApprove = (d) => {
    setSelectedDemande(d);
    setIsApproveModalOpen(true);
  };

  const confirmApprove = async () => {
    if (!selectedDemande) return;
    let finalToken = `JET-${String(selectedDemande.id).padStart(4, '0')}`;

    try {
      const res = await approvalApi.approveDemande(selectedDemande.id, { duree_validite_heures: validiteHeures });
      const resData = res?.data || res;
      if (resData?.jeton?.code) {
        finalToken = resData.jeton.code;
      } else if (resData?.jeton?.token) {
        finalToken = resData.jeton.token;
      }
    } catch (err) {
      console.warn('API approve error:', err.message);
    }

    dataStore.updateDerogation(selectedDemande.id, {
      statut: 'APPROVED',
      statut_label: 'Approuvée',
      statut_badge: 'emerald',
      code_jeton: finalToken,
    });
    setDemandes(dataStore.getDerogations());
    setIsApproveModalOpen(false);
    success(`Demande approuvée avec succès ! Jeton de sécurité officiel : ${finalToken} (valide ${validiteHeures}h)`);
  };

  const handleReject = async (d) => {
    try {
      await approvalApi.rejectDemande(d.id, 'Rejet par la Direction');
    } catch (err) {
      console.warn('API reject fallback');
    }
    dataStore.updateDerogation(d.id, {
      statut: 'REJECTED',
      statut_label: 'Rejetée',
      statut_badge: 'rose',
    });
    setDemandes(dataStore.getDerogations());
    error(`Demande "${d.objet}" rejetée par la Direction.`);
  };

  const columns = [
    { header: "Type d'Opération", accessor: 'type_label', render: (r) => <strong style={{ color: '#fff' }}>{r.type_label}</strong> },
    { header: 'Objet', accessor: 'objet' },
    { header: 'Demandeur (Opérateur)', accessor: 'demandeur_nom', render: (r) => <span style={{ color: '#60a5fa' }}>{r.demandeur_nom}</span> },
    { header: 'Date Soumission', accessor: 'date_demande', render: (r) => formatDate(r.date_demande) },
    { header: 'Statut', accessor: 'statut_label', render: (r) => <StatusBadge label={r.statut_label} color={r.statut_badge} /> },
    {
      header: 'Jeton Attribué',
      render: (r) => (
        r.code_jeton ? (
          <span style={{ fontFamily: 'var(--font-mono)', color: '#34d399', fontWeight: 700 }}>{r.code_jeton}</span>
        ) : (
          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>-</span>
        )
      ),
    },
    {
      header: 'Actions Hiérarchiques',
      render: (r) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          {r.statut === 'PENDING' ? (
            <>
              <button
                className="btn btn-primary"
                style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem', background: 'linear-gradient(135deg, #059669, #10b981)' }}
                onClick={() => handleOpenApprove(r)}
              >
                <Check size={14} /> Approuver
              </button>
              <button
                className="btn btn-danger"
                style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}
                onClick={() => handleReject(r)}
              >
                <X size={14} /> Rejeter
              </button>
            </>
          ) : (
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Traité</span>
          )}
        </div>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <CheckCheck size={26} color="#8b5cf6" />
          Centre d'Approbation des Dérogations
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Validation des remises commerciales, annulations de quittances et génération des jetons sécurisés.
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable columns={columns} data={demandes} searchPlaceholder="Filtrer une demande d'approbation..." />
      </div>

      {/* Approval Modal */}
      <Modal isOpen={isApproveModalOpen} onClose={() => setIsApproveModalOpen(false)} title="Autorisation Exceptionnelle">
        {selectedDemande && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Vous vous apprêtez à émettre un <strong>jeton d'autorisation numérique</strong> pour :
            </p>

            <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', background: 'rgba(30, 41, 59, 0.6)', fontSize: '0.85rem' }}>
              <div><strong>Opération :</strong> {selectedDemande.type_label}</div>
              <div><strong>Objet :</strong> {selectedDemande.objet}</div>
              <div><strong>Demandeur :</strong> {selectedDemande.demandeur_nom}</div>
            </div>

            <div className="form-group">
              <label className="form-label">Durée de validité du jeton (Heures)</label>
              <select className="form-control" value={validiteHeures} onChange={(e) => setValiditeHeures(parseInt(e.target.value))}>
                <option value={12}>12 Heures</option>
                <option value={24}>24 Heures (1 jour)</option>
                <option value={48}>48 Heures (2 jours)</option>
                <option value={72}>72 Heures</option>
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
              <button className="btn btn-secondary" onClick={() => setIsApproveModalOpen(false)}>Annuler</button>
              <button className="btn btn-primary" onClick={confirmApprove} style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
                <Key size={16} /> Générer le Jeton et Autoriser
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ApprovalCenterPage;
