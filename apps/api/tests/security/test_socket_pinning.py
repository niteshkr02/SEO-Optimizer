"""Security tests verifying low-level socket pinning and egress blocking."""

import pytest

from app.core.errors import SSRFViolationError
from app.crawler.transport import SSRFSafeNetworkBackend


@pytest.mark.asyncio
async def test_socket_pinning_rejects_forbidden_host_directly():
    """Verifies backend rejects connection attempts to loopback or private destinations."""
    backend = SSRFSafeNetworkBackend()

    with pytest.raises(SSRFViolationError):
        await backend.connect_tcp(host="127.0.0.1", port=80)

    with pytest.raises(SSRFViolationError):
        await backend.connect_tcp(host="169.254.169.254", port=80)

    with pytest.raises(SSRFViolationError):
        await backend.connect_tcp(host="10.0.0.5", port=80)

    with pytest.raises(SSRFViolationError):
        await backend.connect_tcp(host="localhost", port=80)


@pytest.mark.asyncio
async def test_socket_pinning_rejects_unpermitted_port():
    """Verifies backend rejects unpermitted egress ports before connecting."""
    backend = SSRFSafeNetworkBackend()

    with pytest.raises(SSRFViolationError):
        await backend.connect_tcp(host="93.184.216.34", port=22)

    with pytest.raises(SSRFViolationError):
        await backend.connect_tcp(host="93.184.216.34", port=8080)

