# Patterns with applicability — synthetic examples

These are decision aids, not templates to stamp onto every product. Preserve a supplied design or justified product requirement over these examples.

## Find and act

**Use when:** a person must locate a record and take a specific next action.

Bad: six total-count cards, an introductory essay, advanced filters, then the result list below the fold.

Better: relevant default scope, concise search/filter controls, identifiable results, a clear action and useful empty state. Keep a count if it helps compare or understand the result set.

**Example:** an employee checking a reservation sees the item, time, confirmation state, and change/cancel action. Server version and import diagnostics do not help this task.

**Counterexample:** a capacity planner may need aggregate utilization to decide where to allocate inventory. Do not remove metrics when they serve that decision.

## Configure → preview → commit

**Use when:** a user changes inputs and must inspect consequential output before committing.

Bad: inputs update while the previous result still appears current; a green “success” banner appears before validation; the commit button doesn't identify which result it will save.

Better: keep the result linked to the inputs/revision that produced it; indicate when recalculation is needed; show material differences and violations; explain what committing changes. Preserve the previous confirmed result until a valid replacement is accepted, when required by the domain.

**Counterexample:** immediate low-impact settings may not need a separate preview or confirmation step.

## Review a revision

**Use when:** a decision applies to a particular document or record revision.

Bad: a large project status dashboard hides the changed content; approval silently follows later edits.

Better: identity and revision, relevant changes, decision context, approve/request-changes actions, and the result. Ensure the approved revision remains explicit.

For this pattern, optionally inspect the [standalone synthetic example — reference](../../../references/design/ui/index.json), [desktop rendering — reference](../../../references/design/ui/index.json), and [narrow rendering — reference](../../../references/design/ui/index.json). It demonstrates hierarchy and revision-scoped decisions. State is page-local and resets on reload; it is not a production persistence or permission implementation. Its content, colors, numbers, and layout are example choices, not requirements for other products.

## Recover from an error

**Use when:** the user can correct input or retry an action.

Bad: raw stack traces, “backend not ready” banners, or a disabled page that explains the development schedule.

Better: explain which action failed, retain recoverable input, and give the next useful action. Show a genuine service outage when it affects the task. Keep technical details in diagnostics unless the audience needs them.

## Forms and progressive detail

Use meaningful defaults only when supported by the domain. Distinguish an unset value from zero or an empty choice. Put optional advanced settings behind a clear affordance when this reduces effort; don't hide required fields or consequences. Validate at a useful moment and retain input after failure.

## Small changes

If asked to fix an overflowing button label, inspect the existing layout and fix the overflow. Do not create personas, new navigation, a dashboard, or a full product discovery document. The workflow should scale down as readily as it scales up.
