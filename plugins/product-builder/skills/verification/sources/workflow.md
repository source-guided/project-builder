# Verify the outcome

Use the brief and decisions as the expected behavior. Existing code and tests are observations, not authority to shrink the requirement. Scale the checks to the change and time budget.

## Plan and execute relevant checks

Derive coverage from the supplied outcomes and material decisions before relying on the implementation's existing tests. For each applicable requirement, identify a concrete starting state, user action, observable result, and evidence type. Mark omitted or unexecutable checks as unverified with a reason. Source reading, component presence, test totals, and an agent's completion message are not substitutes for that coverage.

For each mandatory outcome, choose the smallest meaningful check. Consider:
- Normal task completion with representative input.
- Invalid/empty input, important boundaries, and recovery.
- Changed inputs versus old results; unsaved versus confirmed state.
- Duplicate requests, conflicting edits, partial failure where relevant.
- Restart persistence, export schema, run/deployment artifacts if required.
- Role/permission behavior and rendered UX for affected paths.
- Each primary role's entry-to-outcome path and a concrete find-and-act task from visible UI. Check current scope, selected item, and detail/action identity after filtering; do not substitute the administrator view for other roles. Use UX reference `task-navigation` where relevant.
- First use without prepared successful state, repeat use, and a required outcome outside the default scope where relevant. For an input journey, check preparation, start, recovery/backtracking, and the final commit boundary from visible UI, not just whether the submitted payload is valid.
- Open controls and secondary surfaces: selection/commit/cancel keyboard paths, viewport-edge clipping, close/reopen draft preservation, main-page anchors, scrollbar width, and return focus.
- Interaction transitions: expected stable controls, scroll, and focus across editing, cancellation, errors, and loading. Distinguish intended expansion from incidental layout jumps; load-only metrics are insufficient.
- Data-dependent transitions with and without conditional context, including appearance and disappearance. Select contrasting inputs while holding the task constant; inspect the changing region and meaningful downstream anchors. A static screenshot or no horizontal overflow does not cover this behavior.
- Feedback lifecycle and scope: completion/cancel events do not remain as unrelated page state; contextual messages belong to the current item; temporary messages clear as designed while actionable errors remain recoverable. Check actual action-region correspondence, not only stable siblings. Use UX reference `feedback-actions` for the decision method.

For computed output, check invariants independently of the generator. Reusing the same calculation as the test oracle can repeat the same mistake. Use small hand-checkable fixtures or a separate validation path. Do not add tests that only mirror text or implementation details.

For material format, range, precision, or normalization decisions, include contract-valid inputs near an implementation boundary as well as contract-invalid inputs a library may accept. Derive expected behavior from the adopted profile, not from another call to the same parser. Compare available supported environments when a dependency default can change the outcome; do not claim all-version coverage from one runtime. Separate a confirmed contract mismatch from an unspecified dialect or resource envelope that needs clarification, and state practical impact without inventing operational scale.

Run the project's required static and targeted dynamic checks. Use available browser/app tools for affected user flows. Inspect meaningful visual states as well as accessible controls. A screenshot proves appearance at a moment, not persistence or concurrency.

## Evidence and completion

Record input/action, expected outcome, observed result, evidence location, and revision. Distinguish **passed**, **failed**, **not run**, and **blocked**. Mark evidence invalidated when relevant code changes after the run. Do not broaden or repeat passing checks without new changes or unresolved concerns.

Do not turn a documentation checklist into a passing test report. Tool failures are not product passes. If runtime checks cannot run, identify the minimum missing capability and finish independent static work. No screenshots or measurements may be invented.

For a reusable-workflow evaluation, resolve `independent-review` through the [delivery reference](../../../references/delivery/index.json). That source owns the independent review method and its relationship to the execution harness.

Use [evidence and handoff — reference](../../../references/delivery/index.json) for a substantial final handoff. Keep final reporting compact for small edits. Report residual limitations without claiming external submission, deployment, or acceptance that was not observed and authorized.
