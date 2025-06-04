# inverter_telemetry.py

import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from huawei_solar import create_tcp_bridge, create_rtu_bridge, register_names as rn

# === Logging Setup ===
Path("logs").mkdir(exist_ok=True)
logger = logging.getLogger("telemetry")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler("logs/telemetry.log",
                                   maxBytes=5 * 1024 * 1024,
                                   backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# :contentReference[oaicite:6]{index=6}

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

# === Read Helper ===
async def read_param(bridge, register, label: str):
    """
    Reads a single register value and logs it.
    """
    try:
        result = await bridge.client.get(register, slave=bridge.slave_id)
        logger.info(f"[TELEMETRY] {label} = {result.value}")
        return result.value
    except Exception as e:
        logger.error(f"Failed to read {label}: {e}")
        return None

# :contentReference[oaicite:7]{index=7}

# === Telemetry Functions ===
async def read_active_power(bridge):
    return await read_param(bridge, rn.INV_ACTIVE_POWER, "Inverter Active Power (W)")

async def read_pv_power(bridge):
    return await read_param(bridge, rn.INV_PV_POWER, "PV String Power (W)")

async def read_grid_voltage(bridge):
    return await read_param(bridge, rn.INV_GRID_VOLTAGE, "Grid Voltage (V)")

async def read_grid_frequency(bridge):
    return await read_param(bridge, rn.INV_GRID_FREQUENCY, "Grid Frequency (Hz)")

async def read_battery_soc(bridge):
    return await read_param(bridge, rn.STORAGE_STATE_OF_CAPACITY, "Battery SoC (%)")

async def read_battery_power(bridge):
    return await read_param(bridge, rn.STORAGE_CHARGE_DISCHARGE_POWER, "Battery Charge/Discharge Power (W)")

async def read_inverter_status(bridge):
    return await read_param(bridge, rn.INV_OPERATION_STATE, "Inverter Operation State")

# Add any additional telemetry reads here (e.g. DC Voltage, AC Current, etc.)

async def poll_telemetry(bridge, interval: int = 5):
    """
    Continuously polls every telemetry point at the given interval (seconds).
    """
    logger.info("Telemetry polling started.")
    try:
        while True:
            await read_active_power(bridge)
            await read_pv_power(bridge)
            await read_grid_voltage(bridge)
            await read_grid_frequency(bridge)
            await read_battery_soc(bridge)
            await read_battery_power(bridge)
            await read_inverter_status(bridge)
            # … any other telemetry points you require
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("Telemetry polling stopped.")
    except Exception as e:
        logger.error(f"Telemetry poll error: {e}")

async def main_rtu():
    # Example RTU params
    port = "COM3"
    baudrate = 9600
    slave_id = 1
    bridge = await connect_rtu(port, baudrate, slave_id)
    if not bridge:
        logger.error("Exiting: RTU telemetry failed.")
        return

    poll_task = asyncio.create_task(poll_telemetry(bridge, interval=5))
    # Run for 2 minutes then stop (example); in real tests you may run indefinitely
    await asyncio.sleep(120)
    poll_task.cancel()
    await bridge.stop()
    logger.info("RTU telemetry test completed.")

async def main_tcp():
    # Example TCP params
    host = "192.168.1.100"
    port = 6607
    slave_id = 0
    password = "00000a"
    bridge = await connect_tcp(host, port, slave_id, password)
    if not bridge:
        logger.error("Exiting: TCP telemetry failed.")
        return

    poll_task = asyncio.create_task(poll_telemetry(bridge, interval=5))
    await asyncio.sleep(120)
    poll_task.cancel()
    await bridge.stop()
    logger.info("TCP telemetry test completed.")

if __name__ == "__main__":
    # By default, run TCP telemetry. Switch to asyncio.run(main_rtu()) for RTU.
    asyncio.run(main_tcp())
# Note: Adjust the host, port, slave_id, and password as needed for your setup.
# This script will continuously poll telemetry data from the inverter and log it.   