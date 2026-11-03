"""평가 입력과 첫 산출물의 파일 목록 및 해시를 보존한다."""

import hashlib
import os
import shutil
from contextlib import contextmanager
import threading
import time
from pathlib import Path


EXCLUDED_DIRECTORIES = {".git", "node_modules", ".venv", "venv", "__pycache__"}
_workspace_locks = {}
_workspace_locks_guard = threading.Lock()


@contextmanager
def workspace_lock(review: Path, timeout=60):
    key = str(review.resolve())
    with _workspace_locks_guard:
        lock = _workspace_locks.setdefault(key, threading.Lock())
    if not lock.acquire(timeout=timeout):
        raise TimeoutError("Another capture is using this review workspace")
    folder = review / ".harness"
    started = time.monotonic()
    try:
        folder.mkdir(exist_ok=True)
        with (folder / "capture.lock").open("a+b") as stream:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                if not stream.read(1):
                    stream.write(b"0");stream.flush()
            else:
                import fcntl
            while True:
                try:
                    if os.name == "nt":
                        stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                    else:
                        fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic()-started >= timeout:
                        raise TimeoutError("Another process is capturing this review workspace")
                    time.sleep(0.05)
            try:
                yield
            finally:
                if os.name == "nt":
                    stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
    finally:
        lock.release()


def file_manifest(root: Path) -> dict:
    root = root.resolve()
    result = {}
    for current, directories, files in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in EXCLUDED_DIRECTORIES)
        for name in [*directories, *sorted(files)]:
            path = Path(current) / name
            if path.is_symlink():
                raise ValueError(f"Artifact contains an unreviewed symlink: {path.relative_to(root)}")
        for name in sorted(files):
            path = Path(current) / name
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            result[path.relative_to(root).as_posix()] = digest.hexdigest()
    return result


def executable_manifest(root: Path) -> dict:
    root = root.resolve()
    return {name: (root / name).stat().st_mode & 0o111 for name in file_manifest(root)}


def snapshot(source: Path, destination: Path) -> dict:
    manifest = file_manifest(source)
    modes = executable_manifest(source)
    if destination.exists():
        raise ValueError("Snapshot destination already exists")
    def ignored(directory, names):
        return [name for name in names if name in EXCLUDED_DIRECTORIES and (Path(directory) / name).is_dir()]

    shutil.copytree(source, destination, ignore=ignored)
    if file_manifest(destination) != manifest or executable_manifest(destination) != modes:
        raise ValueError("Source changed during snapshot creation")
    return manifest
