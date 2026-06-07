"""Exception hierarchy for the Picus 2 client.

These live in their own module so that both :mod:`picus2.client` and
:mod:`picus2.transport` can import them without a circular dependency.
"""

from __future__ import annotations


class Picus2Error(Exception):
    """Base class for Picus 2 client errors."""


class DeviceNotFoundError(Picus2Error):
    """Raised when the pipette cannot be reached on a transport.

    Covers a BLE scan that finds nothing and a serial port that cannot
    be opened.
    """


class CommandTimeoutError(Picus2Error):
    """Raised when a command's END response does not arrive in time."""


class CommandError(Picus2Error):
    """Raised when the pipette returns an error result.

    Attributes:
        command: The command string that failed.
        result: The error result tag returned by the firmware.
    """

    def __init__(self, command: str, result: str | None) -> None:
        """Store the failing command and its error result."""
        super().__init__(f"command {command!r} returned {result}")
        self.command = command
        self.result = result
