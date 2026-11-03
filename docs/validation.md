# Plugin validation

## Reproduce package checks

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm run test:ui
python3 scripts/package.py
```

The package validator checks the five skill entry points, metadata-only reference indexes, local source locations, source Markdown links, the explicit distributable-file allowlist, and publication boundaries. Unit tests exercise file preservation, invalid registration, symlinks, independent/concurrent receipts, partial failures, bounded discovery, HTTP index access boundaries, metadata maintenance conflicts, cache invalidation, moved installations, execution provenance (fresh outputs and executable permissions), consumer-local registries, and archive exclusion.

The common UX example has browser regression coverage at actual desktop and narrow viewports. Its thresholds apply to that example's expected stable elements; they are not universal layout rules.

## Public repository boundary

Generic harness self-improvement methods, input preparers, model runners, and their own regression tests are public development tools. `scripts/prepare_eval.py` accepts consumer-owned input and optional user clarifications, preserving their provenance separately from evaluator material. `scripts/run_eval.py --review` separates implementation execution from a fresh reviewer. `scripts/review_eval.py` prepares an unchanged first artifact and delegates report checking to `evaluation_report.py`; `evaluation_execution.py` captures the actual exercised revision, command and evidence. None includes a task catalogue, product quality score, or custom grader.

Specific briefs, datasets, rubrics, generated apps, answers, traces, results, and project bindings stay in the consuming project or ignored `.local/`. This distinction is about task dependency, not a folder's name. The common UX example is an explicitly designated reusable teaching asset.

`publication-files.json` lists reviewed public repository files; the installation package has its own narrower allowlist. New public files require explicit inventory review. The validator checks Git-index membership as well as unignored files; removing a worktree copy does not make an indexed private file safe to publish. The inventory detects unexpected files but cannot determine whether their contents are task-specific. Review actual staged content before publication.

## Evidence boundaries

A reference trace audit validates recorded transitions; it cannot prove that an agent made no unrecorded reads. Markdown link checks do not interpret arbitrary prose or inline commands. Review actual tool use as well as the trace.

Independent-review validation checks source/evidence ownership and captured execution provenance, not truth or coverage completeness. Required behavior with no executable evidence remains unverified; successful process exit does not override it. The baseline protects input, artifact, plugin, harness and report contract. Reproduction uses an unchanged runtime source copy with mutable state/results outside that tree; repairing that copy invalidates its execution evidence.

`evaluation_inputs.py` owns test-input tracking. Standalone file arguments, including relative paths, are resolved against the recorded execution working directory. Review-local scripts outside `runtime/` are hashed and checked again with their original path binding; changed symlink targets cannot reuse an earlier input hash. Use `--test-input <review-relative-file>` for indirect dependencies, files read by inline code, or paths embedded in tool-specific options. Automatic argument inspection does not parse arbitrary shell/program semantics.

`evaluation_process.py` owns process-group lifetime for implementation, independent review, and evidence capture. It ends remaining group members before returning on normal completion or timeout, so completion snapshots and evidence hashing happen after cleanup. This adapter currently supports POSIX process groups; other operating systems fail explicitly before starting a process. Processes that deliberately detach into another session are outside this lifecycle boundary; it is not an OS security containment mechanism.

Model behavior is evaluated separately in local development work using the caller's selected configuration. No specific model or effort is required by the package; execution records distinguish explicit arguments from inherited CLI configuration. Dispatch configuration is not independent provider attestation of the serving model. A repaired example and a new-context run are different evidence; an earlier failed attempt stays failed.

Release notes identify the published commit and observed package, regression, CI, and installation results. Task-specific tooling and evidence remain local; generic improvement tooling stays public. Finite evaluations do not establish universal compliance, user research, live integration, deployment, or stakeholder acceptance.

For the native CLI path, also exercise execution capture under the installed Codex workspace sandbox without a model call. Unit mocks alone do not establish write permissions. Record the local CLI version and distinguish this test from a successful model-backed run.
