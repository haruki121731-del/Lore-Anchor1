"""Shared fixtures for the API test suite.

All tests run with DEBUG=true so external services (R2, Supabase, Redis)
are replaced by in-memory / local-filesystem stubs.
"""

import os

# Ensure DEBUG mode BEFORE any application code is imported.
os.environ["DEBUG"] = "true"

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture()
def client() -> TestClient:
    """Return a synchronous FastAPI TestClient."""
    return TestClient(app)
