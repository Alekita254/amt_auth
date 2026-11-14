import pytest
from pytest_httpx import HTTPXMock

from amt_auth.core.admin import AdminClient
from amt_auth.core.config import load_config
from amt_auth.exceptions import AdminAPIError

KC_URL = "http://localhost:8080"
REALM = "amilliontechies"
TOKEN_URL = f"{KC_URL}/realms/{REALM}/protocol/openid-connect/token"
ADMIN_BASE = f"{KC_URL}/admin/realms/{REALM}"
FAKE_TOKEN = {"access_token": "fake-token", "expires_in": 300}


def _client(amt_env: dict, httpx_mock: HTTPXMock) -> AdminClient:
    httpx_mock.add_response(url=TOKEN_URL, json=FAKE_TOKEN)
    return AdminClient(load_config(amt_env))


def test_get_organization(httpx_mock: HTTPXMock, amt_env):
    client = _client(amt_env, httpx_mock)
    httpx_mock.add_response(
        url=f"{ADMIN_BASE}/organizations/org-123",
        json={"id": "org-123", "name": "JKUAT"},
    )
    result = client.get_organization("org-123")
    assert result["name"] == "JKUAT"


def test_list_organizations(httpx_mock: HTTPXMock, amt_env):
    client = _client(amt_env, httpx_mock)
    httpx_mock.add_response(
        url=f"{ADMIN_BASE}/organizations?first=0&max=100",
        json=[{"id": "org-1"}],
    )
    result = client.list_organizations()
    assert len(result) == 1


def test_list_org_members(httpx_mock: HTTPXMock, amt_env):
    client = _client(amt_env, httpx_mock)
    httpx_mock.add_response(
        url=f"{ADMIN_BASE}/organizations/org-123/members?first=0&max=100",
        json=[{"id": "user-1", "username": "alice"}],
    )
    result = client.list_org_members("org-123")
    assert result[0]["id"] == "user-1"


def test_401_retries_once(httpx_mock: HTTPXMock, amt_env):
    httpx_mock.add_response(url=TOKEN_URL, json=FAKE_TOKEN)   # initial token
    client = AdminClient(load_config(amt_env))
    httpx_mock.add_response(
        url=f"{ADMIN_BASE}/organizations/org-1", status_code=401
    )  # first attempt: 401
    httpx_mock.add_response(url=TOKEN_URL, json=FAKE_TOKEN)   # token refresh
    httpx_mock.add_response(
        url=f"{ADMIN_BASE}/organizations/org-1", json={"id": "org-1"}
    )  # retry: success
    result = client.get_organization("org-1")
    assert result["id"] == "org-1"


def test_404_raises(httpx_mock: HTTPXMock, amt_env):
    client = _client(amt_env, httpx_mock)
    httpx_mock.add_response(
        url=f"{ADMIN_BASE}/organizations/not-found", status_code=404
    )
    with pytest.raises(AdminAPIError) as exc_info:
        client.get_organization("not-found")
    assert exc_info.value.status_code == 404


def test_500_raises(httpx_mock: HTTPXMock, amt_env):
    client = _client(amt_env, httpx_mock)
    httpx_mock.add_response(
        url=f"{ADMIN_BASE}/organizations/boom", status_code=500
    )
    with pytest.raises(AdminAPIError) as exc_info:
        client.get_organization("boom")
    assert exc_info.value.status_code == 500
