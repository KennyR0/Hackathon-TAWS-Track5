#!/usr/bin/env python3
"""Compara por SHA-256 la skill canónica del repositorio y su espejo global."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

SKILL_NAME = "run-nexomercado-phase"
IGNORED_PARTS = {"__pycache__", ".pytest_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError("No se encontró la raíz Git.")


def iter_skill_files(skill_path: Path):
    for path in sorted(skill_path.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(skill_path)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        if path.suffix.lower() in IGNORED_SUFFIXES:
            continue
        yield relative, path


def manifest_hash(skill_path: Path) -> tuple[str, list[str]]:
    if not (skill_path / "SKILL.md").is_file():
        raise FileNotFoundError(f"No existe SKILL.md en {skill_path}")
    digest = hashlib.sha256()
    files: list[str] = []
    for relative, path in iter_skill_files(skill_path):
        normalized = relative.as_posix()
        files.append(normalized)
        digest.update(normalized.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest(), files


def global_candidates() -> list[Path]:
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    return [
        home / ".codex" / "skills" / SKILL_NAME,
        home / ".agents" / "skills" / SKILL_NAME,
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="Ruta dentro del repositorio; por defecto usa el cwd")
    parser.add_argument("--global-skill", help="Ruta explícita al espejo global")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        repo_root = find_repo_root(Path(args.repo or Path.cwd()))
        repo_skill = repo_root / ".agents" / "skills" / SKILL_NAME
        if args.global_skill:
            global_skill = Path(args.global_skill).expanduser().resolve()
        else:
            global_skill = next((path for path in global_candidates() if (path / "SKILL.md").is_file()), None)
            if global_skill is None:
                raise FileNotFoundError("No se encontró un espejo global de la skill.")

        repo_hash, repo_files = manifest_hash(repo_skill)
        global_hash, global_files = manifest_hash(global_skill)
        is_match = repo_hash == global_hash and repo_files == global_files
        result = {
            "ok": is_match,
            "repoSkill": str(repo_skill),
            "globalSkill": str(global_skill),
            "repoHash": repo_hash,
            "globalHash": global_hash,
            "repoFiles": repo_files,
            "globalFiles": global_files,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if is_match else 1
    except (FileNotFoundError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
