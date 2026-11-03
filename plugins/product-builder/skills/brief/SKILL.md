---
name: brief
description: Analyze a project brief, README, data contracts, workflow rules, and acceptance criteria into sourced requirements and verification priorities. Use before substantial implementation or when scope changes; do not invent success criteria.
---

# brief

Read the package [reference index](../../references/index.json), follow its governance reference, and apply that source throughout the task. This also applies when improving this harness. The governing rule is owned there, not duplicated here.

Then select `delivery` / `brief` through the reference graph to find this capability's actual workflow. Route from the user's intent and relevant metadata, including horizontal links and the consuming project's own registry. The user should not need to enumerate skills or source paths.

The package root is two directories above this skill folder. Bootstrap the mandatory source using the packaged helper:

```sh
python3 <plugin-root>/scripts/references.py read --index <plugin-root>/references/governance/index.json --id routing-policy --trace <project>/.local/product-builder/source-trace.jsonl
```

Use `list` for metadata; use `resolve` → appropriate reader → `record` for each source, or `read` for text files. Find the project initializer through the delivery reference if a consumer registry is missing. Follow the selected source workflow, then audit the recorded traversal.
