# Debug: pair with the device using its Bluetooth passkey (WinRT custom
# pairing), then send GET_VERSION over the bonded link.
import asyncio

from bleak import BleakClient, BleakScanner
from winrt.windows.devices.bluetooth import BluetoothLEDevice
from winrt.windows.devices.enumeration import (
    DevicePairingKinds,
    DevicePairingResultStatus,
)

DEVICE_NAME = "Picus-46980628"
ADDRESS = "FE:BE:2D:A2:35:1F"
PASSKEY = ""         # Differ with every minutes,
                     # check current PASSKEY in BlueTooth Settings

UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
COMMAND = '{"data":"GET_VERSION"}\r\n'


def address_to_int(address):
    return int(address.replace(":", ""), 16)


async def pair_device():
    device = await BluetoothLEDevice.from_bluetooth_address_async(
        address_to_int(ADDRESS)
    )
    if device is None:
        print("Could not resolve device for pairing.")
        return False

    pairing = device.device_information.pairing
    print("can_pair:", pairing.can_pair, "| is_paired:", pairing.is_paired)
    if pairing.is_paired:
        print("Stale pairing found; unpairing first ...")
        unpair = await pairing.unpair_async()
        print("Unpair status:", unpair.status)

    custom = pairing.custom

    def on_pairing_requested(sender, args):
        print("Pairing requested, kind:", args.pairing_kind)
        deferral = args.get_deferral()
        args.accept_with_pin(PASSKEY)
        deferral.complete()

    print(
        "pair methods:",
        [m for m in dir(custom) if m.startswith("pair")],
    )
    token = custom.add_pairing_requested(on_pairing_requested)
    try:
        result = await custom.pair_async(DevicePairingKinds.PROVIDE_PIN)
    finally:
        custom.remove_pairing_requested(token)

    print("Pairing status:", result.status)
    return result.status == DevicePairingResultStatus.PAIRED


async def send_command():
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if device is None:
        print("Device not found for command.")
        return

    def handle_rx(_, data: bytearray):
        print("  >> received:", bytes(data))

    async with BleakClient(device) as client:
        print("Connected:", client.is_connected)
        await client.start_notify(UART_TX_CHAR_UUID, handle_rx)
        print("Sending:", COMMAND.strip())
        await client.write_gatt_char(
            UART_RX_CHAR_UUID, COMMAND.encode(), response=False
        )
        await asyncio.sleep(8.0)
        print("done")


async def main():
    print("--- pairing ---")
    paired = await pair_device()
    if not paired:
        print("Pairing did not succeed; skipping command.")
        return
    print("--- sending command over bonded link ---")
    await send_command()


if __name__ == "__main__":
    asyncio.run(main())
