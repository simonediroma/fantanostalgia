Neon-green fill bar for tracking bounded completion. Used in the coach lock-bar for nostalgia player assignments.

```jsx
<ProgressBar value={7} max={12} label="7/12 assegnati" showPercent />
<ProgressBar value={100} max={100} label="Completato" />
<ProgressBar value={3} max={10} />
```

Clamps `value` between 0 and `max`. The fill uses a CSS `transition: width 0.3s` for smooth updates. Label is drawn in data font, percentage in neon green.
