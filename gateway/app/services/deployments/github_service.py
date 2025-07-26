"""
github_service.py
=================

Task 1 – Check that a GitHub repository exists and return metadata.

Design Highlights
-----------------
* **Single-responsibility:** `GitHubRepoService` only handles GitHub I/O.
* **SOLID:** Constructor receives an *abstraction* (`IGitHubGateway`) so behaviour
  can be mocked in tests; default implementation is `PyGithubGateway`.
* **Error reporting:** Domain errors bubble up as `AppException`
  (converted by your global handlers to RFC 7807 JSON).
* **Observability:** Uses existing `gateway.core.logging.get_logger`.
* **Data structures:** Returns a plain `dict` (JSON-serialisable) defined by
  `RepoInfo` model in `schemas.py` for strong typing.
* **Version compatibility:** Works with both PyGithub v1.x and v2.x+
* **Resource management:** Proper context manager support and cleanup
* **Enhanced validation:** Better URL parsing and error handling

No algorithmic complexity – just validation, parsing and API calls – but the
code emphasises clean flow, small functions, and explicit types for learning.
"""

from __future__ import annotations
import re
from contextlib import contextmanager
from typing import Dict, Any, Optional, Union
from urllib.parse import urlparse

try:
    # PyGithub v2.0+ (preferred)
    from github import Auth, Github
    PYGITHUB_V2 = True
except ImportError:
    # PyGithub v1.x (fallback)
    from github import Github
    PYGITHUB_V2 = False

from github.GithubException import (
    BadCredentialsException, 
    UnknownObjectException,
    RateLimitExceededException,
    GithubException
)

from gateway.core.logging import get_logger
from gateway.core.exceptions import AppException
from gateway.app.services.deployments.schemas import RepoInfo

logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# Interfaces – allow mocking / swapping implementations
# ──────────────────────────────────────────────────────────────────────────

class IGitHubGateway:
    """Port interface for GitHub operations (hexagonal / clean-arch style)."""
    
    def get_repo(self, full_name: str):
        """Retrieve repository information by full name (owner/repo)."""
        raise NotImplementedError
    
    def close(self) -> None:
        """Clean up resources."""
        pass
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class PyGithubGateway(IGitHubGateway):
    """Concrete adapter over PyGithub with version compatibility."""
    
    def __init__(self, token: str, timeout: int = 30):
        """
        Initialize GitHub client with proper authentication.
        
        Args:
            token: GitHub personal access token
            timeout: Request timeout in seconds
        """
        if not token or not isinstance(token, str):
            raise ValueError("GitHub token must be a non-empty string")
            
        self._token = token
        self._timeout = timeout
        self._client = self._create_client()
    
    def _create_client(self) -> Github:
        """Create GitHub client with version-appropriate authentication."""
        try:
            if PYGITHUB_V2:
                # PyGithub v2.0+ with Auth class
                auth = Auth.Token(self._token)
                return Github(auth=auth, timeout=self._timeout)
            else:
                # PyGithub v1.x with direct token
                return Github(self._token, timeout=self._timeout)
        except Exception as exc:
            logger.error("Failed to create GitHub client", error=str(exc))
            raise AppException(
                code="github/client-initialization-failed",
                message="Failed to initialize GitHub client",
                status_code=500,
            ) from exc
    
    def get_repo(self, full_name: str):
        """Get repository by full name with enhanced error handling."""
        if not self._client:
            raise AppException(
                code="github/client-not-initialized",
                message="GitHub client not properly initialized",
                status_code=500,
            )
        
        try:
            return self._client.get_repo(full_name)
        except Exception as exc:
            logger.debug("GitHub API call failed", repo=full_name, error=str(exc))
            raise  # Re-raise for service layer to handle
    
    def close(self) -> None:
        """Clean up GitHub client resources."""
        if hasattr(self._client, 'close'):
            try:
                self._client.close()
            except Exception as exc:
                logger.warning("Error closing GitHub client", error=str(exc))
        self._client = None


# ──────────────────────────────────────────────────────────────────────────
# Service
# ──────────────────────────────────────────────────────────────────────────

class GitHubRepoService:
    """Application service for repository validation and metadata retrieval."""
    
    # Enhanced regex to handle more GitHub repository name variations
    _RE_OWNER_REPO = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-_]*[a-zA-Z0-9])?/[a-zA-Z0-9]([a-zA-Z0-9\-_\.]*[a-zA-Z0-9])?$")
    
    def __init__(self, gateway: IGitHubGateway):
        """Initialize service with GitHub gateway dependency."""
        if not isinstance(gateway, IGitHubGateway):
            raise TypeError("Gateway must implement IGitHubGateway interface")
        self._gw = gateway
    
    # ── Public API ──────────────────────────────────────────────────
    
    def validate_and_fetch(self, identifier: str) -> RepoInfo:
        """
        Parse identifier (URL or 'owner/repo'), verify repo exists,
        and return structured metadata. Raises AppException on failure.
        
        Args:
            identifier: Repository identifier (URL, SSH, or owner/repo format)
            
        Returns:
            RepoInfo: Structured repository metadata
            
        Raises:
            AppException: On validation or API errors
        """
        if not identifier or not isinstance(identifier, str):
            raise AppException(
                code="github/invalid-identifier",
                message="Repository identifier must be a non-empty string",
                status_code=400,
            )
        
        owner_repo = self._normalize(identifier)
        logger.info("Checking GitHub repository", repo=owner_repo)
        
        try:
            repo = self._gw.get_repo(owner_repo)
            
            # Validate that we got a proper repository object
            if not hasattr(repo, 'full_name'):
                raise AppException(
                    code="github/invalid-response",
                    message="Invalid repository response from GitHub API",
                    status_code=502,
                )
            
        except BadCredentialsException as exc:
            logger.warning("GitHub authentication failed", repo=owner_repo)
            raise AppException(
                code="github/bad-credentials", 
                message="Invalid or expired GitHub token",
                status_code=401,
            ) from exc
            
        except UnknownObjectException as exc:
            logger.info("Repository not found", repo=owner_repo)
            raise AppException(
                code="github/repo-not-found",
                message=f"Repository '{owner_repo}' does not exist or is private",
                status_code=404,
            ) from exc
            
        except RateLimitExceededException as exc:
            logger.warning("GitHub rate limit exceeded", repo=owner_repo)
            raise AppException(
                code="github/rate-limit-exceeded",
                message="GitHub API rate limit exceeded. Please try again later.",
                status_code=429,
            ) from exc
            
        except GithubException as exc:
            logger.error("GitHub API error", repo=owner_repo, status=exc.status, data=exc.data)
            raise AppException(
                code="github/api-error",
                message=f"GitHub API error: {exc.data.get('message', 'Unknown error')}",
                status_code=exc.status if hasattr(exc, 'status') else 502,
            ) from exc
            
        except Exception as exc:
            logger.exception("Unexpected GitHub API error", repo=owner_repo)
            raise AppException(
                code="github/unexpected-error",
                message="Unexpected error while contacting GitHub API",
                status_code=502,
            ) from exc
        
        # Build repository info with safe attribute access
        info = RepoInfo(
            full_name=getattr(repo, 'full_name', owner_repo),
            description=getattr(repo, 'description', None) or "",
            stars=getattr(repo, 'stargazers_count', 0),
            forks=getattr(repo, 'forks_count', 0),
            private=getattr(repo, 'private', False),
            clone_url=getattr(repo, 'clone_url', ""),
            default_branch=getattr(repo, 'default_branch', 'main'),
        )
        
        logger.info("Repository validated successfully", 
                   repo=info.full_name, 
                   stars=info.stars, 
                   private=info.private)
        
        return info
    
    # ── Helpers ────────────────────────────────────────────────
    
    def _normalize(self, raw: str) -> str:
        """
        Normalize various GitHub repository identifier formats to 'owner/repo'.
        
        Accepts:
          * https://github.com/owner/repo
          * https://github.com/owner/repo.git
          * git@github.com:owner/repo.git
          * owner/repo
          
        Returns:
          owner/repo format
          
        Raises:
          AppException: If identifier format is invalid
        """
        if not raw:
            raise AppException(
                code="github/invalid-identifier",
                message="Repository identifier cannot be empty",
                status_code=400,
            )
        
        normalized = raw.strip()
        
        # Handle different URL formats
        if normalized.startswith(("http://", "https://")):
            # HTTP/HTTPS URLs
            parsed = urlparse(normalized)
            if parsed.hostname not in ('github.com', 'www.github.com'):
                raise AppException(
                    code="github/invalid-identifier",
                    message="Only GitHub.com repositories are supported",
                    status_code=400,
                )
            normalized = parsed.path.lstrip("/")
            
        elif normalized.startswith("git@"):
            # SSH URLs: git@github.com:owner/repo.git
            if not normalized.startswith("git@github.com:"):
                raise AppException(
                    code="github/invalid-identifier",
                    message="Only GitHub.com SSH URLs are supported",
                    status_code=400,
                )
            normalized = normalized.split(":", 1)[-1]
        
        # Remove .git suffix if present
        if normalized.endswith(".git"):
            normalized = normalized[:-4]
        
        # Validate final format
        if not self._RE_OWNER_REPO.match(normalized):
            raise AppException(
                code="github/invalid-identifier",
                message="Repository identifier must be in 'owner/repo' format or a valid GitHub URL",
                status_code=400,
            )
        
        # Additional validation for reserved names
        parts = normalized.split('/')
        if len(parts) != 2:
            raise AppException(
                code="github/invalid-identifier",
                message="Repository identifier must contain exactly one forward slash",
                status_code=400,
            )
            
        owner, repo = parts
        if not owner or not repo:
            raise AppException(
                code="github/invalid-identifier",
                message="Both owner and repository name must be non-empty",
                status_code=400,
            )
        
        return normalized
    
    def close(self) -> None:
        """Clean up service resources."""
        if self._gw:
            self._gw.close()
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ──────────────────────────────────────────────────────────────────────────
# Facade – function that a Celery task or FastAPI handler can call
# ──────────────────────────────────────────────────────────────────────────

def get_repo_metadata(identifier: str, token: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Convenience wrapper returning plain dict plus 'next_step' instruction.
    
    Args:
        identifier: Repository identifier (URL or owner/repo)
        token: GitHub personal access token
        timeout: Request timeout in seconds
        
    Returns:
        Dict containing repository metadata and next step instructions
        
    Raises:
        AppException: On validation or API errors
    """
    if not token:
        raise AppException(
            code="github/missing-token",
            message="GitHub token is required",
            status_code=400,
        )
    
    # Use context managers for proper resource cleanup
    with PyGithubGateway(token, timeout=timeout) as gateway:
        with GitHubRepoService(gateway) as service:
            repo_info = service.validate_and_fetch(identifier)
            
            result = repo_info.model_dump()
            result["next_step"] = (
                "Repository validated successfully. "
                "Run `az login` to grant Azure permissions before deployment."
            )
            
            return result


@contextmanager
def github_service_context(token: str, timeout: int = 30):
    """
    Context manager for GitHubRepoService with automatic cleanup.
    
    Usage:
        with github_service_context(token) as service:
            repo_info = service.validate_and_fetch("owner/repo")
    """
    gateway = None
    service = None
    
    try:
        gateway = PyGithubGateway(token, timeout=timeout)
        service = GitHubRepoService(gateway)
        yield service
    finally:
        if service:
            service.close()
        if gateway:
            gateway.close()