# Source participation contract v1

This is the common boundary for sources connected to Project Builder. It governs discovery and exposure, not a domain's creation methodology. It applies whether the caller selects default guidance, custom guidance or the AI's general approach.

A source owns its instructions, internal capabilities, domain criteria, examples and checks. Its entry index exposes navigation metadata only. A source-local skill is reached through a reference and applied only in that context. It is not copied into a global `skills/` directory, exported by a plugin manifest, or registered as an automatic host trigger. No source may install another source as a hidden prerequisite. Cross-source needs return to the consuming project's connection choices.

Repository-backed sources declare `source.json`: format 1, a source ID and version, role, exposure `source-only`, contract `project-builder.source/v1`, an entry index and a list of internal `capabilities/.../SKILL.md` paths. This manifest is a source of ownership/version information; those values are not duplicated into discovery records. `source-files.json` lists the source's reviewed public files. DB, Confluence and other hosts provide equivalent entry/ownership information through their authorized adapter; a Git repository is not mandatory.

Use reference access `relative` for a source-owned path that must work in both a local checkout and a hosted HTTP index. The reference client resolves it using the current index transport. Local paths stay within the source in source-package validation; hosted connectors keep their own access controls. Absolute web and opaque connector bindings remain available for other sources.

The common plugin distributes only its reference entry capability, connection tools, participation rules and optional default metadata. It must work without any default-source body. Default roots are not fetched on installation or while listing suggestions. User source selection records intent and binding, not copied skill bodies or account credentials.

Source maintainers keep their own domain and authoring rules. When authoring guidance is absent, the caller chooses default, custom or general mode; selecting a methodology never waives this participation contract. Source content changes trigger a review of affected discovery metadata. Contract checks verify package boundaries and references, while domain checks remain with the source owner.
