from worker.celery_app import app
from gateway.app.services.deployments.github_service import get_repo_metadata

@app.task(bind=True, name="deployments.check")
def check_repo_task(self, identifier: str, gh_token: str):
    return get_repo_metadata(identifier, gh_token)
