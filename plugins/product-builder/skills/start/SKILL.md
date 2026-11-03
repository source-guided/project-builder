---
name: start
description: Deliver or resume a product task from a brief, README, specification, or existing repository, coordinating requirements, task-focused UX, implementation, and evidence. Use for end-to-end work; keep small fixes small.
---

# Product Builder

Use the user's language. Adapt to the task, available time, existing owner rules, tools, and artifacts. This workflow is not a fixed page generator or an approval process.

## Enter or resume

1. Read repository instructions and the provided brief before choosing a stack. Inspect the actual working tree and runnable entry point. Preserve existing work.
2. Look for the project's existing decisions and task state. If none exists, use the compact [work record](assets/work-record.md) in a user-authorized project-local location. For sensitive task records prefer ignored `.local/product-builder/`; the [initializer](scripts/init_context.py) prepares this without overwriting existing files. Read task sources there only when relevant; never copy their contents to the public plugin.
3. Read [brief analysis](../brief/SKILL.md) to distinguish deliverable requirements, constraints, evaluation evidence, and unknowns. Read the full product and delivery context rather than treating a single message as the complete contract.
4. Confirm the smallest runnable path early. Separate environment failure from product failure. If a tool is unavailable, use an available supported path or report the exact unverified layer; do not block unrelated work.

## Execute

- For UI work, read [product UX](../product-ux/SKILL.md) before selecting screens. For a CLI, API, batch process, or a narrow edit, skip irrelevant UI work.
- Read [implementation](../implementation/SKILL.md) for the next end-to-end slice, then [verification](../verification/SKILL.md) to check observable outcomes. Repeat only for new changes, failures, or remaining uncertainty.
- Use the user's requested model and reasoning effort. This package's target validation profile is **GPT-6.1 Sol / high**. It does not change model configuration, require a stronger model, or require parallel agents. If the current model or effort cannot be verified, say so; do not claim a switch.
- Ask only for missing decisions that materially alter the result and cannot be resolved from sources. Continue independent work. Existing authorization persists; routine phases do not need separate approvals.
- Keep planning proportional. Reserve time for verification and delivery, and trim optional scope when needed. Do not spend the time budget producing documents instead of working software.
- At meaningful milestones, update the work record with decisions, changed files, evidence, remaining work, and the next action. Do not duplicate existing authoritative documents.

## Complete

Link each required result to implementation and evidence. State passed, failed, not run, and blocked layers separately. Read the actual delivery contract before packaging or handing off; do not submit or publish externally unless authorized. Summarize the important choices and limitations so the user can explain their own work. In a new session, verify the current files and state before resuming; stale claims are not fresh evidence.
