"""Pure helpers for the Picus 2 line protocol (no I/O).

The firmware exchanges newline-terminated JSON. Commands look like
``{"no": 3, "data": "RUN_ASPIRATE 500 7"}``; responses are line based.
Control markers (``ACK``/``BEGIN``/``END``) and result tags (``OK``,
``NOT_ALLOWED``, ...) carry the command number as a trailing token, while
data lines (e.g. ``CP-7.0``) are untagged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import constants


def build_payload(number: int, command: str) -> bytes:
    """Build the wire bytes for a command.

    Args:
        number: Command sequence number echoed back in responses.
        command: Command string, e.g. ``"RUN_ASPIRATE 500 7"``.

    Returns:
        Encoded JSON line terminated with the firmware's line ending.
    """
    line = json.dumps({"no": number, "data": command})
    return (line + constants.command_terminator).encode("ascii")


def build_button_payload(button: str) -> bytes:
    """Build the wire bytes for a button-emulation command.

    Args:
        button: Button name, e.g. ``"TRIGGER_BUTTON_RIGHT"``.

    Returns:
        Encoded JSON line terminated with the firmware's line ending.
    """
    line = json.dumps({"button": button})
    return (line + constants.command_terminator).encode("ascii")


@dataclass
class ParsedLine:
    """A single decoded response line.

    Attributes:
        tag: First token, e.g. ``"ACK"``, ``"OK"``, or a data token.
        number: Trailing command number if present, else ``None``.
        is_button_event: True for ``{"button": ...}`` notifications.
        text: The full stripped line.
    """

    tag: str
    number: int | None
    is_button_event: bool
    text: str


def parse_line(raw: bytes) -> ParsedLine | None:
    """Parse one notification line.

    Args:
        raw: Raw bytes from a TX characteristic notification.

    Returns:
        A :class:`ParsedLine`, or ``None`` for an empty line.
    """
    text = raw.decode("ascii", "replace").strip()
    if not text:
        return None
    if text.startswith("{"):
        return ParsedLine(tag="", number=None, is_button_event=True, text=text)
    parts = text.split()
    number = None
    if len(parts) >= 2 and _is_int(parts[-1]):
        number = int(parts[-1])
    return ParsedLine(
        tag=parts[0], number=number, is_button_event=False, text=text
    )


def _is_int(token: str) -> bool:
    """Return True if ``token`` is a base-10 integer."""
    return token.lstrip("-").isdigit()


@dataclass
class CommandResponse:
    """Accumulated response for one command.

    Attributes:
        number: The command number this response belongs to.
        result: Result tag (e.g. ``"OK"``) if one was returned.
        data: Data lines returned between BEGIN and END.
        capturing: True once BEGIN was seen and before END.
        complete: True once the END marker arrived.
    """

    number: int
    result: str | None = None
    data: list[str] = field(default_factory=list)
    capturing: bool = False
    complete: bool = False

    def feed(self, line: ParsedLine) -> None:
        """Update state from one parsed line.

        Lines addressed to other command numbers and stray button
        events are ignored, so concurrent device chatter cannot corrupt
        this response.

        Args:
            line: A parsed notification line.
        """
        if line.is_button_event:
            return
        if line.tag in constants.control_tags:
            if line.number != self.number:
                return
            if line.tag == "BEGIN":
                self.capturing = True
            elif line.tag == "END":
                self.complete = True
            return
        if line.tag in constants.result_tags:
            if line.number == self.number:
                self.result = line.tag
            return
        if self.capturing:
            self.data.append(line.text)

    @property
    def ok(self) -> bool:
        """True if the command did not return an error result."""
        return self.result not in constants.error_results
