# Project Builder reference client

- Start through `plugins/project-builder/references/index.json` and its governance source. The source participation contract is reached through `usage` / `source-contract`.
- This repository owns reference entry, selection, metadata, transport/session tools and their generic validation. Domain instructions and examples live in independent source repositories and must not re-enter this package.
- Only `skills/start` is globally exposed. Source-local capabilities are discovered after reference entry, never installed automatically.
- Model, effort and task time belong to the caller. Use existing project connections and ask only about missing material choices. Default/custom/general are all supported authoring choices.
- Preserve user work and keep private bindings, test tasks and outputs under ignored `.local/`.
- Validate with `python3 scripts/validate.py` and `python3 -m unittest discover -s tests -v`. Validate connected source repositories with `scripts/validate_source.py`; domain-specific checks stay with their owner.
- After changing the decision workflow, use a fresh context to verify relevant source selection behavior. Keep prior answers out of its supplied context. Do not impose model selection in this repository.
- Package with `scripts/package.py`; it must not read or depend on neighboring source repositories.
