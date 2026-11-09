"""Security tests verifying comprehensive CIDR denylist and IP validation."""

import pytest

from app.core.errors import SSRFViolationError
from app.crawler.cidr import is_ip_allowed, validate_ip_address


@pytest.mark.parametrize(
    "forbidden_ip,category",
    [
        # Loopback
        ("127.0.0.1", "IPv4 Loopback"),
        ("127.0.0.2", "IPv4 Loopback"),
        ("127.255.255.255", "IPv4 Loopback"),
        ("::1", "IPv6 Loopback"),
        # Cloud Metadata & Link-Local
        ("169.254.169.254", "AWS/GCP/Azure Metadata"),
        ("169.254.1.1", "IPv4 Link-Local"),
        ("fe80::1", "IPv6 Link-Local"),
        # Private RFC 1918
        ("10.0.0.1", "Private 10.0.0.0/8"),
        ("10.254.254.254", "Private 10.0.0.0/8"),
        ("172.16.0.1", "Private 172.16.0.0/12"),
        ("172.31.255.255", "Private 172.16.0.0/12"),
        ("192.168.0.1", "Private 192.168.0.0/16"),
        ("192.168.1.254", "Private 192.168.0.0/16"),
        ("fc00::1", "IPv6 Unique Local Address"),
        ("fd00::1", "IPv6 Unique Local Address"),
        # Carrier-Grade NAT
        ("100.64.0.1", "Carrier-Grade NAT (RFC 6598)"),
        ("100.127.255.255", "Carrier-Grade NAT (RFC 6598)"),
        # Current host / broadcast / multicast
        ("0.0.0.0", "Current network host"),
        ("224.0.0.1", "Multicast"),
        ("240.0.0.1", "Reserved"),
        ("255.255.255.255", "Broadcast"),
        ("ff02::1", "IPv6 Multicast"),
        # Documentation & Test Nets
        ("192.0.2.1", "TEST-NET-1"),
        ("198.51.100.1", "TEST-NET-2"),
        ("203.0.113.1", "TEST-NET-3"),
        ("2001:db8::1", "IPv6 Documentation"),
        # IPv4-Mapped IPv6
        ("::ffff:127.0.0.1", "IPv4-Mapped IPv6 Loopback"),
        ("::ffff:169.254.169.254", "IPv4-Mapped IPv6 Cloud Metadata"),
        ("::ffff:10.0.0.1", "IPv4-Mapped IPv6 RFC 1918"),
        ("::ffff:192.168.1.1", "IPv4-Mapped IPv6 RFC 1918"),
    ],
)
def test_forbidden_cidr_ips_are_rejected(forbidden_ip: str, category: str):
    """Verifies that all forbidden IP ranges raise SSRFViolationError and return False."""
    assert is_ip_allowed(forbidden_ip) is False, f"Expected {forbidden_ip} ({category}) to be forbidden"
    with pytest.raises(SSRFViolationError):
        validate_ip_address(forbidden_ip)


@pytest.mark.parametrize(
    "allowed_ip,label",
    [
        ("93.184.216.34", "example.com public IPv4"),
        ("8.8.8.8", "Google DNS public IPv4"),
        ("1.1.1.1", "Cloudflare DNS public IPv4"),
        ("142.250.190.46", "Google Search public IPv4"),
        ("2606:4700:4700::1111", "Cloudflare public IPv6"),
        ("2001:4860:4860::8888", "Google DNS public IPv6"),
    ],
)
def test_public_globally_routable_ips_are_permitted(allowed_ip: str, label: str):
    """Verifies that legitimate globally routable public IPs pass validation."""
    assert is_ip_allowed(allowed_ip) is True, f"Expected {allowed_ip} ({label}) to be permitted"
    # Should not raise
    validate_ip_address(allowed_ip)

