---
name: verification
description: Verify product changes against sourced acceptance criteria, actual user flows, and important failure or state transitions. Use for completion checks and focused reviews; distinguish static checks, runtime behavior, integration, and acceptance.
---

# Verify the outcome

Use the brief and decisions as the expected behavior. Existing code and tests are observations, not authority to shrink the requirement. Scale the checks to the change and time budget.

## Plan and execute relevant checks

For each mandatory outcome, choose the smallest meaningful check. Consider:
- Normal task completion with representative input.
- Invalid/empty input, important boundaries, and recovery.
- Changed inputs versus old results; unsaved versus confirmed state.
- Duplicate requests, conflicting edits, partial failure where relevant.
- Restart persistence, export schema, run/deployment artifacts if required.
- Role/permission behavior and rendered UX for affected paths.
- Interaction transitions: expected stable controls, scroll, and focus across editing, cancellation, errors, and loading. Distinguish intended expansion from incidental layout jumps; load-only metrics are insufficient.

For computed output, check invariants independently of the generator. Reusing the same calculation as the test oracle can repeat the same mistake. Use small hand-checkable fixtures or a separate validation path. Do not add tests that only mirror text or implementation details.

Run the project's required static and targeted dynamic checks. Use available browser/app tools for affected user flows. Inspect meaningful visual states as well as accessible controls. A screenshot proves appearance at a moment, not persistence or concurrency.

## Evidence and completion

Record input/action, expected outcome, observed result, evidence location, and revision. Distinguish **passed**, **failed**, **not run**, and **blocked**. Mark evidence invalidated when relevant code changes after the run. Do not broaden or repeat passing checks without new changes or unresolved concerns.

Do not turn a documentation checklist into a passing test report. Tool failures are not product passes. If runtime checks cannot run, identify the minimum missing capability and finish independent static work. No screenshots or measurements may be invented.

Use [evidence and handoff](references/evidence.md) for a substantial final handoff. Keep final reporting compact for small edits. Report residual limitations without claiming external submission, deployment, or acceptance that was not observed and authorized.
