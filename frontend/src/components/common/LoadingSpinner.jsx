import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner = ({ text = 'Chargement des données...', size = 36, overlay = false }) => {
  const content = (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.875rem',
        padding: overlay ? '2rem' : '3.5rem 1rem',
        width: '100%',
      }}
    >
      <Loader2
        size={size}
        style={{
          color: 'var(--primary-color, #10b981)',
          animation: 'uranus-spin 1s linear infinite',
        }}
      />
      {text && (
        <span
          style={{
            fontSize: '0.875rem',
            fontWeight: 500,
            color: 'var(--text-secondary, #94a3b8)',
            letterSpacing: '0.01em',
          }}
        >
          {text}
        </span>
      )}
      <style>{`
        @keyframes uranus-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );

  if (overlay) {
    return (
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.75)',
          backdropFilter: 'blur(3px)',
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
