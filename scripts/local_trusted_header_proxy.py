from __future__ import annotations

import argparse
import http.client
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


DEFAULT_PRINCIPAL_HEADER = "X-Forwarded-Email"
DEFAULT_ROLES_HEADER = "X-Forwarded-Roles"
DEFAULT_UPSTREAM = "http://127.0.0.1:8000"
DEFAULT_LISTEN_HOST = "127.0.0.1"
DEFAULT_LISTEN_PORT = 8010
DEFAULT_PRINCIPAL = "clerk@example.gov"
DEFAULT_ROLES = "clerk_admin,meeting_editor"
PRINCIPAL_HEADER_ENV_VAR = "CIVICCLERK_STAFF_SSO_PRINCIPAL_HEADER"
ROLES_HEADER_ENV_VAR = "CIVICCLERK_STAFF_SSO_ROLES_HEADER"
UPSTREAM_ENV_VAR = "CIVICCLERK_LOCAL_PROXY_UPSTREAM"
LISTEN_HOST_ENV_VAR = "CIVICCLERK_LOCAL_PROXY_LISTEN_HOST"
LISTEN_PORT_ENV_VAR = "CIVICCLERK_LOCAL_PROXY_LISTEN_PORT"
PRINCIPAL_ENV_VAR = "CIVICCLERK_LOCAL_PROXY_PRINCIPAL"
ROLES_ENV_VAR = "CIVICCLERK_LOCAL_PROXY_ROLES"
ALLOWED_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
REQUEST_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class ProxyConfig:
    upstream_url: str
    listen_host: str
    listen_port: int
    principal_header_name: str
    roles_header_name: str
    principal: str
    roles: str


class LocalTrustedHeaderProxy(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], config: ProxyConfig) -> None:
        super().__init__(server_address, LocalTrustedHeaderProxyHandler)
        self.config = config


class LocalTrustedHeaderProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_DELETE(self) -> None:
        self._forward_request()

    def do_GET(self) -> None:
        self._forward_request()

    def do_HEAD(self) -> None:
        self._forward_request()

    def do_OPTIONS(self) -> None:
        self._forward_request()

    def do_PATCH(self) -> None:
        self._forward_request()

    def do_POST(self) -> None:
        self._forward_request()

    def do_PUT(self) -> None:
        self._forward_request()

    def _forward_request(self) -> None:
        config = self.server.config
        upstream_parts = urlsplit(config.upstream_url)
        connection_class = (
            http.client.HTTPSConnection if upstream_parts.scheme == "https" else http.client.HTTPConnection
        )
        upstream_path = f"{upstream_parts.path.rstrip('/')}{self.path}" if upstream_parts.path else self.path
        if not upstream_path.startswith("/"):
            upstream_path = f"/{upstream_path}"
        body = self._read_request_body()
        headers = self._build_upstream_headers(config)

        try:
            connection = connection_class(
                upstream_parts.hostname,
                upstream_parts.port,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            connection.request(self.command, upstream_path, body=body, headers=headers)
            upstream_response = connection.getresponse()
            response_body = upstream_response.read()
        except OSError as exc:
            self._send_proxy_failure(config.upstream_url, exc)
            return
        finally:
            try:
                connection.close()
            except UnboundLocalError:
                pass

        self.send_response(upstream_response.status, upstream_response.reason)
        for name, value in upstream_response.getheaders():
            lowered = name.lower()
            if lowered in {"connection", "content-length", "transfer-encoding"}:
                continue
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        if self.command != "HEAD" and response_body:
            self.wfile.write(response_body)

    def _build_upstream_headers(self, config: ProxyConfig) -> dict[str, str]:
        stripped_headers = {
            "host",
            "connection",
            "content-length",
            "transfer-encoding",
            config.principal_header_name.lower(),
            config.roles_header_name.lower(),
        }
        headers = {
            name: value
            for name, value in self.headers.items()
            if name.lower() not in stripped_headers
        }
        headers[config.principal_header_name] = config.principal
        headers[config.roles_header_name] = config.roles
        return headers

    def _read_request_body(self) -> bytes | None:
        raw_length = self.headers.get("Content-Length", "").strip()
        if not raw_length:
            return None
        try:
            length = int(raw_length)
        except ValueError:
            return None
        if length <= 0:
            return None
        return self.rfile.read(length)

    def _send_proxy_failure(self, upstream_url: str, exc: OSError) -> None:
        message = (
            f"Local trusted-header rehearsal proxy could not reach {upstream_url}. "
            "Start CivicClerk on the loopback upstream URL, then retry the request."
        )
        payload = message.encode("utf-8")
        self.send_response(502, "Bad Gateway")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)
        self.log_error("upstream request failed: %s", exc)

    def log_message(self, format: str, *args) -> None:
        return


def _require_loopback_host(host: str, label: str) -> str:
    resolved = host.strip().lower()
    if resolved not in ALLOWED_LOOPBACK_HOSTS:
        raise SystemExit(f"{label} must stay on loopback for rehearsal safety, got: {host}")
    return host.strip()


def _parse_upstream_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise SystemExit(f"Upstream URL must use http or https, got: {url}")
    if parsed.hostname is None:
        raise SystemExit(f"Upstream URL must include a hostname, got: {url}")
    _require_loopback_host(parsed.hostname, "Upstream host")
    return url


def _read_cli_args() -> ProxyConfig:
    parser = argparse.ArgumentParser(
        description="Loopback-only trusted-header proxy rehearsal helper for CivicClerk."
    )
    parser.add_argument(
        "--upstream",
        default=os.environ.get(UPSTREAM_ENV_VAR, DEFAULT_UPSTREAM),
        help="Loopback CivicClerk upstream URL, for example http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--listen-host",
        default=os.environ.get(LISTEN_HOST_ENV_VAR, DEFAULT_LISTEN_HOST),
        help="Loopback host to bind, for example 127.0.0.1",
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=int(os.environ.get(LISTEN_PORT_ENV_VAR, str(DEFAULT_LISTEN_PORT))),
        help="Loopback port to bind, for example 8010",
    )
    parser.add_argument(
        "--principal",
        default=os.environ.get(PRINCIPAL_ENV_VAR, DEFAULT_PRINCIPAL),
        help="Placeholder staff principal injected into the trusted principal header.",
    )
    parser.add_argument(
        "--roles",
        default=os.environ.get(ROLES_ENV_VAR, DEFAULT_ROLES),
        help="Comma-delimited placeholder staff roles injected into the trusted roles header.",
    )
    parser.add_argument(
        "--principal-header",
        default=os.environ.get(PRINCIPAL_HEADER_ENV_VAR, DEFAULT_PRINCIPAL_HEADER),
        help="Trusted principal header name expected by CivicClerk.",
    )
    parser.add_argument(
        "--roles-header",
        default=os.environ.get(ROLES_HEADER_ENV_VAR, DEFAULT_ROLES_HEADER),
        help="Trusted roles header name expected by CivicClerk.",
    )
    args = parser.parse_args()

    upstream_url = _parse_upstream_url(args.upstream.strip())
    listen_host = _require_loopback_host(args.listen_host, "Listen host")
    if not 1 <= args.listen_port <= 65535:
        raise SystemExit(f"Listen port must be between 1 and 65535, got: {args.listen_port}")
    principal_header_name = args.principal_header.strip() or DEFAULT_PRINCIPAL_HEADER
    roles_header_name = args.roles_header.strip() or DEFAULT_ROLES_HEADER
    principal = args.principal.strip() or DEFAULT_PRINCIPAL
    roles = args.roles.strip() or DEFAULT_ROLES

    return ProxyConfig(
        upstream_url=upstream_url,
        listen_host=listen_host,
        listen_port=args.listen_port,
        principal_header_name=principal_header_name,
        roles_header_name=roles_header_name,
        principal=principal,
        roles=roles,
    )


def main() -> None:
    config = _read_cli_args()
    server = LocalTrustedHeaderProxy((config.listen_host, config.listen_port), config)
    print(
        "Local trusted-header rehearsal proxy listening on "
        f"http://{config.listen_host}:{config.listen_port} -> {config.upstream_url}"
    )
    print(
        "Injecting headers "
        f"{config.principal_header_name}={config.principal} and "
        f"{config.roles_header_name}={config.roles}"
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
