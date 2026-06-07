# Debug: send GET_VERSION to the Picus 2 over USB serial and read reply.
# Mirrors the BLE GET_VERSION smoke test but over /dev/ttyACM0.
import sys

import serial

PORT = "/dev/ttyACM0"
BAUD = 9600  # from the USB PowerShell reference; CDC-ACM ignores it anyway
COMMAND = '{"no": 0, "data":"GET_VERSION"}\r\n'
READ_TIMEOUT_S = 3.0


def main():
    print(f"Opening {PORT} @ {BAUD} 8N1 ...")
    with serial.Serial(PORT, BAUD, timeout=READ_TIMEOUT_S) as port:
        port.reset_input_buffer()
        print("Sending:", COMMAND.strip())
        port.write(COMMAND.encode())
        port.flush()

        print("--- reading reply lines (until END or timeout) ---")
        got_any = False
        for _ in range(10):
            line = port.readline()
            if not line:
                break
            got_any = True
            text = line.decode(errors="replace").rstrip()
            print("  >>", text)
            if "END" in text:
                break
        if not got_any:
            print("No reply. Is the pipette on and is this the right port?")
            sys.exit(1)


if __name__ == "__main__":
    main()
