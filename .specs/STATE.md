# Project state

## Decisions

| ID | Decision | Rationale | Status | Date |
| --- | --- | --- | --- | --- |
| AD-001 | Info hash normalization does not require `torf` for magnet URIs | Users supply info hashes directly (40-char hex or 32-char base32), handled via base32 decoding and hex validation without `torf` dependency | active | 2026-11-09 |
