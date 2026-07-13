#!/usr/bin/env python3
"""Valida el estado de una fase de NexoMercado sin modificar el repositorio."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PHASE_ORDER = ["S0", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
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


class ValidationError(RuntimeError):
    """Representa una violación del contrato de fases."""


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ValidationError("No se encontró una raíz Git desde la ruta indicada.")


def parse_frontmatter(plan_text: str) -> dict[str, str]:
    lines = plan_text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValidationError("El plan no empieza con frontmatter delimitado por ---.")

    try:
        closing_index = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValidationError("El frontmatter del plan no tiene cierre.") from exc

    values: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValidationError(f"Línea de frontmatter inválida: {line!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or not value:
            raise ValidationError(f"Clave o valor vacío en frontmatter: {line!r}")
        if key in values:
            raise ValidationError(f"Clave duplicada en frontmatter: {key}")
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
        raise ValidationError(f"Git falló: {message}")
    return completed.stdout.strip()


def validate(args: argparse.Namespace) -> dict[str, object]:
    repo_root = find_repo_root(Path(args.repo or Path.cwd()))
    plan_path = repo_root / "docs" / "PLAN_IMPLEMENTACION_POR_FASES.md"
    readme_path = repo_root / "README.md"

    if not plan_path.is_file():
        raise ValidationError(f"No existe el plan esperado: {plan_path}")
    if not readme_path.is_file() or "NexoMercado AI" not in readme_path.read_text(encoding="utf-8"):
        raise ValidationError("El repositorio no contiene el marcador NexoMercado AI en README.md.")
    if args.phase not in PHASE_ORDER:
        raise ValidationError(f"Fase desconocida: {args.phase}")

    plan_text = plan_path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(plan_text)
    plan_version = frontmatter.get("plan_version", "")
    if not plan_version.isdigit() or int(plan_version) < 1:
        raise ValidationError("plan_version debe ser un entero positivo.")

    current_phase = frontmatter.get("current_phase")
    if current_phase not in PHASE_ORDER:
        raise ValidationError("current_phase no identifica una fase válida.")

    statuses: dict[str, str] = {}
    for phase in PHASE_ORDER:
        key = f"phase_{phase}"
        status = frontmatter.get(key)
        if status not in VALID_STATUSES:
            raise ValidationError(f"{key} tiene un estado inválido o ausente: {status!r}")
        statuses[phase] = status

    active = [phase for phase, status in statuses.items() if status in ACTIVE_STATUSES]
    if len(active) > 1:
        raise ValidationError(f"Hay múltiples fases activas: {', '.join(active)}")

    phase_index = PHASE_ORDER.index(args.phase)
    incomplete_predecessors = [phase for phase in PHASE_ORDER[:phase_index] if statuses[phase] != "aceptada"]
    if incomplete_predecessors:
        raise ValidationError(
            "Prerrequisitos no aceptados: "
            + ", ".join(f"{phase}={statuses[phase]}" for phase in incomplete_predecessors)
        )

    status = statuses[args.phase]
    if current_phase != args.phase:
        raise ValidationError(f"La fase solicitada {args.phase} no coincide con current_phase={current_phase}.")

    branch = git_output(repo_root, "branch", "--show-current")
    if args.action == "implement":
        if status != "en_curso":
            raise ValidationError(f"Implementar exige estado en_curso; estado actual: {status}")
        if active != [args.phase]:
            raise ValidationError("Implementar exige que la fase solicitada sea la única fase activa.")
        phase_slug = args.phase.lower()
        branch_pattern = re.compile(rf"^codex/fase-{re.escape(phase_slug)}(?:-|$)")
        if not branch_pattern.match(branch):
            raise ValidationError(
                f"Implementar la Fase {args.phase} exige una rama codex/fase-{phase_slug}-*; "
                f"rama actual: {branch or '(detached)'}"
            )
    elif status not in {"en_curso", "lista_para_revision", "aceptada"}:
        raise ValidationError(f"Validar no admite el estado actual: {status}")

    section_pattern = re.compile(rf"^### Fase {re.escape(args.phase)}(?:\s|—|-)", re.MULTILINE)
    if not section_pattern.search(plan_text):
        raise ValidationError(f"No existe una sección documentada para la Fase {args.phase}.")

    dirty_paths = [line for line in git_output(repo_root, "status", "--short").splitlines() if line]
    if args.require_clean and dirty_paths:
        raise ValidationError("El worktree no está limpio: " + ", ".join(dirty_paths))

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
    parser.add_argument("phase", help="Fase objetivo: S0, 0, 1, ..., 10")
    parser.add_argument("--repo", help="Ruta dentro del repositorio; por defecto usa el cwd")
    parser.add_argument("--require-clean", action="store_true", help="Fallar si existen cambios sin confirmar")
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
