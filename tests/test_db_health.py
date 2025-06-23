import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"


def test_db_health():
    if subprocess.run(["which", "docker"], capture_output=True).returncode != 0:
        pytest.skip("docker not available")
    subprocess.run(["docker", "compose", "up", "-d", "db"], cwd=INFRA, check=True)
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
