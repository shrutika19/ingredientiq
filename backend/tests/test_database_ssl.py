import pytest

from app.database.session import database_sslmode_for_host


@pytest.mark.parametrize(
    "host",
    [
        "localhost",
        "LOCALHOST.",
        "127.0.0.1",
        "::1",
        "::ffff:127.0.0.1",
    ],
)
def test_local_database_hosts_disable_ssl(host: str) -> None:
    assert database_sslmode_for_host(host) == "disable"


@pytest.mark.parametrize(
    "host",
    [
        "db.example.com",
        "host.docker.internal",
        "192.0.2.12",
        "2001:db8::10",
    ],
)
def test_nonlocal_database_hosts_require_ssl(host: str) -> None:
    assert database_sslmode_for_host(host) == "require"
