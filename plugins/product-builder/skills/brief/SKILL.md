---
name: brief
description: Analyze a project brief, README, data contracts, workflow rules, and acceptance criteria into sourced requirements and verification priorities. Use before substantial implementation or when scope changes; do not invent success criteria.
---

# Understand the product brief

Read the actual brief/README and referenced files, not only the user's paraphrase or later review questions. Use [source and evaluation guidance](references/source-evaluation.md) to interpret evidence and [constraint extraction](references/constraints.md) when a specification contains many interacting conditions.

Build a compact source map covering the parts that exist:
- Product goal, roles, core tasks, explicit exclusions.
- Input formats, schemas, examples, units, dates/time zones, invalid inputs.
- Output/export contract, persistence, deployment/run instructions, required artifacts.
- Delivery context: execution environment, stakeholders, handoff artifacts, time budget, tool constraints, and any provided delivery procedure.
- Acceptance criteria and any supplied review rubric; exact weights **only when available**, otherwise mark them unknown.

Convert requirements into observable acceptance conditions. Record source and locator for each. Distinguish mandatory constraints from optimization goals and informal usability signals. Keep stakeholder clarifications traceable and flag conflicts that materially affect delivery.

Explain priority using mandatory completion, correctness impact, dependency, user value, and available time. Keep these delivery priorities separate from external evaluation. Do not introduce invented numerical weights or predicted scores.

For a missing original, label reconstructed material as secondary evidence, identify missing sections, and continue bounded work. Ask for the missing source only when its absence blocks a material decision. A remembered statement is not a verified current contract.

Generate only useful project records, using existing owner documents where possible. Do not write project-specific confidential material into this plugin, its public examples, or evaluation reports. See [synthetic brief examples](references/examples.md) for distinctions that apply across domains.
