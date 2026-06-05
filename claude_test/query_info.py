# Debug: query read-only device info to learn the safe volume range
# before sending any motor (piston) commands.
import asyncio

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "Picus-46980628"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

QUERIES = [
    "GET_VERSION",
    "GET_MODEL",
    "GET_SERIAL",
    "GET_NOMINAL_VOLUME",
    "GET_MIN_VOLUME",
    "GET_BATTERY_LEVEL",
    "NO_ACTION",
]


async def main():
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if device is None:
        print("Device not found.")
        return

    def handle_rx(_, data: bytearray):
        text = bytes(data).decode("ascii", "replace").strip()
        print("   <<", text)

    async with BleakClient(device) as client:
        print("Connected:", client.is_connected)
        await client.start_notify(UART_TX_CHAR_UUID, handle_rx)
        for command in QUERIES:
            payload = '{"no": 0, "data":"' + command + '"}\r\n'
            print(">>", command)
            await client.write_gatt_char(
                UART_RX_CHAR_UUID, payload.encode(), response=False
            )
            await asyncio.sleep(1.5)
        print("done")


if __name__ == "__main__":
    asyncio.run(main())
