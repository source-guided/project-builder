---
name: implementation
description: Implement a product task as observable end-to-end slices with clear contracts, state transitions, and decision evidence. Use for meaningful feature work; respect existing architecture and avoid process overhead for small edits.
---

# Build a working slice

Read the current brief, relevant owner rules, and the actual implementation. Fit the existing architecture. Do not impose this plugin's internal file layout on the product.

## Choose the next slice

Select the smallest useful path from real input to an observable result. Include persistence, export, permissions, or restart behavior when the brief requires them. A collection of static pages is not proof of a working flow.

Before changing code, identify:
- Input and output contracts, including invalid values and units.
- State ownership and the event that changes it.
- A calculation or policy choice, alternatives, and limits if relevant.
- Failure behavior and which existing state must be preserved.
- The test or observation that will establish completion.

Implement with the project's API/adapter/domain/state/UI boundaries. Use a bounded provisional contract only where the project allows it and record the integration delta. Do not present mocks as real integration or developer backlog as customer-facing error policy.

## Correctness and change

Separate hard constraints from optimization goals. If choosing a heuristic, explain why and what it does not guarantee; do not claim optimality without proof. Preserve data lineage where changing inputs can make results stale.

Consider duplicate actions, concurrent edits, retry behavior, partial failure, and restart only to the depth the task warrants. A single intended operator does not rule out duplicate tabs or requests. UI disabling alone does not establish server-side concurrency safety. Do not build queues or distributed infrastructure without a requirement or measured need.

For a defect, establish the failing condition before accepting a proposed fix. Re-run the reproducer afterward. Record actual AI suggestions and the user's decisions where collaboration evidence is requested; do not invent a rejection to make a narrative complete.

## Hand off to verification

Record the meaningful decision and implementation location, then use [verification](../verification/SKILL.md). Update existing project records rather than accumulating parallel reports. Keep authoring claims, test output, real integration, deployment, and stakeholder acceptance distinct.
