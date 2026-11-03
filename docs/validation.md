# Validation record

Target: GPT-6.1 Sol, reasoning effort **high**. This record separates package checks, model behavior, and product execution. Initial exploratory runs without explicit High are not final qualification evidence.

## Reproduction

Run the static package checks and unit tests in the root README. Prepare a new scenario with `scripts/prepare_eval.py`; select GPT-6.1 Sol / High explicitly in a compatible app agent. Do not supply evaluator criteria or previous outputs to the implementing agent. Use a separate copied package and fresh project directory for each run. This is logical separation, not enforced filesystem read isolation.

The optional CLI runner requests the same model and effort and saves execution receipts. In the tested ChatGPT-account CLI, the model identifier was rejected. That failure is not a product failure or a successful model evaluation. No alternate model or lower effort is substituted.

## Evidence boundaries

- Package validation checks structure, local links, basic identity, and publication boundaries.
- Unit tests check file preservation, symlink refusal, and deterministic archive exclusion.
- Behavioral cases inspect artifacts, actual execution, and consistency with the user request.
- Browser checks cover the rendered states actually exercised; they do not establish a user study.
- Review a new release after material workflow changes; prior checks may be invalidated.

## 2026-11-03 release qualification

Model behavior runs were dispatched through the app agent API with `model=gpt-6.1-sol` and `reasoning_effort=high` explicitly specified. The agents could not independently introspect the serving model; this records the dispatch configuration, not a separate provider attestation. Earlier runs without explicit High are excluded.

| Case | Observed result | Scope / limitation |
| --- | --- | --- |
| Reservation design | Supplied criteria and export contract traced; role-specific task flow; informal timing comment not promoted into an approval requirement | Design-only request respected; no service or runtime pass claimed |
| CSV reconciliation | Executable standard-library CLI; 10 generated tests passed; parent independently ran 20 checks including precision, invalid inputs on both sides, and preservation of previous output | No large-volume or power-loss durability claim |
| Document review UX | Irrelevant metrics removed; revision-scoped decisions and edit recovery exercised; desktop and narrow rendering checked | First narrow screenshot failed review and its pass claim was withdrawn; corrected evidence and independent actual-viewport Chromium checks support the final result. Screen reader and user study not run |
| Narrow resume fix | Current zero-versus-missing defect reproduced and corrected; parent independently checked zero, None, positive values, and preserved unrelated note | No unrelated architecture work or deployment |
| Private project-context analysis | Required source categories, provenance, and missing contracts remained distinct; observed example values were not treated as global limits | Document analysis only; private inputs and output are not distributed; not proof of original source completeness |

Package checks: portable manifest validated against the published schema; all five skills passed the skill-authoring validator; internal references passed. **12 unit tests** cover initializer preservation, ignore-rule edge cases, symlinks, explicit archive file lists, and fresh evaluation preparation. Local Codex CLI 0.153.4 successfully installed the package; the release notes record the final remote-source installation and CI results.

## Findings corrected before release

- The local-record initializer previously mistook a comment or negation ending in `/.local/` for an ignore rule. Exact rule matching and regression tests now cover this. An independent review checked actual `git check-ignore` outcomes.
- Initial archive collection accepted unlisted ordinary files. `package-files.json` now explicitly enumerates every distributable file; unexpected, missing, private, or escaping paths fail validation.
- Initial responsive evidence did not support its pass claim. The claim was invalidated, the actual viewport was measured, and screenshots were reopened and independently checked. The UX skill now explicitly rejects crop/element-width substitutes for viewport verification.
- User interaction exposed a second issue: entering edit mode moved the review region by about 205px and changed its width by 15px at the observed viewport. The Korean demo now uses a stable inline content frame and action/error slots. The design choice follows the linked interaction-pattern references rather than making modals a default. **12 Playwright tests** across actual 1280, 618, 375, and 320px viewports now check edit/error/cancel geometry, scroll/focus, native keyboard order, long-content accessibility, and revision semantics. These pass locally and are included in CI. The 1px tolerance is specific to this example's expected stable anchors, not a universal product rule.

The final package adds the verified synthetic UI example and the above evidence/packaging safeguards to the evaluated workflow. Deterministic fixes were regression-tested; no unrelated model case was rerun merely to inflate counts. This finite scenario set demonstrates these observed behaviors, not universal reliability.
