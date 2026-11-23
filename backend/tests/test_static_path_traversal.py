"""Regression tests: the SPA fallback must never serve files outside the frontend build directory."""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import app.main as main_module


def _request(accept: str = "*/*") -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": [(b"accept", accept.encode())]})


@pytest.fixture
def fake_dist(tmp_path, monkeypatch):
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html>spa</html>", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.db").write_text("TOP-SECRET", encoding="utf-8")
    (tmp_path / "frontend" / "config.py").write_text("SECRET_KEY='x'", encoding="utf-8")
    monkeypatch.setattr(main_module, "FRONTEND_DIST", dist)
    return dist


def test_serves_file_inside_dist(fake_dist):
    response = main_module.serve_spa_or_static("favicon.svg", _request())
    assert response.path == str((fake_dist / "favicon.svg").resolve())


@pytest.mark.parametrize(
    "malicious_path",
    [
        "../../secret.db",
        "x/../../../secret.db",
        "x/../../config.py",
        "x/..\\..\\..\\secret.db",
        "assets/../../config.py",
    ],
)
def test_rejects_paths_escaping_dist(fake_dist, malicious_path):
    with pytest.raises(HTTPException) as exc:
        main_module.serve_spa_or_static(malicious_path, _request())
    assert exc.value.status_code == 404


def test_escaping_path_falls_back_to_index_for_browsers(fake_dist):
    response = main_module.serve_spa_or_static("x/../../../secret.db", _request("text/html"))
    assert response.path == str(fake_dist / "index.html")
