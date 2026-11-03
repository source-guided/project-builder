---
name: start
description: Find and connect relevant sources for the current task. Use existing project references first, offer relevant default or custom sources only where needed, and apply source-local capabilities after reference entry. Does not prescribe a product workflow or install domain skills.
---

# Project Builder reference entry

Read the package reference index and bootstrap its governance source with the packaged `scripts/references.py` helper. Then resolve `usage` / `entry` and `source-contract` for the current connection workflow. This is the only globally exposed skill in the package.

```sh
python3 <plugin-root>/scripts/references.py read --index <plugin-root>/references/governance/index.json --id routing-policy --trace <project>/.local/project-builder/session.jsonl
```

Start from the user's task and existing project connections. Default sources are suggestions, not dependencies. Do not fetch their bodies, clone them, install their capabilities, or select them before the user chooses a relevant connection. Preserve existing choices and authorization. Source skills are read contextually through their owning references; they are never added to the global skill list by this client.

Reference registries and connection choices may live in the user's local or remote store. `.local` above is an example for a session trace, not a requirement for data or references. For storage, sharing, or database setup, resolve `storage` / `guide` from the package reference index. Reuse the selected store and access context; do not silently copy a shared registry into a new local authority or change its permissions.
