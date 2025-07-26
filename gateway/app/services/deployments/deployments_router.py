# gateway/app/services/deployments/router.py
"""
Deployments (GitHub) API Router
-------------------------------
RESPONSIBILITIES
* Routing / HTTP concerns ONLY (Single-responsibility).
* Delegates business logic to `GitHubRepoFacade` via dependency-injection.
* Converts domain exceptions → HTTP responses.
"""

from __future__ import annotations

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from gateway.core.logging import get_logger
from gateway.core.exceptions import AppException
from gateway.app.services.deployments.schemas import RepoRequest, RepoInfoResponse, ErrorResponse
from gateway.app.services.deployments.service_facade import GitHubRepoFacade    # thin orchestration layer

# -----------------------------------------------------------------------------
logger: logging.Logger = get_logger(__name__)
router = APIRouter(prefix="/deployments", tags=["deployments"])
# -----------------------------------------------------------------------------


# Dependency ------------------------------------------------------------------
def get_facade() -> GitHubRepoFacade:
    """
    Provide a fresh facade instance per-request.
    (Could be singleton if it kept no state.)
    """
    return GitHubRepoFacade()


# Routes ----------------------------------------------------------------------
@router.post(
    "/repo-info",
    response_model=RepoInfoResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
    summary="Get GitHub Repository Information",
)
async def get_repository_info(
    body: RepoRequest,
    facade: GitHubRepoFacade = Depends(get_facade),
) -> RepoInfoResponse:
    """
    Validate *body* then return enriched repository metadata.
    """
    logger.info("Repo-info request", repo=body.repo)

    try:
        data = facade.fetch_repo_metadata(body.repo, body.token)
        return RepoInfoResponse(**data)

    except AppException as exc:
        # Domain error – map to Problem-Details JSON
        logger.warning("Domain error", code=exc.problem.type, repo=body.repo)
        raise HTTPException(status_code=exc.problem.status, detail=exc.problem.dict())

    except Exception as exc:
        # Unexpected error – generic 500
        logger.exception("Unhandled repo-info error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "code": "unexpected_error",
                "message": "Unexpected error while processing request",
                "status_code": 500,
            },
        )


@router.get(
    "/repo-info/test",
    response_model=Dict[str, str],
    summary="Test GitHub API Connection (ping)",
)
async def test_github_connection() -> Dict[str, str]:
    """Lightweight ping endpoint (no GitHub call)."""
    return {
        "status": "healthy",
        "service": "github_service",
        "message": "Use POST /deployments/repo-info to query repositories.",
    }


@router.get(
    "/health",
    response_model=Dict[str, str],
    summary="Deployment Service Health Check",
)
async def deployment_health() -> Dict[str, str]:
    """Simple health check for k8s / load-balancer probes."""
    return {
        "status": "healthy",
        "service": "deployment_service",
        "endpoints": [
            "POST /deployments/repo-info",
            "GET  /deployments/repo-info/test",
        ],
    }
