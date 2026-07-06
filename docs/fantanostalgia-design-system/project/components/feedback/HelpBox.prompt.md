Informational box placed before any non-obvious feature to explain what it does and what's needed. Pattern: prepend to wizard steps, upload zones, lock actions.

```jsx
<HelpBox title="Carica Listone" variant="info">
  Importa la rosa completa della lega da file Excel.
  Il file deve usare il foglio "TutteLeRose" con due squadre affiancate.
</HelpBox>

<HelpBox title="Apertura Buste" variant="warn">
  Questa operazione è irreversibile: gli alter ego vengono rivelati a tutti i coach.
</HelpBox>

<HelpBox variant="danger" title="Conferma e Blocca">
  Una volta confermato, l'associazione storico→attuale non può essere modificata.
</HelpBox>
```

**Variants:** `info` (cyan border — default), `warn` (yellow — caution), `danger` (red — destructive action).
Add `link` + `linkText` to link to format specs or further documentation.
