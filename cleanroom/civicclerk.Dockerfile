# syntax=docker/dockerfile:1.7

FROM --platform=linux/amd64 node:24-bookworm-slim@sha256:03eae3ef7e88a9de535496fb488d67e02b9d96a063a8967bae657744ecd513f2

ARG CIVICCLERK_REPO_URL=https://github.com/CivicSuite/civicclerk.git
ARG CIVICCLERK_COMMIT
ARG CIVICCORE_REPO_URL=https://github.com/CivicSuite/civiccore.git
ARG CIVICCORE_FREEZE_REF=v1.2.1
ARG COSIGN_VERSION=v3.0.6
ARG COSIGN_SHA256=c956e5dfcac53d52bcf058360d579472f0c1d2d9b69f55209e256fe7783f4c74

LABEL org.opencontainers.image.title="CivicMeetings CC-1 cleanroom harness"
LABEL org.opencontainers.image.description="Pinned cleanroom image for CivicMeetings against the CivicCore CO-7 freeze release."

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN test -n "${CIVICCLERK_COMMIT}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
        gzip \
        gnupg \
        openssl \
        python3 \
        python3-venv \
        tar \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/civicclerk-venv \
    && /opt/civicclerk-venv/bin/python -m pip install --upgrade pip
ENV PATH="/opt/civicclerk-venv/bin:${PATH}"

RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg \
        -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli

RUN docker --version

RUN curl -fsSL \
        "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64" \
        -o /usr/local/bin/cosign \
    && echo "${COSIGN_SHA256}  /usr/local/bin/cosign" | sha256sum -c - \
    && chmod 0755 /usr/local/bin/cosign \
    && cosign version

RUN git clone --filter=blob:none "${CIVICCORE_REPO_URL}" /workspace/civiccore-freeze \
    && cd /workspace/civiccore-freeze \
    && git fetch --depth 1 origin "${CIVICCORE_FREEZE_REF}" \
    && git checkout --detach "${CIVICCORE_FREEZE_REF}"

RUN git clone --filter=blob:none "${CIVICCLERK_REPO_URL}" /workspace/civicclerk \
    && cd /workspace/civicclerk \
    && git fetch --depth 1 origin "${CIVICCLERK_COMMIT}" \
    && git checkout --detach "${CIVICCLERK_COMMIT}" \
    && test "$(git rev-parse HEAD)" = "${CIVICCLERK_COMMIT}"

WORKDIR /workspace/civicclerk

RUN python -m pip install -e ".[dev]" \
    && npm --prefix frontend ci \
    && npx --prefix frontend playwright install --with-deps chromium

RUN install -m 0755 scripts/cleanroom/civicclerk-cleanroom-runner.sh /usr/local/bin/civicclerk-cleanroom-runner

ENV CIVICCLERK_REPO_URL="${CIVICCLERK_REPO_URL}"
ENV CIVICCLERK_COMMIT="${CIVICCLERK_COMMIT}"
ENV CIVICCORE_REPO_URL="${CIVICCORE_REPO_URL}"
ENV CIVICCORE_FREEZE_REF="${CIVICCORE_FREEZE_REF}"
ENV CLEANROOM_BASE_IMAGE="node:24-bookworm-slim"
ENV CLEANROOM_BASE_IMAGE_DIGEST="sha256:03eae3ef7e88a9de535496fb488d67e02b9d96a063a8967bae657744ecd513f2"
ENV CLEANROOM_COSIGN_VERSION="${COSIGN_VERSION}"
ENV CLEANROOM_COSIGN_SHA256="${COSIGN_SHA256}"

ENTRYPOINT ["civicclerk-cleanroom-runner"]
CMD ["online"]
