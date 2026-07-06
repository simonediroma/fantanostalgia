/**
 * Styled text input with label, focus ring, error and help-text states.
 */
export interface InputProps {
  /** Label above the input — pixel font, uppercase */
  label?: string;
  /** HTML id, links label to input */
  id?: string;
  /** Input type */
  type?: 'text' | 'number' | 'password' | 'email';
  placeholder?: string;
  value?: string | number;
  onChange?: React.ChangeEventHandler<HTMLInputElement>;
  disabled?: boolean;
  /** Error message — shown in red pixel font below the input */
  error?: string;
  /** Hint text — shown in muted data font below when no error */
  helpText?: string;
  required?: boolean;
}
