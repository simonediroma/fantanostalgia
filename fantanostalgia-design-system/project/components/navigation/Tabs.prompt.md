Tab navigation bar with pixel-font labels. Active tab: yellow fill + cyan bottom border. Used for classifica multi-view (nostalgia / normale / scontri / calendario).

```jsx
const tabs = [
  { id: 'nostalgia', label: 'Nostalgia' },
  { id: 'normale',   label: 'Normale' },
  { id: 'scontri',   label: 'Scontri' },
  { id: 'calendario', label: 'Calendario' },
];

<Tabs tabs={tabs} defaultTab="nostalgia">
  {(active) => (
    <>
      {active === 'nostalgia'  && <ClassificaNostalgia />}
      {active === 'normale'    && <ClassificaNormale />}
      {active === 'scontri'    && <ScontriDiretti />}
      {active === 'calendario' && <Calendario />}
    </>
  )}
</Tabs>
```

The render function pattern lazily mounts panels — pass it for anything with data fetching. Pass static children if you prefer to manage visibility yourself.
