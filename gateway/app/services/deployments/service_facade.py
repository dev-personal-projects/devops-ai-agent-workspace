from gateway.app.services.deployments.github_service import get_repo_metadata

class GitHubRepoFacade:
    """
    Thin façade so the router doesn’t import business modules directly.
    Helps testing and future expansion (SOLID's Dependency Inversion).
    """

    def fetch_repo_metadata(self, repo: str, token: str) -> dict:
        return get_repo_metadata(repo, token)
