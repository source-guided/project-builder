# Reference routing — governing source

This is the authoritative routing rule for this harness. It governs normal product work and improvements to the harness itself. Do not weaken it as a routine optimization, convenience shortcut, or response to a single example. A change to this invariant requires explicit direction from the user who owns the harness.

## Mandatory navigation

Every knowledge-source access must be mediated by a reference:

`request → reference → source A → reference → source B → …`

Never navigate directly from source A to source B. A link discovered inside a source is a candidate location, not permission to skip reference lookup. Locate an existing reference or register the observed location in the consuming project's reference registry before accessing it. This also applies to horizontal movement across design, frontend, API, project, and version domains.

Reference folders organize navigation; they are not a fixed execution sequence. Select branches using the user's intent and reference topics. Follow relevant horizontal relationships as new needs emerge. Track visited references and sources, stop cycles and unnecessary repeated reads, and stop exploring when the task's material context is resolved. Do not fetch every branch.

## Reference versus source

References contain navigation metadata: identifier, label, topics, target kind, location, access method, and related references. They do not contain copied requirements, rules, answers, source bodies, or authoritative owner/version values.

Version and ownership information must be obtained from their own sources through a reference, such as the package manifest, release record, or a project's ownership document. The reference format number describes the index encoding only; it is not the source's version.

Keep source content with its owner. Do not build a large central document, cache, or knowledge database that becomes a competing source of truth. A temporary read result and a project decision/evidence record are not replacements for the source.

Common references and generic workflows may ship with the public plugin. Project-specific conventions, Figma bindings, API locations, and custom source relationships belong in the consuming project. Never publish a consuming project's registry or source material with the common package.

The same ownership boundary applies to evaluation work. Decide by dependency on a specific task, not by file or folder names. Generic harness self-improvement methods, input preparers, model runners, and regression tests of those tools may live in the public repository. They accept consumer-provided inputs and must not embed a particular task catalogue or grading policy. Task-specific briefs, fixtures, rubrics, generated apps, answers, execution traces, results, and project settings belong in the consuming project or an ignored local evaluation area, even when synthetic. Explicitly designated common UX examples are reusable teaching assets, not private project results. A package allowlist alone is not sufficient: also review the public repository's tracked files and publication inventory before publication. Generic source improvements derived from a local failure may be published; the local case remains local.

## Operation

Use the packaged `scripts/references.py` helper. `list` reads index metadata. `resolve` returns a source or reference location and a receipt; access the returned source with its appropriate tool, then `record` the read using that receipt. For text files, `read` performs reference resolution and the actual read together, while recording separate reference/source events. It does not store the source body in the trace.

Bootstrap with the governance reference first. Register additional local sources with `add` using an observed file location; never invent a path or URL. Before each next source, resolve again, even if the previous source contains a direct link. The trace auditor rejects source-to-source transitions and reused receipts. The trace is evidence of recorded accesses, not a security sandbox or proof that unlogged tool use is impossible; reviewers must also compare actual agent actions.

Applicable host instructions and the implementation's ordinary imports are not knowledge-source traversal. They do not provide an exception for an agent to read task context directly. Do not turn the workflow into a repeated user approval gate.
