def compose_pr_body(record, result) -> str:
    files = "\n".join(f"- `{f}`" for f in result.changed_files) or "- (none)"
    return f"""## Driftless: fix for `{record.id}`

record: {record.id}
**Vendor:** {record.vendor} | **Type:** {record.type} | **Effective:** {record.effective}
**Source:** {record.source_url}

{record.migration_note}

### Changed files
{files}

### Evidence
- Confidence: {result.confidence:.2f} ({result.status})

*Opened by Driftless. A human must review and merge. Never auto-merged.*
"""
