# Behavioral evaluation

These are synthetic product scenarios. They are not real customer briefs or official grading rubrics.

Use GPT-6.1 Sol with reasoning effort `high` only. Package/static checks do not establish behavioral quality. Each run is given a fresh project directory, a separate copy of the packaged `start` skill, and the scenario's raw input. Do not provide the reviewer's desired answer to the implementing agent. Do not let runs change the plugin itself or use live external accounts. This is logical input separation, not a filesystem security sandbox: a workspace-write policy does not prevent reading other accessible paths. Use an OS/container sandbox for untrusted evaluators. In the reported runs, inspect tool records for source access; do not claim enforced read isolation.

Run the cases independently. Review the actual artifacts and executed checks using `criteria.json`; do not grade on headings or exact wording. Record the model, package revision/hash, actual outcome, evidence paths, failures, and unverified layers. A finite passing set is not a guarantee for every domain.

Cases:
- `reservation`: interpret a sourced brief and produce a task-focused design without implementing outside requested scope.
- `reconciliation`: implement and execute a non-UI workflow with exact data semantics.
- `review-screen`: improve a rendered review flow without removing necessary decision information.
- `resume`: repair a narrow defect while recognizing stale prior verification.

`python3 scripts/prepare_eval.py --case reconciliation --output /absolute/temporary/project` prepares raw input and a prompt. Use the prompt with GPT-6.1 Sol. The evaluator criteria remain in this repository, outside the agent's fixture. Evaluation outputs should live outside tracked files or under `.local/evals/`.

For repeatable CLI execution, `python3 scripts/run_eval.py --case reconciliation` prepares the fixture and invokes `codex exec --model gpt-6.1-sol -c 'model_reasoning_effort="high"'`. It stops on failure; it never switches models or effort. The command requires an authenticated Codex CLI with that exact model available. The tested ChatGPT-account CLI rejected that identifier; app-agent runs can be used with the prepared prompt and explicit model/effort selection instead. It does not install the plugin or change the user's model setting. Read the generated artifacts before marking a case passed. A requested setting in a receipt is not independent proof of the serving model.
