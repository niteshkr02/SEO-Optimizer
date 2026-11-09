"""Security tests verifying DNS pre-resolution and rebinding defenses."""

import pytest

from app.core.errors import SSRFViolationError
from app.crawler.dns_resolver import resolve_and_validate_hostname


@pytest.mark.asyncio
async def test_resolve_legitimate_domain():
    """Verifies that legitimate public domain resolves to safe IP addresses."""
    ips = await resolve_and_validate_hostname("dns.google", port=80)
    assert len(ips) > 0
    # 8.8.8.8 or 8.8.4.4 or 2001:4860:4860::8888
    for ip in ips:
        assert not ip.startswith(("127.", "10.", "192.168.", "169.254."))


@pytest.mark.asyncio
async def test_resolve_localhost_is_blocked():
    """Verifies that resolving localhost raises SSRFViolationError."""
    with pytest.raises(SSRFViolationError):
        await resolve_and_validate_hostname("localhost", port=80)

