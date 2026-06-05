# Debug: dry-run forward pipetting over BLE with an empty tip (no liquid).
# Enables motor control, initializes, aspirates a safe volume, blows out,
# then disables motor control. Watch the pipette for piston motion.
import asyncio

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "Picus-46980628"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

ASPIRATE_VOLUME_UL = 200
PIPETTE_SPEED = 7
BLOW_OUT_GO_HOME = 1
BLOW_OUT_DELAY_MS = 3000

# Each step: (command string, seconds to wait for the motion to finish).
STEPS = [
    ("ENABLE_MOTOR_CONTROL 1", 2.0),
    ("RUN_INIT", 6.0),
    (f"RUN_ASPIRATE {ASPIRATE_VOLUME_UL} {PIPETTE_SPEED}", 5.0),
    (f"BLOW_OUT {BLOW_OUT_GO_HOME} {PIPETTE_SPEED} {BLOW_OUT_DELAY_MS}", 7.0),
    ("ENABLE_MOTOR_CONTROL 0", 2.0),
]


async def main():
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if device is None:
        print("Device not found. Wake the pipette and retry.")
        return

    def handle_rx(_, data: bytearray):
        text = bytes(data).decode("ascii", "replace").strip()
        print("   <<", text)

    async with BleakClient(device) as client:
        print("Connected:", client.is_connected)
        await client.start_notify(UART_TX_CHAR_UUID, handle_rx)
        for index, (command, wait_seconds) in enumerate(STEPS):
            payload = '{"no": ' + str(index) + ', "data":"' + command + '"}\r\n'
            print(f">> [{index}] {command}")
            await client.write_gatt_char(
                UART_RX_CHAR_UUID, payload.encode(), response=False
            )
            await asyncio.sleep(wait_seconds)
        print("sequence complete")


if __name__ == "__main__":
    asyncio.run(main())
