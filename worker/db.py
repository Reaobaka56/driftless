import os

import psycopg
from psycopg.rows import dict_row


def get_conn() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)  # type: ignore[arg-type]
