import hashlib


def repo_hash(repo_url: str) -> str:
    """Stable, non-reversible repo identifier (we store hashes, never URLs)."""
    return hashlib.sha256(repo_url.encode()).hexdigest()[:32]
