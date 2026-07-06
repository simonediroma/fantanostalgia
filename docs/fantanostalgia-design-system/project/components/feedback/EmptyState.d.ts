/**
 * Placeholder shown when a list or data area has no content yet.
 */
export interface EmptyStateProps {
  /** Message describing what's absent */
  message: string;
  /** Optional CTA label — renders as ghost button when provided */
  action?: string;
  /** CTA click handler */
  onAction?: () => void;
}
