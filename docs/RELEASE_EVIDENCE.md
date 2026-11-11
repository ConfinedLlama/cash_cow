# Manual economic-release evidence

The offline release selector checks metric, unit, vintage and first-observed
timing. A plausible URL and hash alone cannot establish which saved document
was reviewed. The additional read-only provenance audit joins each record to
actual saved bytes and a review of that exact record hash.

```sh
.venv/bin/python -m cash_cow.packet_research.release_evidence \
  --records .local/research/releases.json \
  --manifest .local/research/evidence.json \
  --as-of 2026-11-11T09:00:00Z
```

Those paths are examples. Store real source captures and records locally, not
in Git. The manifest has exactly `schema: release_evidence_v1`, `sources` and
`reviews`. Each source contains `sha256`, `url`, a plain local basename `file`,
`method` and `received_at`. Method is `http_response_body` or `web_tool_rendering`;
do not call a browser/tool rendering original HTTP bytes. Each review contains
the exact `record_sha256` (the selector's canonical JSON digest) and `reviewed_at`.

Publication must precede source receipt, which must precede review, which must
precede or equal the structured record's first observation. A later manual
extraction cannot inherit the document's earlier publication time. Conflicting,
unreviewed, unreferenced or changed sources/records fail. Sources cannot be
symlinks or directory traversals, and each is bounded to five megabytes. The
audit rechecks source hashes after reviewing all records and writes nothing.

The command prints aggregate provenance and availability counts, not article
text. Exit 2 means invalid evidence. Exit 0 may contain zero eligible values:
later observations or releases older than the fixed seven-day limit remain
excluded. All exclusions and source captures must be retained.

Passing means consistency of supplied local evidence. It does not authenticate
an official author, verify a numeric extraction against prose, certify review
identity or guarantee truthful timestamps. Manually inspect the official dated
document, metric, period, units and adjustment basis. A monthly percentage
change is not an annual rate or a surprise relative to an unobserved consensus.

This audit does not alter `packet_context_v2`, invoke a model, write an active
news packet or enable trading. A new receipt-aware strategy comparison still
requires a separate frozen protocol and prospective evaluation.
