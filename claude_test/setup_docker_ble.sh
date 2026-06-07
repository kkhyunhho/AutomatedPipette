#!/usr/bin/env bash
# Bring up the BlueZ stack inside the Docker container so bleak can reach
# the Picus 2 pipette. One-off bring-up helper (see claude_test/README.md).
#
# PREREQUISITE -- the container MUST share the host network namespace:
#   docker run --privileged --network host ...
# Without --network host, AF_BLUETOOTH sockets fail with EAFNOSUPPORT even
# though /sys/class/bluetooth/hci0 is visible. --privileged alone is NOT
# enough; Bluetooth sockets are network-namespace scoped.
#
# Usage: bash claude_test/setup_docker_ble.sh
set -euo pipefail

echo "== 1. Verify AF_BLUETOOTH is usable in this namespace =="
if ! python3 - <<'PY'
import socket, sys
try:
    socket.socket(31, socket.SOCK_RAW, 1).close()  # AF_BLUETOOTH, HCI
except OSError as err:
    print(f"  AF_BLUETOOTH unavailable: {err}")
    sys.exit(1)
print("  AF_BLUETOOTH OK")
PY
then
    echo "  FAIL: relaunch the container with --network host." >&2
    exit 1
fi

echo "== 2. Start the D-Bus system bus =="
mkdir -p /run/dbus
if [ -S /run/dbus/system_bus_socket ]; then
    echo "  already running"
else
    dbus-daemon --system --fork
    echo "  started"
fi

echo "== 3. Start bluetoothd =="
if pgrep -x bluetoothd >/dev/null; then
    echo "  already running"
else
    /usr/libexec/bluetooth/bluetoothd &
    sleep 2
    echo "  started"
fi

echo "== 4. Power on the adapter =="
bluetoothctl power on
bluetoothctl show | head -15

cat <<'NEXT'

== Next: bond the pipette (it only answers commands once bonded) ==
The pipette must be unpaired on any other host first. Then pair here:

  bluetoothctl
  > agent KeyboardOnly
  > default-agent
  > scan on            # wait for Picus-46980628 (FE:BE:2D:A2:35:1F)
  > scan off
  > pair FE:BE:2D:A2:35:1F
  > (enter the passkey from the device:
  >  Settings -> Bluetooth -> Bluetooth Passkey)
  > trust FE:BE:2D:A2:35:1F
  > quit

Then verify the round-trip with bleak:

  .venv/bin/python claude_test/diagnose_ble.py
NEXT
