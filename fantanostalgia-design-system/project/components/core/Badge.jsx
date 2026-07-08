import React from 'react';

export function Badge({ children, variant = 'default' }) {
  const variants = {
    default: { background: 'var(--border)',  color: 'var(--muted)'  },
    accent:  { background: 'var(--accent)',  color: 'var(--bg)'     },
    cyan:    { background: 'var(--accent2)', color: 'var(--bg)'     },
    green:   { background: 'var(--green)',   color: '#000'          },
    red:     { background: 'var(--red)',     color: '#fff'          },
    outline: {
      background: 'transparent',
      color: 'var(--accent)',
      border: '1px solid var(--accent)',
    },
  };

  return (
    <span
      style={{
        display: 'inline-block',
        fontFamily: 'var(--font-pixel)',
        fontSize: 'var(--fs-pixel-xs)',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        padding: '2px 6px',
        verticalAlign: 'middle',
        lineHeight: 1.6,
        ...(variants[variant] ?? variants.default),
      }}
    >
      {children}
    </span>
  );
}
