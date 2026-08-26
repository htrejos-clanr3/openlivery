"""Meta Platform diagnostics via Developer Tools MCP (not on message path)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas_meta import (
    MetaDiagnosticsOut,
    MetaHealthOut,
    MetaMcpStatusOut,
    MetaWebhookInspectOut,
    MetaWebhookRepairIn,
    MetaWebhookRepairPreviewOut,
    MetaWebhookTestHistoryOut,
    MetaWebhookTestIn,
    MetaWebhookTestOut,
)
from ..services.meta_devtools_mcp import MetaDeveloperToolsProvider, MetaMcpError, MetaMcpUnavailable, mock_mode
from ..services.meta_platform_health import MetaPlatformHealthService, clear_meta_cache, list_recent_webhook_tests


router = APIRouter(prefix="/meta", tags=["Meta Platform"])


def _service(scenario: str | None = None) -> MetaPlatformHealthService:
    return MetaPlatformHealthService(MetaDeveloperToolsProvider(scenario=scenario))


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, MetaMcpUnavailable):
        return HTTPException(status_code=503, detail={"message": str(exc), "code": exc.code})
    if isinstance(exc, MetaMcpError):
        return HTTPException(status_code=400, detail={"message": str(exc), "code": exc.code})
    return HTTPException(status_code=500, detail={"message": "Unexpected Meta diagnostics error"})


@router.get("/status", response_model=MetaMcpStatusOut)
def meta_status(user: User = Depends(get_current_user)):
    return MetaMcpStatusOut(**_service().status_payload())


@router.get("/health", response_model=MetaHealthOut)
async def meta_health(
    time_range: str = Query("24h", pattern="^(1h|24h|7d|30d)$"),
    force: bool = False,
    scenario: str | None = None,
    user: User = Depends(get_current_user),
):
    # scenario only honored in mock mode (UI/dev).
    svc = _service(scenario if mock_mode() else None)
    data = await svc.get_health(time_range=time_range, force=force)
    return MetaHealthOut(**data)


@router.post("/health/refresh", response_model=MetaHealthOut)
async def meta_health_refresh(
    time_range: str = Query("24h", pattern="^(1h|24h|7d|30d)$"),
    user: User = Depends(get_current_user),
):
    clear_meta_cache()
    data = await _service().get_health(time_range=time_range, force=True)
    return MetaHealthOut(**data)


@router.post("/diagnostics", response_model=MetaDiagnosticsOut)
async def meta_diagnostics(user: User = Depends(get_current_user)):
    clear_meta_cache()
    data = await _service().run_diagnostics()
    return MetaDiagnosticsOut(**data)


@router.get("/api-usage")
async def meta_api_usage(
    time_range: str = Query("24h", pattern="^(1h|24h|7d|30d)$"),
    user: User = Depends(get_current_user),
):
    health = await _service().get_health(time_range=time_range)
    return {"api_usage": health.get("api_usage"), "rate_limits": health.get("rate_limits"), "fetched_at": health.get("fetched_at")}


@router.get("/app-review")
async def meta_app_review(user: User = Depends(get_current_user)):
    health = await _service().get_health()
    return health.get("app_review")


@router.get("/compliance")
async def meta_compliance(user: User = Depends(get_current_user)):
    health = await _service().get_health()
    return health.get("compliance")


@router.get("/deprecations")
async def meta_deprecations(user: User = Depends(get_current_user)):
    health = await _service().get_health()
    return health.get("deprecations")


@router.get("/webhooks", response_model=MetaWebhookInspectOut)
async def meta_webhooks(force: bool = False, user: User = Depends(get_current_user)):
    try:
        data = await _service().inspect_webhooks(force=force)
        return MetaWebhookInspectOut(**data)
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.get("/webhooks/diff", response_model=MetaWebhookInspectOut)
async def meta_webhooks_diff(user: User = Depends(get_current_user)):
    try:
        data = await _service().inspect_webhooks(force=True)
        return MetaWebhookInspectOut(**data)
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.post("/webhooks/test", response_model=MetaWebhookTestOut)
async def meta_webhooks_test(
    payload: MetaWebhookTestIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = await _service().start_webhook_test(db, user, field=payload.field)
        return MetaWebhookTestOut(**data)
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.get("/webhooks/tests", response_model=list[MetaWebhookTestHistoryOut])
def meta_webhook_test_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list_recent_webhook_tests(db, user.agency_id, limit=10)
    return [MetaWebhookTestHistoryOut.model_validate(r) for r in rows]


@router.get("/webhooks/repair/preview", response_model=MetaWebhookRepairPreviewOut)
async def meta_webhook_repair_preview(user: User = Depends(get_current_user)):
    try:
        data = await _service().preview_webhook_repair()
        return MetaWebhookRepairPreviewOut(**data)
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc


@router.post("/webhooks/repair")
async def meta_webhook_repair(
    payload: MetaWebhookRepairIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return await _service().apply_webhook_repair(confirm=payload.confirm, db=db, user=user)
    except Exception as exc:  # noqa: BLE001
        raise _http_error(exc) from exc
