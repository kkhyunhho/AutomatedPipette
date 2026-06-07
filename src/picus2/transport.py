"""Transport backends for the Picus 2 command interface.

The pipette speaks the same newline-framed JSON protocol over both
Bluetooth Low Energy (the Nordic UART Service) and USB serial (a CDC-ACM
port). A :class:`Transport` hides that difference: it opens a link,
writes command bytes, and delivers each complete response line to a
handler registered by the client.

Both backends import their third-party library lazily, so a program that
only uses USB does not need ``bleak`` installed, and vice versa.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable

from . import constants
from .errors import DeviceNotFoundError, Picus2Error

logger = logging.getLogger(__name__)

# Called with the raw bytes of one response line (terminator stripped).
LineHandler = Callable[[bytes], None]


class Transport(ABC):
    """A bidirectional link to the pipette's line protocol."""

    def __init__(self) -> None:
        """Initialize with no line handler registered."""
        self._line_handler: LineHandler | None = None

    def set_line_handler(self, handler: LineHandler) -> None:
        """Register the callback invoked with each received line.

        The handler is always invoked on the event loop thread, with the
        raw bytes of a single response line.

        Args:
            handler: Callable receiving one line of response bytes.
        """
        self._line_handler = handler

    def _emit(self, line: bytes) -> None:
        """Deliver one received line to the registered handler."""
        if self._line_handler is not None:
            self._line_handler(line)

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """True while the link is open."""

    @abstractmethod
    async def connect(self) -> None:
        """Open the link and begin delivering received lines.

        Raises:
            DeviceNotFoundError: If the pipette cannot be reached.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the link if it is open."""

    @abstractmethod
    async def write(self, payload: bytes) -> None:
        """Write raw command bytes to the link.

        Raises:
            Picus2Error: If the link is not open.
        """


class BleTransport(Transport):
    """BLE transport over the Nordic UART Service, backed by ``bleak``.

    The pipette must already be bonded with the host (pair once via the
    operating system using the passkey shown on the device).
    """

    def __init__(
        self,
        device_name: str,
        *,
        scan_attempts: int = constants.default_scan_attempts,
        scan_timeout: float = constants.scan_timeout,
    ) -> None:
        """Initialize the BLE transport.

        Args:
            device_name: Advertised name, e.g. ``"Picus-46980628"``.
            scan_attempts: Times to retry scanning before giving up.
            scan_timeout: Seconds per scan attempt.
        """
        super().__init__()
        self._device_name = device_name
        self._scan_attempts = scan_attempts
        self._scan_timeout = scan_timeout
        self._client: object | None = None

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
        from bleak import BleakClient, BleakScanner

        device = None
        for attempt in range(1, self._scan_attempts + 1):
            logger.info(
                "scanning for %s (attempt %d/%d)",
                self._device_name,
                attempt,
                self._scan_attempts,
            )
            device = await BleakScanner.find_device_by_name(
                self._device_name, timeout=self._scan_timeout
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
            constants.uart_tx_char_uuid, self._on_notify
        )
        logger.info("connected to %s over BLE", self._device_name)

    async def disconnect(self) -> None:
        """Close the BLE connection if it is open."""
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()
        self._client = None

    async def write(self, payload: bytes) -> None:
        """Write to the RX characteristic without a response.

        Raises:
            Picus2Error: If the link is not open.
        """
        if self._client is None:
            raise Picus2Error("not connected")
        await self._client.write_gatt_char(
            constants.uart_rx_char_uuid, payload, response=False
        )

    def _on_notify(self, _characteristic: object, data: bytearray) -> None:
        """Forward a TX notification as one response line."""
        self._emit(bytes(data))


class SerialTransport(Transport):
    """USB serial transport over a CDC-ACM port, backed by ``pyserial``.

    A background thread reads the port and splits the byte stream into
    ``\\r\\n``-terminated lines, marshalling each onto the event loop so
    the client's handler runs on the loop thread, as it does for BLE.
    """

    def __init__(
        self,
        port: str,
        *,
        baud: int = constants.default_serial_baud,
    ) -> None:
        """Initialize the serial transport.

        Args:
            port: Serial device path, e.g. ``"/dev/ttyACM0"``.
            baud: Baud rate; CDC-ACM ignores it but it must be valid.
        """
        super().__init__()
        self._port = port
        self._baud = baud
        self._serial: object | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._reader: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def is_connected(self) -> bool:
        """True while the serial port is open."""
        return self._serial is not None and self._serial.is_open

    async def connect(self) -> None:
        """Open the serial port and start the reader thread.

        Raises:
            DeviceNotFoundError: If the port cannot be opened.
        """
        import serial

        self._loop = asyncio.get_running_loop()
        try:
            self._serial = await self._loop.run_in_executor(
                None,
                lambda: serial.Serial(
                    self._port,
                    self._baud,
                    timeout=constants.serial_read_timeout,
                ),
            )
        except (serial.SerialException, OSError) as error:
            raise DeviceNotFoundError(
                f"could not open {self._port}: {error}"
            ) from error
        self._stop.clear()
        self._reader = threading.Thread(
            target=self._reader_loop,
            name="picus2-serial-reader",
            daemon=True,
        )
        self._reader.start()
        logger.info("opened %s over USB serial", self._port)

    async def disconnect(self) -> None:
        """Stop the reader thread and close the serial port."""
        self._stop.set()
        reader, self._reader = self._reader, None
        if reader is not None and self._loop is not None:
            await self._loop.run_in_executor(None, reader.join)
        if self._serial is not None:
            self._serial.close()
        self._serial = None

    async def write(self, payload: bytes) -> None:
        """Write command bytes to the serial port.

        Raises:
            Picus2Error: If the port is not open.
        """
        if self._serial is None or self._loop is None:
            raise Picus2Error("not connected")
        await self._loop.run_in_executor(None, self._serial.write, payload)

    def _reader_loop(self) -> None:
        """Read the port and dispatch each complete line (reader thread).

        Runs until :attr:`_stop` is set or the port errors. Reads in
        small bursts so shutdown latency stays near one poll interval.
        """
        buffer = bytearray()
        while not self._stop.is_set():
            try:
                waiting = self._serial.in_waiting
                chunk = self._serial.read(waiting or 1)
            except OSError:
                # The port was closed mid-read (e.g. on disconnect).
                break
            if not chunk:
                continue
            buffer.extend(chunk)
            while True:
                index = buffer.find(b"\n")
                if index < 0:
                    break
                line = bytes(buffer[:index])
                del buffer[: index + 1]
                self._dispatch(line)

    def _dispatch(self, line: bytes) -> None:
        """Hand one line to the event loop thread."""
        loop = self._loop
        if loop is not None:
            loop.call_soon_threadsafe(self._emit, line)
