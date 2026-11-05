---
name: start
description: Find and connect relevant sources for the current task. Use existing project references first, offer relevant default or custom sources only where needed, and apply source-local capabilities after reference entry. Does not prescribe a product workflow or install domain skills.
---

# Project Builder reference entry

Read the package reference index and bootstrap its governance source with the packaged `scripts/references.py` helper. Use the caller's chosen receipt location from this first operation. For `store://` receipts, pass the supplied `--store-config` and an explicit `--scope` for this access context. Profile loading is runtime connection setup and does not require a preliminary local trace. Then resolve `usage` / `entry` and `source-contract` for the current connection workflow. This is the only globally exposed skill in the package.

```sh
python3 <plugin-root>/scripts/references.py read --index <plugin-root>/references/governance/index.json --id routing-policy --trace <chosen-trace-location>
```

Start from the user's task and existing project connections. Default sources are suggestions, not dependencies. Do not fetch their bodies, clone them, install their capabilities, or select them before the user chooses a relevant connection. Preserve existing choices and authorization. Source skills are read contextually through their owning references; they are never added to the global skill list by this client.

For source or project-record creation, apply the source contract's content-organization requirements even when the caller chooses general mode. Methodology selection does not remove the common participation contract.

Reference registries, connection choices and receipts may each live in the user's local or remote store. A local trace path is a default only when no receipt destination was selected; report that location. Never fall back to a local receipt file when the selected remote store fails. For storage, sharing, or database setup, resolve `storage` / `guide` from the package reference index. Reuse the selected store and access context; do not silently copy shared records into a new local authority or change permissions. Team members may review shared receipts, while each caller records their own source access in a separate context/trace key.
