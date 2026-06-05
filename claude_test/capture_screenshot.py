# Debug: capture the pipette screen via the SCREENSHOT command so we can
# see on-screen prompts (e.g. the tip-ejection dialog) and their soft-key
# answers. Accumulates the Base64 payload between BEGIN and END markers.
import asyncio
import base64
import sys

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "Picus-46980628"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

# Format passed to SCREENSHOT: GIF, GIF_4BIT, BMP, BMP_RLE8.
SCREENSHOT_FORMAT = sys.argv[1] if len(sys.argv) > 1 else "BMP"
OUTPUT_PATH = f"claude_test/screenshot.{SCREENSHOT_FORMAT.split('_')[0].lower()}"
DONE_TIMEOUT_S = 15.0


async def main():
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if device is None:
        print("Device not found.")
        return

    buffer = bytearray()
    done = asyncio.Event()

    def handle_rx(_, data: bytearray):
        buffer.extend(bytes(data))
        if b"END 0" in buffer:
            done.set()

    async with BleakClient(device) as client:
        print("Connected:", client.is_connected)
        await client.start_notify(UART_TX_CHAR_UUID, handle_rx)
        payload = '{"no": 0, "data":"SCREENSHOT ' + SCREENSHOT_FORMAT + '"}\r\n'
        print(">> SCREENSHOT", SCREENSHOT_FORMAT)
        await client.write_gatt_char(
            UART_RX_CHAR_UUID, payload.encode(), response=False
        )
        try:
            await asyncio.wait_for(done.wait(), timeout=DONE_TIMEOUT_S)
        except asyncio.TimeoutError:
            print("Timed out waiting for END.")

    raw = bytes(buffer)
    print("total bytes received:", len(raw))
    print("preview:", raw[:80])

    # Slice the Base64 payload that sits between the BEGIN and END markers.
    start = raw.find(b"BEGIN 0")
    end = raw.find(b"END 0")
    if start == -1 or end == -1:
        print("Markers not found; saved raw dump instead.")
        with open("claude_test/screenshot_raw.bin", "wb") as handle:
            handle.write(raw)
        return
    start = raw.find(b"\n", start) + 1
    b64 = raw[start:end].strip()
    print("base64 length:", len(b64))
    try:
        image = base64.b64decode(b64)
        with open(OUTPUT_PATH, "wb") as handle:
            handle.write(image)
        print("saved image:", OUTPUT_PATH, "bytes:", len(image))
    except Exception as exc:
        print("decode failed:", type(exc).__name__, "->", exc)
        with open("claude_test/screenshot_b64.txt", "wb") as handle:
            handle.write(b64)
        print("saved raw base64 for inspection.")


if __name__ == "__main__":
    asyncio.run(main())
