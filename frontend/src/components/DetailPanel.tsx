import { type ReactNode } from "react";

interface DetailPanelProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export function DetailPanel({ title, subtitle, children }: DetailPanelProps) {
  return (
    <aside className="detail-panel">
      <header className="detail-panel__header">
        <h3>{title}</h3>
        {subtitle ? <p>{subtitle}</p> : null}
      </header>
      <div className="detail-panel__content">{children}</div>
    </aside>
  );
}
