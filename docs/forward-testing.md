# Fresh-context workflow validation

A repaired example demonstrates that the repair works. To evaluate a reusable workflow, also test whether a new agent applies it to an unseen task.

1. Freeze a package snapshot and record its hash, requested model, and effort.
2. Preserve existing outputs as a baseline. Create a new empty work directory; do not delete unrelated user work.
3. Supply only the user's raw brief/data and the plugin package. For from-scratch cases, do not supply starter implementation, previous screenshots, fixes, or expected answers.
4. Dispatch a fresh GPT-6.1 Sol / High context. Keep evaluator criteria and previous conversation outside its supplied context. This is logical separation unless an actual OS sandbox enforces read access.
5. Observe the chosen workflow, code, rendered product, failures, and verification claims. Review actual outcomes independently, using criteria derived from the brief and the workflow's intended behavior.
6. Separate implementation failure, verification failure, missing tool access, and missing requirements. Do not promote a claimed pass without supporting evidence.
7. If an issue is found, fix the narrow general decision criterion, recheck the affected case, and use another fresh task when a generalization claim needs evidence. Do not accumulate one universal prohibition per example.

Use distinct domains and interaction shapes. A UI case should examine information relevance, justified inline/dialog/page choice, editing/error/cancel transitions, keyboard/accessibility, and data semantics. A non-UI case should not acquire a dashboard or unnecessary persistence. Keep task-specific numbers and business rules in fixtures, not in skills.

Finite cases provide observed evidence, not proof of universal compliance. Report task coverage and limits. A sample that ships inside the plugin is a reference, not a held-out answer; use a different task when testing transfer.
