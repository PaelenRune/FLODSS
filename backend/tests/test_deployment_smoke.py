"""Exercise public entry points without the suite's authentication override."""

from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import db_manager
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from app.services import auth_service
import re
import pytest
from app.main import FRONTEND_DIST


def test_root_health_matches_api_health():
    with TestClient(app) as client:
        root = client.get('/health')
        api = client.get(f'{settings.API_V1_PREFIX}/health')
    assert root.status_code == api.status_code == 200
    assert root.json()['status'] == api.json()['status']


def test_demo_login_issues_usable_session(tmp_path, monkeypatch):
    monkeypatch.setattr(db_manager, '_custom_db_path', str(tmp_path / 'fresh-demo.db'))
    monkeypatch.setattr(db_manager, '_migrated', False)
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as client:
        for _ in range(2):
            response = client.post(f'{settings.API_V1_PREFIX}/auth/demo-login')
            assert response.status_code == 200, response.text
            assert response.json()['session_token']
            profile = client.get(f'{settings.API_V1_PREFIX}/auth/me')
            assert profile.status_code == 200
            assert profile.json()['email'] == 'guest@flodss.local'


def test_concurrent_first_demo_logins(tmp_path, monkeypatch):
    monkeypatch.setattr(db_manager, '_custom_db_path', str(tmp_path / 'concurrent-demo.db'))
    monkeypatch.setattr(db_manager, '_migrated', False)
    with TestClient(app, raise_server_exceptions=False) as client:
        barrier = Barrier(2)
        original_hash = auth_service.hash_password

        def simultaneous_hash(password):
            barrier.wait(timeout=10)
            return original_hash(password)

        monkeypatch.setattr(auth_service, 'hash_password', simultaneous_hash)
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: client.post(f'{settings.API_V1_PREFIX}/auth/demo-login'), range(2)))
        assert [response.status_code for response in responses] == [200, 200]
        assert responses[0].json()['user']['id'] == responses[1].json()['user']['id']
        with db_manager.get_connection() as conn:
            count = conn.execute('SELECT COUNT(*) FROM research_projects WHERE owner_user_id = ?', (responses[0].json()['user']['id'],)).fetchone()[0]
            assert count == 1


@pytest.mark.skipif(not (FRONTEND_DIST / 'index.html').exists(), reason='Build frontend before production SPA smoke test')
def test_production_spa_and_built_assets():
    with TestClient(app) as client:
        index = client.get('/', headers={'Accept': 'text/html'})
        assert index.status_code == 200
        assert 'text/html' in index.headers['content-type']
        assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', index.text)
        assert assets
        for asset in assets:
            assert client.get(asset).status_code == 200
        assert client.get('/workspace/layout', headers={'Accept': 'text/html'}).text == index.text
        assert client.get(f'{settings.API_V1_PREFIX}/not-a-route', headers={'Accept': 'text/html'}).status_code == 404
