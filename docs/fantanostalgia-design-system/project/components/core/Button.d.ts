/**
 * Pixel-art button with four variants for CTAs, secondary actions, danger ops, and ghost.
 * @startingPoint section="Core" subtitle="All button variants — CTA, secondary, danger, ghost" viewport="700x200"
 */
export interface ButtonProps {
  /** Visual and semantic variant */
  variant?: 'default' | 'secondary' | 'danger' | 'ghost';
  /** Disabled state — reduces opacity to 0.45, blocks interaction */
  disabled?: boolean;
  /** Stretch to full container width */
  fullWidth?: boolean;
  /** HTML button type */
  type?: 'button' | 'submit' | 'reset';
  /** Click handler */
  onClick?: () => void;
  /** Button label or content */
  children: React.ReactNode;
}
