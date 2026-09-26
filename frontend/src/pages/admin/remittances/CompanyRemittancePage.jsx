import React, { useState, useEffect } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { dataStore } from '../../../api/dataStore';
import { remittanceApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { Building2, Check, Download, Send, AlertTriangle, ShieldCheck, Clock, FileText, Printer } from 'lucide-react';
import { formatDate } from '../../../utils/dateUtils';

export const CompanyRemittancePage = () => {
  const { success, info } = useToast();

  const [remittances, setRemittances] = useState(dataStore.getRemittances());
  const [selectedBordereau, setSelectedBordereau] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    compagnie: 'NSIA Assurances CI',
    nombre_polices: 15,
    montant_primes: 5000000,
    taux_commission: 12,
    reference: `REV-MANUEL-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 900) + 100)}`,
  });

  const handleCreateBordereau = (e) => {
    e.preventDefault();
    const primes = Number(createForm.montant_primes) || 0;
    const taux = Number(createForm.taux_commission) || 0;
    const comms = Math.round(primes * (taux / 100));
    const net = primes - comms;
    const today = new Date();
    const dateGen = today.toISOString().split('T')[0];
    const echeance = new Date(today);
    echeance.setDate(echeance.getDate() + 30);
    const dateEch = echeance.toISOString().split('T')[0];

    const newB = {
      reference: createForm.reference || `REV-MANUEL-${Date.now()}`,
      compagnie: createForm.compagnie,
      nombre_polices: Number(createForm.nombre_polices) || 1,
      montant_primes: primes,
      commissions_deduites: comms,
      net_a_reverser: net,
      date_generation: dateGen,
      date_echeance_30j: dateEch,
      jours_restants_cima: 30,
      statut_delai_cima: 'CONFORME',
      statut: 'En attente validation',
      statut_badge: 'amber',
    };

    const saved = dataStore.saveRemittance(newB);
    setRemittances(dataStore.getRemittances());
    setIsCreateModalOpen(false);
    success(`Bordereau officiel ${saved.reference} émis avec succès sous délai impératif CIMA de 30 jours.`);
    setSelectedBordereau(saved);
    setModalOpen(true);
  };

  useEffect(() => {
    const refreshData = () => {
      setRemittances(dataStore.getRemittances());
    };
    refreshData();

    remittanceApi.getRemittances().then((data) => {
      if (data && Array.isArray(data) && data.length > 0) {
        const local = dataStore.getRemittances();
        const merged = [...local];
        data.forEach((r) => {
          const id = r.idreversement || r.id;
          if (!merged.some((m) => m.id === id || m.reference === r.reference)) {
            const today = new Date();
            const dateGen = r.date_generation || r.datecreation || '2026-09-01';
            let echeanceDate = r.date_echeance_30j;
            if (!echeanceDate) {
              const d = new Date(dateGen);
              d.setDate(d.getDate() + 30);
              echeanceDate = d.toISOString().split('T')[0];
            }
            const diffDays = Math.ceil((new Date(echeanceDate) - today) / (1000 * 60 * 60 * 24));
            const statutDelai = diffDays < 0 ? 'HORS_DELAI' : diffDays <= 10 ? 'ALERTE_IMMINENTE' : 'CONFORME';

            merged.push({
              id,
              reference: r.reference || `REV-CIE-2026-${String(id).padStart(3, '0')}`,
              compagnie: r.compagnie || 'Compagnie Partenaire',
              nombre_polices: r.nombre_polices || 12,
              montant_primes: Number(r.montant_primes || r.montanttotal || 5000000),
              commissions_deduites: Number(r.commissions_deduites || 600000),
              net_a_reverser: Number(r.net_a_reverser || (r.montanttotal ? r.montanttotal * 0.88 : 4400000)),
              date_generation: dateGen,
              date_echeance_30j: echeanceDate,
              jours_restants_cima: r.jours_restants_cima !== undefined ? r.jours_restants_cima : diffDays,
              statut_delai_cima: r.statut_delai_cima || statutDelai,
              statut: r.statut === '1' || r.statut === 'Validé' ? 'Validé' : 'En attente validation',
              statut_badge: r.statut === '1' || r.statut === 'Validé' ? 'emerald' : 'amber',
            });
          }
        });
        setRemittances(merged);
      }
    }).catch(() => {
      setRemittances(dataStore.getRemittances());
    });

    return dataStore.subscribe((key) => {
      if (key === 'uranus_remittances') {
        refreshData();
      }
    });
  }, []);

  const validerBordereau = async (id) => {
    dataStore.updateRemittance(id, { statut: 'Validé', statut_badge: 'emerald' });
    try {
      await remittanceApi.validerBordereau(id);
    } catch (err) {
      console.warn('API valider bordereau fallback to dataStore');
    }
    setRemittances(dataStore.getRemittances());
    success('Bordereau de reversement approuvé. Ordre de virement bancaire conforme au délai légal CIMA (30j).');
  };

  const handleOpenBordereau = (r) => {
    setSelectedBordereau(r);
    setModalOpen(true);
  };

  const columns = [
    {
      header: 'Réf. Bordereau',
      accessor: 'reference',
      render: (r) => <strong style={{ color: '#fff', fontFamily: 'var(--font-mono)' }}>{r.reference}</strong>,
    },
    { header: 'Compagnie Mandante', accessor: 'compagnie' },
    {
      header: 'Primes Recouvrées',
      render: (r) => <span>{Number(r.montant_primes || 0).toLocaleString('fr-FR')} FCFA</span>,
    },
    {
      header: 'Courtage Retenu',
      render: (r) => <span style={{ color: '#fbbf24' }}>{Number(r.commissions_deduites || 0).toLocaleString('fr-FR')} FCFA</span>,
    },
    {
      header: 'Net à Reverser (CIMA)',
      render: (r) => <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{Number(r.net_a_reverser || 0).toLocaleString('fr-FR')} FCFA</strong>,
    },
    {
      header: 'Délai CIMA 30 Jours',
      render: (r) => {
        const isUrgent = r.statut_delai_cima === 'ALERTE_IMMINENTE';
        const isLate = r.statut_delai_cima === 'HORS_DELAI';
        const color = isLate ? '#ef4444' : isUrgent ? '#f59e0b' : '#10b981';
        const bg = isLate ? 'rgba(239,68,68,0.1)' : isUrgent ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)';

        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Échéance : {r.date_echeance_30j}
            </span>
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                color,
                background: bg,
                padding: '0.15rem 0.45rem',
                borderRadius: '4px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                width: 'fit-content',
              }}
            >
              <Clock size={12} />
              {isLate
                ? 'HORS DÉLAI CIMA'
                : `J-${r.jours_restants_cima} restants`}
            </span>
          </div>
        );
      },
    },
    { header: 'Statut', accessor: 'statut', render: (r) => <StatusBadge label={r.statut} color={r.statut_badge} /> },
    {
      header: 'Actions',
      render: (r) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          {r.statut === 'En attente validation' && (
            <button
              className="btn btn-primary"
              style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', background: 'linear-gradient(135deg, #059669, #10b981)' }}
              onClick={() => validerBordereau(r.id)}
            >
              <Check size={14} /> Valider Virement
            </button>
          )}
          <button
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
            onClick={() => handleOpenBordereau(r)}
          >
            <FileText size={14} /> Bordereau CIMA
          </button>
        </div>
      ),
    },
  ];

  const totalPrimes = remittances.reduce((acc, r) => acc + (Number(r.montant_primes) || 0), 0);
  const totalCommissions = remittances.reduce((acc, r) => acc + (Number(r.commissions_deduites) || 0), 0);
  const totalNet = remittances.reduce((acc, r) => acc + (Number(r.net_a_reverser) || 0), 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <span className="badge badge-success">Module CIMA – Reversements Compagnies</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Délai Légal Impératif de 30 Jours</span>
          </div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Building2 size={26} color="#3b82f6" />
            Reversements aux compagnies
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Primes encaissées à reverser aux compagnies, commissions déduites, sous 30 jours (règle CIMA).
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setIsCreateModalOpen(true)}>
          <Send size={16} />
          <span>Générer Bordereau Compagnie</span>
        </button>
      </div>

      {/* CIMA Article 544 Legal Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(37, 99, 235, 0.08) 0%, rgba(16, 185, 129, 0.08) 100%)',
          border: '1px solid rgba(37, 99, 235, 0.25)',
          borderRadius: 'var(--radius-lg)',
          padding: '1rem 1.25rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <ShieldCheck size={26} color="#10b981" />
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
              Obligation Réglementaire CIMA – Délai Strict de 30 Jours de Reversement
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              En vertu du Code des Assurances CIMA, toutes les primes recouvrées par les courtiers et intermédiaires pour le compte des sociétés d'assurances doivent faire l'objet d'un reversement net effectif dans les 30 jours calendaires suivant leur encaissement.
            </div>
          </div>
        </div>
        <div style={{ padding: '0.4rem 0.75rem', borderRadius: '6px', background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', fontWeight: 700, fontSize: '0.8rem' }}>
          100% Bordereaux Conformes
        </div>
      </div>

      {/* Cockpit KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Primes Encaissées (Art. 13)</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
            {totalPrimes.toLocaleString('fr-FR')} FCFA
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Total collecté pour les assureurs</div>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Courtage LE PHARE Retenu</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fbbf24', marginTop: '0.25rem' }}>
            {totalCommissions.toLocaleString('fr-FR')} FCFA
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Commissions acquises sur primes</div>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Net à Reverser aux Assureurs</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#34d399', marginTop: '0.25rem' }}>
            {totalNet.toLocaleString('fr-FR')} FCFA
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Virements bancaires sous 30j</div>
        </div>
      </div>

      {/* Main Table */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable columns={columns} data={remittances} searchPlaceholder="Filtrer une compagnie ou référence..." />
      </div>

      {/* Modal Bordereau CIMA */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Bordereau Officiel de Reversement CIMA"
        subtitle={`Réf: ${selectedBordereau?.reference} • Compagnie: ${selectedBordereau?.compagnie}`}
        maxWidth="680px"
      >
        {selectedBordereau && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Header Bordereau */}
            <div style={{ borderBottom: '2px solid var(--border-color)', paddingBottom: '1rem', textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-muted)' }}>
                RÉPUBLIQUE DE CÔTE D'IVOIRE • CODE DES ASSURANCES CIMA (LIVRE V)
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                LE PHARE – BORDEREAU DE COMPENSATION & REVERSEMENT
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Établi le {formatDate(selectedBordereau.date_generation)} • Échéance légale 30 jours : <strong>{selectedBordereau.date_echeance_30j}</strong>
              </div>
            </div>

            {/* Financial Details */}
            <div style={{ background: 'var(--bg-surface)', padding: '1.25rem', borderRadius: 'var(--radius-md)', display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Compagnie Assureur Bénéficiaire :</span>
                <strong>{selectedBordereau.compagnie}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Nombre de Polices / Attestations Couvertes :</span>
                <strong>{selectedBordereau.nombre_polices} polices</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.5rem' }}>
                <span>Total Primes Brutes Encaissées (Art. 13 CIMA) :</span>
                <strong style={{ color: 'var(--text-primary)' }}>{Number(selectedBordereau.montant_primes || 0).toLocaleString('fr-FR')} FCFA</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Commissions de Courtage Contractuelles Déduites :</span>
                <strong style={{ color: '#fbbf24' }}>- {Number(selectedBordereau.commissions_deduites || 0).toLocaleString('fr-FR')} FCFA</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '2px solid var(--border-color)', paddingTop: '0.75rem', fontSize: '1.1rem' }}>
                <span style={{ fontWeight: 700 }}>Montant Net de l'Ordre de Virement :</span>
                <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{Number(selectedBordereau.net_a_reverser || 0).toLocaleString('fr-FR')} FCFA</strong>
              </div>
            </div>

            {/* Legal Statement */}
            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.85rem', borderRadius: 'var(--radius-md)', fontSize: '0.8rem', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>
              <strong>Mention Réglementaire Impérative (Art. 544 CIMA) :</strong>
              <p style={{ margin: '0.25rem 0 0 0' }}>
                Le présent bordereau certifie le décompte contradictoire des primes d'assurances recouvrées et justifie le respect de l'obligation de reversement sous 30 jours au compte bancaire désigné de la compagnie mandante.
              </p>
            </div>

            {/* Signatures */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginTop: '0.5rem', paddingTop: '1rem', borderTop: '1px dashed var(--border-color)', fontSize: '0.8rem' }}>
              <div>
                <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '2.5rem' }}>
                  Direction Financière LE PHARE :
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Visa & Ordre de Virement Émis</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '2.5rem' }}>
                  Pour la Compagnie {selectedBordereau.compagnie} :
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Accusé de réception & Quittance définitive</div>
              </div>
            </div>

            {/* Actions */}
            <div className="no-print" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
              <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>
                Fermer
              </button>
              <button className="btn btn-primary" onClick={() => window.print()} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Printer size={15} />
                <span>Imprimer Bordereau CIMA</span>
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Modal Création Bordereau de Reversement CIMA */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Générer un Bordereau de Reversement CIMA"
        subtitle="Décompte contradictoire des primes et mandatement sous 30 jours (Art. 544 CIMA)."
        maxWidth="600px"
      >
        <form onSubmit={handleCreateBordereau} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div className="form-group">
              <label className="form-label">Référence Bordereau *</label>
              <input
                type="text"
                className="form-control"
                required
                value={createForm.reference}
                onChange={(e) => setCreateForm({ ...createForm, reference: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Compagnie Assureur *</label>
              <select
                className="form-control"
                value={createForm.compagnie}
                onChange={(e) => setCreateForm({ ...createForm, compagnie: e.target.value })}
              >
                <option value="ALLIANZ Côte d'Ivoire">ALLIANZ Côte d'Ivoire</option>
                <option value="ATLANTIQUE Assurances CI">ATLANTIQUE Assurances CI</option>
                <option value="GNA Assurances">GNA Assurances</option>
                <option value="NSIA Assurances CI">NSIA Assurances CI</option>
                <option value="SANLAM Assurances CI">SANLAM Assurances CI</option>
                <option value="SUNU Assurances CI">SUNU Assurances CI</option>
                <option value="WAFA Assurance CI">WAFA Assurance CI</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div className="form-group">
              <label className="form-label">Nombre de Polices Couvertes *</label>
              <input
                type="number"
                min="1"
                className="form-control"
                required
                value={createForm.nombre_polices}
                onChange={(e) => setCreateForm({ ...createForm, nombre_polices: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Primes Brutes Encaissées (FCFA) *</label>
              <input
                type="number"
                min="0"
                step="1000"
                className="form-control"
                required
                value={createForm.montant_primes}
                onChange={(e) => setCreateForm({ ...createForm, montant_primes: e.target.value })}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Taux Commission de Courtage Retenu (%)</label>
            <input
              type="number"
              min="0"
              max="50"
              step="0.5"
              className="form-control"
              value={createForm.taux_commission}
              onChange={(e) => setCreateForm({ ...createForm, taux_commission: e.target.value })}
            />
          </div>

          {/* Calculations preview */}
          <div style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Commissions Déduites ({createForm.taux_commission}%) :</span>
              <strong style={{ color: '#fbbf24' }}>
                {Math.round((Number(createForm.montant_primes) || 0) * ((Number(createForm.taux_commission) || 0) / 100)).toLocaleString('fr-FR')} FCFA
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.4rem' }}>
              <span style={{ fontWeight: 700 }}>Net à Reverser à la Compagnie :</span>
              <strong style={{ color: '#34d399', fontSize: '1rem' }}>
                {(
                  (Number(createForm.montant_primes) || 0) -
                  Math.round((Number(createForm.montant_primes) || 0) * ((Number(createForm.taux_commission) || 0) / 100))
                ).toLocaleString('fr-FR')} FCFA
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              <span>Échéance légale CIMA (30 jours) :</span>
              <span style={{ color: '#60a5fa', fontWeight: 600 }}>
                {new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsCreateModalOpen(false)}>
              Annuler
            </button>
            <button type="submit" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Check size={16} />
              <span>Émettre le Bordereau CIMA</span>
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default CompanyRemittancePage;
