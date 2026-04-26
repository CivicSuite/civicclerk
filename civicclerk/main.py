"""FastAPI runtime foundation for CivicClerk."""

from __future__ import annotations

from fastapi import FastAPI

from civicclerk import __version__
from civiccore import __version__ as CIVICCORE_VERSION

app = FastAPI(
    title="CivicClerk",
    version=__version__,
    summary="Runtime foundation for CivicClerk municipal meeting workflows.",
)


@app.get("/")
async def root() -> dict[str, str]:
    """Describe what the runtime foundation currently provides."""
    return {
        "name": "CivicClerk",
        "status": "runtime foundation",
        "message": (
            "CivicClerk runtime foundation is online; meeting workflows are not implemented yet."
        ),
        "next_step": "Milestone 2: canonical schema and Alembic migrations",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Provide a simple operational health check for IT staff."""
    return {
        "status": "ok",
        "service": "civicclerk",
        "version": __version__,
        "civiccore": CIVICCORE_VERSION,
    }
