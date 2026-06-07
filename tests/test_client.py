"""Tests for the transport-agnostic client behavior.

A fake transport stands in for BLE/USB so the request/response plumbing
can be exercised without hardware.
"""

import asyncio
import unittest

from picus2 import Picus2Client
from picus2.transport import Transport


class FakeTransport(Transport):
    """In-memory transport that records writes and injects responses."""

    def __init__(self) -> None:
        """Start disconnected with an empty write log."""
        super().__init__()
        self._connected = False
        self.writes: list[bytes] = []

    @property
    def is_connected(self) -> bool:
        """True once :meth:`connect` has been called."""
        return self._connected

    async def connect(self) -> None:
        """Mark the link as open."""
        self._connected = True

    async def disconnect(self) -> None:
        """Mark the link as closed."""
        self._connected = False

    async def write(self, payload: bytes) -> None:
        """Record an outgoing payload."""
        self.writes.append(payload)

    def feed(self, *lines: bytes) -> None:
        """Deliver canned response lines to the client handler."""
        for line in lines:
            self._emit(line)


class ClientTransportTest(unittest.IsolatedAsyncioTestCase):
    """The client should drive any transport that follows the protocol."""

    async def test_query_round_trip(self):
        """A query writes its command and returns the data line."""
        transport = FakeTransport()
        client = Picus2Client(transport)
        await client.connect()

        task = asyncio.create_task(client.send_command("GET_VERSION"))
        await asyncio.sleep(0)  # let send_command write and start waiting

        self.assertEqual(len(transport.writes), 1)
        self.assertIn(b"GET_VERSION", transport.writes[0])

        transport.feed(
            b"ACK 1\r\n", b"BEGIN 1\r\n", b"CP-7.0\r\n", b"END 1\r\n"
        )
        response = await task
        self.assertEqual(response.data, ["CP-7.0"])
        self.assertTrue(response.ok)

    async def test_error_result_raises(self):
        """An error result tag raises :class:`CommandError`."""
        from picus2 import CommandError

        transport = FakeTransport()
        client = Picus2Client(transport)
        await client.connect()

        task = asyncio.create_task(client.send_command("RUN_ASPIRATE 1 7"))
        await asyncio.sleep(0)
        transport.feed(
            b"ACK 1\r\n", b"BEGIN 1\r\n", b"NOT_ALLOWED 1\r\n", b"END 1\r\n"
        )
        with self.assertRaises(CommandError):
            await task


if __name__ == "__main__":
    unittest.main()
