from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import (
    authenticate_dashboard_admin,
    build_dashboard_session_payload,
    clear_dashboard_session,
    get_dashboard_allowed_origins,
    get_dashboard_allowed_origin_regex,
    get_dashboard_session,
    require_dashboard_admin,
    set_dashboard_session,
)
from app.api.dependencies import get_repository
from app.api.schemas import (
    DashboardLoginRequest,
    DashboardOverviewResponse,
    DashboardSessionResponse,
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
    WaitlistRegistrationRequest,
    WaitlistRegistrationResponse,
    WorkerStatusResponse,
)
from app.database.repository import Repository
from app.profiles.profile_store import get_runtime_user_profile


def create_app() -> FastAPI:
    app = FastAPI(title="AI News Aggregator API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_dashboard_allowed_origins(),
        allow_origin_regex=get_dashboard_allowed_origin_regex(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", status_code=204)
    def health() -> Response:
        return Response(status_code=204)

    @app.post("/api/waitlist", response_model=WaitlistRegistrationResponse)
    def join_waitlist(
        payload: WaitlistRegistrationRequest,
        repo: Repository = Depends(get_repository),
    ) -> WaitlistRegistrationResponse:
        registration, already_registered = repo.upsert_waitlist_registration(payload.email)
        return WaitlistRegistrationResponse(
            email=registration.email,
            created_at=registration.created_at,
            already_registered=already_registered,
        )

    @app.get("/api/session", response_model=DashboardSessionResponse)
    def session_status(request: Request) -> DashboardSessionResponse:
        session = get_dashboard_session(request)
        if session is None:
            return DashboardSessionResponse(authenticated=False, username=None)
        return DashboardSessionResponse(authenticated=True, username=session["username"])

    @app.post("/api/login", response_model=DashboardSessionResponse)
    def login(
        payload: DashboardLoginRequest,
        response: Response,
    ) -> DashboardSessionResponse:
        if not authenticate_dashboard_admin(payload.username, payload.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid dashboard credentials",
            )

        set_dashboard_session(response, build_dashboard_session_payload())
        return DashboardSessionResponse(
            authenticated=True,
            username=build_dashboard_session_payload()["username"],
        )

    @app.post("/api/logout", response_model=DashboardSessionResponse)
    def logout(response: Response) -> DashboardSessionResponse:
        clear_dashboard_session(response)
        return DashboardSessionResponse(authenticated=False, username=None)

    @app.get("/api/dashboard/overview", response_model=DashboardOverviewResponse)
    def dashboard_overview(
        hours: int = Query(default=24, ge=1, le=168),
        repo: Repository = Depends(get_repository),
        _admin: dict[str, str] = Depends(require_dashboard_admin),
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
        _admin: dict[str, str] = Depends(require_dashboard_admin),
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
        _admin: dict[str, str] = Depends(require_dashboard_admin),
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
        _admin: dict[str, str] = Depends(require_dashboard_admin),
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
        _admin: dict[str, str] = Depends(require_dashboard_admin),
    ) -> StoryArchiveDetailResponse:
        item = repo.get_story_archive_item(story_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Story not found")
        return StoryArchiveDetailResponse.model_validate(item)

    @app.get("/api/failures", response_model=FailureSummaryResponse)
    def list_failures(
        hours: int = Query(default=168, ge=1, le=24 * 30),
        repo: Repository = Depends(get_repository),
        _admin: dict[str, str] = Depends(require_dashboard_admin),
    ) -> FailureSummaryResponse:
        return FailureSummaryResponse.model_validate(repo.get_failure_summary(hours=hours))

    @app.get("/api/pipeline-runs", response_model=PipelineRunListResponse)
    def list_pipeline_runs(
        limit: int = Query(default=20, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        repo: Repository = Depends(get_repository),
        _admin: dict[str, str] = Depends(require_dashboard_admin),
    ) -> PipelineRunListResponse:
        return PipelineRunListResponse.model_validate(
            repo.list_pipeline_runs(limit=limit, offset=offset)
        )

    @app.get("/api/pipeline-runs/{run_id}", response_model=PipelineRunResponse)
    def get_pipeline_run(
        run_id: str,
        repo: Repository = Depends(get_repository),
        _admin: dict[str, str] = Depends(require_dashboard_admin),
    ) -> PipelineRunResponse:
        item = repo.get_pipeline_run_detail(run_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        return PipelineRunResponse.model_validate(item)

    @app.get("/api/worker-status", response_model=WorkerStatusResponse | None)
    def get_worker_status(
        repo: Repository = Depends(get_repository),
        _admin: dict[str, str] = Depends(require_dashboard_admin),
    ) -> WorkerStatusResponse | None:
        status = repo.get_worker_status()
        if status is None:
            return None
        return WorkerStatusResponse.model_validate(status)

    @app.post("/api/pipeline-runs", response_model=PipelineRunResponse, status_code=202)
    def create_pipeline_run(
        payload: PipelineRunCreateRequest,
        repo: Repository = Depends(get_repository),
        _admin: dict[str, str] = Depends(require_dashboard_admin),
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
        return PipelineRunResponse.model_validate(repo.get_pipeline_run_detail(pipeline_run.id))

    @app.post("/api/pipeline-runs/{run_id}/cancel", response_model=PipelineRunResponse)
    def cancel_pipeline_run(
        run_id: str,
        repo: Repository = Depends(get_repository),
        _admin: dict[str, str] = Depends(require_dashboard_admin),
    ) -> PipelineRunResponse:
        pipeline_run = repo.get_pipeline_run(run_id)
        if pipeline_run is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        if pipeline_run.status not in ("queued", "running"):
            raise HTTPException(status_code=409, detail="Pipeline run is not cancellable")

        repo.cancel_pipeline_run(run_id)
        item = repo.get_pipeline_run_detail(run_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        return PipelineRunResponse.model_validate(item)

    @app.post(
        "/api/pipeline-runs/{run_id}/stage-runs/{stage_run_id}/retry",
        response_model=PipelineRunResponse,
        status_code=202,
    )
    def retry_pipeline_stage_run(
        run_id: str,
        stage_run_id: str,
        repo: Repository = Depends(get_repository),
        _admin: dict[str, str] = Depends(require_dashboard_admin),
    ) -> PipelineRunResponse:
        pipeline_run = repo.get_pipeline_run(run_id)
        if pipeline_run is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")

        stage_run = repo.get_pipeline_stage_run(stage_run_id)
        if stage_run is None or stage_run.pipeline_run_id != run_id:
            raise HTTPException(status_code=404, detail="Pipeline stage run not found")

        if stage_run.status != "failed":
            raise HTTPException(status_code=409, detail="Only failed stages can be retried")

        if repo.has_active_pipeline_run():
            raise HTTPException(status_code=409, detail="A pipeline run is already active")

        retry_run = repo.create_pipeline_run(
            trigger_source="api",
            run_type="single_stage",
            requested_stage=stage_run.stage_name,
            retry_stage_run_id=stage_run.id,
            requested_hours=pipeline_run.requested_hours,
            requested_top_n=pipeline_run.requested_top_n,
            profile_slug=pipeline_run.profile_slug,
            send_email=False,
            status="queued",
        )
        item = repo.get_pipeline_run_detail(retry_run.id)
        if item is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        return PipelineRunResponse.model_validate(item)

    @app.get("/api/newsletter-runs", response_model=NewsletterRunListResponse)
    def list_newsletter_runs(
        limit: int = Query(default=20, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        repo: Repository = Depends(get_repository),
        _admin: dict[str, str] = Depends(require_dashboard_admin),
    ) -> NewsletterRunListResponse:
        return NewsletterRunListResponse.model_validate(
            repo.list_newsletter_runs(limit=limit, offset=offset)
        )

    @app.get("/api/newsletter-runs/{newsletter_run_id}", response_model=NewsletterRunResponse)
    def get_newsletter_run(
        newsletter_run_id: str,
        repo: Repository = Depends(get_repository),
        _admin: dict[str, str] = Depends(require_dashboard_admin),
    ) -> NewsletterRunResponse:
        item = repo.get_newsletter_run_detail(newsletter_run_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Newsletter run not found")
        return NewsletterRunResponse.model_validate(item)

    return app


app = create_app()
