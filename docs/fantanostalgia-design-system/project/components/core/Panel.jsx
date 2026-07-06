import React from 'react';

export function Panel({ children, title, variant = 'default' }) {
  const variants = {
    default: { border: '2px solid var(--border)',  boxShadow: 'var(--shadow-md)' },
    accent:  { border: '2px solid var(--accent)',  boxShadow: 'var(--shadow-accent)' },
    danger:  { border: '2px solid var(--red)',     boxShadow: 'var(--shadow-md)' },
    plain:   { border: '1px solid var(--border)',  boxShadow: 'none' },
  };

  return (
    <div
      style={{
        background: 'var(--surface)',
        padding: 'var(--space-5)',
        marginBottom: 'var(--space-4)',
        ...(variants[variant] ?? variants.default),
      }}
    >
      {title && (
        <h4
          style={{
            fontFamily: 'var(--font-pixel)',
            fontSize: 'var(--fs-pixel-md)',
            color: 'var(--accent)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: 'var(--space-3)',
          }}
        >
          {title}
        </h4>
      )}
      {children}
    </div>
  );
}
