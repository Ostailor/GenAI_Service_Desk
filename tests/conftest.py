import shutil
import subprocess
import time
from typing import Iterable

import pytest


def wait_for_container_healthy(
    service_name: str, infra_dir: str = "infra", timeout: int = 300
) -> None:
    """Poll Docker until the container for service_name is healthy."""
    container_id = subprocess.check_output(
        ["docker", "compose", "ps", "-q", service_name], cwd=infra_dir, text=True
    ).strip()
    inspect_fmt = (
        "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}"
    )
    start = time.time()
    while time.time() - start < timeout:
        status = subprocess.check_output(
            ["docker", "inspect", "-f", inspect_fmt, container_id], text=True
        ).strip()
        if status == "healthy":
            return
        if status in {"exited", "unhealthy"}:
            raise RuntimeError(f"{service_name} container status {status}")
        time.sleep(2)
    raise RuntimeError(f"{service_name} did not become healthy in time")


def wait_for_services(services: Iterable[str], infra_dir: str = "infra") -> None:
    for svc in services:
        wait_for_container_healthy(svc, infra_dir=infra_dir)


@pytest.fixture(scope="session", autouse=True)
def ensure_services() -> None:
    if shutil.which("docker") is None:
        pytest.skip("docker not available")
    services = ["db", "qdrant", "ollama", "api"]
    subprocess.run(
        [
            "docker",
            "compose",
            "up",
            "-d",
            "--build",
            *services,
        ],
        cwd="infra",
        check=True,
    )
    wait_for_services(services)
    yield
    subprocess.run(["docker", "compose", "down"], cwd="infra", check=True)
