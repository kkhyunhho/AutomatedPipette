# Debug: connect to Picus 2 over BLE and send GET_VERSION once.
import asyncio
import sys

from bleak import BleakClient, BleakScanner

UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

DEVICE_NAME = "Picus-46980628"
COMMAND = '{"data":"GET_VERSION"}\r\n'
WAIT_SECONDS = 5.0


async def main():
    print(f"Scanning for {DEVICE_NAME} ...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if device is None:
        print("Device not found. Is it on and in range?")
        sys.exit(1)

    print(f"Found {device.address}. Connecting ...")

    def handle_rx(_, data: bytearray):
        print("received:", bytes(data))

    async with BleakClient(device) as client:
        await client.start_notify(UART_TX_CHAR_UUID, handle_rx)
        print("Connected. Sending:", COMMAND)
        await client.write_gatt_char(
            UART_RX_CHAR_UUID, COMMAND.encode(), response=False
        )
        await asyncio.sleep(WAIT_SECONDS)
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
