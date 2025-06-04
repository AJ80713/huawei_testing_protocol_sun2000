# tcp_battery_control.py

import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from huawei_solar import create_tcp_bridge, register_names as rn

# === Logging Setup ===

# Ensure the 'logs' directory exists
Path("logs").mkdir(exist_ok=True)

# Create a logger instance
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Define the log format
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Log to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Log to rotating file inside the logs directory
file_handler = RotatingFileHandler(
    "logs/battery_control.log", maxBytes=5 * 1024 * 1024, backupCount=3
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# === Connection and Disconnection Helpers ===

async def connect_and_login(host: str, port: int, slave_id: int, password: str, delay: int = 5):
    """
    Connect to the inverter and perform installer login.

    Args:
        host: IP address of the inverter.
        port: Modbus TCP port (usually 6607).
        slave_id: Device ID (usually 0).
        password: Installer password.
        delay: Wait time after login to stabilize.

    Returns:
        bridge: A connected HuaweiSolarBridge object.
    """
    try:
        bridge = await create_tcp_bridge(host, port, slave_id)
        await bridge.login("installer", password)
        logging.info("Logged in as installer.")
        logging.info(f"Waiting {delay} seconds for inverter to stabilize...")
        await asyncio.sleep(delay)
        return bridge
    except Exception as e:
        logging.error(f"Connection or login failed: {e}")
        return None

async def shutdown_bridge(bridge):
    """
    Gracefully stop the connection with the inverter.
    """
    try:
        await bridge.stop()
        logging.info("Bridge stopped successfully.")
    except Exception as e:
        logging.error(f"Failed to stop bridge: {e}")

# === Write Helper ===

async def ensure_and_set(bridge, register, value, label=""):
    """
    Set a register value and validate the result.

    Args:
        bridge: Connected inverter bridge.
        register: Target register from register_names.
        value: Value to write.
        label: Human-readable label for logging.
    """
    try:
        await bridge.ensure_logged_in()
        await bridge.set(register, value)
        logging.info(f"[SET] {label or register.name} = {value}")

        # Validate the write
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

    Args:
        bridge: Connected inverter bridge.
        register: Register to read.
        label: Human-readable label for logging.
    """
    try:
        result = await bridge.client.get(register, slave=bridge.slave_id)
        logging.info(f"[READ] {label or register.name} = {result.value}")
        return result.value
    except Exception as e:
        logging.error(f"Failed to read {label or register.name}: {e}")
        return None

# === Monitoring ===

async def monitor_stats(bridge, interval_seconds: int = 5):
    """
    Monitor SoC and battery power during an active session.

    Args:
        bridge: Connected inverter bridge.
        interval_seconds: How often to log stats.
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

# === Charge/Discharge Session Controls ===

async def force_charge_duration(bridge, power: int, duration: int = 0):
    """
    Force charge the battery for a given duration.

    Args:
        bridge: Connected inverter bridge.
        power: Charging power in watts.
        duration: Duration in minutes.
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC, 100, "Target SoC for Charge")
    await ensure_and_set(bridge, rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD, duration, "Charge Period")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_POWER, power, "Charge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 1, "Trigger Charge")

    bridge._monitor_task = asyncio.create_task(monitor_stats(bridge))

async def force_discharge_duration(bridge, power: int, duration: int = 0):
    """
    Force discharge the battery for a given duration.

    Args:
        bridge: Connected inverter bridge.
        power: Discharging power in watts.
        duration: Duration in minutes.
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC, 0, "Target SoC for Discharge")
    await ensure_and_set(bridge, rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD, duration, "Discharge Period")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_DISCHARGE_POWER, power, "Discharge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 2, "Trigger Discharge")

    bridge._monitor_task = asyncio.create_task(monitor_stats(bridge))

async def force_charge_soc(bridge, power: int, target_soc: int = 100):
    """
    Force charge until a specific SoC is reached.

    Args:
        bridge: Connected inverter bridge.
        power: Charging power in watts.
        target_soc: Target battery State of Capacity (0-100).
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC, target_soc, "Target SoC for Charge")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_POWER, power, "Charge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 1, "Trigger Charge")

    bridge._monitor_task = asyncio.create_task(monitor_stats(bridge))

async def force_discharge_soc(bridge, power: int, target_soc: int = 0):
    """
    Force discharge until a specific SoC is reached.

    Args:
        bridge: Connected inverter bridge.
        power: Discharging power in watts.
        target_soc: Target battery State of Capacity (0-100).
    """
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC, target_soc, "Target SoC for Discharge")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_DISCHARGE_POWER, power, "Discharge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 2, "Trigger Discharge")

    bridge._monitor_task = asyncio.create_task(monitor_stats(bridge))

async def stop_charge(bridge):
    await ensure_and_set(bridge, rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD, 0, "Discharge Period (min)")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_POWER, 0, "Charge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_DISCHARGE_POWER, 0, "Discharge Power")
    await ensure_and_set(bridge, rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE, 0, "Stop Charge/Discharge")

    monitor_task = getattr(bridge, "_monitor_task", None)
    if monitor_task and not monitor_task.done():
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

async def default_params(bridge):
    """
    Restore safe default inverter settings for battery operation.
    """
    await ensure_and_set(bridge, rn.STORAGE_CHARGING_CUTOFF_CAPACITY, 1000, "Max SoC (% x10)")
    await ensure_and_set(bridge, rn.STORAGE_DISCHARGING_CUTOFF_CAPACITY, 100, "Min SoC (% x10)")
    await ensure_and_set(bridge, rn.STORAGE_MAXIMUM_CHARGING_POWER, 3000, "Max Charging Power")
    await ensure_and_set(bridge, rn.STORAGE_MAXIMUM_DISCHARGING_POWER, 3000, "Max Discharging Power")
    await ensure_and_set(bridge, rn.STORAGE_CHARGE_FROM_GRID_FUNCTION, 1, "Charge From Grid Enable")
