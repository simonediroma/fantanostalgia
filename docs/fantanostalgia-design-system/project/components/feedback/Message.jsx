import React from 'react';

export function Message({ children, variant = 'ok', onDismiss }) {
  const variants = {
    ok:   { borderColor: 'var(--green)',   color: 'var(--green)',   background: 'rgba(0,255,85,0.08)'   },
    err:  { borderColor: 'var(--red)',     color: 'var(--red)',     background: 'rgba(255,17,68,0.08)'  },
    info: { borderColor: 'var(--accent2)', color: 'var(--accent2)', background: 'rgba(0,212,255,0.08)'  },
    warn: { borderColor: 'var(--accent)',  color: 'var(--accent)',  background: 'rgba(255,230,0,0.08)'  },
  };

  return (
    <div
      style={{
        fontFamily: 'var(--font-pixel)',
        fontSize: 'var(--fs-pixel-sm)',
        textTransform: 'uppercase',
        padding: 'var(--space-2) var(--space-4)',
        border: '2px solid',
        marginBottom: 'var(--space-3)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 'var(--space-2)',
        ...(variants[variant] ?? variants.ok),
      }}
    >
      <span>{children}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'inherit',
            fontFamily: 'var(--font-pixel)',
            fontSize: 'var(--fs-pixel-sm)',
            padding: '0 var(--space-1)',
            boxShadow: 'none',
            lineHeight: 1,
            opacity: 0.7,
          }}
        >
          ×
        </button>
      )}
    </div>
  );
}
