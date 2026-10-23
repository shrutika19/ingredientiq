from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api.routes import analysis, submissions
from app.database.dependencies import get_db
from app.main import app
from app.services import api_limits


def override_db(db):
    def dependency():
        yield db

    return dependency


def make_request(
    peer_ip: str = "198.51.100.24",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/submissions",
            "raw_path": b"/api/v1/submissions",
            "query_string": b"",
            "headers": headers or [],
            "client": (peer_ip, 12345),
            "server": ("testserver", 80),
        }
    )


def test_client_ip_uses_peer_unless_peer_is_trusted(monkeypatch):
    monkeypatch.setattr(
        api_limits,
        "get_settings",
        lambda: SimpleNamespace(TRUSTED_PROXY_IPS=["10.0.0.0/8"]),
    )

    untrusted_request = make_request(
        headers=[(b"x-real-ip", b"203.0.113.42")]
    )
    assert api_limits.get_client_ip(untrusted_request) == "198.51.100.24"

    trusted_request = make_request(
        peer_ip="10.0.0.5",
        headers=[(b"x-real-ip", b"203.0.113.42")],
    )
    assert api_limits.get_client_ip(trusted_request) == "203.0.113.42"


def test_ipv6_clients_are_grouped_by_slash_64(monkeypatch):
    monkeypatch.setattr(
        api_limits,
        "get_settings",
        lambda: SimpleNamespace(TRUSTED_PROXY_IPS=[]),
    )

    first = api_limits.get_client_ip(
        make_request(peer_ip="2001:db8:abcd:12::1")
    )
    same_subnet = api_limits.get_client_ip(
        make_request(peer_ip="2001:db8:abcd:12::beef")
    )
    other_subnet = api_limits.get_client_ip(
        make_request(peer_ip="2001:db8:abcd:13::1")
    )

    assert first == "2001:db8:abcd:12::/64"
    assert same_subnet == first
    assert other_subnet == "2001:db8:abcd:13::/64"


def test_ipv4_clients_keep_individual_address_keys(monkeypatch):
    monkeypatch.setattr(
        api_limits,
        "get_settings",
        lambda: SimpleNamespace(TRUSTED_PROXY_IPS=[]),
    )

    assert api_limits.get_client_ip(
        make_request(peer_ip="198.51.100.24")
    ) == "198.51.100.24"


def test_invalid_forwarded_ip_from_trusted_proxy_is_rejected(monkeypatch):
    monkeypatch.setattr(
        api_limits,
        "get_settings",
        lambda: SimpleNamespace(TRUSTED_PROXY_IPS=["10.0.0.0/8"]),
    )

    request = make_request(
        peer_ip="10.0.0.5",
        headers=[(b"x-real-ip", b"not-an-ip")],
    )

    with pytest.raises(HTTPException) as error:
        api_limits.get_client_ip(request)

    assert error.value.status_code == 400


def test_api_limit_upsert_is_postgresql_atomic(monkeypatch):
    settings = SimpleNamespace(
        TRUSTED_PROXY_IPS=[],
        API_LIMIT_HASH_SECRET=None,
        API_REQUESTS_PER_MINUTE=10,
        API_DAILY_ANALYSES_PER_IP=5,
        API_DAILY_SUBMISSIONS_PER_IP=100,
    )
    monkeypatch.setattr(api_limits, "get_settings", lambda: settings)
    db = MagicMock()
    db.execute.return_value.one.return_value = (1, 1, 1)

    api_limits.apply_api_limits(
        make_request(),
        db,
        count_analysis=True,
        count_submission=False,
    )

    statement = db.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "ON CONFLICT" in sql
    assert "RETURNING" in sql
    assert "minute_request_count" in sql
    assert "daily_analysis_count" in sql
    assert "daily_submission_count" in sql
    db.commit.assert_called_once()


def test_submission_route_enforces_minute_limit(monkeypatch):
    db = MagicMock()
    db.execute.return_value.one.return_value = (11, 0, 0)
    app.dependency_overrides[get_db] = override_db(db)
    monkeypatch.setattr(
        submissions,
        "create_submission",
        lambda **kwargs: pytest.fail("submission should be rate limited"),
    )

    try:
        with TestClient(
            app,
            client=("127.0.0.1", 50000),
        ) as client:
            response = client.post(
                "/api/v1/submissions",
                json={"ingredient_text": "Aqua, Glycerin"},
            )

        assert response.status_code == 429
        assert response.json()["error"]["code"] == (
            "API_RATE_LIMIT_EXCEEDED"
        )
        assert response.headers["retry-after"]
    finally:
        app.dependency_overrides.clear()


def test_analysis_route_enforces_daily_cap(monkeypatch):
    db = MagicMock()
    db.execute.return_value.one.return_value = (1, 6, 0)
    app.dependency_overrides[get_db] = override_db(db)
    monkeypatch.setattr(
        analysis,
        "queue_analysis",
        lambda **kwargs: pytest.fail("analysis should be rate limited"),
    )

    try:
        with TestClient(
            app,
            client=("127.0.0.1", 50000),
        ) as client:
            response = client.post(
                "/api/v1/submissions/"
                "d19320a8-fc66-42f8-a0fd-9dd0c1777588/analyze"
            )

        assert response.status_code == 429
        assert response.json()["error"]["code"] == (
            "DAILY_ANALYSIS_LIMIT_REACHED"
        )
        assert response.headers["retry-after"]
    finally:
        app.dependency_overrides.clear()


def test_submission_route_enforces_daily_cap(monkeypatch):
    db = MagicMock()
    db.execute.return_value.one.return_value = (1, 0, 101)
    app.dependency_overrides[get_db] = override_db(db)
    monkeypatch.setattr(
        submissions,
        "create_submission",
        lambda **kwargs: pytest.fail("submission should be daily limited"),
    )

    try:
        with TestClient(
            app,
            client=("127.0.0.1", 50000),
        ) as client:
            response = client.post(
                "/api/v1/submissions",
                json={"ingredient_text": "Aqua, Glycerin"},
            )

        assert response.status_code == 429
        assert response.json()["error"]["code"] == (
            "DAILY_SUBMISSION_LIMIT_REACHED"
        )
        assert response.headers["retry-after"]
    finally:
        app.dependency_overrides.clear()
@pytest.mark.parametrize(
    (
        "counts",
        "count_analysis",
        "count_submission",
        "expected_error",
    ),
    [
        ((11, 1, 0), False, False, "API_RATE_LIMIT_EXCEEDED"),
        ((1, 6, 0), True, False, "DAILY_ANALYSIS_LIMIT_REACHED"),
        ((1, 0, 101), False, True, "DAILY_SUBMISSION_LIMIT_REACHED"),
    ],
)
def test_limits_return_429_and_retry_after(
    monkeypatch,
    counts,
    count_analysis,
    count_submission,
    expected_error,
):
    settings = SimpleNamespace(
        TRUSTED_PROXY_IPS=[],
        API_LIMIT_HASH_SECRET=None,
        API_REQUESTS_PER_MINUTE=10,
        API_DAILY_ANALYSES_PER_IP=5,
        API_DAILY_SUBMISSIONS_PER_IP=100,
    )
    monkeypatch.setattr(api_limits, "get_settings", lambda: settings)
    db = MagicMock()
    db.execute.return_value.one.return_value = counts

    with pytest.raises(HTTPException) as error:
        api_limits.apply_api_limits(
            make_request(),
            db,
            count_analysis=count_analysis,
            count_submission=count_submission,
        )

    assert error.value.status_code == 429
    assert error.value.detail["error"] == expected_error
    assert int(error.value.headers["Retry-After"]) > 0
    db.commit.assert_called_once()
