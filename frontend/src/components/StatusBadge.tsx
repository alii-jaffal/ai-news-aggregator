interface StatusBadgeProps {
  label: string;
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
}

const toneClassMap = {
  neutral: "badge badge-neutral",
  info: "badge badge-info",
  success: "badge badge-success",
  warning: "badge badge-warning",
  danger: "badge badge-danger",
} as const;

export function StatusBadge({ label, tone = "neutral" }: StatusBadgeProps) {
  return <span className={toneClassMap[tone]}>{label}</span>;
}
