/**
 * Inline label for roles, statuses, and metadata. Always uppercase pixel font.
 * @startingPoint section="Core" subtitle="Status badges — admin, live, role tags" viewport="700x120"
 */
export interface BadgeProps {
  /** Color scheme */
  variant?: 'default' | 'accent' | 'cyan' | 'green' | 'red' | 'outline';
  /** Badge label */
  children: React.ReactNode;
}
