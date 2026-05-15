# CivicClerk Windows Installer

This folder contains the unsigned Windows installer source package for CivicClerk.
It wraps the Docker Compose product stack and provides two daily-use shortcuts:

- `Start CivicClerk`: starts the existing Docker Compose stack and opens the staff app.
- `Install or Repair CivicClerk`: checks Docker Desktop, creates `.env` when needed, builds containers, starts the stack, waits for health checks, and opens the staff app.

## Requirements

- Windows 10 or newer.
- Docker Desktop for Windows with the engine running.
- Inno Setup 6 to build the setup executable from source.

## Build

From Git Bash, WSL, or another Bash shell with Inno Setup available:

```bash
bash installer/windows/build-installer.sh
```

Set `CIVICCLERK_VERSION=1.0.1` to override the version read from `pyproject.toml`, or set `ISCC=/path/to/ISCC.exe` if the compiler is installed outside the default locations.

## Unsigned Installer Warning

CivicClerk is a small free open-source project. The Windows installer is unsigned, and that is the supported path for this project. Windows SmartScreen may show "Unknown Publisher" or "Windows protected your PC" because Windows cannot verify a paid publisher certificate.

That warning is expected. It is OK to choose "More info" and then "Run anyway" when the installer came from the official CivicSuite GitHub release source or your IT team built it from verified CivicSuite source. Do not bypass the warning for installers from email attachments, chat links, mirrors, or any source you cannot verify.

## Install Behavior

The installer shows an in-wizard warning before interactive installs. Silent installs skip the dialog so IT can automate verified deployments, but the same rule applies: install only from official CivicSuite release artifacts or from source your organization verified and built.

The first install or repair creates `.env` from `docs/examples/docker.env.example`, generates a local PostgreSQL password, starts the Docker Compose stack, and keeps `CIVICCLERK_DEMO_SEED=1` unless an operator changes it. That seed creates Brookfield demo meetings, agenda intake, packets, notices, outcomes, minutes, and public archive data so a clerk can see a real workflow immediately.

`CIVICCLERK_STAFF_AUTH_MODE=protected` is the default and denies anonymous staff writes. Use `CIVICCLERK_STAFF_AUTH_MODE=open` only for a single-workstation rehearsal; change to bearer, OIDC, or trusted-header mode before any shared municipal deployment.

Uninstalling the Windows application stops the Docker Compose stack and removes the installed source files. Docker volumes are preserved so meeting data is not destroyed accidentally. Operators who intentionally want to erase local rehearsal data must run `docker compose down -v` from the install directory before or after uninstall.
