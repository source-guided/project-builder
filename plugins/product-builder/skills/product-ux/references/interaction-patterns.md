# Choose the interaction surface

The decision depends on the task. A layout shift does not automatically justify a modal, and avoiding modals does not justify forcing every workflow into inline fields.

| Pattern | Useful when | Review tradeoff |
| --- | --- | --- |
| Inline editing | A small local change should preserve the surrounding reading/review context | Match read/edit geometry where practical; make save/cancel and draft state clear |
| Dedicated editing area/page | Editing is the primary task, content is long, or multiple dependent steps need room | Preserve prior input and provide a clear return path and unsaved-work behavior |
| Modal dialog | A short focused interruption is justified by a decision or required input | Background is blocked; manage focus, cancellation, and recovery; avoid nested/repeated dialogs |

An adjacent panel is another option when the task needs both context and editing space, but narrow screens and keyboard navigation must be designed explicitly. No pattern is automatically better because it looks tidy in one screenshot.

## Preserve useful spatial continuity

For mode changes such as read → edit → cancel/error/save:
- Identify elements expected to remain stable: title, surrounding content, decision controls, scroll position, and the return-focus target.
- Compare actual rectangles and screenshots before and after the action at relevant real viewport sizes. Use a tolerance appropriate to the component; do not impose one pixel threshold on all products.
- Account for controls/help/error messages and scrollbar appearance. Reserve a justified local slot or match read/edit dimensions, without creating excessive blank space.
- Keep long and translated content accessible. A fixed frame must support scrolling or another explicit expansion path; do not hide overflow merely to make a test pass. Check text enlargement and keyboard behavior.
- Distinguish intentional expansion, navigation, and newly saved content from incidental movement that makes users lose their place. Focus should move to the relevant control and return meaningfully; do not suppress necessary focus visibility to preserve scroll numerically.

Do not use CLS alone as the acceptance criterion for an interaction. Shifts shortly after discrete input can be excluded from that metric even when an edit button pushes another action away. Test the user's actual transition in addition to load metrics.

## Source basis and limits

Reviewed 2026-11-03. These references inform pattern selection; the geometry checklist above is this plugin's practical review method, not a claim that the sources mandate one layout.

- [Atlassian inline editable text field](https://atlassian.design/components/inline-edit/inline-editable-textfield/usage): supports switching between reading and editing on one page, matching custom read/edit sizing, and using a dedicated text area when editing is the screen's main purpose.
- [Carbon modal guidelines](https://www.carbondesignsystem.com/building-blocks/core/components/modal/guidelines): modals interrupt the main workflow; use them sparingly, and consider keeping repeated tasks on the main page.
- [NN/g modal and nonmodal dialogs](https://www.nngroup.com/articles/modal-nonmodal-dialog/): describes interruption/context costs and circumstances that justify dialogs; complex multi-step work may deserve a full page.
- [web.dev CLS](https://web.dev/articles/cls): explains expected versus unexpected shifts and the recent-input exclusion window. A good CLS score is not proof that an interaction has good spatial continuity.
