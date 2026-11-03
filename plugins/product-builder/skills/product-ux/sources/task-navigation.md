# Make the current task and selection clear

Use this source when a screen contains competing summaries, filters, detail views, roles, or expandable tools. Visual polish does not establish that people can find the item they need. Follow the UX reference index to inspect the relevant original guidance; apply the user's preferences and the product's actual task.

## Start from the user's question

Identify what each role arrives knowing, what they want to find or do, and which information answers that question. Complete and review the real entry path for every primary role. An administrator screenshot does not demonstrate the recipient/customer experience. Make role entry understandable while preserving authorization; do not silently switch identities to make a demo easier.

Give the current decision a dominant place. Show distinguishing attributes before internal identifiers. Connect selection controls, results, and details so a user can tell what is selected without reconciling several panels. A useful flow is context → matching choices → selected item → action/detail, but do not impose the same layout on every product.

Choose a relevant initial scope from the brief and available state. Do not dump every date, category, and record into a default list merely because data exists. Preserve explicit user choices on refresh. If several matching items remain, keep them discoverable; if none match, show an honest empty state instead of silently displaying an item from another scope.

Separate the initial scope from the supported exploration scope. For each required task, establish which context axes users may change and which are true permission or product boundaries. Personalization, a current-time default, or a recommended subset must not accidentally remove required exploration. Conversely, do not invent global browsing or expose private data merely because a broader view is technically possible. Verify a concrete outcome outside the initial selection whenever the brief requires it, including a meaningful return to the user's prior context.

After a date, filter, role, or primary item changes, reconcile the selected result, detail title, status, and action target together. A separate pinned or recommended item needs a clear, deliberate identity and purpose. Avoid two similar summaries that appear to describe the same selection while actually referring to different records.

Name the event or entity that a date/status filter describes. When related events cross a boundary, distinguish their dates and offer an explicit path to the relevant result; do not silently reinterpret the user's selection.

## Choose a control, including its open state

- A small set of meaningful choices may be clearer as visible radio/segmented controls. A longer fixed set can use a select-only popup; search may help when finding an item is materially harder than scanning.
- Native controls are not inherently wrong. Consider platform behavior, accessibility, existing components, and the user's visual preference. If a branded popup is required, changing only the closed trigger's CSS does not satisfy it.
- Record the actual interaction mechanism when it matters to a requirement: platform control, existing design-system component, or custom widget. Check the rendered open mechanism against that requirement. A themed border, ARIA role, or successful programmatic value assignment cannot establish the appearance or usability of the opened control.
- Prefer an established accessible component where available. A custom control also owns keyboard navigation, commit versus cancellation, selected/disabled states, labels, popup positioning, scrolling, and focus behavior. Do not trade those away for styling or introduce a framework migration just for a small control.
- Inspect both closed and open states at real narrow/desktop viewports. Check long labels, viewport edges, scroll containers, menus inside panels, pointer selection, Arrow/Home/End keys, Enter/Space, Escape, Tab, and applicable typeahead. Verify focus and committed value separately.
- Match the declared keyboard pattern, not merely a list of handled keys. For example, the APG select-only example distinguishes exploring an active option from committing it on Tab and retaining the previous value on Escape. Closing a popup alone does not prove the expected value was committed or focus moved correctly.

## Reveal supporting work without displacing the main task

In-flow disclosure intentionally moves following content. That may be appropriate for a short explanation; it is a poor default when opening a long form or list pushes the decision, results, or next action out of place.

Choose among structured visible content, tabs, a reserved adjacent region, an overlay panel, or a dedicated page according to task length and whether the main content must remain interactive. Do not automatically turn every disclosure into a modal. A bounded secondary task may suit a panel; long multi-step work may need its own page. Keep necessary outcomes and important warnings discoverable in the main context even when their full details are elsewhere.

For a panel or dialog, define opening focus, closing/Escape behavior, return focus, scroll ownership, and what happens to input on close/reopen. Avoid stacking blocking surfaces. Closing should not silently discard work. Preserve the main page's width and scroll context; account for scrollbar changes instead of adding large blank placeholders. Small screens may need a full-height surface, but controls, errors, and overflow must remain reachable.

A read-only overflow region also needs a usable keyboard path to its offscreen content. Test scrolling to the final item; a focus trap that cycles only through Close and form buttons can strand the rest of a long list even when mouse scrolling works.

## Test the task, not only component existence

Ask a reviewer to find a concrete item from the user's starting knowledge without code or developer coaching. Record the path and whether the visible screen answers: whose context, which scope, which selected item, what status, and what next action? Test more than one role and a changed selection. This is a task walkthrough, not a claim of user research.

Exercise secondary surfaces open → input/error → close → reopen → complete. Compare the meaningful main-page anchors before/after and ensure drafts survive according to policy. Test focus visibility and intentional scrolling separately from document geometry. A menu or panel opening without horizontal overflow is not enough if it hides the selected value or loses keyboard position.

## Source basis and limits

Reviewed 2026-11-03. Resolve these source IDs through the [UX reference index](../../../references/design/ux/index.json):
- `carbon-dropdown` distinguishes stylable dropdowns, native selects, and searchable choices. Its platform and sizing advice is context-specific.
- `wai-combobox` defines combobox semantics and keyboard interaction; custom visuals do not remove those responsibilities.
- `wai-selectonly` gives a concrete exploration/commit/cancel keyboard contract. It is an illustrative example, not a production-ready component or proof of assistive-technology compatibility.
- `gov-accordion` explains the cost of hiding content and alternatives to accordion layouts. It does not prohibit every intentional expansion.
- `fluent-drawer` distinguishes inline and overlay secondary surfaces, including modality, input preservation, and overflow tradeoffs.
- `google-transit` illustrates a real sequence connecting trip context, departure choices, and selected-route details. Its transport-specific fields are an example, not requirements for other products.

The hierarchy and verification method above are this plugin's synthesis. Keep project-specific defaults, expected coordinates, data, and walkthrough results in the consuming project.
