from pydantic import BaseModel, Field, validator

class RepoRequest(BaseModel):
    repo: str = Field(..., example="octocat/Hello-World")
    token: str = Field(..., min_length=1)

    # validators kept
    @validator("repo")
    def _repo_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Repository identifier cannot be empty")
        return v.strip()

    @validator("token")
    def _token_not_empty(cls, v):
        if not v.strip():
            raise ValueError("GitHub token cannot be empty")
        return v.strip()


# ──────────────────────────────────────────────────────────────
class RepoInfo(BaseModel):          # ← add this
    """Internal DTO used by github_service.py"""
    full_name: str
    description: str
    stars: int
    forks: int
    private: bool
    clone_url: str
    default_branch: str

class RepoInfoResponse(BaseModel):
    full_name: str
    description: str
    stars: int
    forks: int
    private: bool
    clone_url: str
    default_branch: str
    next_step: str


class ErrorResponse(BaseModel):
    error: str
    code: str
    message: str
    status_code: int
