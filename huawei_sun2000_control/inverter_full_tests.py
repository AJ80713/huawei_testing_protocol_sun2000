# inverter_full_tests.py

import asyncio
import logging
from pathlib import Path
from inverter_register_map import main_tcp as generate_register_map_tcp
from inverter_telemetry import main_tcp as run_telemetry_tcp
from inverter_battery_control import (
    connect_tcp,
    force_charge_duration,
    force_discharge_duration,
    force_charge_soc,
    force_discharge_soc,
    stop_charge,
    shutdown_bridge
)
import inverter_register_map as rn

# === Logging for Full Test ===
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    filename="logs/full_test.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("full_test")

# :contentReference[oaicite:15]{index=15}

async def run_battery_cycles(bridge):
    """
    Execute:
      A. Two duration-based cycles at 500 W for 2 min
      B. Two SoC-based cycles: Charge to 80 %, Discharge to 20 % at 500 W
    """
    # --- Duration-based Cycle #1 (Charge 500 W, 2 min) ---
    logger.info("Starting duration-based charge @500 W for 2 min.")
    await force_charge_duration(bridge, power=500, duration=2)
    await asyncio.sleep(2 * 60)             # actual 2 minutes
    await stop_charge(bridge)
    logger.info("Duration-based charge stopped.")

    # --- Duration-based Cycle #2 (Discharge 500 W, 2 min) ---
    logger.info("Starting duration-based discharge @500 W for 2 min.")
    await force_discharge_duration(bridge, power=500, duration=2)
    await asyncio.sleep(2 * 60)
    await stop_charge(bridge)
    logger.info("Duration-based discharge stopped.")

    # --- SoC-based Cycle #1 (Charge to 80% @500 W) ---
    logger.info("Starting SoC-based charge to 80% @500 W.")
    await force_charge_soc(bridge, power=500, target_soc=80)
    # Poll until SoC ≥ 80% (max 10 min)
    for _ in range(20):
        soc = await bridge.client.get(rn.STORAGE_STATE_OF_CAPACITY, slave=bridge.slave_id)
        if soc.value >= 80:
            break
        await asyncio.sleep(30)
    await stop_charge(bridge)
    logger.info("SoC-based charge stopped at 80%.")

    # --- SoC-based Cycle #2 (Discharge to 20% @500 W) ---
    logger.info("Starting SoC-based discharge to 20% @500 W.")
    await force_discharge_soc(bridge, power=500, target_soc=20)
    for _ in range(20):
        soc = await bridge.client.get(rn.STORAGE_STATE_OF_CAPACITY, slave=bridge.slave_id)
        if soc.value <= 20:
            break
        await asyncio.sleep(30)
    await stop_charge(bridge)
    logger.info("SoC-based discharge stopped at 20%.")

async def full_tcp_sequence():
    """
    1. Generate register map over TCP
    2. Poll telemetry for 2 min over TCP
    3. Run battery control cycles over TCP
    """
    # (1) Generate Register Map
    await generate_register_map_tcp()
    logger.info("Register map generation complete.")

    # (2) Run Telemetry Polling for 2 mins
    # Launch telemetry in background, stop after 120 s
    logger.info("Starting telemetry polling for 2 minutes.")
    import inverter_telemetry
    telemetry_bridge = await inverter_telemetry.connect_tcp(
        host="192.168.1.100", port=6607, slave_id=0, password="00000a", delay=3
    )
    if telemetry_bridge:
        telemetry_task = asyncio.create_task(inverter_telemetry.poll_telemetry(telemetry_bridge, interval=5))
        await asyncio.sleep(120)
        telemetry_task.cancel()
        await telemetry_bridge.stop()
        logger.info("Telemetry polling run complete.")
    else:
        logger.error("Telemetry bridge failed; skipping telemetry.")

    # (3) Battery Control Cycles
    battery_bridge = await connect_tcp(host="192.168.1.100", port=6607, slave_id=0, password="00000a", delay=3)
    if not battery_bridge:
        logger.error("Battery-control bridge failed; skipping cycles.")
        return
    await run_battery_cycles(battery_bridge)
    await shutdown_bridge(battery_bridge)
    logger.info("Battery control cycles complete.")

if __name__ == "__main__":
    asyncio.run(full_tcp_sequence())
# This script runs a full sequence of tests on the inverter system:
# 1. Generates a register map over TCP      
# 2. Polls telemetry data for 2 minutes
# 3. Executes battery control cycles (charge/discharge) 
# It logs all actions and results to a file for later analysis.
# Note: Adjust the host, port, and password as needed for your specific inverter setup.
