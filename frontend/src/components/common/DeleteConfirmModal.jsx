import React from 'react';
import { Modal } from './Modal';
import { AlertTriangle, ShieldAlert, Archive, Trash2, XCircle, CheckCircle2, ArrowRight } from 'lucide-react';

export const DeleteConfirmModal = ({
  isOpen,
  onClose,
  onConfirm,
  title = "Confirmation d'archivage réglementaire CIMA",
  itemType = 'élément',
  itemName = '',
  itemCode = '',
  validation = { allowed: true },
  onAlternativeAction,
  alternativeLabel = 'Archiver',
  confirmLabel = "Archiver l'enregistrement",
  isSubmitting = false,
}) => {
  if (!isOpen) return null;

  const isBlocked = !validation.allowed;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="medium"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', padding: '0.5rem 0' }}>
        {/* Header Icon + Description */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '10px',
              backgroundColor: isBlocked ? 'rgba(239, 68, 68, 0.12)' : 'rgba(59, 130, 246, 0.12)',
              border: `1px solid ${isBlocked ? 'rgba(239, 68, 68, 0.25)' : 'rgba(59, 130, 246, 0.25)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            {isBlocked ? (
              <ShieldAlert size={24} style={{ color: '#ef4444' }} />
            ) : (
              <Archive size={24} style={{ color: '#3b82f6' }} />
            )}
          </div>
          <div style={{ flex: 1 }}>
            <h4 style={{ margin: '0 0 0.35rem 0', fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {isBlocked ? 'Action Restreinte par les Règles CIMA' : `Archivage réglementaire de ce ${itemType}`}
            </h4>
            <div
              style={{
                fontSize: '0.85rem',
                color: 'var(--text-secondary)',
                backgroundColor: 'var(--surface-sunken)',
                padding: '0.6rem 0.8rem',
                borderRadius: '6px',
                border: '1px solid var(--border-subtle)',
                marginTop: '0.35rem',
              }}
            >
              {itemCode && (
                <span
                  style={{
                    display: 'inline-block',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 600,
                    color: '#60a5fa',
                    marginRight: '0.5rem',
                  }}
                >
                  [{itemCode}]
                </span>
              )}
              <strong style={{ color: 'var(--text-primary)' }}>{itemName || 'Élément sélectionné'}</strong>
            </div>
          </div>
        </div>

        {/* If Blocked by Business / Regulatory Rule */}
        {isBlocked ? (
          <div
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              borderRadius: '8px',
              padding: '0.85rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#ef4444', fontWeight: 600, fontSize: '0.85rem' }}>
              <XCircle size={16} />
              <span>Règle de Contrôle CIMA & Intégrité Référentielle</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {validation.reason || "Cette action ne peut pas être exécutée en raison de contraintes légales ou d'intégrité de la base."}
            </p>
            {validation.suggestion && (
              <div
                style={{
                  marginTop: '0.35rem',
                  paddingTop: '0.5rem',
                  borderTop: '1px dashed rgba(239, 68, 68, 0.2)',
                  fontSize: '0.8rem',
                  color: '#93c5fd',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                }}
              >
                <ArrowRight size={14} />
                <span><strong>Alternative recommandée :</strong> {validation.suggestion}</span>
              </div>
            )}
          </div>
        ) : (
          <div
            style={{
              backgroundColor: 'rgba(59, 130, 246, 0.08)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              borderRadius: '8px',
              padding: '0.75rem',
              fontSize: '0.82rem',
              color: 'var(--text-secondary)',
              lineHeight: 1.45,
            }}
          >
            <strong>Note de Conformité CIMA :</strong> La suppression définitive d'un enregistrement est proscrite afin de garantir l'intégrité des audits. Cet élément sera placé en <strong>Archive sécurisée</strong> avec horodatage et traçabilité complète de l'opération.
          </div>
        )}

        {/* Actions Footer */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            gap: '0.75rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid var(--border-subtle)',
          }}
        >
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            style={{ minWidth: '100px' }}
          >
            Annuler
          </button>

          {isBlocked ? (
            onAlternativeAction && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  onAlternativeAction();
                  onClose();
                }}
                style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', backgroundColor: '#2563eb' }}
              >
                <Archive size={15} />
                <span>{alternativeLabel}</span>
              </button>
            )
          ) : (
            <button
              type="button"
              className="btn btn-primary"
              disabled={isSubmitting}
              onClick={onConfirm}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                backgroundColor: '#2563eb',
                borderColor: '#3b82f6',
                color: '#fff',
                minWidth: '130px',
                justifyContent: 'center',
              }}
            >
              <Archive size={15} />
              <span>{isSubmitting ? 'Archivage en cours...' : confirmLabel}</span>
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
};
