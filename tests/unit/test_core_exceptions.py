from fastapi import FastAPI
from fastapi.testclient import TestClient

from gateway.core.exceptions import AppException, add_exception_handlers


def test_problem_details_handler():
    app = FastAPI()
    add_exception_handlers(app)

    @app.get("/")
    def boom():
        raise AppException(code="demo/error", message="boom", status_code=418)

    cli = TestClient(app)
    r = cli.get("/")
    assert r.status_code == 418
    body = r.json()
    assert body["type"] == "demo/error"
    assert body["detail"] == "boom"
