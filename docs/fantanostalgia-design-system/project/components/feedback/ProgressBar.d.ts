/**
 * Neon-green fill progress bar for bounded completion states.
 */
export interface ProgressBarProps {
  /** Current value */
  value: number;
  /** Maximum value — defaults to 100 */
  max?: number;
  /** Optional label shown above the bar on the left */
  label?: string;
  /** Show percentage on the right — defaults to false */
  showPercent?: boolean;
}
