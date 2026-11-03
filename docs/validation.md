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

The package validator checks the five skill entry points, metadata-only reference indexes, local source locations, source Markdown links, the explicit distributable-file allowlist, and publication boundaries. Unit tests exercise file preservation, invalid registration, symlinks, reference receipts, cycles, moved installations, consumer-local registries, and archive exclusion.

The common UX example has browser regression coverage at actual desktop and narrow viewports. Its thresholds apply to that example's expected stable elements; they are not universal layout rules.

## Public repository boundary

Generic harness self-improvement methods, input preparers, model runners, and their own regression tests are public development tools. `scripts/prepare_eval.py` accepts a consumer-owned raw-input directory; `scripts/run_eval.py` executes it and records outcomes locally. Neither includes a task catalogue or custom grader.

Specific briefs, datasets, rubrics, generated apps, answers, traces, results, and project bindings stay in the consuming project or ignored `.local/`. This distinction is about task dependency, not a folder's name. The common UX example is an explicitly designated reusable teaching asset.

`publication-files.json` lists reviewed public repository files; the installation package has its own narrower allowlist. New public files require explicit inventory review. The validator checks Git-index membership as well as unignored files; removing a worktree copy does not make an indexed private file safe to publish. The inventory detects unexpected files but cannot determine whether their contents are task-specific. Review actual staged content before publication.

## Evidence boundaries

A reference trace audit validates recorded transitions; it cannot prove that an agent made no unrecorded reads. Markdown link checks do not interpret arbitrary prose or inline commands. Review actual tool use as well as the trace.

Model behavior is evaluated separately in local development work using the target GPT-6.1 Sol / High configuration. Dispatch configuration is not independent provider attestation of the serving model. A repaired example and a new-context run are different evidence; an earlier failed attempt stays failed.

Release notes identify the published commit and observed package, regression, CI, and installation results. Task-specific tooling and evidence remain local; generic improvement tooling stays public. Finite evaluations do not establish universal compliance, user research, live integration, deployment, or stakeholder acceptance.
