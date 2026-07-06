Styled text input with label, focus ring, and error/help states. Label is pixel font; the typed value is data font.

```jsx
<Input
  label="Nome lega"
  id="name"
  placeholder="es. Erculo Tuo 2024/25"
  value={name}
  onChange={e => setName(e.target.value)}
  required
/>

<Input
  label="Budget (crediti)"
  type="number"
  value={budget}
  onChange={e => setBudget(e.target.value)}
  error={budget < 100 ? 'Minimo 100 crediti' : undefined}
  helpText="Valore standard: 500 crediti"
/>

<Input label="Password" type="password" disabled />
```

**States:** default (blue border), focused (yellow border + glow), error (red border + red label), disabled (opacity 0.5).
