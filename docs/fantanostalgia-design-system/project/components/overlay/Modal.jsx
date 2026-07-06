import React from 'react';

export function Modal({ open, title, children, onClose, actions }) {
  if (!open) return null;

  return (
    <div
      onClick={(e) => {
        if (e.target === e.currentTarget && onClose) onClose();
      }}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.75)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          background: 'var(--surface)',
          border: '2px solid var(--accent)',
          boxShadow: 'var(--shadow-modal)',
          padding: 'var(--space-6)',
          maxWidth: '480px',
          width: '90%',
        }}
      >
        {title && (
          <h3
            style={{
              fontFamily: 'var(--font-pixel)',
              fontSize: 'var(--fs-pixel-md)',
              color: 'var(--accent)',
              marginBottom: 'var(--space-3)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {title}
          </h3>
        )}
        <div style={{ marginBottom: actions ? 'var(--space-4)' : 0 }}>
          {children}
        </div>
        {actions && (
          <div
            style={{
              display: 'flex',
              gap: 'var(--space-2)',
              flexWrap: 'wrap',
            }}
          >
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}
