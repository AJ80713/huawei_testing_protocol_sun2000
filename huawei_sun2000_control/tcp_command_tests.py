# tcp_command_tests.py

import asyncio
from tcp_battery_control import (
    connect_and_login,
    force_charge_duration,
    force_discharge_duration,
    stop_charge,
    shutdown_bridge,
)

# === Inverter Configuration ===

INVERTER_IP = "192.168.200.1"          # Replace with your inverter's IP address
PORT = 6607                            # Default Modbus TCP port for Huawei Sun2000
UNIT_ID = 0                            # Slave ID, typically 0 for single inverter
INSTALLER_PASSWORD = "00000a"          # Default installer-level password

async def run_cycle(bridge, power: int, duration: int):
    """
    Run one full charge/discharge cycle.

    Args:
        bridge: Connected Huawei inverter bridge.
        power: Power to use for both charging and discharging (in watts).
        duration: Duration of each session in minutes.
    """
    # --- Charge Phase ---
    print(f"Starting charge at {power}W for {duration} minute(s)...")
    await force_charge_duration(bridge, power=power, duration=duration)
    await asyncio.sleep(duration * 60)    # Wait for the full duration
    await stop_charge(bridge)
    print("Charge stopped.\n")

    # --- Discharge Phase ---
    print(f"Starting discharge at {power}W for {duration} minute(s)...")
    await force_discharge_duration(bridge, power=power, duration=duration)
    await asyncio.sleep(duration * 60)    # Wait for the full duration
    await stop_charge(bridge)
    print("Discharge stopped.\n")

async def main():
    """
    Main test sequence:
    Connects to the inverter and performs 3 full test cycles:
    - Charge and discharge at 100W
    - Charge and discharge at 200W
    - Charge and discharge at 300W
    """
    # Connect and authenticate
    bridge = await connect_and_login(
        host=INVERTER_IP,
        port=PORT,
        slave_id=UNIT_ID,
        password=INSTALLER_PASSWORD,
        delay=5  # Stabilization delay after login
    )

    # Exit if connection fails
    if not bridge:
        print("Failed to connect to inverter.")
        return

    try:
        # Run tests at 3 power levels
        for power in [500, 500, 500]:
            await run_cycle(bridge, power=power, duration=2)
    finally:
        # Always cleanly disconnect
        await shutdown_bridge(bridge)

if __name__ == "__main__":
    asyncio.run(main())
# This script is a test for the battery control functions.
# It connects to the inverter over TCP, performs a charge/discharge cycle,  
# and then shuts down the connection.
# The script is designed to be run in an asynchronous environment using asyncio.    
# It uses the asyncio.run() function to execute the main() coroutine.
# The script is structured to allow for easy modification and extension.    
# You can easily add more test cases or modify the existing ones.
# The script is designed to be run in an asynchronous environment using asyncio.
# It uses the asyncio.run() function to execute the main() coroutine.
