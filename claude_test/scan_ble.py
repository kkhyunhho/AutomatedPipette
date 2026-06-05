# Debug: scan nearby BLE devices to find the Picus 2 pipette name.
import asyncio

from bleak import BleakScanner


async def main():
    devices = await BleakScanner.discover(timeout=8.0)
    if not devices:
        print("No BLE devices found.")
        return
    for d in devices:
        name = d.name or "(no name)"
        marker = "  <-- PICUS?" if d.name and "picus" in d.name.lower() else ""
        print(f"{d.address}  {name}{marker}")


if __name__ == "__main__":
    asyncio.run(main())
