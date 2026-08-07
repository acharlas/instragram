"""Guards for backend container startup behavior."""

import os
import stat
import subprocess
import tempfile
import time
from pathlib import Path


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _run_start_script(
    *,
    prune_on_startup: str,
    uv_should_fail: bool,
) -> tuple[subprocess.CompletedProcess[str], str]:
    backend_root = _backend_root()
    script = backend_root / "scripts" / "start.sh"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        fake_bin = temp_path / "bin"
        fake_bin.mkdir(parents=True, exist_ok=True)
        log_path = temp_path / "calls.log"

        _write_executable(
            fake_bin / "alembic",
            "#!/bin/sh\n"
            'echo "alembic $*" >> "$FAKE_STARTUP_LOG"\n'
            "exit 0\n",
        )
        _write_executable(
            fake_bin / "uv",
            "#!/bin/sh\n"
            'echo "uv $*" >> "$FAKE_STARTUP_LOG"\n'
            'if [ "${FAKE_UV_SHOULD_FAIL:-0}" = "1" ] \\\n'
            '  && [ "$1" = "run" ] \\\n'
            '  && [ "$2" = "python" ] \\\n'
            '  && [ "$3" = "scripts/prune_dismissed_notifications.py" ]; then\n'
            "  exit 1\n"
            "fi\n"
            "exit 0\n",
        )
        _write_executable(
            fake_bin / "uvicorn",
            "#!/bin/sh\n"
            'echo "uvicorn $*" >> "$FAKE_STARTUP_LOG"\n'
            "exit 0\n",
        )

        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{fake_bin}:{env.get('PATH', '')}",
                "FAKE_STARTUP_LOG": str(log_path),
                "FAKE_UV_SHOULD_FAIL": "1" if uv_should_fail else "0",
                "DISMISSED_PRUNE_ON_STARTUP": prune_on_startup,
                "SYNC_DEFAULT_AVATARS_ON_STARTUP": "false",
                "UVICORN_RELOAD": "false",
            }
        )
        completed = subprocess.run(
            [str(script)],
            cwd=str(backend_root),
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        # Background prune can log slightly after uvicorn exits in tests.
        deadline = time.time() + 1.0
        while time.time() < deadline:
            if not log_path.exists():
                time.sleep(0.02)
                continue
            if prune_on_startup != "true":
                break
            content = log_path.read_text(encoding="utf-8")
            if "uv run python scripts/prune_dismissed_notifications.py" in content:
                break
            time.sleep(0.02)

        log_output = ""
        if log_path.exists():
            log_output = log_path.read_text(encoding="utf-8")

    return completed, log_output


def test_start_script_contains_migration_and_prune_commands() -> None:
    script = (_backend_root() / "scripts" / "start.sh").read_text(encoding="utf-8")
    migration_command = "alembic upgrade head"
    prune_command = "uv run python scripts/prune_dismissed_notifications.py"
    uvicorn_exec = "exec uvicorn"

    assert migration_command in script
    assert prune_command in script
    assert uvicorn_exec in script
    assert script.index(migration_command) < script.index(uvicorn_exec)
    assert script.index(prune_command) < script.index(uvicorn_exec)
    assert script.index(migration_command) < script.index(prune_command)


def test_start_script_supports_prune_opt_out() -> None:
    script = (_backend_root() / "scripts" / "start.sh").read_text(encoding="utf-8")

    assert 'PRUNE_ON_STARTUP="${DISMISSED_PRUNE_ON_STARTUP:-true}"' in script
    assert 'if [ "$PRUNE_ON_STARTUP" = "true" ]; then' in script
    assert 'Skipping dismissed-notification prune' in script


def test_start_script_keeps_startup_alive_when_prune_fails() -> None:
    completed, log_output = _run_start_script(
        prune_on_startup="true",
        uv_should_fail=True,
    )

    assert completed.returncode == 0
    assert "alembic upgrade head" in log_output
    assert "uv run python scripts/prune_dismissed_notifications.py" in log_output
    assert "uvicorn main:app --host 0.0.0.0 --port 8000" in log_output


def test_start_script_skips_prune_command_when_opted_out() -> None:
    completed, log_output = _run_start_script(
        prune_on_startup="false",
        uv_should_fail=False,
    )

    assert completed.returncode == 0
    assert "alembic upgrade head" in log_output
    assert "uv run python scripts/prune_dismissed_notifications.py" not in log_output
    assert "uvicorn main:app --host 0.0.0.0 --port 8000" in log_output


def test_dockerfile_uses_single_startup_script() -> None:
    dockerfile = (_backend_root() / "Dockerfile").read_text(encoding="utf-8")
    assert 'CMD ["./scripts/start.sh"]' in dockerfile


def test_docs_disabled_outside_local_and_test() -> None:
    from core.config import settings
    from app.main import create_app

    original_env = settings.app_env
    try:
        settings.app_env = "production"
        app = create_app()
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None
    finally:
        settings.app_env = original_env
