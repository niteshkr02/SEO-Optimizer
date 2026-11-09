"""Asynchronous DNS resolver with strict IP inspection and timeout boundaries."""

import asyncio
import socket

from app.core.config import settings
from app.core.errors import CrawlerTimeoutError, SSRFViolationError
from app.crawler.cidr import parse_ip, validate_ip_address


async def resolve_and_validate_hostname(
    hostname: str,
    port: int = 80,
    timeout: float = settings.DNS_RESOLVER_TIMEOUT_SECONDS,
) -> list[str]:
    """Resolves all IPv4 and IPv6 addresses for a hostname and validates each against CIDR denylists.

    Returns:
        List of validated IP address strings.

    Raises:
        SSRFViolationError: If any resolved IP is in a forbidden range or no answers returned.
        CrawlerTimeoutError: If DNS resolution exceeds configured timeout.
    """
    loop = asyncio.get_running_loop()

    try:
        # socket.getaddrinfo queries both AF_INET and AF_INET6
        addrinfo = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                socket.getaddrinfo,
                hostname,
                port,
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
            ),
            timeout=timeout,
        )
    except TimeoutError as exc:
        raise CrawlerTimeoutError(
            f"DNS resolution timed out for '{hostname}' ({timeout}s)"
        ) from exc
    except socket.gaierror as exc:
        raise SSRFViolationError(f"Could not resolve host '{hostname}': {exc}") from exc

    if not addrinfo:
        raise SSRFViolationError(f"No DNS records found for host '{hostname}'.")

    resolved_ips: list[str] = []

    for entry in addrinfo:
        sockaddr = entry[4]
        ip_str = sockaddr[0]

        # Validate IP against comprehensive CIDR denylist
        ip_obj = parse_ip(ip_str)
        try:
            validate_ip_address(ip_obj)
        except SSRFViolationError as exc:
            raise SSRFViolationError(
                f"Host '{hostname}' resolved to forbidden address {ip_str}: {exc.message}"
            ) from exc

        if ip_str not in resolved_ips:
            resolved_ips.append(ip_str)

    if not resolved_ips:
        raise SSRFViolationError(
            f"Host '{hostname}' resolved to zero valid public addresses."
        )

    return resolved_ips
