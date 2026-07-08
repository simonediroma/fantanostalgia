Data table with neon-yellow column headers, hover highlight, and horizontal scroll on small viewports.

```jsx
<Table
  columns={[
    { label: '#',      align: 'center', pixel: true },
    { label: 'Squadra' },
    { label: 'Nostalgia', align: 'right', color: 'var(--green)' },
    { label: 'Normale',   align: 'right' },
    { label: 'Diff',      align: 'right' },
  ]}
  rows={[
    ['1', 'Erculo Tuo', <span style={{color:'var(--green)'}}>98.5</span>, '91.0', '+7.5'],
    ['2', 'Roma FC',    <span style={{color:'var(--green)'}}>91.0</span>, '88.5', '+2.5'],
  ]}
  onRowClick={(row, i) => console.log(i)}
/>
```

**Column options:** `align`, `pixel` (pixel font in cells — good for rank/role), `color` (sets cell text color), `nowrap`.

Pass React nodes as cell values for colored scores, badges, inline buttons, etc.
