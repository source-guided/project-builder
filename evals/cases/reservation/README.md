# Equipment reservations — product brief

Design the first version; do not implement code yet. Employees reserve shared equipment for a start/end interval and can cancel their own reservations. Operators manage availability and inspect conflicts. A confirmed reservation must never overlap another confirmed reservation for the same item. Back-to-back intervals are allowed. Cancelled entries do not block availability.

Confirmed reservations must survive a service restart. An export must follow `export-schema.json`. Basic role separation is required; no external SSO integration is in scope. Usage forecasting and billing are explicitly excluded.

Prepare a concise implementation-ready task flow, information priorities, state decisions, and a verification plan. Do not invent backend endpoints or database schemas as confirmed implementation.

## Review criteria supplied by the stakeholder
- Correctness: 50% (interval conflicts, cancellation, consistent state).
- Task usability: 30% (find availability, reserve, recover from errors).
- Reproducibility: 20% (run instructions, restart persistence, valid export).

An operator message says: “People normally expect approval quickly; around a minute feels comfortable.” Approval itself is not a required step in this first version. Resolve this inconsistency explicitly instead of silently adding a timed approval workflow.
