/**
 * Informational box that explains a feature before its controls are shown.
 * @startingPoint section="Feedback" subtitle="Help box — explain before the UI, info/warn/danger" viewport="700x180"
 */
export interface HelpBoxProps {
  /** Title in small pixel font above the body text */
  title?: string;
  /** Explanatory body text in data font */
  children: React.ReactNode;
  /** Optional "learn more" URL */
  link?: string;
  /** Link label — defaults to "Dettagli →" */
  linkText?: string;
  /** Semantic variant */
  variant?: 'info' | 'warn' | 'danger';
}
