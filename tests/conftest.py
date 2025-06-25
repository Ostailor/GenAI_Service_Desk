import subprocess
import time
import pytest

def wait_for_container_healthy(service_name, infra_dir="infra", timeout=120):
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

@pytest.fixture(scope="session", autouse=True)
def ensure_services():
    # Start all required services
    subprocess.run(["docker", "compose", "up", "-d", "--build", "db", "qdrant", "ollama", "api"], cwd="infra", check=True)
    for service in ["db", "qdrant", "ollama", "api"]:
        wait_for_container_healthy(service)
    yield
    subprocess.run(["docker", "compose", "down"], cwd="infra", check=True)