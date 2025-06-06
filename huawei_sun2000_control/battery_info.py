#!/usr/bin/env python3
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from huawei_solar import create_tcp_bridge
import huawei_solar.register_names as rn
from huawei_solar.registers import REGISTERS

# ─── CONFIGURE YOUR INVERTER HERE ────────────────────────────────────────────────
HOST     = "192.168.200.1"    # IP of your inverter
PORT     = 6607               # Modbus-TCP port (usually 502 or 6607)
PASSWORD = "00000a"           # Installer password
# ────────────────────────────────────────────────────────────────────────────────

# === Logging Setup ===
Path("logs").mkdir(exist_ok=True)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console = logging.StreamHandler()
console.setFormatter(fmt)
logger.addHandler(console)
file_handler = RotatingFileHandler("logs/battery_info.log", maxBytes=5e6, backupCount=3)
file_handler.setFormatter(fmt)
logger.addHandler(file_handler)

async def main():
    # 1) Connect to inverter CPU (slave 0)
    bridge = await create_tcp_bridge(HOST, PORT, 0)
    await bridge.login("installer", PASSWORD)
    logger.info("Logged in as installer on slave 0; waiting 5s…")
    await asyncio.sleep(5)

    # 2) Define the register-name constants for each mode
    discharge = [
        rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC,
        rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD,
        rn.STORAGE_FORCIBLE_DISCHARGE_POWER,
        rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE,
    ]
    charge = [
        rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC,
        rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD,
        rn.STORAGE_FORCIBLE_CHARGE_POWER,
        rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE,
    ]
    idle = [
        rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD,
        rn.STORAGE_FORCIBLE_CHARGE_POWER,
        rn.STORAGE_FORCIBLE_DISCHARGE_POWER,
        rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE,
    ]

    # 3) Print names & numeric addresses
    def dump(title, regs, trigger_value):
        print(f"\n--- {title} (trigger={trigger_value}) ---")
        for key in regs:
            r = REGISTERS[key]
            unit = r.unit if r.unit is not None else "–"
            print(f" • {key}: address {r.register}   unit={unit}")
    dump("Forced Discharge", discharge, 2)
    dump("Forced Charge",    charge,    1)
    dump("Forced Idle",      idle,      0)

    # 4) Static resolutions
    print("\nMinimum resolutions:")
    print(" • Power  → 1 W")
    print(" • Period → 1 min")

    # 5) Read back current values from the **battery** (slave ID 2)
    print("\nCurrent storage (slave 2) values:")
    for key in set(discharge + charge + idle):
        r = REGISTERS[key]
        try:
            resp = await bridge.client.get(r, slave=2)
            print(f" • {key}: {resp.value}")
        except Exception:
            print(f" • {key}: <read failed>")

    # 6) Clean up
    await bridge.stop()
    logger.info("Connection closed.")

if __name__ == "__main__":
    asyncio.run(main())
# This script reads and prints the forced charge/discharge settings of a Huawei battery inverter.
# It connects to the inverter, retrieves the current settings, and displays them in a user-friendly format.
