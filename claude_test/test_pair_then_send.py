# Debug: pair (bond) via bleak first, then send GET_VERSION and wait.
import asyncio

from bleak import BleakClient, BleakScanner

UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
DEVICE_NAME = "Picus-46980628"
COMMAND = '{"data":"GET_VERSION"}\r\n'


async def main():
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if device is None:
        print("Device not found.")
        return

    def handle_rx(_, data: bytearray):
        print("  >> received:", bytes(data))

    async with BleakClient(device) as client:
        print("Connected:", client.is_connected)
        try:
            print("Pairing ...")
            paired = await client.pair()
            print("pair() returned:", paired)
        except Exception as exc:
            print("pair() FAILED:", type(exc).__name__, "->", exc)

        await client.start_notify(UART_TX_CHAR_UUID, handle_rx)
        print("Sending:", COMMAND.strip())
        await client.write_gatt_char(
            UART_RX_CHAR_UUID, COMMAND.encode(), response=False
        )
        await asyncio.sleep(8.0)
        print("done")


if __name__ == "__main__":
    asyncio.run(main())
