# inverter_register_map.py

import asyncio
import csv
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from huawei_solar import create_tcp_bridge, create_rtu_bridge, register_names as rn

# === Logging Setup ===
Path("logs").mkdir(exist_ok=True)
logger = logging.getLogger("register_map")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler("logs/register_map.log",
                                   maxBytes=5 * 1024 * 1024,
                                   backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# :contentReference[oaicite:4]{index=4}

async def connect_rtu(port: str, baudrate: int, slave_id: int, delay: int = 3):
    """
    Connects via Modbus RTU to the inverter. No installer login is needed on RTU.
    """
    try:
        bridge = await create_rtu_bridge(port=port, baudrate=baudrate, slave_id=slave_id)
        logger.info(f"RTU connected: port={port}, baud={baudrate}, slave={slave_id}")
        await asyncio.sleep(delay)  # let the inverter settle
        return bridge
    except Exception as e:
        logger.error(f"RTU connection failed: {e}")
        return None

async def connect_tcp(host: str, port: int, slave_id: int, password: str, delay: int = 3):
    """
    Connects via Modbus TCP to the inverter and logs in as installer.
    """
    try:
        bridge = await create_tcp_bridge(host=host, port=port, slave_id=slave_id)
        await bridge.login("installer", password)
        logger.info("TCP connected & logged in as installer.")
        await asyncio.sleep(delay)
        return bridge
    except Exception as e:
        logger.error(f"TCP connection/login failed: {e}")
        return None

async def read_all_registers(bridge, out_csv: str):
    """
    Reads every register in register_names and writes to a CSV file.
    CSV columns: Register_Name, Address, Value.
    """
    fieldnames = ["Register_Name", "Address", "Value"]
    with open(out_csv, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for reg_name, register in rn.__dict__.items():
            # Only process actual register objects (skip private or non-register entries)
            if not hasattr(register, "address"):
                continue

            try:
                result = await bridge.client.get(register, slave=bridge.slave_id)
                writer.writerow({
                    "Register_Name": reg_name,
                    "Address": register.address,
                    "Value": result.value
                })
                logger.info(f"[MAP] {reg_name} (0x{register.address:X}) = {result.value}")
            except Exception as e:
                logger.error(f"Failed to read {reg_name} at {register.address}: {e}")
                writer.writerow({
                    "Register_Name": reg_name,
                    "Address": register.address,
                    "Value": "ERROR"
                })

async def main_rtu():
    # Example RTU parameters; change as needed:
    port = "COM3"
    baudrate = 9600
    slave_id = 1
    bridge = await connect_rtu(port, baudrate, slave_id)
    if not bridge:
        logger.error("Exiting: RTU bridge not established.")
        return
    await read_all_registers(bridge, out_csv="inverter_register_map_rtu.csv")
    await bridge.stop()
    logger.info("RTU register map export completed.")

async def main_tcp():
    # Example TCP parameters; change as needed:
    host = "192.168.1.100"
    port = 6607
    slave_id = 0
    installer_password = "00000a"
    bridge = await connect_tcp(host, port, slave_id, installer_password)
    if not bridge:
        logger.error("Exiting: TCP bridge not established.")
        return
    await read_all_registers(bridge, out_csv="inverter_register_map_tcp.csv")
    await bridge.stop()
    logger.info("TCP register map export completed.")

if __name__ == "__main__":
    # By default, run TCP; switch to asyncio.run(main_rtu()) for RTU.
    asyncio.run(main_tcp())
# To run the RTU version, change the last line to:
# asyncio.run(main_rtu())   
# To run the TCP version, keep the last line as is:
# asyncio.run(main_tcp())
# # This script will create a CSV file with all registers and their values.
# The CSV will be named `inverter_register_map_rtu.csv` or `inverter_register_map_tcp.csv` depending on the connection type.
#  # Make sure to adjust the port, baudrate, host, and password as needed for your setup.
# The script connects to a Huawei inverter via Modbus RTU or TCP, reads all registers defined in the `register_names` module,   
#  and writes them to a CSV file.
# The script supports both RTU and TCP connections, allowing you to choose based on your setup. 
# # The CSV file will contain the register name, address, and current value.
# The script logs all actions and errors to a rotating log file.                                                                                                                                                                                                                                                                                                                                                                                                                       
