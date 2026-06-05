# Debug: find the correct way to provide a PIN in the WinRT
# PairingRequested handler.
import asyncio

from winrt.windows.devices.bluetooth import BluetoothLEDevice
from winrt.windows.devices.enumeration import (
    DevicePairingKinds,
    DevicePairingResultStatus,
)

ADDRESS = "FE:BE:2D:A2:35:1F"
PASSKEY = "723904"


def address_to_int(address):
    return int(address.replace(":", ""), 16)


async def main():
    device = await BluetoothLEDevice.from_bluetooth_address_async(
        address_to_int(ADDRESS)
    )
    pairing = device.device_information.pairing
    print("is_paired:", pairing.is_paired)
    custom = pairing.custom

    def on_pairing_requested(sender, args):
        print("kind:", args.pairing_kind)
        print("accept attrs:", [a for a in dir(args) if "accept" in a.lower()])
        # Try several call forms; report which one does not raise.
        deferral = args.get_deferral()
        for label, fn in [
            ("accept(pin)", lambda: args.accept(PASSKEY)),
            ("accept_with_password", getattr(args, "accept_with_password", None)),
        ]:
            if fn is None:
                continue
            try:
                fn()
                print(f"OK: {label}")
                break
            except Exception as exc:
                print(f"FAIL {label}: {type(exc).__name__} -> {exc}")
        deferral.complete()

    token = custom.add_pairing_requested(on_pairing_requested)
    try:
        result = await custom.pair_async(DevicePairingKinds.PROVIDE_PIN)
    finally:
        custom.remove_pairing_requested(token)
    print("status:", result.status, "paired ==", DevicePairingResultStatus.PAIRED)


if __name__ == "__main__":
    asyncio.run(main())
