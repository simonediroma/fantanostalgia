/**
 * Tab navigation bar with pixel-font labels and an active-state yellow fill.
 * @startingPoint section="Navigation" subtitle="Tab bar for multi-section views" viewport="700x300"
 */
export interface TabItem {
  /** Unique identifier */
  id: string;
  /** Display label */
  label: string;
}

export interface TabsProps {
  /** Tab definitions in display order */
  tabs: TabItem[];
  /** Initially active tab id — defaults to the first tab */
  defaultTab?: string;
  /**
   * Render function or static children.
   * Render function `(activeId: string) => ReactNode` is preferred for
   * conditional rendering of heavy tab panels (avoids mounting all panels).
   */
  children: React.ReactNode | ((activeId: string) => React.ReactNode);
}
