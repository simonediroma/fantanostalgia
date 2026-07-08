import React from 'react';

export function Input({
  label,
  id,
  type = 'text',
  placeholder,
  value,
  onChange,
  disabled = false,
  error,
  helpText,
  required = false,
}) {
  const [focused, setFocused] = React.useState(false);
  const borderColor = error
    ? 'var(--red)'
    : focused
    ? 'var(--accent)'
    : 'var(--border)';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-1)',
        width: '100%',
      }}
    >
      {label && (
        <label
          htmlFor={id}
          style={{
            fontFamily: 'var(--font-pixel)',
            fontSize: 'var(--fs-pixel-sm)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--muted)',
            display: 'block',
          }}
        >
          {label}
          {required && (
            <span style={{ color: 'var(--red)', marginLeft: '0.25rem' }}>*</span>
          )}
        </label>
      )}
      <input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        disabled={disabled}
        required={required}
        style={{
          background: 'var(--bg)',
          border: `2px solid ${borderColor}`,
          color: 'var(--text)',
          fontFamily: 'var(--font-data)',
          fontSize: 'var(--fs-data-md)',
          padding: 'var(--space-2) var(--space-3)',
          width: '100%',
          outline: 'none',
          opacity: disabled ? 0.5 : 1,
          boxShadow: focused ? `0 0 0 1px ${borderColor}` : 'none',
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
      />
      {error && (
        <span
          style={{
            fontFamily: 'var(--font-pixel)',
            fontSize: 'var(--fs-pixel-xs)',
            color: 'var(--red)',
            textTransform: 'uppercase',
          }}
        >
          {error}
        </span>
      )}
      {helpText && !error && (
        <span
          style={{
            fontFamily: 'var(--font-data)',
            fontSize: 'var(--fs-data-sm)',
            color: 'var(--muted)',
          }}
        >
          {helpText}
        </span>
      )}
    </div>
  );
}
