#!/usr/bin/env python3
"""Validate a NexoMercado phase without modifying the repository."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PHASE_ORDER = ["S0", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
VALID_STATUSES = {
    "pendiente",
    "en_curso",
    "lista_para_revision",
    "aceptada",
    "ajustar",
    "descartada",
    "bloqueada",
}
ACTIVE_STATUSES = {"en_curso", "lista_para_revision"}
MAIN_BRANCH_EXCEPTIONS = {
    "6": "Fase 6 ejecutada en `main` por autorizacion explicita del usuario",
    "7": "Fase 7 ejecutada en `main` por autorizacion explicita del usuario",
}


class ValidationError(RuntimeError):
    """Represents a phase contract violation."""


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ValidationError("No Git root was found from the provided path.")


def parse_frontmatter(plan_text: str) -> dict[str, str]:
    lines = plan_text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValidationError("The plan must start with --- frontmatter.")

    try:
        closing_index = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration as exc:
        raise ValidationError("The plan frontmatter is not closed.") from exc

    values: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValidationError(f"Invalid frontmatter line: {line!r}")

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or not value:
            raise ValidationError(f"Empty key or value in frontmatter: {line!r}")
        if key in values:
            raise ValidationError(f"Duplicate frontmatter key: {key}")
        values[key] = value

    return values


def git_output(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise ValidationError(f"Git failed: {message}")
    return completed.stdout.strip()


def allows_main_branch_exception(
    *,
    phase: str,
    branch: str,
    plan_text: str,
) -> bool:
    exception_text = MAIN_BRANCH_EXCEPTIONS.get(phase)
    return branch == "main" and exception_text is not None and exception_text in plan_text


def validate(args: argparse.Namespace) -> dict[str, object]:
    repo_root = find_repo_root(Path(args.repo or Path.cwd()))
    plan_path = repo_root / "docs" / "PLAN_IMPLEMENTACION_POR_FASES.md"
    readme_path = repo_root / "README.md"

    if not plan_path.is_file():
        raise ValidationError(f"Missing expected plan: {plan_path}")
    if not readme_path.is_file():
        raise ValidationError("Missing README.md.")
    if "NexoMercado AI" not in readme_path.read_text(encoding="utf-8"):
        raise ValidationError("README.md does not contain the NexoMercado AI marker.")
    if args.phase not in PHASE_ORDER:
        raise ValidationError(f"Unknown phase: {args.phase}")

    plan_text = plan_path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(plan_text)
    plan_version = frontmatter.get("plan_version", "")
    if not plan_version.isdigit() or int(plan_version) < 1:
        raise ValidationError("plan_version must be a positive integer.")

    current_phase = frontmatter.get("current_phase")
    if current_phase not in PHASE_ORDER:
        raise ValidationError("current_phase does not identify a valid phase.")

    statuses: dict[str, str] = {}
    for phase in PHASE_ORDER:
        key = f"phase_{phase}"
        status = frontmatter.get(key)
        if status not in VALID_STATUSES:
            raise ValidationError(f"{key} has an invalid or missing status: {status!r}")
        statuses[phase] = status

    active = [phase for phase, status in statuses.items() if status in ACTIVE_STATUSES]
    if len(active) > 1:
        raise ValidationError(f"Multiple active phases: {', '.join(active)}")

    phase_index = PHASE_ORDER.index(args.phase)
    incomplete_predecessors = [
        phase for phase in PHASE_ORDER[:phase_index] if statuses[phase] != "aceptada"
    ]
    if incomplete_predecessors:
        details = ", ".join(f"{phase}={statuses[phase]}" for phase in incomplete_predecessors)
        raise ValidationError(f"Unaccepted prerequisites: {details}")

    status = statuses[args.phase]
    if current_phase != args.phase:
        raise ValidationError(
            f"Requested phase {args.phase} does not match current_phase={current_phase}."
        )

    branch = git_output(repo_root, "branch", "--show-current")
    if args.action == "implement":
        if status != "en_curso":
            raise ValidationError(f"Implement requires en_curso; current status: {status}")
        if active != [args.phase]:
            raise ValidationError("Implement requires the requested phase to be the only active phase.")

        phase_slug = args.phase.lower()
        branch_pattern = re.compile(rf"^codex/fase-{re.escape(phase_slug)}(?:-|$)")
        if not branch_pattern.match(branch) and not allows_main_branch_exception(
            phase=args.phase,
            branch=branch,
            plan_text=plan_text,
        ):
            raise ValidationError(
                f"Implementing Phase {args.phase} requires a codex/fase-{phase_slug}-* "
                f"branch; current branch: {branch or '(detached)'}"
            )
    elif status not in {"en_curso", "lista_para_revision", "aceptada"}:
        raise ValidationError(f"Validate does not allow the current status: {status}")

    section_pattern = re.compile(
        rf"^### Fase {re.escape(args.phase)}(?:\s|—|-)",
        re.MULTILINE,
    )
    if not section_pattern.search(plan_text):
        raise ValidationError(f"No documented section exists for Phase {args.phase}.")

    dirty_paths = [
        line for line in git_output(repo_root, "status", "--short").splitlines() if line
    ]
    if args.require_clean and dirty_paths:
        raise ValidationError("The worktree is not clean: " + ", ".join(dirty_paths))

    return {
        "ok": True,
        "action": args.action,
        "phase": args.phase,
        "status": status,
        "currentPhase": current_phase,
        "activePhases": active,
        "branch": branch,
        "dirtyPaths": dirty_paths,
        "planVersion": plan_version,
        "repoRoot": str(repo_root),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("implement", "validate"))
    parser.add_argument("phase", help="Target phase: S0, 0, 1, ..., 10")
    parser.add_argument("--repo", help="Path inside the repository; defaults to cwd")
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="Fail if there are uncommitted changes",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = validate(args)
    except ValidationError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
