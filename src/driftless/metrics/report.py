def get_stats(since: str | None = None) -> str:
    # Local CLI keeps no state; hosted mode reads fix_attempts from Postgres.
    return "Opened: 0\nAccepted-PR rate: n/a (use the hosted dashboard)\n"
