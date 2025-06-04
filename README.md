
# Huawei Testing Protocol Sun2000

This repository contains Python scripts for interacting with a **Huawei Sun2000** inverter over Modbus RTU or TCP. The utilities allow you to read telemetry, generate register maps and run battery charge/discharge tests.

## Repository structure

```
 huawei_sun2000_control/
 ├── battery_info.py             # Dump battery related register values
 ├── inverter_battery_control.py # Common helpers for battery control
 ├── inverter_full_tests.py      # Example end‑to‑end test sequence
 ├── inverter_register_map.py    # Export all register values to CSV
 ├── inverter_telemetry.py       # Poll inverter telemetry
 ├── minimal_rtu_read.py         # Simple RTU read example
 ├── read_rtu.py                 # Basic Modbus‑RTU read utility
 ├── rtu_battery_control.py      # RTU battery control helper
 ├── rtu_command_tests.py        # Example RTU test script
 ├── tcp_battery_control.py      # TCP battery control helper
 └── tcp_command_tests.py        # Example TCP test script
```

A small set of dependency packages is vendored in `huawei_sun2000_control/packages/` for offline installation.

## Installation

1. Use **Python 3.10+**.
2. Create a virtual environment and install the dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install huawei_sun2000_control/packages/*.tar.gz
```

Alternatively install packages from PyPI: `huawei-solar`, `pymodbus`, `pyserial`, `backoff`, `pyserial-asyncio`, `typing_extensions`, and `pytz`.

## Basic usage

- Update connection settings (IP address, COM port, passwords) in each script before running.
- Telemetry polling via TCP:

```bash
python huawei_sun2000_control/inverter_telemetry.py
```

- Export a register map to CSV:

```bash
python huawei_sun2000_control/inverter_register_map.py
```

- Run the full test sequence combining telemetry and battery control:

```bash
python huawei_sun2000_control/inverter_full_tests.py
```

Logs are written to the `logs/` directory (rotating files are configured in most scripts).

## Example constants

`battery_info.py` shows typical configuration fields used across the scripts:

```python
HOST     = "192.168.200.1"    # IP of your inverter
PORT     = 6607               # Modbus-TCP port
PASSWORD = "00000a"           # Installer password
```

These constants appear near the top of that file and should be adjusted for your environment.【F:huawei_sun2000_control/battery_info.py†L12-L15】

The helper in `tcp_battery_control.py` demonstrates how a TCP connection is established and logged:

```python
async def connect_and_login(host: str, port: int, slave_id: int, password: str, delay: int = 5):
    """Connect to the inverter and perform installer login."""
    bridge = await create_tcp_bridge(host, port, slave_id)
    await bridge.login("installer", password)
    logging.info("Logged in as installer.")
    logging.info(f"Waiting {delay} seconds for inverter to stabilize...")
    await asyncio.sleep(delay)
    return bridge
```

【F:huawei_sun2000_control/tcp_battery_control.py†L33-L55】

The `inverter_full_tests.py` script orchestrates a sequence of charge/discharge cycles and telemetry collection, writing its output to `logs/full_test.log`:

```python
async def run_battery_cycles(bridge):
    """Execute:
      A. Two duration-based cycles at 500 W for 2 min
      B. Two SoC-based cycles: Charge to 80 %, Discharge to 20 % at 500 W"""
    logger.info("Starting duration-based charge @500 W for 2 min.")
    await force_charge_duration(bridge, power=500, duration=2)
    await asyncio.sleep(2 * 60)
    await stop_charge(bridge)
```

【F:huawei_sun2000_control/inverter_full_tests.py†L30-L39】

Refer to the individual scripts for more detailed inline comments on configuration and usage.

---
