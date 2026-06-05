# Debug: send GET_VERSION with response=True to see if the ATT write
# is rejected (e.g. insufficient encryption -> bonding required).
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
        await client.start_notify(UART_TX_CHAR_UUID, handle_rx)
        try:
            print("Writing with response=True ...")
            await client.write_gatt_char(
                UART_RX_CHAR_UUID, COMMAND.encode(), response=True
            )
            print("Write-with-response ACCEPTED by device (ATT ok).")
        except Exception as exc:
            print("Write FAILED:", type(exc).__name__, "->", exc)

        await asyncio.sleep(6.0)
        print("done")


if __name__ == "__main__":
    asyncio.run(main())
