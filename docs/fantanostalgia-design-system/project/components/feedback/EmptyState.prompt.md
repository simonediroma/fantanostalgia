Placeholder for empty lists and data areas. Always indicates the next step to take.

```jsx
<EmptyState
  message="Nessun manager ancora."
  action="+ Aggiungi manager"
  onAction={() => openForm()}
/>

<EmptyState message="Nessun risultato per questa giornata." />
```

Write `message` as a complete sentence. Provide `action` + `onAction` whenever there's an immediate user action that would populate the area (e.g. adding the first item, uploading a file).
