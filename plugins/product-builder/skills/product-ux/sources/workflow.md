# Task-focused product UX

Start with the user's situation and intended outcome. Existing design systems, research, and supplied designs are evidence; do not replace them with a generic dashboard. Read [patterns and counterexamples — reference](../../../references/design/ux/index.json) for the relevant type of task, not every pattern.

For a new UI direction or a request for broader references, follow the design/UI reference `selection`, then choose relevant sources from the UI, UX, and project-local reference branches. Existing user preferences take priority over a generic style. Compare viable alternatives when a material preference is unknown; do not make a new approval gate or ask again after a direction was chosen.

## Before building a screen

For each primary role/task, identify the trigger, information already known, decisions to make, completion outcome, and recovery path. Separate role-specific workflows when their decisions differ; share screens when the task and context genuinely match.

Produce a compact flow and low-fidelity layout proportional to the change. For each visible region state:
- Which user decision or action needs it now?
- Is it primary, contextual detail, or unnecessary in this view?
- Which requirement, source, or explicit design decision justifies it?

Use this to select information, not to generate more product copy. Do not automatically add overview cards, charts, banners, filters, navigation, AI explanations, or “coming soon” panels. A metric belongs when someone makes a relevant decision with it. Technical provenance can belong when needed to judge freshness or validity; debug logs and implementation status usually belong in development records.

Do not minimize blindly. Keep accessibility instructions, meaningful errors, essential context, required disclosures, and decision consequences. A primary action is a useful default, not an arbitrary one-button limit. Avoid hiding important actions behind generic menus solely to reduce visible controls.

## State and interaction

Model relevant states: initial, loading, empty, failure, success, editing/unsaved, stale result, and permission constraints. Use only states the product needs. Make selected inputs and displayed results refer to the same context. Preserve the user's work on recoverable errors. Choose explicit actions where silent changes would surprise the user.

For feedback and edit actions, resolve `feedback-actions` in the [UX reference index](../../../references/design/ux/index.json). Choose message scope and lifetime together, map the action region through the full transition, and test removal as well as appearance. A page-top persistent sentence is not the default for a completed local action; neither is a toast mandatory.

When selecting an editing surface or changing stateful layouts, read [interaction pattern selection — reference](../../../references/design/ux/index.json). Choose inline editing, a dialog, or a dedicated page from task complexity, frequency, context needs, and available space; do not use a modal simply to hide a layout bug. Check before/after position, scroll, and focus of meaningful controls. Intentional disclosure may move content; incidental jumps or disappearing targets need correction.

Use the project's tokens, components, language, and accessibility conventions. Inspect a supplied reference through an available supported tool; missing Figma MCP is not by itself a reason to stop. Never label an uninspected design as matched. Do not introduce a new component library merely for a small change.

Check accessible names and descriptions across valid/error/recovered states, not only visual visibility and focus. A hidden message can still be exposed when referenced by an accessible description; connect error text only when the error applies.

## Review the rendered flow

Use an available browser or application tool to perform the task from its actual entry point. Inspect structure for labels and controls, and rendered screenshots for hierarchy, clipping, spacing, and visual states. Automated accessibility or DOM checks alone do not prove visual or usability quality.

For responsive checks, confirm the browser's actual viewport dimensions and inspect the final captured image. Cropping a screenshot, changing an element's width, or checking horizontal overflow alone is not an equivalent viewport test. If the tool cannot set or verify the viewport, mark that coverage unverified. Reconcile the screenshot with the reported result: missing content, unusable wrapping, or invisible actions cannot be called a visual pass merely because a DOM check passed.

For each finding record: reproduction → observed behavior → user impact → smallest useful correction → recheck. Label inference separately from observation. Prefer removing, moving, consolidating, or improving defaults before adding explanations. Do not repeat a passed review unless changes or remaining concerns justify it.

If browser access is unavailable, review code/layout evidence and mark runtime UX unverified; continue independent work. Do not fabricate screenshots, clicks, or user validation. The developer's or agent's review is not a user study.
