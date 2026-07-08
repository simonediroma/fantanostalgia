import React from 'react';

export function ProgressBar({ value = 0, max = 100, label, showPercent = false }) {
  const pct = Math.min(100, Math.max(0, max > 0 ? (value / max) * 100 : 0));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      {(label || showPercent) && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontFamily: 'var(--font-data)',
            fontSize: 'var(--fs-data-sm)',
            color: 'var(--muted)',
          }}
        >
          {label && <span>{label}</span>}
          {showPercent && (
            <span style={{ color: 'var(--green)' }}>{Math.round(pct)}%</span>
          )}
        </div>
      )}
      <div
        style={{
          background: '#1a1a40',
          border: '1px solid var(--border)',
          height: '12px',
        }}
      >
        <div
          style={{
            background: 'var(--green)',
            height: '100%',
            width: `${pct}%`,
            transition: 'width 0.3s',
          }}
        />
      </div>
    </div>
  );
}
