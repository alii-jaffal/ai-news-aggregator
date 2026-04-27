import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api";
import { DataTable } from "../components/DataTable";
import { DetailPanel } from "../components/DetailPanel";
import { StatusBadge } from "../components/StatusBadge";
import { formatDate, formatDuration, toneForStatus } from "../utils";

export function RunsPage() {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const runsQuery = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: () => api.getPipelineRuns(50, 0),
    refetchInterval: (query) => {
      const hasActiveRun = (query.state.data?.items ?? []).some((item) =>
        ["queued", "running"].includes(item.status)
      );
      return hasActiveRun ? 3000 : false;
    },
  });

  const runDetailQuery = useQuery({
    queryKey: ["pipeline-run-detail", selectedRunId],
    queryFn: () => api.getPipelineRun(selectedRunId ?? ""),
    enabled: Boolean(selectedRunId),
  });

  useEffect(() => {
    if (!selectedRunId && runsQuery.data?.items.length) {
      setSelectedRunId(runsQuery.data.items[0].id);
    }
  }, [runsQuery.data?.items, selectedRunId]);

  if (runsQuery.isLoading) {
    return <div className="empty-state">Loading pipeline runs...</div>;
  }

  if (runsQuery.error || !runsQuery.data) {
    return (
      <div className="inline-alert inline-alert-danger">
        {(runsQuery.error as Error | undefined)?.message ?? "Failed to load pipeline runs."}
      </div>
    );
  }

  return (
    <div className="archive-layout">
      <section className="panel">
        <DataTable
          rows={runsQuery.data.items}
          emptyMessage="No pipeline history has been recorded yet."
          onRowClick={(row) => setSelectedRunId(row.id)}
          columns={[
            {
              key: "run",
              header: "Run",
              render: (row) => (
                <div>
                  <strong>{row.trigger_source}</strong>
                  <p>{row.id}</p>
                </div>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (row) => (
                <StatusBadge label={row.status} tone={toneForStatus(row.status)} />
              ),
            },
            {
              key: "window",
              header: "Window",
              render: (row) => `${row.requested_hours}h`,
            },
            {
              key: "started",
              header: "Started",
              render: (row) => formatDate(row.started_at),
            },
            {
              key: "duration",
              header: "Duration",
              render: (row) => formatDuration(row.duration_seconds),
            },
          ]}
        />
      </section>

      <DetailPanel
        title={runDetailQuery.data?.id ?? "Run detail"}
        subtitle={
          runDetailQuery.data
            ? `${runDetailQuery.data.trigger_source} · ${formatDate(runDetailQuery.data.started_at)}`
            : "Select a pipeline run from the list."
        }
      >
        {runDetailQuery.data ? (
          <div className="stack-list">
            <StatusBadge label={runDetailQuery.data.status} tone={toneForStatus(runDetailQuery.data.status)} />
            <div className="key-value">
              <span>Profile</span>
              <strong>{runDetailQuery.data.profile_slug}</strong>
            </div>
            <div className="key-value">
              <span>Email delivery</span>
              <strong>{runDetailQuery.data.send_email ? "Enabled" : "Disabled"}</strong>
            </div>
            <div className="key-value">
              <span>Top N override</span>
              <strong>{runDetailQuery.data.requested_top_n ?? "Profile default"}</strong>
            </div>
            {runDetailQuery.data.error_message ? (
              <div className="inline-alert inline-alert-danger">
                {runDetailQuery.data.error_message}
              </div>
            ) : null}
            <div className="detail-block">
              <h4>Scraping summary</h4>
              <pre>{JSON.stringify(runDetailQuery.data.scraping_summary, null, 2)}</pre>
            </div>
            <div className="detail-block">
              <h4>Processing summary</h4>
              <pre>{JSON.stringify(runDetailQuery.data.processing_summary, null, 2)}</pre>
            </div>
            <div className="detail-block">
              <h4>Digest summary</h4>
              <pre>{JSON.stringify(runDetailQuery.data.digest_summary, null, 2)}</pre>
            </div>
            <div className="detail-block">
              <h4>Email summary</h4>
              <pre>{JSON.stringify(runDetailQuery.data.email_summary, null, 2)}</pre>
            </div>
          </div>
        ) : (
          <div className="empty-state">Select a pipeline run from the list.</div>
        )}
      </DetailPanel>
    </div>
  );
}
