# Debug: interactive forward pipetting with real liquid over USB, using
# the picus2 module's serial transport. Pauses for the physical steps
# (mount tip, dip in liquid, move to destination). Run it directly in a
# terminal so the Enter prompts work:
#
#     PYTHONPATH=src .venv/bin/python claude_test/forward_pipetting_usb.py
#
# Flow: authorize motor control with NO tip (so nothing ejects; the
# client also sends AUTO 1) -> mount tip + dip -> aspirate -> move ->
# blow-out (dispense + home) -> release motor control.
import asyncio

from picus2 import Picus2Client

SERIAL_PORT = "/dev/ttyACM0"
VOLUME_UL = 500
PIPETTE_SPEED = 7


async def main():
    async with Picus2Client.over_serial(SERIAL_PORT) as pipette:
        print("connected:", pipette.is_connected)
        print("model:", await pipette.get_model())
        print("version:", await pipette.get_version())

        loop = asyncio.get_running_loop()

        async def wait_enter(prompt):
            await loop.run_in_executor(None, input, prompt)

        await wait_enter(
            "STEP 1: Make sure NO tip is attached, then press Enter "
            "to authorize motor control..."
        )
        await pipette.enable_motor_control()

        await wait_enter(
            f"STEP 2: Attach a fresh tip and dip it into the liquid, "
            f"then press Enter to ASPIRATE {VOLUME_UL} uL..."
        )
        await pipette.aspirate(VOLUME_UL, PIPETTE_SPEED)

        await wait_enter(
            "STEP 3: Lift the tip out and hold it over the destination, "
            "then press Enter to DISPENSE + blow-out..."
        )
        await pipette.blow_out(speed=PIPETTE_SPEED)

        await wait_enter(
            "STEP 4: Done. Press Enter to release motor control..."
        )
        await pipette.disable_motor_control()
        print("sequence complete")


if __name__ == "__main__":
    asyncio.run(main())
