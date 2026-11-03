# Feedback and action continuity

Choose feedback from the user's task, affected object, urgency, and need to act. A completed event is not automatically persistent page state. Follow the UX reference index to inspect relevant first-party guidance; keep product-specific choices in the consuming project.

## Choose scope and lifetime together

| Situation | Candidate treatment | Lifetime and recovery |
| --- | --- | --- |
| Simple local completion already visible in the result | Updated content and meaningful focus return; additional notification may be unnecessary | Do not leave a historical success/cancel sentence as current page state |
| Confirmation needed but outcome is not obvious | Concise contextual status near the affected item or action; a toast only if appropriate to the product | Define dismissal or expiry, clear on a new context/action, and retain essential information elsewhere |
| Invalid input or failed save | Field error and, if needed, local form summary | Preserve draft; keep useful error information until correction, retry, or dismissal where appropriate |
| Continuing condition such as read-only state or unavailable service | Persistent message within the affected scope | Remove only when the condition ends; never expire an actionable error merely to remove clutter |
| Long-running or high-consequence operation | Progress and durable outcome/recovery surface | Make completion and next steps discoverable beyond a short timer |

Cancellation usually returns to the prior state. If that return is evident, do not add an unrelated page-top message or require a toast. Provide any necessary assistive announcement without stealing focus or leaving stale feedback attached to a different record. Destructive cancellation may require a separate loss-of-work decision based on the product's draft policy.

If temporary feedback is chosen, specify its owning item/action, clearing conditions, accessible announcement, and behavior when another action happens before expiry. A previous timer must not clear a newer message. Do not make a short-lived notification the only location of an error, required action, or important result. Test both appearance and removal; a screenshot taken immediately after the click is insufficient.

## Choose an action region across the whole transition

Before implementation, map read → edit → validation error → save/cancel back to read. Identify where users find the entry action, commit action, exit action, and returned focus.

- Small in-place edits can replace Edit with Save/Cancel in the same local action region. Preserve the region's anchor, field labels, and text origins; do not append a new footer by accident.
- Dedicated forms often place actions after the fields. A page transition or an intentionally different editing surface may justify a different position; explain it through the structure and return path.
- Long forms may need a consistently reachable action area. Sticky controls must not cover content, errors, or focused fields at narrow widths and zoom.
- Select ordering and emphasis from the established design system and user direction. Do not impose one universal left/right order or top/bottom position.
- Validate the action region itself, not only card boundaries or an unchanged sibling. Use semantic correspondence between Edit and the editing controls. Extra controls may occupy adjacent space; they should not make the user search a distant part of the page.

## Behavioral checks for the consuming project

1. Reproduce success, cancel, invalid save, recovery, repeated actions, and object switching at actual desktop/narrow viewports.
2. Assert the chosen action region's document position and local alignment across modes; check visible keyboard focus separately from intentional scroll.
3. Inspect the affected fields' glyph origin, labels, and surrounding content. Match relevant font/padding metrics and allow intended content growth.
4. Verify local feedback refers to the current object, clears by its declared lifecycle, and does not shift unrelated content. For a no-extra-feedback decision, verify result/focus and absence of stale event text.
5. Check accessible roles/descriptions and input preservation. Do not hide persistent errors to pass a layout test.

## Source basis and differences

Reviewed 2026-11-03. Resolve these IDs through the [UX reference index](../../../references/design/ux/index.json) before opening each source.

- `primer-feedback`: simple visible outcomes may need no secondary success message; discusses proximity and accessibility costs of toasts.
- `carbon-notification`: separates contextual inline messages, transient notifications, and persistent callouts; actionable information needs sufficient time and access.
- `gov-banner`: reserves page-level banners for their appropriate scope and recommends in-content placement for information directly related to the current task.
- `sap-partial-edit`: the v1.96 partial-edit pattern replaces section Edit with Save/Cancel. Its cancellation policy is specific to that system, not a universal confirmation requirement.
- `carbon-forms`: form actions depend on layout and task progression; dedicated forms differ from compact partial editing.

These sources differ by context. The transition map and lifecycle checks are this plugin's synthesis, not a claim that any one source requires the same geometry or timeout everywhere.
