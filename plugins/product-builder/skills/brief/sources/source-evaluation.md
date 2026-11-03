# Sources, process, and evaluation

## Read the full product context

A product brief may be distributed across README, data dictionary, export schema, execution guide, stakeholder messages, delivery rules, and review questions. Inventory present and missing sources. Follow relevant references; do not claim to have inspected an inaccessible file.

Requirements commonly concern functionality, data correctness, restart persistence, reproducible startup, allowed dependencies, role-specific behavior, export shape, and submission artifacts. These are discovery categories, not mandatory features for every product.

Record the delivery process separately from product UX. Release approvals, stakeholder review, workspace limits, and handoff procedures usually do not belong in the customer-facing interface. An environment error is not an application error. A successful upload does not prove stakeholder acceptance.

## Provenance classes

| Class | Meaning | Treatment |
| --- | --- | --- |
| Explicit requirement | Current source states it | Verify it; preserve locator |
| Clarification | Authorized stakeholder explains intent | Link to original and reconcile conflicts |
| Recorded reconstruction | Earlier observation summarizes a source | Mark incomplete; verify material gaps if possible |
| Inference | Interpretation from questions or behavior | Label as inference; no invented weights |
| Proposal | Agent's implementation or UX suggestion | Justify it; do not turn it into a requirement |

If the brief says three checks are mandatory, a later question about scaling does not silently require a production distributed system. If the user changes scope, record that change and reconcile the remaining contract rather than clinging to an older summary.

## Evidence-based evaluation

Map each official criterion to observable behavior, artifacts, and a verification method. When weights are supplied, quote their source and apply them accurately. When absent, say **official weighting unknown**. Prioritize work without pretending the prioritization is the stakeholder's review rubric.

Review questions can indicate areas worth understanding: choice of algorithm, request-to-storage flow, data/state transitions, failure/concurrency, independent verification, and human judgment in AI collaboration. They are not proof of the complete acceptance criteria. Use only the dimensions relevant to the current task.

For AI collaboration, record actual proposal → human decision → implementation → check. Do not fabricate rejected suggestions, rationalize an undocumented choice, or treat AI confidence as execution evidence.

## Minimal acceptance row

`R3 | Restart retains confirmed reservations | README §Persistence | explicit | create → restart → query same IDs | not run`

This row does more work than an essay saying persistence is important. Exact counts, times, schema fields, or tool limits must come from the current source, never a past example.
