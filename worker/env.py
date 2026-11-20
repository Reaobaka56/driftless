import os

_HINTS = {
    "REDIS_URL": "the internal connection string of the Render Key Value instance (driftless-redis)",
    "DATABASE_URL": "the internal connection string of the Render Postgres database (driftless-db)",
}


def require_env(name: str) -> str:
    """Return an environment variable, or fail with what it should contain and how it is set."""
    value = os.environ.get(name)
    if value:
        return value
    hint = _HINTS.get(name, "a value for this service")
    raise RuntimeError(
        f"{name} is not set. It should be {hint}. "
        "In render.yaml it comes from fromService/fromDatabase; if this service was created by hand "
        "rather than from the Blueprint, add it under Environment."
    )
