# Extract constraints without inventing them

Read each relevant section and linked contract. A short task summary is not a complete specification. Track unresolved references instead of silently considering them covered.

For a substantial specification, keep a compact constraint ledger in the project:

`ID | condition | source/locator | provenance | scope | unit/range/boundary | verification | open question`

Split independently testable clauses. Preserve whether a condition is mandatory, configurable, a preference, an example, or an observed runtime value. A number visible in a running form does not automatically become a global default or a mandatory limit.

Inspect only relevant dimensions:
- Actors, ownership, permissions, and which operations they can perform.
- Inputs, schema types, null/empty meaning, identifiers, references, uniqueness, and malformed data.
- Time, dates, time zones, recurrence, interval boundaries, order, and eligibility.
- Hard capacity or validity constraints versus optimization objectives and tradeoffs.
- Change lifecycle: draft, applied, computed, confirmed, stale, cancelled, failure, and recovery.
- Persistence, restart, reproducibility, packaging, output/export schema, and delivery requirements.
- Explicit exclusions, external dependencies, tool restrictions, and source conflicts.

These are coverage questions, not requirements to add to every product. Do not infer exact limits, inequality boundaries, weights, retention periods, or retry policies from an example. If only a summary survives, preserve the condition family and explicitly mark the missing exact clause.

For each mandatory condition, identify an observable check. For each missing material clause, identify the minimum source or stakeholder decision needed. Choose bounded assumptions only where authorized and record them. Do not label a reconstructed ledger “complete original specification.”

After implementation, reconcile the ledger against actual behavior and evidence. Unimplemented requirements remain visible; optional proposals must not displace them.
