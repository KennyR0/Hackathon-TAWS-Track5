from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "validate_phase.py"


def run_validation(*args: str) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = completed.stdout.strip() or completed.stderr.strip()
    return completed.returncode, json.loads(payload)


def create_temp_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "demo-repo"
    docs_path = repo_path / "docs"
    docs_path.mkdir(parents=True)

    (repo_path / "README.md").write_text("# NexoMercado AI\n", encoding="utf-8")
    (docs_path / "PLAN_IMPLEMENTACION_POR_FASES.md").write_text(
        """---
plan_version: 2
current_phase: 1
phase_S0: aceptada
phase_0: aceptada
phase_1: en_curso
phase_2: pendiente
phase_3: pendiente
phase_4: pendiente
phase_5: pendiente
phase_6: pendiente
phase_7: pendiente
phase_8: pendiente
phase_9: pendiente
phase_10: pendiente
last_updated: 2026-07-12
---

# Plan de implementación por fases — NexoMercado AI

### Fase 1 — Walking skeleton

- Backend mínimo.
""",
        encoding="utf-8",
    )

    subprocess.run(["git", "init", "-b", "main"], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Codex Tests"],
        cwd=repo_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "codex-tests@example.com"],
        cwd=repo_path,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Base"], cwd=repo_path, check=True)
    return repo_path


def create_phase6_main_exception_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "demo-repo-phase6"
    docs_path = repo_path / "docs"
    docs_path.mkdir(parents=True)

    (repo_path / "README.md").write_text("# NexoMercado AI\n", encoding="utf-8")
    (docs_path / "PLAN_IMPLEMENTACION_POR_FASES.md").write_text(
        """---
plan_version: 2
current_phase: 6
phase_S0: aceptada
phase_0: aceptada
phase_1: aceptada
phase_2: aceptada
phase_3: aceptada
phase_4: aceptada
phase_5: aceptada
phase_6: en_curso
phase_7: pendiente
phase_8: pendiente
phase_9: pendiente
phase_10: pendiente
last_updated: 2026-07-12
---

# Plan de implementación por fases — NexoMercado AI

### Fase 6 — Proveedores live y fallback

Fase 6 ejecutada en `main` por autorizacion explicita del usuario.
""",
        encoding="utf-8",
    )

    subprocess.run(["git", "init", "-b", "main"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Codex Tests"], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "codex-tests@example.com"],
        cwd=repo_path,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Base"], cwd=repo_path, check=True)
    return repo_path


def create_phase7_main_exception_repo(tmp_path: Path, *, include_exception: bool) -> Path:
    repo_path = tmp_path / f"demo-repo-phase7-{include_exception}"
    docs_path = repo_path / "docs"
    docs_path.mkdir(parents=True)

    exception_line = (
        "Fase 7 ejecutada en `main` por autorizacion explicita del usuario."
        if include_exception
        else "Fase 7 se mantiene pendiente de rama dedicada."
    )
    (repo_path / "README.md").write_text("# NexoMercado AI\n", encoding="utf-8")
    (docs_path / "PLAN_IMPLEMENTACION_POR_FASES.md").write_text(
        f"""---
plan_version: 2
current_phase: 7
phase_S0: aceptada
phase_0: aceptada
phase_1: aceptada
phase_2: aceptada
phase_3: aceptada
phase_4: aceptada
phase_5: aceptada
phase_6: aceptada
phase_7: en_curso
phase_8: pendiente
phase_9: pendiente
phase_10: pendiente
last_updated: 2026-07-12
---

# Plan de implementaciÃ³n por fases â€” NexoMercado AI

### Fase 7 â€” Despliegue y demo

{exception_line}
""",
        encoding="utf-8",
    )

    subprocess.run(["git", "init", "-b", "main"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Codex Tests"], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "codex-tests@example.com"],
        cwd=repo_path,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Base"], cwd=repo_path, check=True)
    return repo_path


def test_validate_phase_script_accepts_valid_repo(tmp_path: Path) -> None:
    repo_path = create_temp_repo(tmp_path)

    code, payload = run_validation("validate", "1", "--repo", str(repo_path))

    assert code == 0
    assert payload["ok"] is True
    assert payload["status"] == "en_curso"
    assert payload["currentPhase"] == "1"
    assert payload["activePhases"] == ["1"]
    assert payload["branch"] == "main"


def test_validate_phase_script_rejects_wrong_implement_branch(tmp_path: Path) -> None:
    repo_path = create_temp_repo(tmp_path)

    code, payload = run_validation("implement", "1", "--repo", str(repo_path))

    assert code == 1
    assert payload["ok"] is False
    assert "codex/fase-1" in str(payload["error"])


def test_validate_phase_script_allows_documented_phase6_main_exception(
    tmp_path: Path,
) -> None:
    repo_path = create_phase6_main_exception_repo(tmp_path)

    code, payload = run_validation("implement", "6", "--repo", str(repo_path))

    assert code == 0
    assert payload["ok"] is True
    assert payload["phase"] == "6"
    assert payload["branch"] == "main"


def test_validate_phase_script_allows_documented_phase7_main_exception(
    tmp_path: Path,
) -> None:
    repo_path = create_phase7_main_exception_repo(tmp_path, include_exception=True)

    code, payload = run_validation("implement", "7", "--repo", str(repo_path))

    assert code == 0
    assert payload["ok"] is True
    assert payload["phase"] == "7"
    assert payload["branch"] == "main"


def test_validate_phase_script_rejects_phase7_main_without_exception(
    tmp_path: Path,
) -> None:
    repo_path = create_phase7_main_exception_repo(tmp_path, include_exception=False)

    code, payload = run_validation("implement", "7", "--repo", str(repo_path))

    assert code == 1
    assert payload["ok"] is False
    assert "codex/fase-7" in str(payload["error"])
