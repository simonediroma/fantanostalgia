Inline label pill for roles, statuses, and metadata. Always uppercase, pixel font, no border-radius.

```jsx
<Badge variant="accent">admin</Badge>
<Badge variant="green">live</Badge>
<Badge variant="red">bloccata</Badge>
<Badge variant="cyan">P</Badge>
<Badge variant="cyan">D</Badge>
<Badge variant="default">bozza</Badge>
<Badge variant="outline">nostalgia</Badge>
```

**Variants**
- `default` — muted blue-grey. Generic tags.
- `accent` — neon yellow. Primary metadata (admin, season labels).
- `cyan` — bright cyan. Role tags (P / D / C / A).
- `green` — neon green. Active / done / positive.
- `red` — hot red. Danger / inactive / blocked.
- `outline` — yellow border, transparent fill. Subtle label.
