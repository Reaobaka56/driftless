import psycopg
from psycopg.rows import dict_row

from worker.env import require_env


def get_conn() -> psycopg.Connection:
    return psycopg.connect(require_env("DATABASE_URL"), row_factory=dict_row)  # type: ignore[arg-type]
