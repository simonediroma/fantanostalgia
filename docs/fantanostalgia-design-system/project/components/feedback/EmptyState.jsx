import React from 'react';

export function EmptyState({ message, action, onAction }) {
  const [hovered, setHovered] = React.useState(false);

  return (
    <div
      style={{
        textAlign: 'center',
        padding: 'var(--space-8) var(--space-4)',
        color: 'var(--muted)',
      }}
    >
      <div
        style={{
          fontFamily: 'var(--font-pixel)',
          fontSize: 'var(--fs-pixel-sm)',
          textTransform: 'uppercase',
          marginBottom: action ? 'var(--space-4)' : 0,
          lineHeight: 1.8,
        }}
      >
        {message}
      </div>
      {action && onAction && (
        <button
          onClick={onAction}
          style={{
            fontFamily: 'var(--font-pixel)',
            fontSize: 'var(--fs-pixel-xs)',
            textTransform: 'uppercase',
            background: 'transparent',
            border: `2px solid ${hovered ? 'var(--accent)' : 'var(--muted)'}`,
            color: hovered ? 'var(--accent)' : 'var(--muted)',
            padding: 'var(--space-2) var(--space-4)',
            cursor: 'pointer',
            boxShadow: 'var(--shadow-sm)',
          }}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          {action}
        </button>
      )}
    </div>
  );
}
