# Synthetic product examples

## Equipment reservation

Brief: Staff reserve equipment for a time interval. Overlapping confirmed bookings are forbidden. Export uses a supplied schema. The application must restart without losing confirmed bookings. A reviewer asks why a lock was chosen.

Interpretation: interval conflicts, persistence, and export validity are explicit. The lock question is evidence about implementation understanding, not an official requirement for a specific database or lock mechanism. A calendar may help selection, but a dashboard with aggregate utilization is optional unless a task requires it.

## Batch reconciliation

Brief: Reconcile two CSVs, emit unmatched rows and a summary JSON, and return a nonzero exit on malformed input. No UI is requested. The scoring table is absent.

Interpretation: preserve the CLI workflow; verify malformed input and exact output schema. Do not create a login screen, database, or dashboard. State that official score weights are unknown. Memory usage may matter if the brief states a size bound; otherwise do not invent one.

## Document approval

Brief: Authors submit a draft; reviewers can request changes or approve a particular revision. A stakeholder says approvals are usually quick.

Interpretation: revision identity matters; approval of one revision must not silently approve later edits. “Usually quick” is not an SLA. A reviewer's decision screen should show the material changes, status, and available actions rather than implementation logs.
