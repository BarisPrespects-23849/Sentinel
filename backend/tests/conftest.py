"""Shared pytest fixtures.

Unit tests (rules, features, engine) need nothing external. API tests use
FastAPI's TestClient against the real dev database -- Docker Compose is
part of the dev environment, so tests exercise the honest stack rather
than a mock that can drift from reality.
"""

import pytest


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
