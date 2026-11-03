# Evidence and handoff

## Evidence layers

| Layer | Establishes | Does not establish |
| --- | --- | --- |
| Static checks | Types, syntax, selected structural constraints | Real execution or UX |
| Unit/invariant tests | Specified behavior for tested inputs | Integration and all possible inputs |
| Local/mock flow | Local interactions with the tested data source | Real service compatibility |
| Real integration | Observed service interaction | Deployment or stakeholder acceptance |
| Rendered UX review | Observed task flow and visible states | A user study or unseen states |
| Deployment check | Specific deployed revision and tested path | Every requirement or acceptance |

## Explainability

For the important decisions, provide decision → reason → implementation → evidence → limitation. A new contributor should be able to follow the references, not merely trust a prose summary.

If a review rubric exists, report the supported criteria and missing evidence without estimating unsupported scores. A question about architecture is answered by tracing the actual request-to-result flow, not by inventing plausible module names.

## Resume reliability

Record the next action and unresolved dependency, not only a completion percentage. On resume, compare recorded evidence with current code and source versions. Do not repeat a completed step merely because a new session began; do rerun a check invalidated by changes.
