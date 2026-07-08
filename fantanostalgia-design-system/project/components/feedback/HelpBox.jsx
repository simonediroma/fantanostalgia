import React from 'react';

export function HelpBox({ title, children, link, linkText = 'Dettagli →', variant = 'info' }) {
  const variants = {
    info:   { borderColor: 'var(--accent2)', iconBg: 'var(--accent2)', iconColor: 'var(--bg)' },
    warn:   { borderColor: 'var(--accent)',  iconBg: 'var(--accent)',  iconColor: 'var(--bg)' },
    danger: { borderColor: 'var(--red)',     iconBg: 'var(--red)',     iconColor: '#fff'       },
  };
  const v = variants[variant] ?? variants.info;

  return (
    <div
      style={{
        display: 'flex',
        gap: 'var(--space-3)',
        background: 'var(--surface)',
        border: `2px solid ${v.borderColor}`,
        padding: 'var(--space-3) var(--space-4)',
        marginBottom: 'var(--space-4)',
      }}
    >
      <span
        style={{
          background: v.iconBg,
          color: v.iconColor,
          fontFamily: 'var(--font-pixel)',
          fontSize: '0.6rem',
          width: '1.5rem',
          height: '1.5rem',
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
          alignSelf: 'flex-start',
          marginTop: '0.1rem',
        }}
      >
        i
      </span>
      <div style={{ flex: 1 }}>
        {title && (
          <strong
            style={{
              fontFamily: 'var(--font-pixel)',
              fontSize: 'var(--fs-pixel-sm)',
              color: 'var(--text)',
              textTransform: 'uppercase',
              display: 'block',
              marginBottom: 'var(--space-2)',
            }}
          >
            {title}
          </strong>
        )}
        <p
          style={{
            fontFamily: 'var(--font-data)',
            fontSize: 'var(--fs-data-sm)',
            color: 'var(--muted)',
            margin: 0,
            lineHeight: 1.6,
          }}
        >
          {children}
        </p>
        {link && (
          <a
            href={link}
            style={{
              fontFamily: 'var(--font-pixel)',
              fontSize: 'var(--fs-pixel-xs)',
              color: v.borderColor,
              textDecoration: 'none',
              display: 'block',
              marginTop: 'var(--space-2)',
            }}
          >
            {linkText}
          </a>
        )}
      </div>
    </div>
  );
}
