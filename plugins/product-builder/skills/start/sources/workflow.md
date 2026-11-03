# Product Builder

Use the user's language. Adapt to the current task, existing owner rules, tools, artifacts, and constraints the user actually supplied. There is no default deadline or required sequence of all skills.

## Enter or resume

1. Read repository instructions and the provided brief before choosing a stack. Inspect the actual working tree and runnable entry point. Preserve existing work.
2. Look for the project's existing decisions and task state. If none exists, use the compact [work record — reference](../../../references/delivery/index.json) in a user-authorized project-local location. For sensitive task records prefer ignored `.local/product-builder/`; the [initializer — reference](../../../references/delivery/index.json) prepares this without overwriting existing files. Read task sources there only when relevant; never copy their contents to the public plugin.
3. Read [brief analysis — reference](../../../references/delivery/index.json) to distinguish deliverable requirements, constraints, evaluation evidence, and unknowns. Read the full product and delivery context rather than treating a single message as the complete contract.
   Reconcile current user clarifications and preferences before delegating or resuming. Preserve their source and scope in the handoff; separate them from prior implementation answers and evaluator-only material.
4. Confirm the smallest runnable path early. Separate environment failure from product failure. If a tool is unavailable, use an available supported path or report the exact unverified layer; do not block unrelated work.

Reference discovery continues throughout the work. When a new question, dependency, changed source, or resumed decision becomes relevant, return through its references and select only the needed capability. Recheck stale context without restarting completed phases or reading every source. A source lookup or comparison can be the whole task; it need not trigger implementation.

## Execute

- For UI work, resolve `workflow` in [product UX — reference](../../../references/design/ux/index.json) before selecting screens. For a CLI, API, batch process, or a narrow edit, skip irrelevant UI work.
- Read [implementation — reference](../../../references/delivery/index.json) for the next end-to-end slice, then [verification — reference](../../../references/delivery/index.json) to check observable outcomes. Repeat only for new changes, failures, or remaining uncertainty.
- Model and reasoning effort belong to the caller's execution environment. Do not choose or change them on behalf of this package, or require a particular model, stronger effort, or parallel agents. Report configuration uncertainty only when it matters to the current task or evaluation claim.
- Ask only for missing decisions that materially alter the result and cannot be resolved from sources. Continue independent work. Existing authorization persists; routine phases do not need separate approvals.
- Keep planning proportional to the work. Apply a time budget only when the user supplies one; otherwise preserve continuity through decisions, verified state, and remaining work rather than inventing a deadline.
- At meaningful milestones, update the work record with decisions, changed files, evidence, remaining work, and the next action. Do not duplicate existing authoritative documents.

## Complete

Link each required result to implementation and evidence. State passed, failed, not run, and blocked layers separately. Read the actual delivery contract before packaging or handing off; do not submit or publish externally unless authorized. Summarize the important choices and limitations so the user can explain their own work. In a new session, verify the current files and state before resuming; stale claims are not fresh evidence.
