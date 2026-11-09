"""Comprehensive CIDR denylist parser and IP validator for SSRF prevention."""

import ipaddress

from app.core.errors import SSRFViolationError

# Forbidden IPv4 networks
FORBIDDEN_IPV4_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),  # This host / current network
    ipaddress.ip_network("10.0.0.0/8"),  # Private network (RFC 1918)
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT (RFC 6598)
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network(
        "169.254.0.0/16"
    ),  # Link-local & cloud metadata (AWS/GCP 169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),  # Private network (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),  # Documentation (TEST-NET-1)
    ipaddress.ip_network("192.88.99.0/24"),  # 6to4 relay anycast
    ipaddress.ip_network("192.168.0.0/16"),  # Private network (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),  # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),  # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),  # Documentation (TEST-NET-3)
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved for future use
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
]

# Forbidden IPv6 networks
FORBIDDEN_IPV6_NETWORKS = [
    ipaddress.ip_network("::1/128"),  # Loopback
    ipaddress.ip_network("::/128"),  # Unspecified
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6
    ipaddress.ip_network("64:ff9b::/96"),  # IPv4/IPv6 translation
    ipaddress.ip_network("100::/64"),  # Discard prefix
    ipaddress.ip_network("2001:db8::/32"),  # Documentation
    ipaddress.ip_network("2002::/16"),  # 6to4
    ipaddress.ip_network("fc00::/7"),  # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),  # Link-local unicast
    ipaddress.ip_network("ff00::/8"),  # Multicast
]


def parse_ip(ip_str: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Parses a string into an IPv4 or IPv6 address object."""
    try:
        return ipaddress.ip_address(ip_str)
    except ValueError as exc:
        raise SSRFViolationError(f"Malformed IP address: {ip_str}") from exc


def is_ip_allowed(ip: str | ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Returns True if the IP address is permitted (public routable)."""
    try:
        validate_ip_address(ip)
        return True
    except SSRFViolationError:
        return False


def validate_ip_address(
    ip: str | ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> None:
    """Validates an IP address against forbidden CIDR ranges.

    Raises:
        SSRFViolationError: If the IP falls inside any forbidden range or is not globally routable.
    """
    if isinstance(ip, str):
        ip_obj = parse_ip(ip)
    else:
        ip_obj = ip

    # Special handling for IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1)
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
        # Check against IPv4 blocklist using mapped IPv4
        ipv4_mapped = ip_obj.ipv4_mapped
        for forbidden in FORBIDDEN_IPV4_NETWORKS:
            if ipv4_mapped in forbidden:
                raise SSRFViolationError(
                    f"Forbidden IPv4-mapped IPv6 address {ip_obj} matches denylist {forbidden}"
                )
        if not ipv4_mapped.is_global:
            raise SSRFViolationError(
                f"IPv4-mapped IPv6 address {ip_obj} is not globally routable"
            )
        return

    if isinstance(ip_obj, ipaddress.IPv4Address):
        for forbidden in FORBIDDEN_IPV4_NETWORKS:
            if ip_obj in forbidden:
                raise SSRFViolationError(
                    f"Forbidden IPv4 address {ip_obj} matches denylist {forbidden}"
                )
        if not ip_obj.is_global:
            raise SSRFViolationError(f"IPv4 address {ip_obj} is not globally routable")

    elif isinstance(ip_obj, ipaddress.IPv6Address):
        for forbidden in FORBIDDEN_IPV6_NETWORKS:
            if ip_obj in forbidden:
                raise SSRFViolationError(
                    f"Forbidden IPv6 address {ip_obj} matches denylist {forbidden}"
                )
        if not ip_obj.is_global:
            raise SSRFViolationError(f"IPv6 address {ip_obj} is not globally routable")
