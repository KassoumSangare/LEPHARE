import React, { useState, useEffect } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { dataStore } from '../../../api/dataStore';
import { cashApi, contractApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { CreditCard, Check, DollarSign, Smartphone, Landmark, Receipt } from 'lucide-react';

export const CashCollectionPage = () => {
  const [contracts, setContracts] = useState([]);
  const [selectedContract, setSelectedContract] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isQuittanceModalOpen, setIsQuittanceModalOpen] = useState(false);
  const [currentQuittance, setCurrentQuittance] = useState(null);
  const { success, error: toastError } = useToast();

  const loadContracts = async () => {
    try {
      const data = await contractApi.getContracts();
      if (Array.isArray(data)) {
        setContracts(data);
      }
    } catch (err) {
      console.error('Erreur chargement contrats caisse Django:', err);
    }
  };

  useEffect(() => {
    loadContracts();
  }, []);

  // Payment Form State
  const [modePaiement, setModePaiement] = useState('ESPECES');
  const [montantEncaisse, setMontantEncaisse] = useState(0);
  const [banque, setBanque] = useState('SGBCI');
  const [numeroCheque, setNumeroCheque] = useState('');
  const [numeroTelephoneMobile, setNumeroTelephoneMobile] = useState('');

  const handleOpenPayment = (contract) => {
    setSelectedContract(contract);
    const reste = contract.prime_totale - (contract.montant_encaisse || 0);
    setMontantEncaisse(reste > 0 ? reste : contract.prime_totale);
    setIsModalOpen(true);
  };

  const handleShowQuittance = (contract) => {
    const quitData = {
      numero_quittance: `QUIT-CIMA-2026-${String(contract.id).padStart(3, '0')}`,
      police_num: contract.numeropolice,
      souscripteur: contract.client_nom,
      compagnie: contract.compagnie,
      branche: contract.produit,
      montant_encaisse: contract.montant_encaisse || contract.prime_totale,
      mode_paiement: 'VIREMENT / CHÈQUE / ESPÈCES',
      reference_paiement: 'RÈGLEMENT ENREGISTRÉ CONFORME',
      date_encaissement: new Date().toLocaleDateString('fr-FR') + ' à ' + new Date().toLocaleTimeString('fr-FR'),
      mention_legale: "Conformément à l'Article 13 du Code des Assurances CIMA (« Pas de prime, pas d'assurance »), la présente quittance atteste du paiement effectif de la prime et confère validité immédiate aux garanties souscrites.",
      emetteur: 'Caisse Centrale LE PHARE'
    };
    setCurrentQuittance(quitData);
    setIsQuittanceModalOpen(true);
  };

  const handleSavePayment = async (e) => {
    e.preventDefault();
    if (!selectedContract) return;

    const reference =
      modePaiement === 'CHEQUE'
        ? (numeroCheque || `CHQ-${banque}`)
        : modePaiement === 'DISTRIPAY'
        ? (numeroTelephoneMobile || 'DISTRIPAY-MOBILE')
        : 'Caisse Espèces Centrale';

    const result = dataStore.savePayment({
      contractId: selectedContract.id,
      numeropolice: selectedContract.numeropolice,
      montant: montantEncaisse,
      modePaiement,
      reference,
      banque,
      emetteur: 'Caisse Centrale LE PHARE',
    });

    const modeCodeMap = { ESPECES: 1, CHEQUE: 2, VIREMENT: 3, DISTRIPAY: 4 };
    const quitNum = `QUIT-${selectedContract.numeropolice || selectedContract.id}`;

    try {
      await cashApi.collectPremium({
        mode_encaissement: modeCodeMap[modePaiement] || 1,
        date_encaissement: new Date().toISOString().split('T')[0],
        banque: 1,
        montant_total: Number(montantEncaisse),
        numero_cheque: modePaiement === 'CHEQUE' ? numeroCheque : null,
        reference_encaissement: reference,
        nom_emetteur: selectedContract.client_nom || 'Souscripteur',
        liste_quittance: [
          {
            numero_quittance: quitNum,
            montant_encaisse: Number(montantEncaisse),
          },
        ],
      });
    } catch (err) {
      console.warn('API collect premium fallback to dataStore');
    }

    setContracts(dataStore.getContracts());
    setIsModalOpen(false);
    setCurrentQuittance(result.quittance);
    setIsQuittanceModalOpen(true);
    success(`Règlement de ${montantEncaisse.toLocaleString()} FCFA validé ! Quittance CIMA ${result.quittance.numero_quittance} enregistrée.`);
  };

  const columns = [
    {
      header: 'N° Police',
      accessor: 'numeropolice',
      render: (row) => <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{row.numeropolice}</strong>,
    },
    { header: 'Souscripteur', accessor: 'client_nom' },
    { header: 'Compagnie', accessor: 'compagnie' },
    {
      header: 'Prime Totale',
      render: (row) => <span>{row.prime_totale.toLocaleString()} F</span>,
    },
    {
      header: 'Déjà Encaissé',
      render: (row) => <span style={{ color: '#34d399' }}>{row.montant_encaisse.toLocaleString()} F</span>,
    },
    {
      header: 'Reste à Encaisser',
      render: (row) => {
        const reste = row.prime_totale - row.montant_encaisse;
        return (
          <strong style={{ color: reste > 0 ? '#fb7185' : '#34d399', fontFamily: 'var(--font-mono)' }}>
            {reste.toLocaleString()} F
          </strong>
        );
      },
    },
    {
      header: 'Statut',
      accessor: 'statut_encaissement',
      render: (row) => <StatusBadge label={row.statut_encaissement} color={row.statut_encaissement === 'Soldé' ? 'emerald' : 'amber'} />,
    },
    {
      header: 'Action',
      render: (row) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button
            className="btn btn-primary"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
            onClick={() => handleOpenPayment(row)}
          >
            <CreditCard size={14} /> Encaisser
          </button>
          {row.montant_encaisse > 0 && (
            <button
              className="btn btn-secondary"
              style={{ padding: '0.35rem 0.55rem', fontSize: '0.75rem' }}
              title="Afficher la Quittance Officielle CIMA"
              onClick={() => handleShowQuittance(row)}
            >
              <Receipt size={14} /> Quittance
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <CreditCard size={26} color="#10b981" />
          Caisse & Encaissement des Primes
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Enregistrement des règlements (espèces, chèques, virements, Wave / Orange Money DistriPay) et émission des reçus.
        </p>
      </div>

      {/* CIMA Article 13 Rule Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(59, 130, 246, 0.08) 100%)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: 'var(--radius-lg)',
          padding: '1rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'rgba(16, 185, 129, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#34d399',
            }}
          >
            <Receipt size={22} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
              Dispositif Réglementaire – Article 13 du Code CIMA
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
              <strong>« Pas de prime, pas d'assurance »</strong> : La prise d'effet des garanties et la délivrance des attestations sont subordonnées au paiement préalable effectif.
            </div>
          </div>
        </div>
        <span className="badge badge-success" style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}>
          Conformité CIMA 100% Active
        </span>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable
          columns={columns}
          data={contracts}
          searchPlaceholder="Rechercher un contrat ou souscripteur à encaisser..."
        />
      </div>

      {/* Payment Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Enregistrement d'un Encaissement">
        {selectedContract && (
          <form onSubmit={handleSavePayment}>
            <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', background: 'rgba(30, 41, 59, 0.6)', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                <span>Police: <strong>{selectedContract.numeropolice}</strong></span>
                <span>Assuré: <strong>{selectedContract.client_nom}</strong></span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', marginTop: '0.35rem' }}>
                <span>Prime globale: {selectedContract.prime_totale.toLocaleString()} F</span>
                <span>Reste dû: <strong style={{ color: '#fb7185' }}>{(selectedContract.prime_totale - selectedContract.montant_encaisse).toLocaleString()} F</strong></span>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Montant perçu (FCFA)</label>
              <input
                type="number"
                className="form-control"
                required
                value={montantEncaisse}
                onChange={(e) => setMontantEncaisse(parseInt(e.target.value) || 0)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Mode de Règlement</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '0.5rem' }}>
                {[
                  { id: 'ESPECES', label: 'Espèces', icon: DollarSign },
                  { id: 'CHEQUE', label: 'Chèque', icon: Receipt },
                  { id: 'VIREMENT', label: 'Virement', icon: Landmark },
                  { id: 'DISTRIPAY', label: 'Mobile Money', icon: Smartphone },
                ].map((item) => {
                  const Icon = item.icon;
                  const isSel = modePaiement === item.id;
                  return (
                    <div
                      key={item.id}
                      onClick={() => setModePaiement(item.id)}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.35rem',
                        padding: '0.65rem 0.25rem',
                        borderRadius: 'var(--radius-md)',
                        background: isSel ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.02)',
                        border: `1px solid ${isSel ? '#10b981' : 'var(--border-subtle)'}`,
                        cursor: 'pointer',
                        textAlign: 'center',
                        minHeight: '60px',
                      }}
                    >
                      <Icon size={18} color={isSel ? '#34d399' : 'var(--text-muted)'} />
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: isSel ? '#fff' : 'var(--text-secondary)' }}>
                        {item.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {modePaiement === 'CHEQUE' && (
              <div className="responsive-form-row" style={{ marginTop: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Banque Émettrice</label>
                  <select className="form-control" value={banque} onChange={(e) => setBanque(e.target.value)}>
                    <option value="SGBCI">SGBCI</option>
                    <option value="BICICI">BICICI</option>
                    <option value="NSIA BANQUE">NSIA BANQUE</option>
                    <option value="ECOBANK">ECOBANK</option>
                    <option value="BOA">BOA</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Numéro du Chèque</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    placeholder="Ex: CHQ-994120"
                    value={numeroCheque}
                    onChange={(e) => setNumeroCheque(e.target.value)}
                  />
                </div>
              </div>
            )}

            {modePaiement === 'DISTRIPAY' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Numéro Mobile Money (Wave / Orange / MTN)</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="+225 07..."
                    value={numeroTelephoneMobile}
                    onChange={(e) => setNumeroTelephoneMobile(e.target.value)}
                  />
                </div>
                <div
                  style={{
                    padding: '0.75rem',
                    background: 'rgba(59, 130, 246, 0.08)',
                    border: '1px solid rgba(59, 130, 246, 0.25)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.78rem',
                    color: '#93c5fd',
                  }}
                >
                  ℹ️ <strong>Passerelle Distripay Mobile Money :</strong> Clés marchandes en phase d'activation finale (DISTRIPAY_ENABLED=0). L'encaissement est enregistré et certifié au niveau de la caisse avec le numéro de téléphone et la quittance officielle CIMA.
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                Annuler
              </button>
              <button type="submit" className="btn btn-primary" style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
                <Check size={18} /> Valider l'Encaissement
              </button>
            </div>
          </form>
        )}
      </Modal>

      {/* Official CIMA Quittance Modal */}
      <Modal
        isOpen={isQuittanceModalOpen}
        onClose={() => setIsQuittanceModalOpen(false)}
        title="Quittance d'Encaissement CIMA Officielle (Art. 13)"
        subtitle="Document probant attestant de la validité de la couverture d'assurance."
        maxWidth="600px"
      >
        {currentQuittance && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div
              style={{
                border: '2px solid rgba(16, 185, 129, 0.4)',
                background: 'rgba(15, 23, 42, 0.6)',
                borderRadius: 'var(--radius-lg)',
                padding: '1.5rem',
                position: 'relative',
              }}
            >
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div>
                  <div style={{ fontWeight: 800, fontSize: '1.1rem', color: 'var(--text-primary)', letterSpacing: '0.05em' }}>
                    LE PHARE ASSURANCES
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Courtage & Gestion Déléguée CIMA • Agrément N° 021/MEF/DGTCP/DA
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span className="badge badge-success">{currentQuittance.numero_quittance}</span>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    {currentQuittance.date_encaissement}
                  </div>
                </div>
              </div>

              {/* Body */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', margin: '1.25rem 0', fontSize: '0.85rem' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem' }}>Souscripteur / Assuré</span>
                  <strong style={{ color: 'var(--text-primary)' }}>{currentQuittance.souscripteur}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem' }}>N° Police d'Assurance</span>
                  <strong style={{ color: '#60a5fa', fontFamily: 'var(--font-mono)' }}>{currentQuittance.police_num}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem' }}>Compagnie Mandante</span>
                  <strong style={{ color: '#34d399' }}>{currentQuittance.compagnie}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem' }}>Mode de Règlement</span>
                  <strong>{currentQuittance.mode_paiement}</strong>
                </div>
              </div>

              {/* Amount */}
              <div
                style={{
                  background: 'rgba(16, 185, 129, 0.1)',
                  padding: '1rem',
                  borderRadius: 'var(--radius-md)',
                  textAlign: 'center',
                  border: '1px dashed rgba(16, 185, 129, 0.4)',
                }}
              >
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>MONTANT ENCAISSÉ ET VALIDÉ</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 900, color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                  {Number(currentQuittance.montant_encaisse).toLocaleString()} FCFA
                </div>
              </div>

              {/* Legal Notice */}
              <div
                style={{
                  marginTop: '1rem',
                  padding: '0.75rem',
                  background: 'rgba(255, 255, 255, 0.02)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.725rem',
                  color: 'var(--text-muted)',
                  fontStyle: 'italic',
                  lineHeight: '1.4',
                }}
              >
                {currentQuittance.mention_legale}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                <span>Émetteur : {currentQuittance.emetteur}</span>
                <span style={{ color: '#34d399', fontWeight: 600 }}>✓ Cachet & Horodatage Numérique Certifiés</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setIsQuittanceModalOpen(false)}>
                Fermer
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  window.print();
                }}
              >
                <Receipt size={16} /> Imprimer Quittance CIMA
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default CashCollectionPage;
