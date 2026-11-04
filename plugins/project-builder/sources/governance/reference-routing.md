# Reference routing — governing source

This is the authoritative routing rule for this harness. It governs normal product work and improvements to the harness itself. Do not weaken it as a routine optimization, convenience shortcut, or response to a single example. A change to this invariant requires explicit direction from the user who owns the harness.

## Mandatory navigation

Every knowledge-source access must be mediated by a reference:

Each access follows `request → reference → source`. Independent branches may proceed in parallel; a newly discovered dependency returns through a reference before its source is read.

Never navigate directly from source A to source B. A link discovered inside a source is a candidate location, not permission to skip reference lookup. Locate an existing reference or register the observed location in the consuming project's reference registry before accessing it. This also applies to horizontal movement across design, frontend, API, project, and version domains.

Reference folders organize navigation; they are not a fixed execution sequence. Select branches using the user's intent and reference topics. Follow relevant horizontal relationships as new needs emerge. Track visited references and sources, stop cycles and unnecessary repeated reads, and stop exploring when the task's material context is resolved. Do not fetch every branch.

## Reference versus source

References contain navigation metadata: identifier, label, optional discovery description, topics, target kind, location, access method, and related references. They do not contain copied requirements, rules, answers, source bodies, or authoritative owner/version values. Relevance indicates a discovery match, not authority, freshness, or a business-policy priority.

Version and ownership information must be obtained from their own sources through a reference, such as the package manifest, release record, or a project's ownership document. The reference format number describes the index encoding only; it is not the source's version.

Keep source content with its owner. Do not build a large central document, cache, or knowledge database that becomes a competing source of truth. A temporary read result and a project decision/evidence record are not replacements for the source.

The discovery interface is stateless. Each entrypoint owns its session, permission-context label, reference cache, and exploration progress. Remembering an address does not establish that its body is current. Reuse observations only when the task permits it; read the source again when current state matters. Source adapters retain existing access controls. A session scope partitions records in the selected storage; it does not grant access or attest an identity. A teammate's shared receipt is evidence of their recorded observation, not an actual read in the current caller's context.

The plugin ships reference-entry rules, tools, and optional default metadata only. Domain and skill-authoring content belongs to independently managed sources. Connecting a source never installs its internal capabilities globally. Read the source participation contract through the usage reference before connecting or maintaining a source. Default/custom/general choices are owned by the consuming project and are made in task context; no source bodies are downloaded at initial setup.

Reference registries, connection choices and real data may live in consumer-selected files, local databases, repositories, cloud databases, object stores or document services. `.local/` is a convenient ignored local workspace, not an ownership or storage restriction. Keep only the necessary bootstrap location/profile in the caller's environment. Do not make a local copied registry authoritative merely to use a remote store. Authentication and actual personal/team sharing permissions remain with the service; profile names, `scope` and `writable` flags do not grant access or establish privacy. Sharing a reference does not share its source permissions.

The same ownership boundary applies to evaluation work. Decide by dependency on a specific task, not by file or folder names. Generic harness self-improvement methods, input preparers, model runners, and regression tests of those tools may live in the public repository. They accept consumer-provided inputs and must not embed a particular task catalogue or grading policy. Task-specific briefs, fixtures, rubrics, generated apps, answers, execution traces, results, and project settings belong in the consumer's selected storage or execution workspace, even when synthetic. An execution adapter may require a local working copy; that is not a rule for the authoritative data or reference location. Reusable domain examples belong to their role source, not to the reference entry package. A package allowlist alone is not sufficient: also review the public repository's tracked files and publication inventory before publication. Generic source improvements derived from a local failure may be published; the consumer's case remains outside the common package.

## Discovery metadata upkeep

The source owner's maintenance workflow reviews affected discovery metadata whenever the source changes. Update descriptions, labels, topics, locations, access methods, and explicit reference relationships when the change affects how the source should be found or what it is relevant to. Editorial or internal changes that leave discovery meaning intact do not require a metadata rewrite.

The source owner maintains the content; the reference registry's maintainer updates its discovery metadata. When both are in the authorized change scope, update them together and verify the reference against the changed source. If they are maintained separately, record the pending metadata update and the affected source/reference in the owning work record. Do not claim synchronization until the registry update is confirmed. Handle moved or removed sources through the registry's maintenance policy; do not guess replacement locations or silently keep misleading entries.

Use the registry's observed digest for an update or removal so another maintainer's intervening change is not overwritten. After inspecting a source revision, record the metadata review against that observation and the current binding. A later differing observation or binding requires another review. This record belongs to the maintenance session, not the reference metadata. A reviewed observation is not a claim that an unobserved remote source has stayed unchanged.

Keep descriptions limited to discovery cues. Do not copy current business rules, policy values, or source summaries into metadata as a substitute for reading the source. This maintenance responsibility belongs to the source/registry workflows, not to the discovery protocol deciding when content or policy is correct. These instructions define upkeep; they do not imply that an automatic synchronization service exists.

## Operation

Use the packaged `scripts/references.py` CLI. `list`, `discover`, `walk`, and `resolve` inspect metadata without creating a session or fetching source bodies. Discovery returns available results together with unavailable branches and any budget-limited remainder. Strict package validation separately requires a complete valid graph. Do not interpret an incomplete search as proof that no matching source exists.

For source access, bootstrap this governing source with `read`. Use `prepare-read` → authorized reader → `record` for external sources; `read` combines those operations for local text. `read-many` performs explicitly selected independent local reads with bounded concurrency. Every completion consumes its own receipt, so independent reads can finish in either order. Unknown or reused receipts are rejected. Failure is recorded per source and does not erase other results.

The session caches discovery metadata, not bodies. Local index changes invalidate cached bindings. Local filesystem cache signatures are not reused from shared stored traces across machines. Use the same `--scope` only within the same access context; use another trace key when that context changes. A stored trace requires an explicit scope. For team review, read the trace under its recorded scope without claiming it as the reviewing user's own source access. A `reused-from-current-context` observation must identify the prior actual read and remains distinct from a fresh source read. File and HTTP index adapters only fetch metadata: local traversal stays within explicitly supplied file-root trees and HTTP traversal within explicitly supplied origins. A discovered link cannot grant another access scope. Other connectors use the host's authorized adapter and retain their opaque identifiers.

Receipts can be stored directly in a chosen `store://` document from the first governance read onward, without a local staging trace. Load the caller's connection profile as runtime setup. Remote writes use storage revisions and retain event validation during conflict reconciliation. Inspect an uncertain write result before retrying; do not repeat the actual source read merely to append its outcome. Trace inspection and explicit snapshot export do not make the client a tamper-proof audit service: users with service-level edit access can still alter data outside this workflow.

Use `add`, `update`, and `remove` for authorized registry maintenance. `metadata-status --refresh` re-observes a local source through the access workflow; `metadata-review` acknowledges the inspected revision and current binding after the maintainer's semantic check. The tool cannot decide whether a description accurately describes the source.

Register additional sources using observed locations; never invent a path or URL. A source link still requires reference resolution before access. The Project Builder workflow enforces its own bootstrap policy; the discovery catalog does not own that policy. Session audit checks receipt and observation integrity, while workflow audit separately reports whether the current governing revision was read. Audit cannot prove that an agent made no unrecorded reads; compare actual tool use as well. Historical traces retain their originating package and format rather than being silently reinterpreted.

Applicable host instructions and the implementation's ordinary imports are not knowledge-source traversal. They do not provide an exception for an agent to read task context directly. Do not turn the workflow into a repeated user approval gate.
