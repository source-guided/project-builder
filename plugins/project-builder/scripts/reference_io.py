"""로컬 참조 파일의 접근, 잠금 및 원자적 저장 어댑터."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
from reference_address import local_path


_locks = {}
_locks_guard = threading.Lock()


def fingerprint(address):
    path = local_path(address)
    if not os.access(path, os.R_OK):
        raise PermissionError(f"Index is not readable: {path}")
    stat = path.stat()
    return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]


def load_index(address):
    data = local_path(address).read_bytes()
    return {"document": json.loads(data), "digest": hashlib.sha256(data).hexdigest()}


@contextmanager
def locked(path):
    key = str(Path(path).resolve())
    with _locks_guard:
        thread_lock = _locks.setdefault(key, threading.RLock())
    user = str(os.getuid()) if hasattr(os, "getuid") else os.environ.get("USERNAME", "local")
    folder = Path(tempfile.gettempdir()) / ("project-builder-locks-" + hashlib.sha256(user.encode()).hexdigest()[:12])
    folder.mkdir(mode=0o700, exist_ok=True)
    lock_path = folder / hashlib.sha256(key.encode()).hexdigest()
    with thread_lock, lock_path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0)
            if not stream.read(1):
                stream.write(b"0"); stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def write_json(path, value):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Refusing to replace a symlink")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, encoding="utf-8") as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
