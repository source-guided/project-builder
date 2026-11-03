"""파일·SQLite 문서 저장. 도메인 변환이나 참조 정책을 소유하지 않는다."""

import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import unquote, urlparse

from document_store import MissingDocument, compare_revision, encode, observation
from reference_address import local_path
from reference_io import locked, write_json


class FileStore:
    def _path(self, key):
        parsed = urlparse(str(key))
        original = Path(unquote(parsed.path)) if parsed.scheme == "file" else Path(key)
        if original.is_symlink():
            raise ValueError("Document state must not be a symlink")
        return local_path(key)

    def read(self, key):
        path = self._path(key)
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            raise MissingDocument("Document does not exist") from None
        return observation(json.loads(raw), hashlib.sha256(raw).hexdigest(), raw=raw)

    def write(self, key, document, *, expected_revision):
        encode(document)
        path = self._path(key)
        with locked(path):
            try:
                current = self.read(path)["revision"]
            except MissingDocument:
                current = None
            compare_revision(current, expected_revision)
            path.parent.mkdir(parents=True, exist_ok=True)
            write_json(path, document)
            return self.read(path)


class SQLiteStore:
    def __init__(self, path):
        self.path = Path(path).absolute()
        if self.path.is_symlink():
            raise ValueError("SQLite store must not be a symlink")

    def read(self, key):
        if self.path.is_symlink():
            raise ValueError("SQLite store must not be a symlink")
        if not self.path.exists():
            raise MissingDocument("SQLite document does not exist")
        # 조회는 DB나 테이블을 생성하지 않으며 파일 권한을 그대로 따른다.
        with sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True) as connection:
            table = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reference_documents'").fetchone()
            if table is None:
                raise MissingDocument("SQLite document table does not exist")
            row = connection.execute("SELECT document, revision FROM reference_documents WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise MissingDocument("SQLite document does not exist")
        return observation(json.loads(row[0]), str(row[1]))

    def write(self, key, document, *, expected_revision):
        raw = encode(document).decode("utf-8")
        if self.path.is_symlink():
            raise ValueError("SQLite store must not be a symlink")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("CREATE TABLE IF NOT EXISTS reference_documents (key TEXT PRIMARY KEY, document TEXT NOT NULL, revision INTEGER NOT NULL)")
            row = connection.execute("SELECT revision FROM reference_documents WHERE key = ?", (key,)).fetchone()
            compare_revision(str(row[0]) if row else None, expected_revision)
            revision = row[0] + 1 if row else 1
            if row:
                connection.execute("UPDATE reference_documents SET document = ?, revision = ? WHERE key = ?", (raw, revision, key))
            else:
                connection.execute("INSERT INTO reference_documents VALUES (?, ?, ?)", (key, raw, revision))
        return observation(document, str(revision))
