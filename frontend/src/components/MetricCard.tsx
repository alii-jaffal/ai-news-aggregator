import { type ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  hint?: string;
  icon?: ReactNode;
}

export function MetricCard({ label, value, hint, icon }: MetricCardProps) {
  return (
    <section className="metric-card">
      <div className="metric-card__header">
        <span className="metric-card__label">{label}</span>
        {icon ? <span className="metric-card__icon">{icon}</span> : null}
      </div>
      <div className="metric-card__value">{value}</div>
      {hint ? <p className="metric-card__hint">{hint}</p> : null}
    </section>
  );
}
