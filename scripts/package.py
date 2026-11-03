#!/usr/bin/env python3
"""공개 플러그인 파일만 결정적인 ZIP으로 만든다."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from validate import PLUGIN, ROOT, plugin_files, validate


def package(destination: Path, plugin: Path = PLUGIN) -> str:
    destination = destination.resolve()
    if destination.is_relative_to(plugin.resolve()):
        raise ValueError("Archive must be outside the plugin directory")
    files = plugin_files(plugin)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(plugin).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return hashlib.sha256(destination.read_bytes()).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    validate()
    version = json.loads((PLUGIN / "plugin.json").read_text())["version"]
    destination = args.output or ROOT / "dist" / f"project-builder-{version}.zip"
    digest = package(destination)
    destination.with_suffix(destination.suffix + ".sha256").write_text(f"{digest}  {destination.name}\n")
    print(f"{destination}\nsha256: {digest}")
