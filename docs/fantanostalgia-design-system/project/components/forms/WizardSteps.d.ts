/**
 * Horizontal multi-step wizard progress indicator.
 * @startingPoint section="Forms" subtitle="Admin wizard: Listone → Mapping → Buste → Giornate" viewport="700x100"
 */
export interface WizardStepsProps {
  /** Step labels in order (displayed as "N — Label") */
  steps: string[];
  /** Currently active step number (1-indexed) */
  current: number;
  /** Navigate to step — enables pointer cursor on past/future steps */
  onNavigate?: (step: number) => void;
}
