from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docker_compose_stack_declares_real_runtime_services() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for service in ("postgres:", "redis:", "ollama:", "api:", "worker:", "beat:", "frontend:"):
        assert service in compose
    assert "pgvector/pgvector:pg17" in compose
    assert "redis:7.2-alpine" in compose
    assert "ollama/ollama:latest" in compose
    assert "postgresql+psycopg2://" in compose
    assert '"psycopg2-binary>=2.9.0,<3.0.0"' in pyproject
    assert "uvicorn\", \"civicclerk.main:app\"" in (ROOT / "Dockerfile.backend").read_text(encoding="utf-8")
    assert "celery -A civicclerk.worker worker" in compose
    nginx = (ROOT / "docker" / "nginx.conf").read_text(encoding="utf-8")
    assert "proxy_pass http://api:8776;" in nginx
    assert "proxy_pass http://api:8776/;" not in nginx
    assert "location = /public" in nginx
    assert "location /public/" in nginx
    assert "try_files /index.html =404;" in nginx


def test_docker_env_example_is_safe_for_local_rehearsal_only() -> None:
    example = (ROOT / "docs" / "examples" / "docker.env.example").read_text(encoding="utf-8")

    assert "CIVICCLERK_POSTGRES_PASSWORD=change-this-before-shared-use" in example
    assert "CIVICCLERK_STAFF_AUTH_MODE=open" in example
    assert "Do not commit a real .env file" in example


def test_celery_worker_module_has_healthcheck_task() -> None:
    from civicclerk.worker import healthcheck

    assert healthcheck.run() == "ok"


def test_docs_describe_compose_without_claiming_installer() -> None:
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "roadmap" / "mvp-plan.md").read_text(encoding="utf-8"),
        ]
    ).lower()

    assert "docker compose" in docs
    assert "postgresql 17" in docs
    assert "redis 7.2" in docs
    assert "installer" in docs
    assert "ships an installer" not in docs
    staff_shell = (ROOT / "docs" / "frontend-staff-shell.md").read_text(encoding="utf-8")
    assert "most legally sensitive staff surface" in staff_shell
    assert "immutable audit hash as proof" in staff_shell
