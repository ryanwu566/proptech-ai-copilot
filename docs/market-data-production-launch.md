# Market data production launch

This repository contains the official-source pipeline and synthetic validation,
but code alone does not populate a hosted database. Before launch an operator
must configure the protected production environment, confirm the official
release and license, run discovery and dry-run validation, apply migration 008,
import a bounded initial 24–36 month residential-sale range, verify counts and
coverage, and approve publication.

The final gate must show a real release ID, valid transaction counts, at least
one verified region with real metrics, source/freshness metadata, and a hosted
browser check. Until then Market Insight must remain an explicit unavailable,
no-data, incomplete, or configuration-required state. Synthetic fixtures never
serve production and no raw nationwide transaction file is committed.
