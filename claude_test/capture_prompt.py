# Debug: trigger the start-of-pipetting flow, then screenshot the screen
# to see the tip-ejection prompt and its soft-key answers.
import asyncio
import base64

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "Picus-46980628"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
OUTPUT_PATH = "claude_test/prompt.bmp"


async def main():
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if device is None:
        print("Device not found.")
        return

    buffer = bytearray()
    screenshot_done = asyncio.Event()
    capturing = {"on": False}

    def handle_rx(_, data: bytearray):
        chunk = bytes(data)
        if not capturing["on"]:
            print("   <<", chunk.decode("ascii", "replace").strip())
        else:
            buffer.extend(chunk)
            if b"END 9" in buffer:
                screenshot_done.set()

    async with BleakClient(device) as client:
        print("Connected:", client.is_connected)
        await client.start_notify(UART_TX_CHAR_UUID, handle_rx)

        async def send(no, command, wait):
            payload = '{"no": ' + str(no) + ', "data":"' + command + '"}\r\n'
            print(f">> [{no}] {command}")
            await client.write_gatt_char(
                UART_RX_CHAR_UUID, payload.encode(), response=False
            )
            await asyncio.sleep(wait)

        await send(1, "ENABLE_MOTOR_CONTROL 1", 1.5)
        await send(2, "RUN_ASPIRATE 200 7", 3.0)

        capturing["on"] = True
        await send(9, "SCREENSHOT BMP", 0.0)
        try:
            await asyncio.wait_for(screenshot_done.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            print("screenshot timed out")
        capturing["on"] = False
        await send(8, "ENABLE_MOTOR_CONTROL 0", 1.0)

    raw = bytes(buffer)
    start = raw.find(b"BEGIN 9")
    end = raw.find(b"END 9")
    if start == -1 or end == -1:
        print("markers not found; raw len", len(raw))
        return
    start = raw.find(b"\n", start) + 1
    b64 = raw[start:end].strip()
    image = base64.b64decode(b64)
    with open(OUTPUT_PATH, "wb") as handle:
        handle.write(image)
    print("saved", OUTPUT_PATH, "bytes:", len(image))


if __name__ == "__main__":
    asyncio.run(main())
