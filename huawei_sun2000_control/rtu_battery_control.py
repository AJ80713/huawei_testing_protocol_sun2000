import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from huawei_solar import create_rtu_bridge, register_names as rn

# === Logging Setup ===
Path("logs").mkdir(exist_ok=True)  # Ensure logs/ exists
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File output (rotate at 5 MB, keep 3 backups)
file_handler = RotatingFileHandler("logs/battery_control.log",
                                   maxBytes=5 * 1024 * 1024,
                                   backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# === RTU Connection Helper ===
async def connect_and_login_rtu(port: str, baudrate: int, slave_id: int,
                                delay: int = 5):
    """
    Open an RTU bridge (no installer login over RTU),
    wait `delay` seconds for the inverter to stabilize, then return it.
    """
    try:
        bridge = await create_rtu_bridge(
            port=port, baudrate=baudrate, slave_id=slave_id
        )
        logging.info(f"Connected over RTU: port={port}, baudrate={baudrate}, slave={slave_id}")
        logging.info(f"Waiting {delay}s for inverter to stabilize…")
        await asyncio.sleep(delay)
        return bridge
    except Exception as e:
        logging.error(f"RTU connection failed: {e}")
        return None

# === Write Helper ===
async def ensure_and_set(bridge, register, value, label=""):
    """
    Write a register and then read it back to validate.
    """
    try:
        await bridge.set(register, value)
        logging.info(f"[SET] {label or register.name} = {value}")

        result = await bridge.client.get(register, slave=bridge.slave_id)
        if result.value == value:
            logging.info(f"[VALIDATED] {label or register.name} = {result.value}")
        else:
            logging.warning(f"[MISMATCH] {label or register.name}: expected {value}, got {result.value}")
    except Exception as e:
        logging.error(f"Failed to set {label or register.name}: {e}")

# === Read Helper ===
async def read_param(bridge, register, label=""):
    """
    Read a register value and log it.
    """
    try:
        result = await bridge.client.get(register, slave=bridge.slave_id)
        logging.info(f"[READ] {label or register.name} = {result.value}")
        return result.value
    except Exception as e:
        logging.error(f"Failed to read {label or register.name}: {e}")
        return None

# === Monitoring Loop ===
async def monitor_stats(bridge, interval_seconds: int = 5):
    """
    Background task: every `interval_seconds` log SoC and power.
    """
    logging.info("[MONITOR] Monitoring started.")
    try:
        while True:
            await read_param(bridge, rn.STORAGE_STATE_OF_CAPACITY, "State of Capacity")
            await read_param(bridge, rn.STORAGE_CHARGE_DISCHARGE_POWER, "Battery Charge/Discharge Power")
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logging.info("[MONITOR] Monitoring stopped.")
    except Exception as e:
        logging.error(f"[MONITOR] Error: {e}")

# === Charge/Discharge Controls ===
async def force_charge_duration(bridge, power: int, duration: int = 0):
    """
    Charge at `power` W for `duration` minutes.
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC, 100, "Target SoC for Charge")
    await ensure_and_set(bridge, rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD, duration, "Charge Period")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_POWER, power, "Charge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 1, "Trigger Charge")
    bridge._monitor_task = asyncio.create_task(monitor_stats(bridge))

async def force_discharge_duration(bridge, power: int, duration: int = 0):
    """
    Discharge at `power` W for `duration` minutes.
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC, 0, "Target SoC for Discharge")
    await ensure_and_set(bridge, rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD, duration, "Discharge Period")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_DISCHARGE_POWER, power, "Discharge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 2, "Trigger Discharge")
    bridge._monitor_task = asyncio.create_task(monitor_stats(bridge))

async def stop_charge(bridge):
    """
    Stop any ongoing charge/discharge and cancel monitoring.
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD, 0, "Discharge Period (min)")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_POWER, 0, "Charge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_DISCHARGE_POWER, 0, "Discharge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 0, "Stop Charge/Discharge")

    task = getattr(bridge, "_monitor_task", None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

async def shutdown_bridge(bridge):
    """
    Gracefully stop the connection.
    """
    try:
        await bridge.stop()
        logging.info("Bridge stopped successfully.")
    except Exception as e:
        logging.error(f"Failed to stop bridge: {e}")
