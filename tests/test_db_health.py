import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INFRA = ROOT / "infra"


def test_db_health():
    if subprocess.run(["which", "docker"], capture_output=True).returncode != 0:
        pytest.skip("docker not available")
    subprocess.run(["docker", "compose", "up", "-d", "db"], cwd=INFRA, check=True)
    container_id = subprocess.check_output(
        ["docker", "compose", "ps", "-q", "db"], cwd=INFRA, text=True
    ).strip()
    inspect_fmt = (
        "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}"
    )
    for _ in range(30):
        status = subprocess.check_output(
            ["docker", "inspect", "-f", inspect_fmt, container_id],
            text=True,
        ).strip()
        if status == "healthy":
            break
        if status in {"exited", "unhealthy"}:
            raise AssertionError(f"db container status {status}")
        time.sleep(1)
    else:
        raise AssertionError("db did not become healthy")
    try:
        env = os.environ.copy()
        env["DATABASE_URL"] = (
            "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres"
        )
        subprocess.run(
            ["alembic", "-c", str(ROOT / "alembic.ini"), "upgrade", "head"],
            check=True,
            env=env,
        )
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "seed_demo.py")],
            check=True,
            env=env,
        )
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "db_health.py")],
            check=True,
            env=env,
        )
    finally:
        subprocess.run(["docker", "compose", "down"], cwd=INFRA, check=True)
