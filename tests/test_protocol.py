"""Unit tests for the Picus 2 line protocol helpers."""

import json
import unittest

from picus2 import protocol
from picus2.protocol import CommandResponse, parse_line


class BuildPayloadTest(unittest.TestCase):
    """Tests for command and button payload encoding."""

    def test_command_payload_is_terminated_json(self):
        """A command encodes to terminated ``{"no", "data"}`` JSON."""
        payload = protocol.build_payload(3, "GET_MODEL")
        self.assertTrue(payload.endswith(b"\r\n"))
        body = json.loads(payload.decode("ascii").strip())
        self.assertEqual(body, {"no": 3, "data": "GET_MODEL"})

    def test_button_payload(self):
        """A button command encodes to ``{"button"}`` JSON."""
        payload = protocol.build_button_payload("TRIGGER_BUTTON_RIGHT")
        body = json.loads(payload.decode("ascii").strip())
        self.assertEqual(body, {"button": "TRIGGER_BUTTON_RIGHT"})


class ParseLineTest(unittest.TestCase):
    """Tests for single-line parsing."""

    def test_empty_line_returns_none(self):
        """A blank line parses to ``None``."""
        self.assertIsNone(parse_line(b"\r\n"))

    def test_tagged_marker_keeps_number(self):
        """A control marker exposes its tag and command number."""
        line = parse_line(b"END 5\r\n")
        self.assertEqual(line.tag, "END")
        self.assertEqual(line.number, 5)

    def test_data_line_has_no_number(self):
        """A data line has no trailing command number."""
        line = parse_line(b"CP-7.0\r\n")
        self.assertEqual(line.tag, "CP-7.0")
        self.assertIsNone(line.number)

    def test_button_event_is_flagged(self):
        """A JSON button notification is flagged as a button event."""
        line = parse_line(b'{"button":"TOP_PRESSED"}\r\n')
        self.assertTrue(line.is_button_event)


class CommandResponseTest(unittest.TestCase):
    """Tests for response accumulation."""

    def _feed(self, response, *raw_lines):
        """Feed several raw lines into ``response``."""
        for raw in raw_lines:
            response.feed(parse_line(raw))

    def test_action_command_collects_result(self):
        """An action command records its OK result and completes."""
        response = CommandResponse(number=2)
        self._feed(
            response,
            b"ACK 2\r\n",
            b"BEGIN 2\r\n",
            b"OK 2\r\n",
            b"END 2\r\n",
        )
        self.assertTrue(response.complete)
        self.assertEqual(response.result, "OK")
        self.assertTrue(response.ok)

    def test_query_collects_data(self):
        """A query records its untagged data line and stays ok."""
        response = CommandResponse(number=1)
        self._feed(
            response,
            b"ACK 1\r\n",
            b"BEGIN 1\r\n",
            b"CP-7.0\r\n",
            b"END 1\r\n",
        )
        self.assertEqual(response.data, ["CP-7.0"])
        self.assertIsNone(response.result)
        self.assertTrue(response.ok)

    def test_error_result_is_not_ok(self):
        """An error result tag marks the response as not ok."""
        response = CommandResponse(number=4)
        self._feed(
            response,
            b"ACK 4\r\n",
            b"BEGIN 4\r\n",
            b"NOT_ALLOWED 4\r\n",
            b"END 4\r\n",
        )
        self.assertEqual(response.result, "NOT_ALLOWED")
        self.assertFalse(response.ok)

    def test_ignores_other_numbers_and_button_events(self):
        """Foreign command numbers and button events are ignored."""
        response = CommandResponse(number=7)
        self._feed(
            response,
            b"ACK 7\r\n",
            b"BEGIN 7\r\n",
            b'{"button":"TOP_PRESSED"}\r\n',
            b"OK 9\r\n",
            b"END 9\r\n",
            b"OK 7\r\n",
            b"END 7\r\n",
        )
        self.assertEqual(response.result, "OK")
        self.assertEqual(response.data, [])
        self.assertTrue(response.complete)


if __name__ == "__main__":
    unittest.main()
