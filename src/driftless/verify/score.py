def compute_confidence(rescan_clean: bool, tests_passed: bool | None, parses: bool) -> float:
    """tests_passed=None means the repo has no tests (partial credit, flagged in PR)."""
    score = 0.0
    if rescan_clean:
        score += 0.5
    if parses:
        score += 0.2
    if tests_passed is True:
        score += 0.3
    elif tests_passed is None:
        score += 0.1
    return round(score, 2)
