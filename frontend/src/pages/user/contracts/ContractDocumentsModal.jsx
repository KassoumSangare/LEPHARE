import React, { useState } from 'react';
import { Modal } from '../../../components/common/Modal';
import {
  Printer,
  FileText,
  Shield,
  Car,
  CheckCircle,
  Building2,
  Calendar,
  Save,
  Globe,
  DollarSign,
} from 'lucide-react';
import { useToast } from '../../../context/ToastContext';

export const ContractDocumentsModal = ({ isOpen, onClose, docType, contract, onSaveContract }) => {
  const { success } = useToast();
  if (!isOpen || !contract) return null;

  const [attestationNum, setAttestationNum] = useState(
    contract.attestation_asaci_num || `ASACI-2026-${String(contract.id || 101).padStart(5, '0')}`
  );
  const [immat, setImmat] = useState(
    contract.details?.immatriculation || contract.immatriculation || '1234 AB 01'
  );
  const [carteBruneNum, setCarteBruneNum] = useState(
    contract.carte_brune_num || `CB-CEDEAO-CI-2026-${String(contract.id || 101).padStart(4, '0')}`
  );

  const getModalTitle = () => {
    switch (docType) {
      case 'facture':
        return 'Facture Officielle d\'Assurance';
      case 'conditions_particulieres':
        return 'Conditions Particulières du Contrat';
      case 'attestation':
        return 'Édition & Gestion de l\'Attestation ASACI';
      case 'carte_brune':
        return 'Certificat International d\'Assurance (Carte Brune CEDEAO)';
      default:
        return 'Document Contractuel';
    }
  };

  const handleSaveAttestation = () => {
    if (onSaveContract) {
      onSaveContract({
        ...contract,
        attestation_asaci_num: attestationNum,
        immatriculation: immat,
        details: {
          ...(contract.details || {}),
          immatriculation: immat,
        },
      });
    }
    success('Attestation mise à jour avec succès !');
  };

  const primeNette = Number(contract.prime_nette || 0);
  const accessoire = Number(contract.accessoire || 9000);
  const taxe = Number(contract.taxe || 0);
  const primeTtc = Number(contract.prime_totale || (primeNette + accessoire + taxe));

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={getModalTitle()}
      subtitle={`Police N° ${contract.numeropolice} • ${contract.compagnie || 'Assurances'}`}
      size="large"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* =========================================================
            1. FACTURE
           ========================================================= */}
        {docType === 'facture' && (
          <div style={{ background: '#fff', color: '#1e293b', padding: '2rem', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid #0284c7', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', margin: 0 }}>LE PHARE ASSURANCES</h2>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Courtage & Sinistres Délégués • Agréé CIMA</div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Plateau, Boulevard de la République, Abidjan</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0284c7' }}>
                  FACTURE N° FAC-{String(contract.id || '2026').slice(-4)}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Date : {contract.date_emission || new Date().toISOString().split('T')[0]}</div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Police : {contract.numeropolice}</div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem', fontSize: '0.85rem' }}>
              <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <strong style={{ display: 'block', color: '#334155', marginBottom: '0.25rem' }}>FACTURÉ À :</strong>
                <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{contract.client_nom}</div>
                <div style={{ color: '#64748b' }}>{contract.adresse || 'Abidjan, Côte d\'Ivoire'}</div>
                <div style={{ color: '#64748b' }}>Souscripteur N° {contract.client_id ? `CLI-${contract.client_id}` : 'Standard'}</div>
              </div>
              <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <strong style={{ display: 'block', color: '#334155', marginBottom: '0.25rem' }}>COMPAGNIE PORTEUSE :</strong>
                <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{contract.compagnie}</div>
                <div style={{ color: '#64748b' }}>Branche : {contract.branche || 'Automobile'}</div>
                <div style={{ color: '#64748b' }}>Période : Du {contract.date_effet} au {contract.date_expiration}</div>
              </div>
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ background: '#f1f5f9', borderBottom: '2px solid #cbd5e1' }}>
                  <th style={{ padding: '0.65rem', textAlign: 'left' }}>Désignation des Primes & Taxes CIMA</th>
                  <th style={{ padding: '0.65rem', textAlign: 'right' }}>Montant (FCFA)</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={{ padding: '0.65rem' }}>Prime Pure / Nette ({contract.produit})</td>
                  <td style={{ padding: '0.65rem', textAlign: 'right', fontWeight: 600 }}>{primeNette.toLocaleString()} FCFA</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={{ padding: '0.65rem' }}>Accessoires de Police & Frais Courtier</td>
                  <td style={{ padding: '0.65rem', textAlign: 'right', fontWeight: 600 }}>{accessoire.toLocaleString()} FCFA</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={{ padding: '0.65rem' }}>Taxe Légale sur Conventions d'Assurance (TCA 14.5%)</td>
                  <td style={{ padding: '0.65rem', textAlign: 'right', fontWeight: 600 }}>{taxe.toLocaleString()} FCFA</td>
                </tr>
                <tr style={{ background: '#f8fafc', borderTop: '2px solid #0f172a', fontWeight: 800, fontSize: '1rem' }}>
                  <td style={{ padding: '0.75rem', color: '#0f172a' }}>TOTAL TTC À PAYER</td>
                  <td style={{ padding: '0.75rem', textAlign: 'right', color: '#059669' }}>{primeTtc.toLocaleString()} FCFA</td>
                </tr>
              </tbody>
            </table>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: '#64748b' }}>
              <div>Mode d'encaissement : Virement / Chèque / Espèces certifié</div>
              <div style={{ textAlign: 'right', fontWeight: 700, color: '#0284c7' }}>Cachet & Signature Courtier</div>
            </div>
          </div>
        )}

        {/* =========================================================
            2. CONDITIONS PARTICULIÈRES
           ========================================================= */}
        {docType === 'conditions_particulieres' && (
          <div style={{ background: '#fff', color: '#1e293b', padding: '2rem', borderRadius: '8px' }}>
            <div style={{ borderBottom: '2px solid #334155', paddingBottom: '1rem', marginBottom: '1.25rem', textAlign: 'center' }}>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 800, margin: 0 }}>CONDITIONS PARTICULIÈRES D'ASSURANCE</h2>
              <div style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.25rem' }}>
                Soumises aux dispositions du Code des Assurances des États membres de la CIMA
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
              <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '6px' }}>
                <div style={{ color: '#64748b' }}>N° de Police :</div>
                <div style={{ fontWeight: 700, fontSize: '1rem' }}>{contract.numeropolice}</div>
                <div style={{ color: '#64748b', marginTop: '0.35rem' }}>Assureur Conseil :</div>
                <div style={{ fontWeight: 600 }}>LE PHARE COURTAGES</div>
              </div>
              <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '6px' }}>
                <div style={{ color: '#64748b' }}>Souscripteur :</div>
                <div style={{ fontWeight: 700, fontSize: '1rem' }}>{contract.client_nom}</div>
                <div style={{ color: '#64748b', marginTop: '0.35rem' }}>Adresse :</div>
                <div style={{ fontWeight: 600 }}>{contract.adresse || 'Abidjan, Côte d\'Ivoire'}</div>
              </div>
            </div>

            <div style={{ marginBottom: '1.25rem', fontSize: '0.85rem' }}>
              <h4 style={{ fontWeight: 700, borderBottom: '1px solid #e2e8f0', paddingBottom: '0.35rem', marginBottom: '0.5rem' }}>
                1. DESCRIPTION DU RISQUE ASSURÉ
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <div><strong>Branche :</strong> {contract.branche || 'Automobile'}</div>
                <div><strong>Compagnie Porteuse :</strong> {contract.compagnie}</div>
                <div><strong>Date de prise d'effet :</strong> {contract.date_effet}</div>
                <div><strong>Date d'échéance :</strong> {contract.date_expiration}</div>
                {contract.details?.immatriculation && (
                  <div><strong>Immatriculation :</strong> {contract.details.immatriculation}</div>
                )}
                {contract.details?.marque && (
                  <div><strong>Véhicule :</strong> {contract.details.marque} {contract.details.modele}</div>
                )}
              </div>
            </div>

            <div style={{ marginBottom: '1.25rem', fontSize: '0.85rem' }}>
              <h4 style={{ fontWeight: 700, borderBottom: '1px solid #e2e8f0', paddingBottom: '0.35rem', marginBottom: '0.5rem' }}>
                2. TABLEAU DES GARANTIES & DÉCOMPTE DE PRIME
              </h4>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px dashed #cbd5e1' }}>
                <span>Prime Nette :</span>
                <strong>{primeNette.toLocaleString()} FCFA</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px dashed #cbd5e1' }}>
                <span>Accessoire de gestion :</span>
                <strong>{accessoire.toLocaleString()} FCFA</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px dashed #cbd5e1' }}>
                <span>Taxes Réglementaires (TCA) :</span>
                <strong>{taxe.toLocaleString()} FCFA</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', fontWeight: 800, fontSize: '0.95rem', color: '#059669' }}>
                <span>Prime Totale TTC :</span>
                <span>{primeTtc.toLocaleString()} FCFA</span>
              </div>
            </div>

            <div style={{ fontSize: '0.75rem', color: '#64748b', textAlign: 'justify', marginTop: '1rem', borderTop: '1px solid #e2e8f0', paddingTop: '0.75rem' }}>
              En conformité avec l'Article 13 du Code CIMA, la prise d'effet de la garantie est subordonnée au paiement intégral de la prime d'assurance. Fait à Abidjan en deux exemplaires originaux.
            </div>
          </div>
        )}

        {/* =========================================================
            3. ÉDITIONS ATTESTATION
           ========================================================= */}
        {docType === 'attestation' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="glass-panel" style={{ padding: '1.25rem', borderLeft: '4px solid #3b82f6' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <Car size={18} color="#3b82f6" />
                <h4 style={{ margin: 0, fontSize: '1rem', color: '#fff' }}>Paramètres d'Édition de l'Attestation ASACI</h4>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Modifiez les informations du certificat d'assurance automobile avant impression ou transmission au serveur central ASACI.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.35rem' }}>
                    Numéro d'Attestation Officielle
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    value={attestationNum}
                    onChange={(e) => setAttestationNum(e.target.value)}
                    style={{ fontFamily: 'var(--font-mono)' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.35rem' }}>
                    Immatriculation du Véhicule
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    value={immat}
                    onChange={(e) => setImmat(e.target.value)}
                    style={{ fontFamily: 'var(--font-mono)' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
                <button className="btn btn-primary" onClick={handleSaveAttestation} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Save size={15} />
                  <span>Enregistrer l'Attestation</span>
                </button>
              </div>
            </div>

            {/* Preview Sheet */}
            <div style={{ background: '#ecfdf5', color: '#065f46', padding: '1.5rem', borderRadius: '8px', border: '2px solid #10b981' }}>
              <div style={{ textAlign: 'center', borderBottom: '1px solid #a7f3d0', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
                <strong style={{ fontSize: '0.9rem', letterSpacing: '0.5px' }}>RÉPUBLIQUE DE CÔTE D'IVOIRE • ATTESTATION D'ASSURANCE AUTOMOBILE</strong>
                <div style={{ fontSize: '0.75rem', color: '#047857' }}>ASSOCIATION DES SOCIÉTÉS D'ASSURANCES DE CÔTE D'IVOIRE (ASACI)</div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.85rem' }}>
                <div><strong>N° Attestation :</strong> <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{attestationNum}</span></div>
                <div><strong>Immatriculation :</strong> <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{immat}</span></div>
                <div><strong>Assuré :</strong> {contract.client_nom}</div>
                <div><strong>Compagnie :</strong> {contract.compagnie}</div>
                <div><strong>Date d'Effet :</strong> {contract.date_effet}</div>
                <div><strong>Date d'Échéance :</strong> {contract.date_expiration}</div>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================
            4. CARTE BRUNE CEDEAO
           ========================================================= */}
        {docType === 'carte_brune' && (
          <div style={{ background: '#78350f', color: '#fef3c7', padding: '2rem', borderRadius: '8px', border: '2px solid #b45309' }}>
            <div style={{ textAlign: 'center', borderBottom: '2px solid #d97706', paddingBottom: '1rem', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <Globe size={22} color="#fef3c7" />
                <h2 style={{ fontSize: '1.3rem', fontWeight: 800, margin: 0 }}>CARTE BRUNE CEDEAO / ECOWAS BROWN CARD</h2>
              </div>
              <div style={{ fontSize: '0.8rem', color: '#fde68a' }}>
                CERTIFICAT INTERNATIONAL D'ASSURANCE DE RESPONSABILITÉ CIVILE AUTOMOBILE
              </div>
              <div style={{ fontSize: '0.9rem', fontFamily: 'monospace', fontWeight: 700, marginTop: '0.35rem', color: '#fff' }}>
                {carteBruneNum}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '6px' }}>
                <div><strong>Souscripteur :</strong> {contract.client_nom}</div>
                <div><strong>Adresse :</strong> {contract.adresse || 'Abidjan, Côte d\'Ivoire'}</div>
                <div><strong>Immatriculation :</strong> {immat}</div>
              </div>
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '6px' }}>
                <div><strong>Bureau National Émetteur :</strong> Bureau National CI</div>
                <div><strong>Compagnie Garante :</strong> {contract.compagnie}</div>
                <div><strong>Validité :</strong> Du {contract.date_effet} au {contract.date_expiration}</div>
              </div>
            </div>

            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '0.75rem', borderRadius: '6px', fontSize: '0.75rem', lineHeight: '1.4' }}>
              <strong>Territoires couverts (15 Pays Membres CEDEAO) :</strong> Bénin, Burkina Faso, Cap-Vert, Côte d'Ivoire, Gambie, Ghana, Guinée, Guinée-Bissau, Libéria, Mali, Niger, Nigeria, Sénégal, Sierra Leone, Togo.
            </div>
          </div>
        )}

        {/* Modal Footer Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
          <button className="btn btn-secondary" onClick={onClose}>
            Fermer
          </button>
          <button
            className="btn btn-primary"
            onClick={() => window.print()}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <Printer size={15} />
            <span>Imprimer le Document</span>
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default ContractDocumentsModal;
