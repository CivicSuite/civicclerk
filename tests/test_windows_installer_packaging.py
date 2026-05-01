from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_windows_installer_source_files_exist() -> None:
    for path in [
        "install.ps1",
        "installer/windows/civicclerk.iss",
        "installer/windows/build-installer.sh",
        "installer/windows/launch-install.ps1",
        "installer/windows/launch-start.ps1",
        "installer/windows/prereq-check.ps1",
        "installer/windows/README.md",
    ]:
        assert (ROOT / path).exists(), path


def test_install_script_creates_env_from_docker_template_and_starts_stack() -> None:
    script = _read("install.ps1")

    assert "docs\\examples\\docker.env.example" in script
    assert "CIVICCLERK_POSTGRES_PASSWORD=change-this-before-shared-use" in script
    assert "RandomNumberGenerator" in script
    assert "docker compose up -d --build" in script
    assert "http://127.0.0.1:$apiPort/health" in script
    assert "http://127.0.0.1:$webPort/" in script
    assert "CIVICCLERK_DEMO_SEED" in script
    assert "Open staff auth is only for a single-workstation rehearsal" in script


def test_launcher_scripts_have_actionable_failure_paths() -> None:
    prereq = _read("installer/windows/prereq-check.ps1")
    start = _read("installer/windows/launch-start.ps1")
    launch_install = _read("installer/windows/launch-install.ps1")

    assert "Install Docker Desktop for Windows" in prereq
    assert "Docker Desktop is not running" in prereq
    assert "Run the 'Install or Repair CivicClerk' shortcut first" in start
    assert "docker compose up -d" in start
    assert "prereq-check.ps1" in launch_install
    assert "install.ps1" in launch_install


def test_inno_setup_requires_version_and_bundles_product_sources() -> None:
    iss = _read("installer/windows/civicclerk.iss")

    assert "#error MyAppVersion must be supplied" in iss
    assert "OutputBaseFilename=CivicClerk-{#MyAppVersion}-Setup" in iss
    assert "PrivilegesRequired=lowest" in iss
    assert "Install or Repair CivicClerk" in iss
    assert "Start CivicClerk" in iss
    assert "docker-compose.yml" in iss
    assert "Dockerfile.backend" in iss
    assert "frontend\\*" in iss
    assert "Docker volumes are preserved" in iss


def test_build_script_resolves_version_and_checks_required_sources() -> None:
    build = _read("installer/windows/build-installer.sh")

    assert "CIVICCLERK_VERSION" in build
    assert "python3" in build
    assert "py -3" in build
    assert "pyproject.toml" in build
    assert "tomllib" in build
    assert "Python 3 was not found" in build
    assert "docs/examples/docker.env.example" in build
    assert "Inno Setup compiler was not found" in build
    assert "CivicClerk-$APP_VERSION-Setup.exe" in build


def test_installer_docs_do_not_overclaim_production_auth_or_data_deletion() -> None:
    docs = "\n".join(
        [
            _read("installer/windows/README.md"),
            _read("README.md"),
            _read("USER-MANUAL.md"),
            _read("docs/roadmap/mvp-plan.md"),
        ]
    )

    assert "unsigned" in docs.lower()
    assert "CIVICCLERK_STAFF_AUTH_MODE=open" in docs
    assert "single-workstation rehearsal" in docs
    assert "bearer or trusted-header" in docs
    assert "Docker volumes are preserved" in docs
    assert "CIVICCLERK_DEMO_SEED=1" in docs
