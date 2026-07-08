/**
 * Drag-and-drop file upload zone. Click to open file picker, drag to upload.
 * @startingPoint section="Forms" subtitle="Excel / CSV file upload drop zone" viewport="700x200"
 */
export interface DropZoneProps {
  /** Called with the selected File when a file is dropped or chosen */
  onFile: (file: File) => void;
  /** Accepted MIME types or extensions (e.g. ".xlsx,.xls") */
  accept?: string;
  /** Primary label inside the zone — defaults to "Trascina il file qui" */
  label?: string;
  /** Secondary help text below the label (format description) */
  sublabel?: string;
  /** File name after selection — replaces label and turns accent yellow */
  fileName?: string;
}
