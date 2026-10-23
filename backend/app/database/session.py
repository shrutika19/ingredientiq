from ipaddress import ip_address

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


settings = get_settings()


def database_sslmode_for_host(host: str) -> str:
    normalized_host = host.rstrip(".").casefold()
    if normalized_host == "localhost":
        return "disable"

    try:
        address = ip_address(host)
    except ValueError:
        return "require"

    if address.is_loopback or (
        address.version == 6
        and address.ipv4_mapped is not None
        and address.ipv4_mapped.is_loopback
    ):
        return "disable"

    return "require"


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=settings.DB_USER,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
    query={"sslmode": database_sslmode_for_host(settings.DB_HOST)},
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)