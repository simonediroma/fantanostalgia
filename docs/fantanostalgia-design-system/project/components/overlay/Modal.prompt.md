Overlay dialog with a dark 75% backdrop. Backdrop click calls `onClose`. Used for confirmations (apertura buste, lock rosa) and detail views (link invito).

```jsx
const [open, setOpen] = React.useState(false);

<Modal
  open={open}
  title="Apertura Buste"
  onClose={() => setOpen(false)}
  actions={<>
    <Button variant="danger" onClick={handleConfirm}>
      Conferma — apri le buste
    </Button>
    <Button variant="secondary" onClick={() => setOpen(false)}>
      Annulla
    </Button>
  </>}
>
  <p style={{
    color: 'var(--muted)',
    fontFamily: 'var(--font-data)',
    fontSize: '0.875rem',
    lineHeight: 1.6,
  }}>
    Questa operazione è irreversibile: gli alter ego verranno rivelati
    a tutti i coach.
  </p>
</Modal>
```

For destructive confirmations: use `variant="danger"` on the confirm button and describe the consequence explicitly in the body text. Always offer an `Annulla` secondary button.
