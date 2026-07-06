Inline feedback for operation outcomes. Pixel font, all-caps, border matches semantic color.

```jsx
<Message variant="ok">Listone importato con successo!</Message>
<Message variant="err" onDismiss={() => setMsg(null)}>
  Errore nel caricamento del file.
</Message>
<Message variant="warn">Attenzione: operazione irreversibile.</Message>
<Message variant="info">Sorteggio in corso...</Message>
```

**Auto-dismiss pattern:** caller sets a timer after showing `ok` messages:
```jsx
setMsg({ text: 'Salvato!', variant: 'ok' });
setTimeout(() => setMsg(null), 3500);
```

**Variants:** `ok` (neon green), `err` (hot red), `warn` (yellow), `info` (cyan).
Pass `onDismiss` to show the × button for manual dismiss on errors.
