"""SSRF-safe network transport with socket connection pinning to prevent DNS rebinding."""

import ssl
from collections.abc import Iterable

import httpcore
import httpx

from app.core.config import settings
from app.core.errors import SSRFViolationError
from app.crawler.cidr import is_ip_allowed, validate_ip_address
from app.crawler.dns_resolver import resolve_and_validate_hostname


class SSRFSafeNetworkBackend(httpcore.AnyIOBackend):
    """Custom network backend that enforces CIDR filtering and pins TCP connections directly to validated IPs."""

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        """Resolves DNS, inspects all IP answers, and connects TCP socket strictly to the pinned IP."""
        # 1. Check port restriction
        if port not in settings.ALLOWED_EGRESS_PORTS:
            raise SSRFViolationError(
                f"Egress port {port} is not permitted. Permitted ports: {settings.ALLOWED_EGRESS_PORTS}"
            )

        # 2. Check if host is already an IP address
        try:
            import ipaddress

            ipaddress.ip_address(host)
            validate_ip_address(host)
            pinned_ip = host
        except ValueError:
            # 3. Host is a domain name: resolve all A and AAAA records and check against denylist
            resolved_ips = await resolve_and_validate_hostname(
                host,
                port=port,
                timeout=timeout or settings.DNS_RESOLVER_TIMEOUT_SECONDS,
            )
            if not resolved_ips:
                raise SSRFViolationError(
                    f"Host '{host}' could not be resolved to any safe public IP."
                )
            pinned_ip = resolved_ips[0]

        # 4. Final safety assertion on the pinned target IP
        if not is_ip_allowed(pinned_ip):
            raise SSRFViolationError(
                f"Pinned IP '{pinned_ip}' is in a forbidden CIDR range."
            )

        # 5. Open TCP connection directly to the pre-validated IP address (eliminates DNS rebinding / TOCTOU)
        # The stream will retain server_hostname=host when start_tls is invoked, preserving SNI and cert checks
        return await super().connect_tcp(
            host=pinned_ip,
            port=port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


class SSRFSafeAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """Custom HTTPX Async transport that integrates SSRFSafeNetworkBackend into the connection pool."""

    def __init__(
        self,
        verify: ssl.SSLContext | str | bool = True,
        http1: bool = True,
        http2: bool = False,
        limits: httpx.Limits | None = None,
        **kwargs,
    ):
        pool_limits = limits or httpx.Limits(
            max_connections=50, max_keepalive_connections=10, keepalive_expiry=5.0
        )
        super().__init__(
            verify=verify, http1=http1, http2=http2, limits=pool_limits, **kwargs
        )

        # Replace underlying pool with SSRFSafeNetworkBackend
        backend = SSRFSafeNetworkBackend()
        ssl_context = (
            self._pool._ssl_context if hasattr(self._pool, "_ssl_context") else None
        )

        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl_context,
            max_connections=pool_limits.max_connections,
            max_keepalive_connections=pool_limits.max_keepalive_connections,
            keepalive_expiry=pool_limits.keepalive_expiry,
            http1=http1,
            http2=http2,
            network_backend=backend,
        )


def create_ssrf_safe_transport(verify_ssl: bool = True) -> SSRFSafeAsyncHTTPTransport:
    """Factory creating an SSRFSafeAsyncHTTPTransport instance."""
    limits = httpx.Limits(
        max_connections=50,
        max_keepalive_connections=10,
        keepalive_expiry=5.0,
    )
    return SSRFSafeAsyncHTTPTransport(
        verify=verify_ssl,
        http1=True,
        http2=False,
        limits=limits,
    )
