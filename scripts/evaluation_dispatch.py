"""호출자의 모델 선택과 평가 작업 공간을 Codex CLI 요청으로 전달한다."""

import json


def selection_record(*, model=None, reasoning_effort=None):
    for value in (model, reasoning_effort):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("Explicit model settings must be nonempty strings")
    return {"model_requested": model, "reasoning_effort_requested": reasoning_effort,
            "configuration_source": {
                "model": "explicit_argument" if model is not None else "caller_cli_configuration",
                "reasoning_effort": "explicit_argument" if reasoning_effort is not None else "caller_cli_configuration"}}


def build_command(*, workspace, answer, model=None, reasoning_effort=None):
    selection_record(model=model, reasoning_effort=reasoning_effort)
    command = ["codex", "exec"]
    if model is not None:
        command.extend(["--model", model])
    if reasoning_effort is not None:
        command.extend(["-c", "model_reasoning_effort=" + json.dumps(reasoning_effort)])
    return command + ["--ephemeral", "--skip-git-repo-check", "--sandbox", "workspace-write",
                      "--json", "--cd", str(workspace), "--output-last-message", str(answer), "-"]
