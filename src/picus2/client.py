"""Asynchronous BLE client for the Sartorius Picus 2 pipette."""

from __future__ import annotations

import asyncio
import logging

from bleak import BleakClient, BleakScanner

from . import constants, protocol

logger = logging.getLogger(__name__)


class Picus2Error(Exception):
    """Base class for Picus 2 client errors."""


class DeviceNotFoundError(Picus2Error):
    """Raised when the pipette cannot be found while scanning."""


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


class Picus2Client:
    """Async BLE client for the Picus 2 command interface.

    The pipette must already be bonded with the host: pair once via the
    operating system using the passkey shown on the device under
    Settings -> Bluetooth (the passkey rotates, so read it just before
    pairing). Motor commands additionally need on-device authorization,
    performed by :meth:`enable_motor_control`, and the device must be in
    a pipetting mode rather than the mode-selection menu.

    Example:
        async with Picus2Client("Picus-46980628") as pipette:
            await pipette.enable_motor_control()
            await pipette.aspirate(500, speed=7)
            await pipette.blow_out(speed=7)
            await pipette.disable_motor_control()
    """

    def __init__(
        self,
        device_name: str,
        *,
        command_timeout: float = constants.default_command_timeout,
        scan_attempts: int = constants.default_scan_attempts,
    ) -> None:
        """Initialize the client.

        Args:
            device_name: Advertised name, e.g. ``"Picus-46980628"``.
            command_timeout: Seconds to wait for each command to finish.
            scan_attempts: Times to retry scanning; the pipette sleeps.
        """
        self._device_name = device_name
        self._command_timeout = command_timeout
        self._scan_attempts = scan_attempts
        self._client: BleakClient | None = None
        self._number = 0
        self._pending: protocol.CommandResponse | None = None
        self._done = asyncio.Event()

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
        """True while the BLE link is up."""
        return self._client is not None and self._client.is_connected

    async def connect(self) -> None:
        """Scan for the pipette and open a notifying BLE connection.

        Raises:
            DeviceNotFoundError: If the device is not found after the
                configured number of scan attempts.
        """
        device = None
        for attempt in range(1, self._scan_attempts + 1):
            logger.info(
                "scanning for %s (attempt %d/%d)",
                self._device_name,
                attempt,
                self._scan_attempts,
            )
            device = await BleakScanner.find_device_by_name(
                self._device_name, timeout=constants.scan_timeout
            )
            if device is not None:
                break
        if device is None:
            raise DeviceNotFoundError(
                f"{self._device_name} not found; is it awake and in range?"
            )
        self._client = BleakClient(device)
        await self._client.connect()
        await self._client.start_notify(
            constants.uart_tx_char_uuid, self._handle_rx
        )
        logger.info("connected to %s", self._device_name)

    async def disconnect(self) -> None:
        """Close the BLE connection if it is open."""
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()
        self._client = None

    def _handle_rx(self, _characteristic: object, data: bytearray) -> None:
        """Feed an incoming notification into the pending response."""
        line = protocol.parse_line(bytes(data))
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
        """Write raw bytes to the RX characteristic.

        Raises:
            Picus2Error: If the client is not connected.
        """
        if self._client is None:
            raise Picus2Error("not connected")
        await self._client.write_gatt_char(
            constants.uart_rx_char_uuid, payload, response=False
        )

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
