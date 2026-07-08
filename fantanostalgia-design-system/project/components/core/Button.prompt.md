Renders a pixel-art button with four variants matching the FantaNostalgia 8-bit aesthetic.

```jsx
<Button onClick={() => {}}>Salva</Button>
<Button variant="secondary" onClick={() => {}}>Annulla</Button>
<Button variant="danger" onClick={openBuste}>Apri Buste</Button>
<Button variant="ghost" disabled>Non disponibile</Button>
<Button fullWidth onClick={submit}>Conferma e Blocca</Button>
```

**Variants**
- `default` — neon-yellow fill; hover turns cyan. Primary CTAs.
- `secondary` — outline only. Secondary / cancel actions.
- `danger` — red fill. Irreversible operations (delete, lock, apertura buste).
- `ghost` — muted outline. Tertiary / disabled-feeling actions.

**Notable props:** `fullWidth` stretches to fill the container (forms, lock-bar). `disabled` applies `opacity: 0.45` and blocks all interaction. Hover transitions are instant (8-bit style — no CSS transition).
