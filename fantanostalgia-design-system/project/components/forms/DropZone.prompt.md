Drag-and-drop upload zone. Click to open the file picker, or drag a file onto it.

```jsx
const [file, setFile] = React.useState(null);

<DropZone
  accept=".xlsx,.xls"
  label="Trascina il listone Excel qui"
  sublabel='Foglio "TutteLeRose" — 2 squadre affiancate, 25 giocatori ciascuna'
  fileName={file?.name}
  onFile={setFile}
/>
```

After selection, `fileName` replaces the label and the border turns yellow to confirm. The sublabel (format hint) disappears once a file is chosen.

Always combine with a `HelpBox` above to explain the expected file format before the user uploads anything.
