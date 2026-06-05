# Debug: inspect Picus 2 GATT table, then send GET_VERSION and wait.
import asyncio

from bleak import BleakClient, BleakScanner

UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

DEVICE_NAME = "Picus-46980628"
COMMAND = '{"data":"GET_VERSION"}\r\n'
WAIT_SECONDS = 8.0


async def main():
    print(f"Scanning for {DEVICE_NAME} ...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if device is None:
        print("Device not found.")
        return

    print(f"Found {device.address}. Connecting ...")

    def handle_rx(_, data: bytearray):
        print("  >> received:", bytes(data))

    async with BleakClient(device) as client:
        print("Connected:", client.is_connected)
        print("--- GATT services ---")
        for service in client.services:
            print(f"[service] {service.uuid}")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(f"    [char] {char.uuid}  ({props})")

        print("--- enabling notify on TX ---")
        await client.start_notify(UART_TX_CHAR_UUID, handle_rx)
        print("--- sending:", COMMAND.strip(), "---")
        await client.write_gatt_char(
            UART_RX_CHAR_UUID, COMMAND.encode(), response=False
        )
        print(f"--- waiting {WAIT_SECONDS}s for response ---")
        await asyncio.sleep(WAIT_SECONDS)
        print("--- done ---")


if __name__ == "__main__":
    asyncio.run(main())
