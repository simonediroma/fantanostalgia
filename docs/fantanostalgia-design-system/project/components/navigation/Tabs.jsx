import React from 'react';

function TabButton({ tab, isActive, onClick }) {
  const [hovered, setHovered] = React.useState(false);
  return (
    <button
      onClick={onClick}
      style={{
        fontFamily: 'var(--font-pixel)',
        fontSize: 'var(--fs-pixel-xs)',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        padding: 'var(--space-2) var(--space-3)',
        background: isActive ? 'var(--accent)' : 'transparent',
        color: isActive ? 'var(--bg)' : (hovered ? 'var(--text)' : 'var(--muted)'),
        border: 'none',
        borderBottom: isActive ? '2px solid var(--accent2)' : '2px solid transparent',
        cursor: 'pointer',
        boxShadow: 'none',
        marginBottom: '-2px',
        whiteSpace: 'nowrap',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {tab.label}
    </button>
  );
}

export function Tabs({ tabs = [], defaultTab, children }) {
  const [active, setActive] = React.useState(
    defaultTab || (tabs[0] && tabs[0].id) || ''
  );

  return (
    <div>
      <div
        style={{
          display: 'flex',
          gap: 0,
          borderBottom: '2px solid var(--border)',
          marginBottom: 'var(--space-5)',
        }}
      >
        {tabs.map((tab) => (
          <TabButton
            key={tab.id}
            tab={tab}
            isActive={tab.id === active}
            onClick={() => setActive(tab.id)}
          />
        ))}
      </div>
      <div>
        {typeof children === 'function' ? children(active) : children}
      </div>
    </div>
  );
}
