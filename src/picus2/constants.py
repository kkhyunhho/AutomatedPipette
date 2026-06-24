"""Constants for the Sartorius Picus 2 command interface (BLE and USB)."""

# Nordic UART Service UUIDs exposed by the Picus 2 over BLE.
uart_service_uuid = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
uart_rx_char_uuid = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
uart_tx_char_uuid = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

# USB serial defaults. The pipette enumerates as a CDC-ACM port, which
# ignores the baud rate, but the reference test uses 9600.
default_serial_baud = 9600

# USB identity of the Picus 2 CDC-ACM port. The Entris-II balance shares
# the Sartorius VID (24BC:0010), so the pipette is matched by full VID:PID,
# never the vendor ID alone. Used to resolve the port by USB identity
# instead of an arrival-order /dev/ttyACM* index.
usb_vid = 0x24BC
usb_pid = 0x2202

# Poll interval (seconds) for the serial reader; bounds shutdown latency.
serial_read_timeout = 0.2

# The firmware parses one command per line; every command ends with this.
command_terminator = "\r\n"

# Default seconds to wait for a command's END response.
default_command_timeout = 25.0

# Scanning defaults; the pipette sleeps quickly, so retries help.
default_scan_attempts = 3
scan_timeout = 10.0

# Seconds to wait after requesting motor control before answering the
# on-device authorization prompt.
motor_prompt_delay = 3.0

# Soft-key button that answers YES to the motor-control prompt.
yes_button = "TRIGGER_BUTTON_RIGHT"

# Inclusive motor speed bounds.
min_speed = 1
max_speed = 9

# Default blow-out delay before the go-home move, in milliseconds.
default_blow_out_delay_ms = 3000

# Result tag that indicates success.
result_ok = "OK"

# Result tags that indicate failure.
error_results = frozenset(
    {
        "FULL",
        "SYNTAX_ERROR",
        "ERROR_PARSING",
        "UNKNOWN_COMMAND",
        "MISSING_PARAMETERS",
        "CHK_ERROR",
        "NOT_ALLOWED",
        "FAILED",
        "MOTOR_CONTROL_ABORTED",
        "INVALID_PARAMETERS",
        "TIP_EJECT_ERROR",
        "RUN_TO_ZERO_ERROR",
        "UNDERSTEP_OVERSTEP_ERROR",
        "FATAL_ERROR",
    }
)

# Every recognized result tag.
result_tags = error_results | {result_ok}

# Control markers that frame every command's response.
control_tags = frozenset({"ACK", "BEGIN", "END"})
