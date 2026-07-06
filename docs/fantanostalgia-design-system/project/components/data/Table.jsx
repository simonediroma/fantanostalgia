import React from 'react';

function TableRow({ cells, columns, onRowClick, rowData, index }) {
  const [hovered, setHovered] = React.useState(false);
  return (
    <tr
      onClick={onRowClick ? () => onRowClick(rowData, index) : undefined}
      style={{
        cursor: onRowClick ? 'pointer' : 'default',
        background: hovered ? 'rgba(255,230,0,0.07)' : 'transparent',
        borderBottom: '1px solid var(--border)',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {cells.map((cell, ci) => {
        const col = columns[ci] || {};
        return (
          <td
            key={ci}
            style={{
              padding: '0.5rem 0.75rem',
              verticalAlign: 'middle',
              border: '1px solid var(--border)',
              color: col.color || undefined,
              fontFamily: col.pixel ? 'var(--font-pixel)' : 'var(--font-data)',
              fontSize: col.pixel ? 'var(--fs-pixel-xs)' : undefined,
              textAlign: col.align || 'left',
              whiteSpace: col.nowrap ? 'nowrap' : undefined,
            }}
          >
            {cell}
          </td>
        );
      })}
    </tr>
  );
}

export function Table({ columns = [], rows = [], onRowClick }) {
  const cellsFor = (row) => (Array.isArray(row) ? row : row.cells || []);

  return (
    <div style={{ overflowX: 'auto' }}>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          border: '2px solid var(--border)',
          fontFamily: 'var(--font-data)',
          fontSize: 'var(--fs-data-md)',
        }}
      >
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th
                key={i}
                style={{
                  background: 'var(--accent)',
                  color: 'var(--bg)',
                  fontFamily: 'var(--font-pixel)',
                  fontSize: 'var(--fs-pixel-sm)',
                  letterSpacing: '0.06em',
                  padding: '0.5rem 0.75rem',
                  textAlign: col.align || 'left',
                  textTransform: 'uppercase',
                  whiteSpace: 'nowrap',
                  border: '1px solid var(--bg)',
                }}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <TableRow
              key={ri}
              cells={cellsFor(row)}
              columns={columns}
              onRowClick={onRowClick}
              rowData={row}
              index={ri}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
