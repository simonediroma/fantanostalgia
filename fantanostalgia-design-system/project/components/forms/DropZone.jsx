import React from 'react';

export function DropZone({ onFile, accept, label = 'Trascina il file qui', sublabel, fileName }) {
  const [dragging, setDragging] = React.useState(false);
  const inputRef = React.useRef(null);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file && onFile) onFile(file);
  };

  const handleInputChange = (e) => {
    const file = e.target.files && e.target.files[0];
    if (file && onFile) onFile(file);
  };

  const isConfirmed = !!fileName;
  const isActive = dragging || isConfirmed;

  return (
    <div
      onClick={() => inputRef.current && inputRef.current.click()}
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      style={{
        border: `2px dashed ${isActive ? 'var(--accent)' : 'var(--border)'}`,
        background: dragging ? 'rgba(255,230,0,0.05)' : 'var(--surface)',
        textAlign: 'center',
        padding: 'var(--space-8) var(--space-4)',
        cursor: 'pointer',
        color: isActive ? 'var(--accent)' : 'var(--muted)',
        userSelect: 'none',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        onChange={handleInputChange}
      />
      <div
        style={{
          fontFamily: 'var(--font-pixel)',
          fontSize: 'var(--fs-pixel-sm)',
          textTransform: 'uppercase',
          marginBottom: (sublabel && !isConfirmed) ? 'var(--space-2)' : 0,
        }}
      >
        {isConfirmed ? `✓ ${fileName}` : label}
      </div>
      {sublabel && !isConfirmed && (
        <div
          style={{
            fontFamily: 'var(--font-data)',
            fontSize: 'var(--fs-data-sm)',
            marginTop: 'var(--space-1)',
            color: 'var(--muted)',
          }}
        >
          {sublabel}
        </div>
      )}
    </div>
  );
}
