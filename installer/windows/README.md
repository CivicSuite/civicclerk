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

Set `CIVICCLERK_VERSION=0.1.14` to override the version read from `pyproject.toml`, or set `ISCC=/path/to/ISCC.exe` if the compiler is installed outside the default locations.

## Enterprise Signing

By default, the build helper produces an unsigned setup executable. On a secured release-signing workstation, IT can opt into signing by setting:

```bash
export CIVICCLERK_SIGN_INSTALLER=true
export CIVICCLERK_SIGNTOOL_PATH="/c/Program Files (x86)/Windows Kits/10/bin/x64/signtool.exe"
export CIVICCLERK_SIGNING_CERT_SHA1="<certificate-thumbprint>"
export CIVICCLERK_SIGNING_TIMESTAMP_URL="<enterprise RFC 3161 timestamp URL>"
```

For PFX-based signing, use `CIVICCLERK_SIGNING_PFX=/secure/path/cert.pfx` and set `CIVICCLERK_SIGNING_PFX_PASSWORD_ENV` to the name of a populated password environment variable. Do not commit certificates or passwords. Run `python scripts/check_enterprise_installer_signing.py --artifact installer/windows/build/CivicClerk-0.1.14-Setup.exe` to verify the signing contract without printing secrets.

## Install Behavior

The installer is unsigned unless the enterprise signing profile above is used. Windows SmartScreen may warn that the publisher is unknown; choose "More info" and "Run anyway" only when the installer came from a trusted CivicSuite release source.

The first install or repair creates `.env` from `docs/examples/docker.env.example`, generates a local PostgreSQL password, starts the Docker Compose stack, and keeps `CIVICCLERK_DEMO_SEED=1` unless an operator changes it. That seed creates Brookfield demo meetings, agenda intake, packets, notices, outcomes, minutes, and public archive data so a clerk can see a real workflow immediately.

`CIVICCLERK_STAFF_AUTH_MODE=open` is suitable only for a single-workstation rehearsal. Change to bearer or trusted-header mode before any shared municipal deployment.

Uninstalling the Windows application stops the Docker Compose stack and removes the installed source files. Docker volumes are preserved so meeting data is not destroyed accidentally. Operators who intentionally want to erase local rehearsal data must run `docker compose down -v` from the install directory before or after uninstall.
