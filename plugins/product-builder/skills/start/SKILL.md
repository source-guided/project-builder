---
name: start
description: Find and connect relevant requirements, designs, contracts, code, and prior decisions as product work develops or resumes. Select the needed brief, UX, implementation, or verification workflow from the current task; keep narrow work narrow.
---

# start

Read the package [reference index](../../references/index.json), follow its governance reference, and apply that source throughout the task. This also applies when improving this harness. The governing rule is owned there, not duplicated here.

Then select `delivery` / `start` through the reference graph to find this capability's actual workflow. Route from the user's intent and relevant metadata, including horizontal links and the consuming project's own registry. The user should not need to enumerate skills or source paths.

The package root is two directories above this skill folder. Bootstrap the mandatory source using the packaged helper:

```sh
python3 <plugin-root>/scripts/references.py read --index <plugin-root>/references/governance/index.json --id routing-policy --trace <project>/.local/product-builder/session-v2.jsonl
```

Use `discover` / `resolve` for stateless metadata lookup. For source access use `prepare-read` → appropriate reader → `record`, or `read` for local text; `read-many` supports independent local reads. The governance source owns session, maintenance, and audit details. Find the project initializer through the delivery reference if a consumer registry is missing, then follow the selected workflow.
