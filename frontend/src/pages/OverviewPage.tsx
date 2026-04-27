import { AlertTriangle, Mail, Newspaper, Play, RefreshCw, Sparkles } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import { MetricCard } from "../components/MetricCard";
import { StatusBadge } from "../components/StatusBadge";
import { formatDate, formatDuration, toneForStatus } from "../utils";

export function OverviewPage() {
  const queryClient = useQueryClient();
  const [hours, setHours] = useState("24");
  const [topN, setTopN] = useState("");

  const overviewQuery = useQuery({
    queryKey: ["overview", 24],
    queryFn: () => api.getOverview(24),
    refetchInterval: (query) => {
      const status = query.state.data?.latest_pipeline_run?.status;
      return status === "queued" || status === "running" ? 3000 : false;
    },
  });

  const createRunMutation = useMutation({
    mutationFn: () =>
      api.createPipelineRun({
        hours: Number(hours),
        top_n: topN ? Number(topN) : null,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["overview"] }),
        queryClient.invalidateQueries({ queryKey: ["pipeline-runs"] }),
      ]);
    },
  });

  if (overviewQuery.isLoading) {
    return <div className="empty-state">Loading dashboard overview...</div>;
  }

  if (overviewQuery.error || !overviewQuery.data) {
    return (
      <div className="inline-alert inline-alert-danger">
        {(overviewQuery.error as Error | undefined)?.message ?? "Failed to load dashboard overview."}
      </div>
    );
  }

  const { source_counts, story_counts, digest_counts, latest_pipeline_run, latest_newsletter_run } =
    overviewQuery.data;

  return (
    <div className="page-stack">
      <section className="toolbar-card">
        <div className="toolbar-card__content">
          <div>
            <h2>Trigger a dashboard rerun</h2>
            <p>
              This reruns the pipeline for a recent window and stores the results in the dashboard.
              Email delivery stays disabled here.
            </p>
          </div>
          <form
            className="toolbar-form"
            onSubmit={(event) => {
              event.preventDefault();
              void createRunMutation.mutateAsync();
            }}
          >
            <label>
              <span>Hours</span>
              <input value={hours} onChange={(event) => setHours(event.target.value)} />
            </label>
            <label>
              <span>Top N override</span>
              <input
                value={topN}
                onChange={(event) => setTopN(event.target.value)}
                placeholder="Profile default"
              />
            </label>
            <button className="primary-button" type="submit" disabled={createRunMutation.isPending}>
              <Play size={15} />
              <span>{createRunMutation.isPending ? "Queued..." : "Run pipeline"}</span>
            </button>
          </form>
        </div>
        {createRunMutation.error ? (
          <div className="inline-alert inline-alert-danger">
            {(createRunMutation.error as Error).message}
          </div>
        ) : null}
      </section>

      <section className="metric-grid">
        <MetricCard
          label="YouTube items"
          value={source_counts.youtube}
          icon={<Newspaper size={16} />}
          hint="Recent source items in the selected overview window."
        />
        <MetricCard label="OpenAI items" value={source_counts.openai} icon={<Sparkles size={16} />} />
        <MetricCard label="Anthropic items" value={source_counts.anthropic} icon={<Sparkles size={16} />} />
        <MetricCard
          label="Stories"
          value={story_counts.total}
          hint={`${story_counts.multi_source} multi-source / ${story_counts.singleton} singleton`}
        />
        <MetricCard
          label="Digests completed"
          value={digest_counts.completed}
          hint={`${digest_counts.pending} pending / ${digest_counts.failed} failed`}
        />
        <MetricCard
          label="Pipeline failures"
          value={overviewQuery.data.failure_summary.summary.pipeline_failed}
          icon={<AlertTriangle size={16} />}
        />
      </section>

      <section className="two-column-grid">
        <article className="panel">
          <div className="panel__header">
            <div>
              <p className="panel__eyebrow">Latest run</p>
              <h2>Pipeline activity</h2>
            </div>
            {latest_pipeline_run ? (
              <StatusBadge
                label={latest_pipeline_run.status}
                tone={toneForStatus(latest_pipeline_run.status)}
              />
            ) : null}
          </div>

          {latest_pipeline_run ? (
            <div className="stack-list">
              <div className="key-value">
                <span>Started</span>
                <strong>{formatDate(latest_pipeline_run.started_at)}</strong>
              </div>
              <div className="key-value">
                <span>Duration</span>
                <strong>{formatDuration(latest_pipeline_run.duration_seconds)}</strong>
              </div>
              <div className="key-value">
                <span>Window</span>
                <strong>{latest_pipeline_run.requested_hours}h</strong>
              </div>
              <div className="key-value">
                <span>Email</span>
                <strong>{latest_pipeline_run.send_email ? "Enabled" : "Disabled"}</strong>
              </div>
              {latest_pipeline_run.error_message ? (
                <div className="inline-alert inline-alert-danger">
                  {latest_pipeline_run.error_message}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="empty-state">No pipeline history yet.</div>
          )}
        </article>

        <article className="panel">
          <div className="panel__header">
            <div>
              <p className="panel__eyebrow">Latest newsletter</p>
              <h2>Stored ranked output</h2>
            </div>
            <Mail size={16} />
          </div>

          {latest_newsletter_run ? (
            <div className="stack-list">
              <div className="key-value">
                <span>Subject</span>
                <strong>{latest_newsletter_run.subject}</strong>
              </div>
              <div className="key-value">
                <span>Created</span>
                <strong>{formatDate(latest_newsletter_run.created_at)}</strong>
              </div>
              <div className="key-value">
                <span>Articles</span>
                <strong>{latest_newsletter_run.article_count}</strong>
              </div>
              <p className="muted-copy">{latest_newsletter_run.introduction}</p>
              <StatusBadge
                label={latest_newsletter_run.sent ? "sent" : "stored"}
                tone={latest_newsletter_run.sent ? "success" : "info"}
              />
            </div>
          ) : (
            <div className="empty-state">No newsletter snapshots stored yet.</div>
          )}
        </article>
      </section>

      <section className="panel">
        <div className="panel__header">
          <div>
            <p className="panel__eyebrow">Recent issues</p>
            <h2>Failure summary</h2>
          </div>
          <button
            className="secondary-button"
            type="button"
            onClick={() => void overviewQuery.refetch()}
          >
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>
        </div>

        <div className="failure-chip-row">
          <StatusBadge
            label={`YouTube failed: ${overviewQuery.data.failure_summary.summary.youtube_failed}`}
            tone="danger"
          />
          <StatusBadge
            label={`YouTube unavailable: ${overviewQuery.data.failure_summary.summary.youtube_unavailable}`}
            tone="warning"
          />
          <StatusBadge
            label={`Anthropic failed: ${overviewQuery.data.failure_summary.summary.anthropic_failed}`}
            tone="danger"
          />
          <StatusBadge
            label={`Story digests failed: ${overviewQuery.data.failure_summary.summary.story_digest_failed}`}
            tone="danger"
          />
        </div>

        {overviewQuery.data.failure_summary.items.length ? (
          <div className="stack-list">
            {overviewQuery.data.failure_summary.items.map((item) => (
              <div key={`${item.category}-${item.reference_id}`} className="list-row">
                <div>
                  <strong>{item.title}</strong>
                  <p>
                    {item.category} · {formatDate(item.occurred_at)}
                  </p>
                </div>
                <div className="list-row__meta">
                  <StatusBadge label={item.status} tone={toneForStatus(item.status)} />
                  {item.failure_reason ? <span>{item.failure_reason}</span> : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">No recent failures in the tracked window.</div>
        )}
      </section>
    </div>
  );
}
