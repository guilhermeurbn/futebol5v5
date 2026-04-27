import os
import psycopg2


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def get_conn():
    url = os.getenv("DATABASE_URL")
    if not url:
        return None

    url = _normalize_database_url(url)
    return psycopg2.connect(url, sslmode=os.getenv("PGSSLMODE", "require"))