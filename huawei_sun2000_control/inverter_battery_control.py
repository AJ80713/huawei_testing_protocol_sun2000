# inverter_battery_control.py

import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from huawei_solar import create_tcp_bridge, create_rtu_bridge, register_names as rn

# === Logging Setup ===
Path("logs").mkdir(exist_ok=True)
logger = logging.getLogger("battery_control")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler("logs/battery_control.log",
                                   maxBytes=5 * 1024 * 1024,
                                   backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# :contentReference[oaicite:9]{index=9}

# === Connection Helpers ===
async def connect_rtu(port: str, baudrate: int, slave_id: int, delay: int = 3):
    try:
        bridge = await create_rtu_bridge(port=port, baudrate=baudrate, slave_id=slave_id)
        logger.info(f"RTU connected: {port}@{baudrate}, slave={slave_id}")
        await asyncio.sleep(delay)
        return bridge
    except Exception as e:
        logger.error(f"RTU connect failed: {e}")
        return None

async def connect_tcp(host: str, port: int, slave_id: int, password: str, delay: int = 3):
    try:
        bridge = await create_tcp_bridge(host=host, port=port, slave_id=slave_id)
        await bridge.login("installer", password)
        logger.info("TCP connected & installer logged in.")
        await asyncio.sleep(delay)
        return bridge
    except Exception as e:
        logger.error(f"TCP connect/login failed: {e}")
        return None

# === Read/Write Helpers ===
async def ensure_and_set(bridge, register, value, label: str):
    """
    Writes `value` to `register` then reads it back to validate.
    """
    try:
        # For TCP: ensure logged in before every write
        if hasattr(bridge, "ensure_logged_in"):
            await bridge.ensure_logged_in()

        await bridge.set(register, value)
        logger.info(f"[SET] {label or register.name} = {value}")

        # Read back to validate
        result = await bridge.client.get(register, slave=bridge.slave_id)
        if result.value == value:
            logger.info(f"[VALIDATED] {label or register.name} = {result.value}")
        else:
            logger.warning(f"[MISMATCH] {label or register.name}: expected {value}, got {result.value}")
    except Exception as e:
        logger.error(f"Failed to set {label or register.name}: {e}")

async def read_param(bridge, register, label: str):
    """
    Reads one register’s value and logs it.
    """
    try:
        result = await bridge.client.get(register, slave=bridge.slave_id)
        logger.info(f"[READ] {label or register.name} = {result.value}")
        return result.value
    except Exception as e:
        logger.error(f"Failed to read {label or register.name}: {e}")
        return None

# :contentReference[oaicite:10]{index=10}

# === Monitoring Loop ===
async def monitor_stats(bridge, interval_seconds: int = 5):
    """
    While a charge/discharge session is active, log SoC and current power.
    """
    logger.info("[MONITOR] Starting battery stats monitoring.")
    try:
        while True:
            await read_param(bridge, rn.STORAGE_STATE_OF_CAPACITY, "SoC (%)")
            await read_param(bridge, rn.STORAGE_CHARGE_DISCHARGE_POWER, "Battery Power (W)")
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("[MONITOR] Monitoring stopped.")
    except Exception as e:
        logger.error(f"[MONITOR] Error: {e}")

# :contentReference[oaicite:11]{index=11}

# === Battery Control Commands ===

async def force_charge_duration(bridge, power: int, duration: int):
    """
    Force-charge at `power` W for `duration` minutes.
    Sequence per §4.2:
      1. Target SoC → 100 (full)
      2. Period (minutes) → duration
      3. Charge Power → power (W)
      4. Write 1 to STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE (trigger)
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC, 100, "Target SoC for Charge")
    await ensure_and_set(bridge, rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD, duration,
                         "Charge Duration (min)")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_POWER, power, "Charge Power (W)")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 1, "Trigger Charge")
    # Start monitoring in background
    bridge._monitor_task = asyncio.create_task(monitor_stats(bridge))

async def force_discharge_duration(bridge, power: int, duration: int):
    """
    Force-discharge at `power` W for `duration` minutes.
    Sequence per §4.2:
      1. Target SoC → 0 (empty)
      2. Period (minutes) → duration
      3. Discharge Power → power (W)
      4. Write 2 to STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE (trigger)
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC, 0, "Target SoC for Discharge")
    await ensure_and_set(bridge, rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD, duration,
                         "Discharge Duration (min)")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_DISCHARGE_POWER, power, "Discharge Power (W)")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 2, "Trigger Discharge")
    bridge._monitor_task = asyncio.create_task(monitor_stats(bridge))

async def force_charge_soc(bridge, power: int, target_soc: int):
    """
    Force charge until `target_soc` % is reached (regardless of time).
    Sequence per §4.2:
      1. Target SoC → target_soc
      2. Charge Power → power (W)
      3. Write 1 to STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC, target_soc, "Target SoC for Charge")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_POWER, power, "Charge Power (W)")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 1, "Trigger Charge")
    bridge._monitor_task = asyncio.create_task(monitor_stats(bridge))

async def force_discharge_soc(bridge, power: int, target_soc: int):
    """
    Force discharge until `target_soc` % is reached.
    Sequence per §4.2:
      1. Target SoC → target_soc
      2. Discharge Power → power (W)
      3. Write 2 to STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC, target_soc, "Target SoC for Discharge")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_DISCHARGE_POWER, power, "Discharge Power (W)")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 2, "Trigger Discharge")
    bridge._monitor_task = asyncio.create_task(monitor_stats(bridge))

async def stop_charge(bridge):
    """
    Stop any ongoing forced charge/discharge.
    Per §4.2: write 0 to the session-control register and cancel monitoring.
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD, 0, "Clear Duration (min)")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_POWER, 0, "Clear Charge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_DISCHARGE_POWER, 0, "Clear Discharge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 0, "Stop Charge/Discharge")

    monitor_task = getattr(bridge, "_monitor_task", None)
    if monitor_task and not monitor_task.done():
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    logger.info("Battery session stopped; inverter returns to idle/self-consumption.")

async def shutdown_bridge(bridge):
    """
    Gracefully close RTU/TCP bridge.
    """
    try:
        await bridge.stop()
        logger.info("Bridge closed.")
    except Exception as e:
        logger.error(f"Error closing bridge: {e}")
async def main_rtu():
    # Example RTU parameters; change as needed:
    port = "COM3"
    baudrate = 9600
    slave_id = 1
    bridge = await connect_rtu(port, baudrate, slave_id)
    if not bridge:
        logger.error("Exiting: RTU bridge not established.")
        return

    try:
        # Example usage of force charge for 30 minutes at 1000W
        await force_charge_duration(bridge, power=1000, duration=30)
        await asyncio.sleep(60)  # Let it run for a while
        await stop_charge(bridge)
    finally:
        await shutdown_bridge(bridge)   