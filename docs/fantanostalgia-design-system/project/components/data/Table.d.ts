/**
 * Data table with neon-yellow headers and row hover. Used for rankings, results, and player lists.
 * @startingPoint section="Data" subtitle="Leaderboard and stats tables" viewport="700x300"
 */
export interface TableColumn {
  /** Header label */
  label: string;
  /** Text alignment — defaults to left */
  align?: 'left' | 'center' | 'right';
  /** Render cells in pixel font (for rank numbers, role codes) */
  pixel?: boolean;
  /** Cell text color — CSS value or custom property */
  color?: string;
  /** Prevent cell content from wrapping */
  nowrap?: boolean;
}

export interface TableProps {
  /** Column definitions in display order */
  columns: TableColumn[];
  /**
   * Rows: each is either an array of ReactNode cells,
   * or an object { cells: ReactNode[] } for future row metadata.
   */
  rows: (React.ReactNode[] | { cells: React.ReactNode[] })[];
  /** Row click callback — receives (rowData, rowIndex) */
  onRowClick?: (row: any, index: number) => void;
}
