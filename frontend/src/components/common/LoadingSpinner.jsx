import React from 'react';

/**
 * Indicateur d'attente volontairement discret et rassurant :
 * trois points qui s'estompent doucement + un message simple (pas de roue qui tourne, pas de jargon technique).
 */
export const LoadingSpinner = ({ text = "Un instant, vos informations s'affichent…", size = 36, overlay = false }) => {
  const dot = Math.max(6, Math.round(size / 5));
  const content = (
    <div
      role="status"
      aria-live="polite"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.875rem',
        padding: overlay ? '2rem' : '3rem 1rem',
        width: '100%',
      }}
    >
      <div style={{ display: 'flex', gap: `${dot}px` }}>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            style={{
              width: dot,
              height: dot,
              borderRadius: '50%',
              background: 'var(--primary-color, #3b82f6)',
              opacity: 0.25,
              animation: `uranus-soft-pulse 1.6s ease-in-out ${i * 0.25}s infinite`,
            }}
          />
        ))}
      </div>
      {text && (
        <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary, #94a3b8)' }}>{text}</span>
      )}
      <style>{`
        @keyframes uranus-soft-pulse {
          0%, 100% { opacity: 0.25; }
          50% { opacity: 0.9; }
        }
      `}</style>
    </div>
  );

  if (overlay) {
    return (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(15, 23, 42, 0.6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 50,
          borderRadius: 'inherit',
        }}
      >
        {content}
      </div>
    );
  }

  return content;
};
