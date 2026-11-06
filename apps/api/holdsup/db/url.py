"""Turn the DATABASE_URL a host gives us (e.g. Neon) into one SQLAlchemy + asyncpg accept."""

from sqlalchemy.engine import URL, make_url

_SCHEMES = {"postgres", "postgresql", "postgresql+psycopg2", "postgresql+psycopg"}
# libpq query options that asyncpg does not understand.
_DROP_PARAMS = {"channel_binding"}


def to_async_url(raw: str) -> URL:
    """Return an asyncpg URL. `sslmode=X` becomes asyncpg's `ssl=X`."""
    url = make_url(raw)
    if url.drivername in _SCHEMES:
        url = url.set(drivername="postgresql+asyncpg")
    elif url.drivername != "postgresql+asyncpg":
        raise ValueError(f"unsupported database driver: {url.drivername}")

    query = {k: v for k, v in url.query.items() if k not in _DROP_PARAMS}
    sslmode = query.pop("sslmode", None)
    if sslmode is not None and "ssl" not in query:
        query["ssl"] = sslmode
    return url.set(query=query)
