import React from 'react';

export function WizardSteps({ steps = [], current = 1, onNavigate }) {
  return (
    <div
      style={{
        display: 'flex',
        marginBottom: 'var(--space-8)',
        borderBottom: '2px solid var(--border)',
      }}
    >
      {steps.map((step, i) => {
        const num = i + 1;
        const isDone   = num < current;
        const isActive = num === current;

        return (
          <div
            key={num}
            onClick={onNavigate && !isActive ? () => onNavigate(num) : undefined}
            style={{
              flex: 1,
              textAlign: 'center',
              fontFamily: 'var(--font-pixel)',
              fontSize: 'var(--fs-pixel-sm)',
              textTransform: 'uppercase',
              cursor: (onNavigate && !isActive) ? 'pointer' : 'default',
              padding: 'var(--space-2) var(--space-3)',
              marginBottom: '-2px',
              color: isDone ? 'var(--green)' : (isActive ? 'var(--bg)' : 'var(--muted)'),
              background: isActive ? 'var(--accent)' : 'transparent',
              borderBottom: isDone
                ? '3px solid var(--green)'
                : isActive
                ? '3px solid var(--accent2)'
                : '3px solid transparent',
            }}
          >
            {num} — {step}
          </div>
        );
      })}
    </div>
  );
}
