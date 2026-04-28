"""Backend API tests for ATS Resume Tailor."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://resume-optimizer-260.preview.emergentagent.com").rstrip("/")


# Health endpoint
def test_health_returns_ok_and_flags():
    r = requests.get(f"{BASE_URL}/api/health", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert data.get("anthropicConfigured") is True
    assert data.get("overleafConfigured") is False  # cookies intentionally empty


# Validation: empty body
def test_generate_empty_body_returns_422():
    r = requests.post(f"{BASE_URL}/api/generate", json={}, timeout=30)
    assert r.status_code == 422


# Validation: missing fields
def test_generate_blank_strings_returns_422():
    r = requests.post(
        f"{BASE_URL}/api/generate",
        json={"jobDescription": "", "currentResume": ""},
        timeout=30,
    )
    assert r.status_code == 422


# Fail-fast: Overleaf creds missing returns 500 quickly with the right message
def test_generate_fails_fast_when_overleaf_not_configured():
    import time
    start = time.time()
    r = requests.post(
        f"{BASE_URL}/api/generate",
        json={"jobDescription": "Senior backend engineer python fastapi", "currentResume": "John Doe\nSoftware engineer\n5y python"},
        timeout=30,
    )
    elapsed = time.time() - start
    assert r.status_code == 500
    body = r.json()
    detail = body.get("detail") or body.get("message") or ""
    assert "Overleaf credentials not configured" in detail
    # Should fail fast (before Claude calls) - well under 10s
    assert elapsed < 10, f"Did not fail fast: took {elapsed:.1f}s"


# Root
def test_api_root():
    r = requests.get(f"{BASE_URL}/api/", timeout=30)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
