from datetime import datetime

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import get_repository
from app.api.schemas import (
    DashboardOverviewResponse,
    FailureSummaryResponse,
    NewsletterRunListResponse,
    NewsletterRunResponse,
    PipelineRunCreateRequest,
    PipelineRunListResponse,
    PipelineRunResponse,
    SourceArchiveItemResponse,
    SourceArchiveListResponse,
    StoryArchiveDetailResponse,
    StoryArchiveListResponse,
)
from app.daily_runner import run_daily_pipeline
from app.database.repository import Repository
from app.profiles.profile_store import get_runtime_user_profile


def execute_pipeline_run(run_id: str, hours: int, top_n: int | None) -> None:
    run_daily_pipeline(
        hours=hours,
        top_n=top_n,
        send_email=False,
        trigger_source="api",
        pipeline_run_id=run_id,
    )


def create_app() -> FastAPI:
    app = FastAPI(title="AI News Aggregator API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", status_code=204)
    def health() -> Response:
        return Response(status_code=204)

    @app.get("/api/dashboard/overview", response_model=DashboardOverviewResponse)
    def dashboard_overview(
        hours: int = Query(default=24, ge=1, le=168),
        repo: Repository = Depends(get_repository),
    ) -> DashboardOverviewResponse:
        return DashboardOverviewResponse.model_validate(repo.get_dashboard_overview(hours=hours))

    @app.get("/api/sources", response_model=SourceArchiveListResponse)
    def list_sources(
        source_type: str | None = None,
        status: str | None = None,
        q: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        repo: Repository = Depends(get_repository),
    ) -> SourceArchiveListResponse:
        data = repo.list_source_archive(
            source_type=source_type,
            status=status,
            q=q,
            start_at=start_at,
            end_at=end_at,
            limit=limit,
            offset=offset,
        )
        return SourceArchiveListResponse.model_validate(data)

    @app.get("/api/sources/{source_type}/{source_id}", response_model=SourceArchiveItemResponse)
    def get_source(
        source_type: str,
        source_id: str,
        repo: Repository = Depends(get_repository),
    ) -> SourceArchiveItemResponse:
        item = repo.get_source_archive_item(source_type, source_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Source item not found")
        return SourceArchiveItemResponse.model_validate(item)

    @app.get("/api/stories", response_model=StoryArchiveListResponse)
    def list_stories(
        status: str | None = None,
        source_type: str | None = None,
        q: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        repo: Repository = Depends(get_repository),
    ) -> StoryArchiveListResponse:
        data = repo.list_story_archive(
            status=status,
            source_type=source_type,
            q=q,
            start_at=start_at,
            end_at=end_at,
            limit=limit,
            offset=offset,
        )
        return StoryArchiveListResponse.model_validate(data)

    @app.get("/api/stories/{story_id}", response_model=StoryArchiveDetailResponse)
    def get_story(
        story_id: str,
        repo: Repository = Depends(get_repository),
    ) -> StoryArchiveDetailResponse:
        item = repo.get_story_archive_item(story_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Story not found")
        return StoryArchiveDetailResponse.model_validate(item)

    @app.get("/api/failures", response_model=FailureSummaryResponse)
    def list_failures(
        hours: int = Query(default=168, ge=1, le=24 * 30),
        repo: Repository = Depends(get_repository),
    ) -> FailureSummaryResponse:
        return FailureSummaryResponse.model_validate(repo.get_failure_summary(hours=hours))

    @app.get("/api/pipeline-runs", response_model=PipelineRunListResponse)
    def list_pipeline_runs(
        limit: int = Query(default=20, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        repo: Repository = Depends(get_repository),
    ) -> PipelineRunListResponse:
        return PipelineRunListResponse.model_validate(
            repo.list_pipeline_runs(limit=limit, offset=offset)
        )

    @app.get("/api/pipeline-runs/{run_id}", response_model=PipelineRunResponse)
    def get_pipeline_run(
        run_id: str,
        repo: Repository = Depends(get_repository),
    ) -> PipelineRunResponse:
        item = repo.get_pipeline_run_detail(run_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        return PipelineRunResponse.model_validate(item)

    @app.post("/api/pipeline-runs", response_model=PipelineRunResponse, status_code=202)
    def create_pipeline_run(
        payload: PipelineRunCreateRequest,
        background_tasks: BackgroundTasks,
        repo: Repository = Depends(get_repository),
    ) -> PipelineRunResponse:
        if repo.has_active_pipeline_run():
            raise HTTPException(status_code=409, detail="A pipeline run is already active")

        user_profile = get_runtime_user_profile(repo=repo)
        pipeline_run = repo.create_pipeline_run(
            trigger_source="api",
            requested_hours=payload.hours,
            requested_top_n=payload.top_n,
            profile_slug=user_profile["slug"],
            send_email=False,
            status="queued",
        )
        background_tasks.add_task(execute_pipeline_run, pipeline_run.id, payload.hours, payload.top_n)
        return PipelineRunResponse.model_validate(repo.get_pipeline_run_detail(pipeline_run.id))

    @app.get("/api/newsletter-runs", response_model=NewsletterRunListResponse)
    def list_newsletter_runs(
        limit: int = Query(default=20, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        repo: Repository = Depends(get_repository),
    ) -> NewsletterRunListResponse:
        return NewsletterRunListResponse.model_validate(
            repo.list_newsletter_runs(limit=limit, offset=offset)
        )

    @app.get("/api/newsletter-runs/{newsletter_run_id}", response_model=NewsletterRunResponse)
    def get_newsletter_run(
        newsletter_run_id: str,
        repo: Repository = Depends(get_repository),
    ) -> NewsletterRunResponse:
        item = repo.get_newsletter_run_detail(newsletter_run_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Newsletter run not found")
        return NewsletterRunResponse.model_validate(item)

    return app


app = create_app()
