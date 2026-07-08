/**
 * Container card for grouping related content. Dark surface fill, pixel shadow, sharp corners.
 */
export interface PanelProps {
  /** Optional title — renders in yellow pixel font at the top */
  title?: string;
  /** Border and shadow variant */
  variant?: 'default' | 'accent' | 'danger' | 'plain';
  /** Panel body content */
  children: React.ReactNode;
}
