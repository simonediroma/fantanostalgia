/**
 * Overlay dialog with dark backdrop for confirmations and detail views.
 * @startingPoint section="Overlay" subtitle="Confirmation and detail dialogs" viewport="700x350"
 */
export interface ModalProps {
  /** Controls visibility */
  open: boolean;
  /** Modal title — yellow pixel font */
  title?: string;
  /** Modal body content */
  children: React.ReactNode;
  /** Close handler — called on backdrop click */
  onClose?: () => void;
  /** Action buttons rendered in a flex row at the bottom */
  actions?: React.ReactNode;
}
