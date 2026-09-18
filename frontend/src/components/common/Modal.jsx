import React, { useEffect } from 'react';
import ReactDOM from 'react-dom';
import { X } from 'lucide-react';

export const Modal = ({ isOpen, onClose, title, subtitle, children, maxWidth = '620px' }) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      document.body.classList.add('modal-open');
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      document.body.classList.remove('modal-open');
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const modalElement = (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div
        className="modal-content"
        style={{ maxWidth }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Official CIMA / Institutional Print Header */}
        <div className="modal-print-header print-only">
          <div className="print-republic-header">
            <div>
              <div className="print-supertitle">RÉPUBLIQUE DE CÔTE D'IVOIRE • MINISTÈRE DES FINANCES • CODE CIMA (CRCA)</div>
              <div className="print-company-name">LE PHARE COURTAGE & GESTION D'ASSURANCES</div>
            </div>
            <div className="print-doc-meta">
              <div>Édité le {new Date().toLocaleDateString('fr-FR')}</div>
              <div className="print-certified-badge">FICHE RÉGLEMENTAIRE OFFICIELLE</div>
            </div>
          </div>
        </div>

        {/* Modal Header */}
        <div className="modal-header">
          <div>
            <h3 className="modal-title" style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              {title}
            </h3>
            {subtitle && (
              <p className="modal-subtitle" style={{ fontSize: '0.825rem', color: 'var(--text-muted)', margin: '0.25rem 0 0 0' }}>
                {subtitle}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Fermer"
            className="modal-close-btn no-print"
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '0.4rem',
              borderRadius: '8px',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = 'var(--text-primary)';
              e.currentTarget.style.background = 'rgba(255,255,255,0.12)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-muted)';
              e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">{children}</div>

        {/* Official CIMA / Institutional Print Footer */}
        <div className="modal-print-footer print-only">
          <div className="print-footer-content">
            <div className="print-legal-notice">
              Certifié conforme aux écritures de gestion et aux dispositions prudentielles du Code des Assurances (CIMA).
            </div>
            <div className="print-signatures">
              <div className="print-sig-block">
                <span>Le Responsable d'Exploitation</span>
                <div className="print-sig-space">Visa & Paraphe</div>
              </div>
              <div className="print-sig-block print-sig-right">
                <span>Direction LE PHARE / Visa CIMA</span>
                <div className="print-sig-space">[ Cachet Officiel ]</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return ReactDOM.createPortal(modalElement, document.body);
};

export default Modal;
