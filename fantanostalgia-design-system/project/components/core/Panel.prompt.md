Container card for grouping related content. Dark surface fill, pixel shadow, sharp corners.

```jsx
<Panel title="Impostazioni Lega">
  <p style={{color:'var(--muted)',fontFamily:'var(--font-data)',fontSize:'0.875rem'}}>
    Stagione corrente: 2024/25
  </p>
</Panel>

<Panel variant="accent">
  <p>Pannello con bordo giallo — per sezioni in evidenza.</p>
</Panel>

<Panel variant="danger" title="Attenzione">
  <p>Operazione irreversibile. Procedi con cautela.</p>
</Panel>

<Panel variant="plain">
  <p>Pannello nested senza ombra, bordo sottile.</p>
</Panel>
```

**Variants:** `default` (blue border + pixel shadow), `accent` (yellow border + yellow shadow — emphasis), `danger` (red border — destructive zones), `plain` (1px border, no shadow — nested content).
