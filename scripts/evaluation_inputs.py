"""실행 작업 디렉터리 기준 검사 입력의 경로와 내용 리비전을 추적한다."""

import hashlib
import os
from pathlib import Path


def _input_path(review, path):
    path = Path(os.path.abspath(path))
    if not path.is_relative_to(review) or not path.resolve().is_relative_to(review) or not path.is_file():
        raise ValueError("Test inputs must be files inside the review workspace")
    return path


def capture_inputs(review, runtime, command, explicit):
    review, runtime = Path(review).resolve(), Path(runtime).resolve()
    paths = [_input_path(review, review / name) for name in explicit]
    for position, argument in enumerate(command):
        candidate = Path(argument)
        path = candidate if candidate.is_absolute() else runtime / candidate
        try:
            exists = path.is_file()
        except OSError:
            # 명령 인자는 파일 경로 외의 긴 인라인 코드 등도 포함한다.
            exists = False
        if not exists:
            continue
        resolved = path.resolve()
        if position == 0 and not resolved.is_relative_to(review):
            continue  # 설치된 실행 도구의 리비전은 환경 증거가 소유한다.
        path = _input_path(review, path)
        if not resolved.is_relative_to(runtime):
            paths.append(path)
    return {path.relative_to(review).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


def verify_inputs(review, inputs):
    review = Path(review).resolve()
    for name, digest in inputs.items():
        path = _input_path(review, review / name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Recorded test input changed after execution")
