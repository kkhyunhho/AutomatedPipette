"""Asynchronous client for the Sartorius Picus 2 pipette (BLE or USB)."""

from __future__ import annotations

import asyncio
import logging

from . import constants, protocol
from .errors import (
    CommandError,
    CommandTimeoutError,
    DeviceNotFoundError,
    Picus2Error,
)
from .transport import BleTransport, SerialTransport, Transport

logger = logging.getLogger(__name__)

__all__ = [
    "Picus2Client",
    "Picus2Error",
    "CommandError",
    "CommandTimeoutError",
    "DeviceNotFoundError",
]


class Picus2Client:
    """Async client for the Picus 2 command interface over any transport.

    The same command protocol runs over BLE and USB serial; construct a
    client with :meth:`over_ble` or :meth:`over_serial`, or pass a
    :class:`~picus2.transport.Transport` directly. Motor commands need
    on-device authorization, performed by :meth:`enable_motor_control`,
    and the device must be in a pipetting mode rather than the
    mode-selection menu.

    Over BLE the pipette must already be bonded with the host (pair once
    via the operating system using the passkey shown under Settings ->
    Bluetooth). Over USB no pairing is needed.

    Example:
        async with Picus2Client.over_serial("/dev/ttyACM0") as pipette:
            await pipette.enable_motor_control()
            await pipette.aspirate(500, speed=7)
            await pipette.blow_out(speed=7)
            await pipette.disable_motor_control()
    """

    def __init__(
        self,
        transport: Transport,
        *,
        command_timeout: float = constants.default_command_timeout,
    ) -> None:
        """Initialize the client over an already-built transport.

        Args:
            transport: The link backend (see :meth:`over_ble`,
                :meth:`over_serial`).
            command_timeout: Seconds to wait for each command to finish.
        """
        self._transport = transport
        self._command_timeout = command_timeout
        self._number = 0
        self._pending: protocol.CommandResponse | None = None
        self._done = asyncio.Event()
        transport.set_line_handler(self._handle_line)

    @classmethod
    def over_ble(
        cls,
        device_name: str,
        *,
        command_timeout: float = constants.default_command_timeout,
        scan_attempts: int = constants.default_scan_attempts,
        scan_timeout: float = constants.scan_timeout,
    ) -> "Picus2Client":
        """Build a client that talks to the pipette over BLE.

        Args:
            device_name: Advertised name, e.g. ``"Picus-46980628"``.
            command_timeout: Seconds to wait for each command to finish.
            scan_attempts: Times to retry scanning; the pipette sleeps.
            scan_timeout: Seconds per scan attempt.

        Returns:
            A client backed by a :class:`BleTransport`.
        """
        transport = BleTransport(
            device_name,
            scan_attempts=scan_attempts,
            scan_timeout=scan_timeout,
        )
        return cls(transport, command_timeout=command_timeout)

    @classmethod
    def over_serial(
        cls,
        port: str | None = None,
        *,
        baud: int = constants.default_serial_baud,
        command_timeout: float = constants.default_command_timeout,
    ) -> "Picus2Client":
        """Build a client that talks to the pipette over USB serial.

        Args:
            port: USB port spec resolved at connect time: ``None``
                (auto-detect the pipette by USB identity ``24BC:2202``),
                an explicit device path (e.g. ``"/dev/ttyACM0"``), or a
                ``"VID:PID"`` / ``"VID:PID:SERIAL"`` hex string.
            baud: Baud rate; CDC-ACM ignores it but it must be valid.
            command_timeout: Seconds to wait for each command to finish.

        Returns:
            A client backed by a :class:`SerialTransport`.
        """
        transport = SerialTransport(port, baud=baud)
        return cls(transport, command_timeout=command_timeout)

    async def __aenter__(self) -> "Picus2Client":
        """Connect on entering an async context."""
        await self.connect()
        return self

    async def __aexit__(
        self, exc_type: object, exc: object, traceback: object
    ) -> None:
        """Disconnect on leaving an async context."""
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """True while the underlying transport link is up."""
        return self._transport.is_connected

    async def connect(self) -> None:
        """Open the transport and start receiving responses.

        Raises:
            DeviceNotFoundError: If the pipette cannot be reached.
        """
        await self._transport.connect()

    async def disconnect(self) -> None:
        """Close the transport if it is open."""
        await self._transport.disconnect()

    def _handle_line(self, raw: bytes) -> None:
        """Feed an incoming response line into the pending response."""
        line = protocol.parse_line(raw)
        if line is None:
            return
        logger.debug("recv %s", line.text)
        if self._pending is None:
            return
        self._pending.feed(line)
        if self._pending.complete:
            self._done.set()

    def _next_number(self) -> int:
        """Return the next command sequence number."""
        self._number += 1
        return self._number

    async def _write(self, payload: bytes) -> None:
        """Write raw bytes to the transport.

        Raises:
            Picus2Error: If the transport is not connected.
        """
        await self._transport.write(payload)

    async def _await_pending(
        self, command: str, timeout: float | None
    ) -> protocol.CommandResponse:
        """Wait for the in-flight command to complete.

        Args:
            command: Command string, used for error messages.
            timeout: Seconds to wait, or ``None`` for the default.

        Returns:
            The completed response.

        Raises:
            CommandTimeoutError: If no END arrives before the timeout.
        """
        try:
            await asyncio.wait_for(
                self._done.wait(), timeout or self._command_timeout
            )
        except asyncio.TimeoutError as error:
            raise CommandTimeoutError(f"no response for {command!r}") from error
        assert self._pending is not None
        return self._pending

    async def send_command(
        self,
        command: str,
        *,
        timeout: float | None = None,
        raise_on_error: bool = True,
    ) -> protocol.CommandResponse:
        """Send a command and wait for its complete response.

        Args:
            command: Command string, e.g. ``"GET_MODEL"``.
            timeout: Override the default per-command timeout.
            raise_on_error: Raise :class:`CommandError` on an error tag.

        Returns:
            The accumulated response.

        Raises:
            CommandTimeoutError: If no END arrives before the timeout.
            CommandError: If the firmware returns an error result and
                ``raise_on_error`` is True.
        """
        number = self._next_number()
        self._pending = protocol.CommandResponse(number=number)
        self._done.clear()
        await self._write(protocol.build_payload(number, command))
        response = await self._await_pending(command, timeout)
        if raise_on_error and response.result in constants.error_results:
            raise CommandError(command, response.result)
        return response

    async def press_button(self, button: str) -> None:
        """Emulate a physical button press (fire and forget).

        Args:
            button: Button name, e.g. ``"TRIGGER_BUTTON_RIGHT"``.
        """
        await self._write(protocol.build_button_payload(button))

    async def get_version(self) -> str:
        """Return the firmware version string (e.g. ``"CP-7.0"``)."""
        return _first_data(await self.send_command("GET_VERSION"))

    async def get_model(self) -> str:
        """Return the model string (e.g. ``"SINGLE_CHANNEL_1000UL"``)."""
        return _first_data(await self.send_command("GET_MODEL"))

    async def get_nominal_volume(self) -> int:
        """Return the nominal (maximum) volume in microliters."""
        response = await self.send_command("GET_NOMINAL_VOLUME")
        return int(_first_data(response))

    async def get_min_volume(self) -> int:
        """Return the minimum volume in microliters."""
        response = await self.send_command("GET_MIN_VOLUME")
        return int(_first_data(response))

    async def enable_motor_control(self) -> None:
        """Authorize motor control and enable automatic execution.

        ``ENABLE_MOTOR_CONTROL 1`` raises an on-device prompt; this
        answers YES, then sets ``AUTO 1`` so buffered motor commands run
        without a manual trigger.

        Note:
            Answering YES with a tip mounted ejects the tip as a
            one-time reset. Authorize with no tip to avoid ejection.

        Raises:
            CommandError: If authorization fails.
            CommandTimeoutError: If the prompt is never answered in time.
        """
        number = self._next_number()
        self._pending = protocol.CommandResponse(number=number)
        self._done.clear()
        await self._write(
            protocol.build_payload(number, "ENABLE_MOTOR_CONTROL 1")
        )
        await asyncio.sleep(constants.motor_prompt_delay)
        await self.press_button(constants.yes_button)
        response = await self._await_pending("ENABLE_MOTOR_CONTROL 1", None)
        if response.result in constants.error_results:
            raise CommandError("ENABLE_MOTOR_CONTROL 1", response.result)
        await self.send_command("AUTO 1")

    async def disable_motor_control(self) -> None:
        """Release motor control."""
        await self.send_command("ENABLE_MOTOR_CONTROL 0")

    async def aspirate(self, volume_ul: int, speed: int) -> None:
        """Aspirate ``volume_ul`` microliters at ``speed``."""
        _check_speed(speed)
        _check_volume(volume_ul)
        await self.send_command(f"RUN_ASPIRATE {volume_ul} {speed}")

    async def dispense(self, volume_ul: int, speed: int) -> None:
        """Dispense ``volume_ul`` microliters at ``speed``."""
        _check_speed(speed)
        _check_volume(volume_ul)
        await self.send_command(f"RUN_DISPENSE {volume_ul} {speed}")

    async def blow_out(
        self,
        *,
        speed: int,
        go_home: bool = True,
        delay_ms: int = constants.default_blow_out_delay_ms,
    ) -> None:
        """Blow out remaining liquid, optionally returning home.

        Args:
            speed: Motor speed (1..9).
            go_home: Return the piston home after the blow-out.
            delay_ms: Delay before the go-home move, in milliseconds.
        """
        _check_speed(speed)
        flag = 1 if go_home else 0
        await self.send_command(f"BLOW_OUT {flag} {speed} {delay_ms}")

    async def eject_tip(self) -> None:
        """Eject the mounted tip."""
        await self.send_command("TIP_EJECT")


def _first_data(response: protocol.CommandResponse) -> str:
    """Return the first data line of a response.

    Raises:
        Picus2Error: If the response carried no data line.
    """
    if not response.data:
        raise Picus2Error("expected a data line in the response")
    return response.data[0]


def _check_speed(speed: int) -> None:
    """Validate a motor speed.

    Raises:
        ValueError: If ``speed`` is outside the supported range.
    """
    if not constants.min_speed <= speed <= constants.max_speed:
        raise ValueError(
            f"speed must be {constants.min_speed}..{constants.max_speed}"
        )


def _check_volume(volume_ul: int) -> None:
    """Validate a volume is positive.

    Raises:
        ValueError: If ``volume_ul`` is not positive.
    """
    if volume_ul <= 0:
        raise ValueError("volume must be positive")
