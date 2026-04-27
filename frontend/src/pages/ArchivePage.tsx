import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api";
import { DataTable } from "../components/DataTable";
import { DetailPanel } from "../components/DetailPanel";
import { StatusBadge } from "../components/StatusBadge";
import type { NewsletterRun, SourceArchiveItem, StoryArchiveItem } from "../types";
import { formatDate, toneForStatus } from "../utils";

type ArchiveTab = "stories" | "sources" | "newsletters";

export function ArchivePage() {
  const [tab, setTab] = useState<ArchiveTab>("stories");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const storiesQuery = useQuery({
    queryKey: ["stories", query, status, sourceType],
    queryFn: () =>
      api.getStories({
        q: query || undefined,
        status: status || undefined,
        source_type: sourceType || undefined,
        limit: 50,
        offset: 0,
      }),
    enabled: tab === "stories",
  });

  const sourcesQuery = useQuery({
    queryKey: ["sources", query, status, sourceType],
    queryFn: () =>
      api.getSources({
        q: query || undefined,
        status: status || undefined,
        source_type: sourceType || undefined,
        limit: 50,
        offset: 0,
      }),
    enabled: tab === "sources",
  });

  const newslettersQuery = useQuery({
    queryKey: ["newsletter-runs"],
    queryFn: () => api.getNewsletterRuns(50, 0),
    enabled: tab === "newsletters",
  });

  const sourceDetailQuery = useQuery({
    queryKey: ["source-detail", selectedId],
    queryFn: async () => {
      const [selectedSourceType, selectedSourceId] = (selectedId ?? "").split(":");
      return api.getSource(selectedSourceType, selectedSourceId);
    },
    enabled: tab === "sources" && Boolean(selectedId),
  });

  const storyDetailQuery = useQuery({
    queryKey: ["story-detail", selectedId],
    queryFn: () => api.getStory(selectedId ?? ""),
    enabled: tab === "stories" && Boolean(selectedId),
  });

  const newsletterDetailQuery = useQuery({
    queryKey: ["newsletter-detail", selectedId],
    queryFn: () => api.getNewsletterRun(selectedId ?? ""),
    enabled: tab === "newsletters" && Boolean(selectedId),
  });

  const activeList =
    tab === "stories"
      ? storiesQuery.data?.items
      : tab === "sources"
        ? sourcesQuery.data?.items
        : newslettersQuery.data?.items;

  useEffect(() => {
    if (activeList?.length) {
      if (!selectedId) {
        if (tab === "stories") {
          setSelectedId((activeList[0] as StoryArchiveItem).story_id);
        } else if (tab === "sources") {
          const source = activeList[0] as SourceArchiveItem;
          setSelectedId(`${source.source_type}:${source.source_id}`);
        } else {
          setSelectedId((activeList[0] as NewsletterRun).id);
        }
      }
    } else {
      setSelectedId(null);
    }
  }, [activeList, selectedId, tab]);

  const listError =
    storiesQuery.error || sourcesQuery.error || newslettersQuery.error || undefined;

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="tab-row">
          {(["stories", "sources", "newsletters"] as ArchiveTab[]).map((item) => (
            <button
              key={item}
              className={tab === item ? "tab-button tab-button-active" : "tab-button"}
              type="button"
              onClick={() => {
                setTab(item);
                setSelectedId(null);
              }}
            >
              {item}
            </button>
          ))}
        </div>
        <div className="filter-bar">
          {tab !== "newsletters" ? (
            <>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search by title"
              />
              <select value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="">All statuses</option>
                <option value="completed">completed</option>
                <option value="pending">pending</option>
                <option value="failed">failed</option>
                <option value="unavailable">unavailable</option>
                <option value="not_applicable">not_applicable</option>
              </select>
              <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
                <option value="">All source types</option>
                <option value="youtube">youtube</option>
                <option value="openai">openai</option>
                <option value="anthropic">anthropic</option>
              </select>
            </>
          ) : (
            <p className="muted-copy">Stored ranked newsletters are listed newest first.</p>
          )}
        </div>
      </section>

      {listError ? (
        <div className="inline-alert inline-alert-danger">{(listError as Error).message}</div>
      ) : null}

      <section className="archive-layout">
        <div className="panel">
          {tab === "stories" ? (
            <DataTable
              rows={storiesQuery.data?.items ?? []}
              emptyMessage="No stories match the current filters."
              onRowClick={(row) => setSelectedId(row.story_id)}
              columns={[
                {
                  key: "title",
                  header: "Story",
                  render: (row) => (
                    <div>
                      <strong>{row.title}</strong>
                      <p>{row.source_types.join(", ")}</p>
                    </div>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  render: (row) => (
                    <StatusBadge
                      label={row.story_digest_status}
                      tone={toneForStatus(row.story_digest_status)}
                    />
                  ),
                },
                {
                  key: "count",
                  header: "Sources",
                  render: (row) => row.source_count,
                },
                {
                  key: "published",
                  header: "Published",
                  render: (row) => formatDate(row.representative_published_at),
                },
              ]}
            />
          ) : null}

          {tab === "sources" ? (
            <DataTable
              rows={sourcesQuery.data?.items ?? []}
              emptyMessage="No source items match the current filters."
              onRowClick={(row) => setSelectedId(`${row.source_type}:${row.source_id}`)}
              columns={[
                {
                  key: "title",
                  header: "Source item",
                  render: (row) => (
                    <div>
                      <strong>{row.title}</strong>
                      <p>
                        {row.source_type} · {row.content_richness}
                      </p>
                    </div>
                  ),
                },
                {
                  key: "stage",
                  header: "Stage",
                  render: (row) => row.enrichment_stage,
                },
                {
                  key: "status",
                  header: "Status",
                  render: (row) => (
                    <StatusBadge
                      label={row.enrichment_status}
                      tone={toneForStatus(row.enrichment_status)}
                    />
                  ),
                },
                {
                  key: "published",
                  header: "Published",
                  render: (row) => formatDate(row.published_at),
                },
              ]}
            />
          ) : null}

          {tab === "newsletters" ? (
            <DataTable
              rows={newslettersQuery.data?.items ?? []}
              emptyMessage="No newsletter snapshots are stored yet."
              onRowClick={(row) => setSelectedId(row.id)}
              columns={[
                {
                  key: "subject",
                  header: "Subject",
                  render: (row) => (
                    <div>
                      <strong>{row.subject}</strong>
                      <p>{row.profile_slug}</p>
                    </div>
                  ),
                },
                {
                  key: "sent",
                  header: "Delivery",
                  render: (row) => (
                    <StatusBadge label={row.sent ? "sent" : "stored"} tone={row.sent ? "success" : "info"} />
                  ),
                },
                {
                  key: "articles",
                  header: "Articles",
                  render: (row) => row.article_count,
                },
                {
                  key: "created",
                  header: "Created",
                  render: (row) => formatDate(row.created_at),
                },
              ]}
            />
          ) : null}
        </div>

        {tab === "stories" ? (
          <DetailPanel
            title={storyDetailQuery.data?.title ?? "Story detail"}
            subtitle={
              storyDetailQuery.data
                ? `${storyDetailQuery.data.source_count} sources · ${formatDate(
                    storyDetailQuery.data.representative_published_at
                  )}`
                : "Select a story from the archive."
            }
          >
            {storyDetailQuery.data ? (
              <div className="stack-list">
                <StatusBadge
                  label={storyDetailQuery.data.story_digest_status}
                  tone={toneForStatus(storyDetailQuery.data.story_digest_status)}
                />
                {storyDetailQuery.data.digest ? (
                  <>
                    <div>
                      <strong>{storyDetailQuery.data.digest.title}</strong>
                      <p>{storyDetailQuery.data.digest.summary}</p>
                    </div>
                    <div className="detail-block">
                      <h4>Why it matters</h4>
                      <p>{storyDetailQuery.data.digest.why_it_matters}</p>
                    </div>
                  </>
                ) : (
                  <div className="empty-state">No current digest stored for this story.</div>
                )}
                <div className="detail-block">
                  <h4>Supporting sources</h4>
                  {storyDetailQuery.data.sources.map((source) => (
                    <div className="list-row" key={`${source.source_type}-${source.source_id}`}>
                      <div>
                        <strong>{source.title}</strong>
                        <p>
                          {source.source_type} · {formatDate(source.published_at)}
                        </p>
                      </div>
                      {source.is_primary ? <StatusBadge label="primary" tone="info" /> : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty-state">Select a story from the archive.</div>
            )}
          </DetailPanel>
        ) : null}

        {tab === "sources" ? (
          <DetailPanel
            title={sourceDetailQuery.data?.title ?? "Source detail"}
            subtitle={
              sourceDetailQuery.data
                ? `${sourceDetailQuery.data.source_type} · ${formatDate(sourceDetailQuery.data.published_at)}`
                : "Select a source item from the archive."
            }
          >
            {sourceDetailQuery.data ? (
              <div className="stack-list">
                <StatusBadge
                  label={sourceDetailQuery.data.enrichment_status}
                  tone={toneForStatus(sourceDetailQuery.data.enrichment_status)}
                />
                {sourceDetailQuery.data.failure_reason ? (
                  <div className="inline-alert inline-alert-warning">
                    {sourceDetailQuery.data.failure_reason}
                  </div>
                ) : null}
                {sourceDetailQuery.data.description ? (
                  <div className="detail-block">
                    <h4>Description</h4>
                    <p>{sourceDetailQuery.data.description}</p>
                  </div>
                ) : null}
                {sourceDetailQuery.data.cleaned_content ? (
                  <div className="detail-block">
                    <h4>Cleaned content</h4>
                    <p>{sourceDetailQuery.data.cleaned_content}</p>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="empty-state">Select a source item from the archive.</div>
            )}
          </DetailPanel>
        ) : null}

        {tab === "newsletters" ? (
          <DetailPanel
            title={newsletterDetailQuery.data?.subject ?? "Newsletter detail"}
            subtitle={
              newsletterDetailQuery.data
                ? `${newsletterDetailQuery.data.profile_slug} · ${formatDate(
                    newsletterDetailQuery.data.created_at
                  )}`
                : "Select a stored newsletter snapshot."
            }
          >
            {newsletterDetailQuery.data ? (
              <div className="stack-list">
                <StatusBadge
                  label={newsletterDetailQuery.data.sent ? "sent" : "stored"}
                  tone={newsletterDetailQuery.data.sent ? "success" : "info"}
                />
                <div className="detail-block">
                  <h4>Greeting</h4>
                  <p>{newsletterDetailQuery.data.greeting}</p>
                </div>
                <div className="detail-block">
                  <h4>Introduction</h4>
                  <p>{newsletterDetailQuery.data.introduction}</p>
                </div>
                <div className="detail-block">
                  <h4>Ranked stories</h4>
                  {(newsletterDetailQuery.data.payload_json.articles ?? []).map((article) => (
                    <div className="list-row" key={article.digest_id}>
                      <div>
                        <strong>{article.title}</strong>
                        <p>{article.summary}</p>
                      </div>
                      <div className="list-row__meta">
                        <span>#{article.rank}</span>
                        {article.source_attribution_line ? (
                          <StatusBadge label={article.source_attribution_line} />
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty-state">Select a stored newsletter snapshot.</div>
            )}
          </DetailPanel>
        ) : null}
      </section>
    </div>
  );
}
