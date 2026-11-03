"""평가 프로세스 그룹의 생성, 대기, 종료를 소유한다."""

import os
import signal
import subprocess


class ProcessTimeout(subprocess.TimeoutExpired):
    def __init__(self, command, timeout, returncode):
        super().__init__(command, timeout)
        self.returncode = returncode


def run_process(command, *, timeout, cwd=None, stdin=None, stdout=None, stderr=None):
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    if os.name != "posix":
        raise OSError("Managed evaluation process groups currently require POSIX")
    process = subprocess.Popen(command, cwd=cwd, stdin=stdin, stdout=stdout, stderr=stderr,
                               start_new_session=True)
    expired = False
    try:
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired = True
    finally:
        # 정상 종료도 잔여 자식을 정리한 뒤 산출물 동결/증거 해시로 진행한다.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
    if expired:
        raise ProcessTimeout(command, timeout, process.returncode)
    return subprocess.CompletedProcess(command, process.returncode)
