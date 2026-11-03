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

Carry material product decisions into the slice's verification, including applicable user preferences and interaction tradeoffs. If implementation constraints change a decision, revise the decision and its check together. Do not keep an earlier rationale or completed checkbox after implementing a different behavior.

Implement with the project's API/adapter/domain/state/UI boundaries. Use a bounded provisional contract only where the project allows it and record the integration delta. Do not present mocks as real integration or developer backlog as customer-facing error policy.

## Correctness and change

Separate hard constraints from optimization goals. If choosing a heuristic, explain why and what it does not guarantee; do not claim optimality without proof. Preserve data lineage where changing inputs can make results stale.

At a format or calculation boundary, compare the chosen parser, serializer, numeric representation, and runtime defaults with the adopted contract before relying on them. A permissive parser or a setting named strict is not proof of contract validation. Own required validation and normalization in the appropriate boundary module; do not make downstream policy depend on accidental library behavior. Where behavior varies across supported environments, choose a compatible implementation or an explicitly supported environment with its actual requirements and limits.

Keep resource controls deliberate and proportionate. Do not disable all limits merely to satisfy an extreme case, or add an arbitrary cap because it is a library default. If the feasible implementation still excludes required inputs, report the gap and its impact separately from completed behavior; documenting that exclusion in a runbook does not resolve it.

Consider duplicate actions, concurrent edits, retry behavior, partial failure, and restart only to the depth the task warrants. A single intended operator does not rule out duplicate tabs or requests. UI disabling alone does not establish server-side concurrency safety. Do not build queues or distributed infrastructure without a requirement or measured need.

For a defect, establish the failing condition before accepting a proposed fix. Re-run the reproducer afterward. Record actual AI suggestions and the user's decisions where collaboration evidence is requested; do not invent a rejection to make a narrative complete.

## Hand off to verification

Record the meaningful decision and implementation location, then use [verification — reference](../../../references/delivery/index.json). Update existing project records rather than accumulating parallel reports. Keep authoring claims, test output, real integration, deployment, and stakeholder acceptance distinct.
