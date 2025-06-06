import asyncio
from rtu_battery_control import (
    connect_and_login_rtu,
    force_charge_duration,
    force_discharge_duration,
    stop_charge,
    shutdown_bridge,
)

# === RTU Configuration ===
COM_PORT = "COM3"  # your USB-RS485 adapter port
BAUDRATE = 9600  # inverter’s RTU baud rate
SLAVE_ID = 2  # RTU slave address


async def run_cycle(bridge, power: int, duration: int):
    """
    One full charge/discharge cycle:
      - Charge at `power` W for `duration` min
      - Stop
      - Discharge at `power` W for `duration` min
      - Stop
    """
    print(f"Starting charge at {power}W for {duration} minute(s)...")
    await force_charge_duration(bridge, power=power, duration=duration)
    await asyncio.sleep(duration * 60)
    await stop_charge(bridge)
    print("Charge stopped.\n")

    print(f"Starting discharge at {power}W for {duration} minute(s)...")
    await force_discharge_duration(bridge, power=power, duration=duration)
    await asyncio.sleep(duration * 60)
    await stop_charge(bridge)
    print("Discharge stopped.\n")


async def main():
    bridge = await connect_and_login_rtu(
        port=COM_PORT,
        baudrate=BAUDRATE,
        slave_id=SLAVE_ID,
        delay=5,  # seconds to wait after opening RTU link
    )
    if not bridge:
        print("Failed to connect to inverter over RTU.")
        return

    try:
        for p in [100, 200, 300]:
            await run_cycle(bridge, power=p, duration=2)
    finally:
        await shutdown_bridge(bridge)
        print("Script completed.")


if __name__ == "__main__":
    asyncio.run(main())
# This script is a test for the battery control functions.
# It connects to the inverter over RTU, performs a charge/discharge cycle,
# and then shuts down the connection.
