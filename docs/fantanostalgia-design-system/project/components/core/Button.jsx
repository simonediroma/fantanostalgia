import React from 'react';

export function Button({
  children,
  variant = 'default',
  disabled = false,
  onClick,
  type = 'button',
  fullWidth = false,
}) {
  const [hovered, setHovered] = React.useState(false);
  const on = hovered && !disabled;

  const base = {
    fontFamily: 'var(--font-pixel)',
    fontSize: '0.6rem',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    border: '2px solid',
    boxShadow: disabled ? 'none' : 'var(--shadow-sm)',
    cursor: disabled ? 'default' : 'pointer',
    padding: '0.4rem 1rem',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.35rem',
    whiteSpace: 'nowrap',
    opacity: disabled ? 0.45 : 1,
    lineHeight: 1.5,
    width: fullWidth ? '100%' : undefined,
    justifyContent: fullWidth ? 'center' : undefined,
  };

  const variants = {
    default: {
      background: on ? 'var(--accent2)' : 'var(--accent)',
      borderColor: on ? 'var(--accent2)' : 'var(--accent)',
      color: 'var(--bg)',
    },
    secondary: {
      background: on ? 'var(--accent)' : 'transparent',
      borderColor: 'var(--accent)',
      color: on ? 'var(--bg)' : 'var(--accent)',
    },
    danger: {
      background: 'var(--red)',
      borderColor: 'var(--red)',
      color: '#fff',
      opacity: disabled ? 0.45 : on ? 0.85 : 1,
    },
    ghost: {
      background: 'transparent',
      borderColor: on ? 'var(--accent)' : 'var(--muted)',
      color: on ? 'var(--accent)' : 'var(--muted)',
    },
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      style={{ ...base, ...(variants[variant] ?? variants.default) }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {children}
    </button>
  );
}
