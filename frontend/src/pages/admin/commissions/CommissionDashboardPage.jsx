import React, { useState, useEffect } from 'react';
import { MetricCard } from '../../../components/common/MetricCard';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { commissionApi } from '../../../api/endpoints';
import { dataStore } from '../../../api/dataStore';
import { mockCommissions } from '../../../api/mockData';
import { Coins, CheckCircle, ArrowUpRight, DollarSign, ShieldAlert, Lock, Printer, FileText } from 'lucide-react';
import { useToast } from '../../../context/ToastContext';

export const CommissionDashboardPage = () => {
  const { success, error } = useToast();
  const [selectedBordereau, setSelectedBordereau] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);

  const [affaires, setAffaires] = useState(() => dataStore.getCommissions());

  useEffect(() => {
    let isMounted = true;
    const loadCommissions = async () => {
      try {
        const [dash, aff] = await Promise.all([
          commissionApi.getDashboard().catch(() => null),
          commissionApi.getAffaires().catch(() => []),
        ]);
        if (isMounted && aff && Array.isArray(aff) && aff.length > 0) {
          setAffaires(aff);
        }
      } catch (err) {
        console.error('Erreur commissions Django:', err);
      }
    };
    loadCommissions();
    return () => { isMounted = false; };
  }, []);

  const reglerCommission = async (affaire) => {
    if (!affaire.prime_encaissee) {
      error("Blocage Article 13 CIMA : La prime d'assurance n'ayant pas été encaissée, aucun droit à commission ne peut être décaissé.");
      return;
    }

    try {
      await commissionApi.createPayment({ affaire_id: affaire.id, montant: affaire.montant_commission });
    } catch (err) {
      console.warn('API pay commission fallback');
    }
    dataStore.updateCommission(affaire.id, { statut: 'Payé', statut_badge: 'emerald' });
    setAffaires(dataStore.getCommissions());
    success(`Commission de ${Number(affaire.montant_commission || 0).toLocaleString()} FCFA réglée à ${affaire.apporteur}.`);
  };

  const handleOpenBordereau = (a) => {
    setSelectedBordereau(a);
    setModalOpen(true);
  };

  const columns = [
    {
      header: 'Apporteur / Partenaire',
      accessor: 'apporteur',
      render: (r) => (
        <div>
          <strong style={{ color: '#fff' }}>{r.apporteur}</strong>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{r.contrat} • {r.client}</div>
        </div>
      ),
    },
    {
      header: 'Branche & Plafond CIMA',
      render: (r) => (
        <div>
          <div style={{ fontSize: '0.85rem' }}>{r.branche}</div>
          <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>CIMA {r.plafond_cima}</span>
        </div>
      ),
    },
    {
      header: 'Prime Nette',
      render: (r) => <span>{Number(r.prime_nette || 0).toLocaleString()} FCFA</span>,
    },
    {
      header: 'Contrôle Art. 13 (Encaissement)',
      render: (r) => (
        <span className={`badge ${r.prime_encaissee ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '0.75rem' }}>
          {r.prime_encaissee ? 'Prime Encaissée' : 'Non Encaissée (Bloqué)'}
        </span>
      ),
    },
    {
      header: 'Taux & Rétrocession',
      render: (r) => (
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Taux : {r.taux_commission}</div>
          <strong style={{ color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>
            {Number(r.montant_commission || 0).toLocaleString()} FCFA
          </strong>
        </div>
      ),
    },
    { header: 'Statut', accessor: 'statut', render: (r) => <StatusBadge label={r.statut} color={r.statut_badge} /> },
    {
      header: 'Action',
      render: (r) => (
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          {r.statut === 'En attente' ? (
            r.prime_encaissee ? (
              <button
                className="btn btn-primary"
                style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', background: 'linear-gradient(135deg, #059669, #10b981)' }}
                onClick={() => reglerCommission(r)}
              >
                <CheckCircle size={14} /> Payer
              </button>
            ) : (
              <button
                className="btn btn-secondary"
                disabled
                title="Paiement interdit par l'article 13 CIMA tant que la prime n'est pas recouvrée"
                style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', opacity: 0.6, cursor: 'not-allowed', color: '#f87171' }}
              >
                <Lock size={13} /> Bloqué Art. 13
              </button>
            )
          ) : (
            <button
              className="btn btn-secondary"
              style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
              onClick={() => handleOpenBordereau(r)}
            >
              <FileText size={13} /> Bordereau
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
          <span className="badge badge-warning">Réglementation CIMA Livre V</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Encadrement du Courtage & Apports d'Affaires</span>
        </div>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <Coins size={26} color="#fbbf24" />
          Commissions & Rémunération des Apporteurs
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Calcul des rétrocessions réglementées, contrôle de l'encaissement préalable (Art. 13) et bordereaux de courtage.
        </p>
      </div>

      {/* CIMA Regulatory Reminder */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(37, 99, 235, 0.08) 100%)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
          borderRadius: 'var(--radius-lg)',
          padding: '1rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
        }}
      >
        <ShieldAlert size={26} color="#f59e0b" />
        <div>
          <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
            Règle CIMA sur les Rétrocessions d'Apporteurs (Articles 13 & Livre V)
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Le paiement de toute commission d'apport est strictement conditionné à l'encaissement effectif préalable de la prime auprès de l'assuré. Les barèmes appliqués respectent impérativement les plafonds légaux par branche (Auto : 10% / 12%, IRD : 15%).
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
        <MetricCard title="Total Commissions Générées" value={mockCommissions.kpis.total_commissions_dues} icon={Coins} color="blue" />
        <MetricCard title="Total Déjà Réglé" value={mockCommissions.kpis.total_paye} icon={CheckCircle} color="emerald" />
        <MetricCard title="Reste à Payer aux Apporteurs" value={mockCommissions.kpis.reste_a_payer} icon={DollarSign} color="amber" />
        <MetricCard title="Apporteurs Partenaires" value={`${mockCommissions.kpis.nombre_apporteurs_actifs} cabinets`} icon={Coins} color="purple" />
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2 className="title-md" style={{ color: '#fff' }}>Affaires Souscrites & Droits à Commission CIMA</h2>
        </div>
        <DataTable columns={columns} data={affaires} searchPlaceholder="Filtrer par apporteur, police ou client..." />
      </div>

      {/* Modal Bordereau Apporteur */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Bordereau de Commission Apporteur d'Affaires"
        subtitle={`Apporteur : ${selectedBordereau?.apporteur} • Police : ${selectedBordereau?.contrat}`}
        maxWidth="620px"
      >
        {selectedBordereau && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ borderBottom: '2px solid var(--border-color)', paddingBottom: '0.75rem', textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-muted)' }}>
                LE PHARE COURTAGE & ASSURANCES
              </div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                BORDEREAU DE LIQUIDATION DE COMMISSION
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Date de règlement : {new Date().toLocaleDateString('fr-FR')} • Conformité CIMA Livre V
              </div>
            </div>

            <div style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-md)', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Bénéficiaire :</span>
                <strong>{selectedBordereau.apporteur}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Police / Client :</span>
                <strong>{selectedBordereau.contrat} ({selectedBordereau.client})</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Branche d'assurance :</span>
                <span>{selectedBordereau.branche} (Plafond CIMA : {selectedBordereau.plafond_cima})</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.5rem' }}>
                <span>Prime Nette Encaissée (Art. 13) :</span>
                <strong>{Number(selectedBordereau.prime_nette || 0).toLocaleString()} FCFA</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Taux de rétrocession appliqué :</span>
                <strong style={{ color: '#fbbf24' }}>{selectedBordereau.taux_commission}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '2px solid var(--border-color)', paddingTop: '0.5rem', fontSize: '1.1rem' }}>
                <span style={{ fontWeight: 700 }}>Net Réglé à l'Apporteur :</span>
                <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{Number(selectedBordereau.montant_commission || 0).toLocaleString()} FCFA</strong>
              </div>
            </div>

            <div className="no-print" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
              <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>
                Fermer
              </button>
              <button className="btn btn-primary" onClick={() => window.print()} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Printer size={15} />
                <span>Imprimer Bordereau</span>
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default CommissionDashboardPage;
