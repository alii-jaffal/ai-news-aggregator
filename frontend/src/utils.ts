export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "N/A";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatDuration(seconds: number | null | undefined) {
  if (seconds === null || seconds === undefined) {
    return "N/A";
  }
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  return `${(seconds / 60).toFixed(1)}m`;
}

export function toneForStatus(
  status: string
): "neutral" | "info" | "success" | "warning" | "danger" {
  if (["completed", "sent"].includes(status)) {
    return "success";
  }
  if (["running", "pending", "queued"].includes(status)) {
    return "info";
  }
  if (["unavailable", "skipped"].includes(status)) {
    return "warning";
  }
  if (["failed", "error"].includes(status)) {
    return "danger";
  }
  return "neutral";
}
