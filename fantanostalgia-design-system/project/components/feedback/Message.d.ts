/**
 * Inline feedback message for operation outcomes. Four semantic variants.
 * @startingPoint section="Feedback" subtitle="ok / err / warn / info inline messages" viewport="700x220"
 */
export interface MessageProps {
  /** Semantic variant */
  variant?: 'ok' | 'err' | 'info' | 'warn';
  /** Dismiss callback — renders × button when provided */
  onDismiss?: () => void;
  /** Message text or content */
  children: React.ReactNode;
}
