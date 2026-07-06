Horizontal progress bar for multi-step flows. States: done (green underline), active (yellow fill + cyan underline), pending (muted).

```jsx
const [step, setStep] = React.useState(1);

<WizardSteps
  steps={['Listone', 'Mapping', 'Buste', 'Giornate']}
  current={step}
  onNavigate={(n) => n < step && setStep(n)}
/>

{step === 1 && <StepListone onNext={() => setStep(2)} />}
{step === 2 && <StepMapping onNext={() => setStep(3)} />}
```

Pass `onNavigate` to let the user click back to completed steps. The active step is never clickable. Restrict `onNavigate` to `n < step` to prevent skipping forward.
