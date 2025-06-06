# ☀️ Huawei SUN2000 Inverter & Battery Characterization Library ⚡

A set of Python scripts to automate and test Huawei SUN2000 inverter and battery characterization over Modbus RTU/TCP.  
This library supports:  
- 🗺️ **Register-Map Export**  
- 📡 **Telemetry Polling**  
- 🔁 **Forced Charge/Discharge Tests (Time- & SoC-Based)**  
- ⚠️ **Behavior & Error Validation**  
- 📊 **Performance Curve Extraction**

All Modbus communication may be done over **RTU (RS-485)** or **TCP (Ethernet/Wi-Fi)**. Every script accepts command-line arguments to specify connection parameters—no YAML files are needed.

---

## 🧭 Table of Contents

1. [📌 Project Overview](#project-overview)  
2. [🔌 Prerequisites & Lab Setup](#prerequisites--lab-setup)  
3. [⚙️ Installation & Dependencies](#installation--dependencies)  
4. [🧪 Configuration Using Command-Line Arguments](#configuration-using-command-line-arguments)  
5. [📁 Directory Structure](#directory-structure)  
6. [🚀 Usage & Step-by-Step Guide](#usage--step-by-step-guide)  
   1. [📥 Register-Map Export (Section 4.2)](#register-map-export-section-42)  
   2. [📈 Telemetry Polling (Section 4.2)](#telemetry-polling-section-42)  
   3. [🔍 4.2 Behavior & Error Tests (Inverter Only)](#42-behavior--error-tests-inverter-only)  
   4. [🧵 End-to-End 4.2 Suite](#end-to-end-42-suite)  
   5. [⚡ 4.3 Behavior & Error Tests (Inverter + Battery)](#43-behavior--error-tests-inverter--battery)  
   6. [📊 Performance Measurements (Section 4.3)](#performance-measurements-section-43)  
7. [🧾 Register Reference](#register-reference)  
8. [📂 Example Logs & CSV Outputs](#example-logs--csv-outputs)  
9. [🛠️ Troubleshooting & FAQ](#troubleshooting--faq)  
10. [📜 License](#license)

---

## 📌 Project Overview

This repository contains Python scripts that implement Sections 4.2 and 4.3 of the IW-Inverter Testing Protocol for Huawei SUN2000-series inverters. The main goals are:

- 📋 Export a full Modbus register map (address → value) to CSV  
- 📡 Continuously poll live telemetry (inverter power, grid voltage, battery SoC, etc.)  
- 🔁 Run forced charge/discharge tests (both time-bound and SoC-bound)  
- ⚠️ Validate inverter behavior when parameters are empty or out of range  
- 📊 Extract performance data (battery capacity, charge/discharge power, efficiency tables)

All Modbus communication may be done over **RTU (RS-485)** or **TCP (Ethernet/Wi-Fi)**. Every script accepts command-line arguments to specify connection parameters—no YAML files are needed.

---

## 🔌 Prerequisites & Lab Setup

1. **Hardware**  
   - 🧠 **Huawei SUN2000 Inverter** (e.g. `SUN2000-3KTL-L1`, Firmware: `V200R001C00SPC148`)  
   - 🌐 **SUN2000 Dongle** (Model: `SDongleA-05`, Firmware: `V100R001C00SPC130`, SN: `TA223002340`) – provides Wi-Fi and Modbus TCP interface.  
   - 🔌 **RS-485 ↔ USB Adapter** (e.g. FTDI FT232R) for Modbus RTU.  
   - ⚡ **ESS Controller (DC/DC)** (Model: ESC, SN: `HV2210277351`, Software: `V100R002C00SPC624`) – connected to a LUNA2000 battery pack (SN: `LS2187411675`).  
   - 🔋 **LUNA2000 Battery Pack** (Li-ion).  
   - ⚙️ **Power Meter** (e.g. “Meter-1”) – measures grid-side values (connected downstream of inverter).

2. **Network & Inverter Configuration**  
   - 🌐 **Dongle IP**: `192.168.1.100` (confirm via inverter display or FusionSolar app).  
   - 🔒 **Modbus TCP Port**: `6607` (default).  
   - 🆔 **RTU Slave ID**: typically `1` (verify in inverter’s “Device Configuration → Modbus”).  
   - 🔑 **Installer Password (for TCP writes)**: default is `00000a` (verify on inverter or FusionSolar app).

3. **Lab Topology**  
   - The inverter communicates with the Dongle via RS-485. The Dongle shares a Wi-Fi network with your PC (e.g. 192.168.1.x/24).  
   - Downstream of the inverter, a power meter (“Meter-1”) is connected to measure grid voltages and currents.  
   - The battery pack and ESS controller are connected to inverter’s storage port. All Modbus traffic (inverter, meter, battery) is tunneled by the Dongle.  
   - For RTU tests, bypass the Dongle: connect the RS-485 USB adapter directly to inverter’s RS-485 port.

---

## ⚙️ Installation & Dependencies

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/YourOrg/SUN2000-Characterization.git
   cd SUN2000-Characterization
   ```

2. **Create & Activate a Python Virtual Environment**  
   - 🐧 **Linux / macOS**  
     ```bash
     python3.11 -m venv .venv
     source .venv/bin/activate
     ```   
   - 🪟 **Windows (PowerShell)**  
     ```powershell
     python3.11 -m venv .venv
     .\.venv\Scripts\Activate
     ```

3. **Install Python Dependencies**  
   The exact pinned versions are in `requirements.txt`. Run:  
   ```bash
   pip install -r requirements.txt
   ```
   The main dependencies include:  
   ```
   backoff==2.2.1
   huawei-solar==2.4.4
   pymodbus==3.8.4
   pyserial==3.5
   pyserial-asyncio==0.6
   pytz==2025.2
   typing_extensions==4.13.2
   ```

4. **(Linux Only) COM Port Permissions**  
   If you run RTU tests on Linux, ensure your user is in the `dialout` group:  
   ```bash
   sudo usermod -aG dialout $USER
   logout
   login again
   ```

---

## 🧪 Configuration Using Command-Line Arguments

Each script in `scripts/` (and the 4.2-only tests in `tests/`) uses Python’s `argparse` to accept necessary connection parameters. Below is the common pattern:

```python
import argparse
import asyncio
from huawei_solar import create_rtu_bridge, create_tcp_bridge

def parse_args():
    p = argparse.ArgumentParser(
        description="Brief description of the script’s function"
    )
    p.add_argument(
        "--mode",
        choices=["rtu", "tcp"],
        required=True,
        help="Connection mode: 'rtu' for RS-485, 'tcp' for Modbus TCP",
    )
    # RTU arguments
    p.add_argument("--port", help="COM port (Windows) or /dev/ttyUSBx (Linux) for RTU")
    p.add_argument("--baudrate", type=int, help="Baudrate for RTU (e.g. 9600)")
    p.add_argument("--slave_id", type=int, help="RTU slave ID (e.g. 1)")

    # TCP arguments
    p.add_argument("--host", help="Inverter IP address for TCP (e.g. 192.168.1.100)")
    p.add_argument("--tcp_port", type=int, default=6607, help="Modbus TCP port (default: 6607)")
    p.add_argument("--unit_id", type=int, help="TCP unit ID (slave ID, e.g. 0)")
    p.add_argument("--password", help="Installer password for TCP (e.g. 00000a)")

    # Additional script-specific arguments (e.g., interval, duration, power, soc)
    # Example for telemetry:
    p.add_argument("--interval", type=int, default=5, help="Telemetry poll interval (s)")
    p.add_argument("--duration", type=int, default=120, help="Total telemetry duration (s)")

    return p.parse_args()

async def main():
    args = parse_args()
    if args.mode == "rtu":
        if not (args.port and args.baudrate and args.slave_id is not None):
            raise RuntimeError("RTU mode requires --port, --baudrate, and --slave_id")
        bridge = await create_rtu_bridge(
            port=args.port, baudrate=args.baudrate, slave_id=args.slave_id
        )
    else:
        if not (args.host and args.unit_id is not None and args.password):
            raise RuntimeError("TCP mode requires --host, --unit_id, and --password")
        bridge = await create_tcp_bridge(
            host=args.host, port=args.tcp_port, slave_id=args.unit_id
        )
        await bridge.login("installer", args.password)

    # Now call the script’s core logic, e.g.:
    # await poll_telemetry(bridge, interval=args.interval, duration=args.duration)

if __name__ == "__main__":
    asyncio.run(main())
```

- **RTU example**  
  ```bash
  python scripts/inverter_telemetry.py \
    --mode rtu \
    --port COM3 --baudrate 9600 --slave_id 1 \
    --interval 5 --duration 120
  ```
- **TCP example**  
  ```bash
  python scripts/inverter_telemetry.py \
    --mode tcp \
    --host 192.168.1.100 --tcp_port 6607 --unit_id 0 --password 00000a \
    --interval 5 --duration 120
  ```

All other scripts follow the same pattern—just replace the “additional script-specific arguments” with whatever is needed (power, duration, SoC, etc.).

---

## 📁 Directory Structure

```
SUN2000-Characterization/
├── LICENSE                          # MIT License text
├── CONTRIBUTING.md                  # Contributing guidelines (short)
├── README.md                        # ← You are here
├── requirements.txt                 # Python dependencies (pinned versions)
├── docs/
│   ├── IW-Inverter_Testing_Protocol.pdf
│   ├── EW-Battery_Control-Modbus_TCP.pdf
│   ├── EW-Fusion_Solar-Functionality_Testing.pdf
│   └── Hybrid_Inverter_Registers.xltx
├── logs/                            # Auto-generated log files
│   └── (e.g. telemetry.log, behavior_errors.log, full_test.log, etc.)
├── scripts/
│   ├── inverter_register_map.py     # §4.2 Export all registers to CSV
│   ├── inverter_telemetry.py        # §4.2 Poll telemetry continuously
│   ├── inverter_battery_control.py  # §4.2 Forced charge/discharge functions
│   ├── inverter_full_tests.py       # §4.2 End-to-end suite (map → telemetry → cycles)
│   ├── inverter_behavior_errors.py  # §4.3 Behavior & error tests
│   ├──	inverter_behavior_tests.py   # §4.3 Behavior test runner
│   ├── inverter_performance.py      # §4.3 Read performance parameters & tables
│   └── inverter_performance_tests.py# §4.3 Export performance data to CSV
└── tests/
    ├── inverter_behavior_errors_4_2.py  # 4.2-only behavior & error tests (inverter)
    └── inverter_behavior_tests_4_2.py   # 4.2 behavior test runner
```

- **`docs/`**: Protocol PDFs and the official `Hybrid_Inverter_Registers.xltx` template.  
- **`logs/`**: Each script writes a rotating log (up to 5 MB, 3 backups) to this folder.  
- **`requirements.txt`**: Exact dependency versions.  
- **`LICENSE`** & **`CONTRIBUTING.md`**: Project governance.  
- **`scripts/`**: All Python scripts implementing 4.2 & 4.3 functionality.  
- **`tests/`**: 4.2-only test runners.

---

## 🚀 Usage & Step-by-Step Guide

Below are examples for each major feature. Replace parameters as needed for your environment.

---

### 📥 Register-Map Export (Section 4.2)

Dump *all* Modbus registers to a CSV file.

```bash
# RTU mode (example COM port COM3, baudrate 9600, slave ID 1)
python scripts/inverter_register_map.py \
  --mode rtu --port COM3 --baudrate 9600 --slave_id 1

# TCP mode (example host 192.168.1.100, unit ID 0, installer password 00000a)
python scripts/inverter_register_map.py \
  --mode tcp --host 192.168.1.100 --tcp_port 6607 --unit_id 0 --password 00000a
```

- **Output Files**:  
  - `inverter_register_map_rtu.csv` (if RTU)  
  - `inverter_register_map_tcp.csv` (if TCP)  

- **CSV Columns**:  
  ```
  Register_Name,Address,Value
  ```
  - `Register_Name`: constant name from `huawei_solar.register_names` (e.g. `inverter_voltage_a`).  
  - `Address`: Modbus register address (decimal, e.g. `32069`).  
  - `Value`: raw register value (apply gain to convert to engineering units).

- **What It Does**:  
  Iterates through every entry in `huawei_solar.register_names`, reads it over Modbus, and writes the results to CSV.

---

### 📈 Telemetry Polling (Section 4.2)

Continuously poll live telemetry (every X seconds for Y seconds).

```bash
# RTU mode: poll every 5 s for 120 s
python scripts/inverter_telemetry.py \
  --mode rtu --port COM3 --baudrate 9600 --slave_id 1 \
  --interval 5 --duration 120

# TCP mode: poll every 5 s for 120 s
python scripts/inverter_telemetry.py \
  --mode tcp --host 192.168.1.100 --tcp_port 6607 --unit_id 0 --password 00000a \
  --interval 5 --duration 120
```

- **Logged Parameters** (example):  
  - Inverter Active Power (W)  
  - PV String Power (W)  
  - Grid Voltage (V)  
  - Grid Frequency (Hz)  
  - Battery SoC (%)  
  - Battery Charge/Discharge Power (W)  
  - Inverter Operation State (Fault, Idle, Running)  

- **Log File**:  
  - `logs/telemetry.log`  

- **Sample Log Lines**:  
  ```  
  2025-06-10 14:00:00 [INFO] [TELEMETRY] Inverter Active Power (W) = 1500  
  2025-06-10 14:00:00 [INFO] [TELEMETRY] PV String Power (W) = 1200  
  2025-06-10 14:00:00 [INFO] [TELEMETRY] Grid Voltage (V) = 230.0  
  2025-06-10 14:00:00 [INFO] [TELEMETRY] Grid Frequency (Hz) = 50.0  
  2025-06-10 14:00:00 [INFO] [TELEMETRY] Battery SoC (%) = 45.0  
  ```

- **What It Does**:  
  Reads a predefined list of registers every `interval` seconds and writes them to log. 

---

### 🔍 4.2 Behavior & Error Tests (Inverter Only)

Verify handling of empty/out-of-range forced charge/discharge commands.

```bash
# RTU mode
python tests/inverter_behavior_tests_4_2.py \
  --mode rtu --port COM3 --baudrate 9600 --slave_id 1

# TCP mode
python tests/inverter_behavior_tests_4_2.py \
  --mode tcp --host 192.168.1.100 --tcp_port 6607 --unit_id 0 --password 00000a
```

- **Tests Performed**:  
  1. **Empty Power**: Skip writing Charge Power – inverter uses default (max) and sets error.  
  2. **Out-of-Range Power**: Write 1 000 000 W or –100 W → clamp to valid range and set error.  
  3. **Empty Duration**: Skip writing Forced Period – inverter uses default and sets error.  
  4. **Out-of-Range Duration**: Write 9999 min or –10 min → clamp to valid range and set error.  
  5. **Empty SoC**: Skip writing Target SoC – inverter uses default and sets error.  
  6. **Out-of-Range SoC**: Write 150 % or –20 % → clamp to valid range and set error.  
  7. **EMS Compatibility**: Interleave an unrelated write (Grid Max Voltage) with forced discharge – check no Modbus bus lock.  

- **Log File**:  
  - `logs/behavior_errors_4_2.log`  

- **Sample Log Excerpt**:  
  ```  
  2025-06-10 09:00:00 [INFO] [SET] Charge Power (empty) → using default fallback  
  2025-06-10 09:00:00 [INFO] [READ] Last Command Error Flag = 1  
  2025-06-10 09:00:05 [INFO] [SET] Charge Power (1e6 W) = 1000000  
  2025-06-10 09:00:05 [WARNING] [MISMATCH] Charge Power: expected 1000000, got 5000 (clamped)  
  2025-06-10 09:00:05 [INFO] [READ] Clamped Charge Power = 5000  
  2025-06-10 09:00:05 [INFO] [READ] Last Command Error Flag = 1  
  ```

- **What It Does**:  
  Runs each test function defined in `scripts/inverter_behavior_errors_4_2.py`, logging clamp/mismatch messages and error flags. 

---

### 🧵 End-to-End 4.2 Suite

Combine Register-Map Export, Telemetry Polling, and Forced Charge/Discharge cycles.

```bash
# TCP mode example
python scripts/inverter_full_tests.py \
  --mode tcp --host 192.168.1.100 --tcp_port 6607 --unit_id 0 --password 00000a
```

- **Sequence**:  
  1. **Register-Map Export** → produces `inverter_register_map_tcp.csv`.  
  2. **Telemetry Polling** (120 s) → logs to `logs/telemetry.log`.  
  3. **Battery Control Cycles** (two duration-based, two SoC-based) → logged to `logs/full_test.log`.  

- **Battery Cycles**:  
  - **Duration Cycle 1**: Charge @ 500 W for 2 min → stop.  
  - **Duration Cycle 2**: Discharge @ 500 W for 2 min → stop.  
  - **SoC Cycle 1**: Charge to 80 % @ 500 W → stop when SoC ≥ 80 %.  
  - **SoC Cycle 2**: Discharge to 20 % @ 500 W → stop when SoC ≤ 20 %.  

- **Output Files**:  
  - `inverter_register_map_tcp.csv`  
  - `logs/telemetry.log`  
  - `logs/full_test.log`  

- **Sample Log Excerpt** (from `logs/full_test.log`):  
  ```  
  2025-06-10 10:00:00 [INFO] Register-Map export (TCP) started  
  2025-06-10 10:00:02 [INFO] Register-Map export completed → inverter_register_map_tcp.csv  
  2025-06-10 10:00:02 [INFO] Telemetry polling started (120 s)  
  2025-06-10 10:02:02 [INFO] Telemetry polling stopped  
  2025-06-10 10:02:02 [INFO] Starting duration-based charge @500 W for 2 min  
  2025-06-10 10:02:02 [INFO] [SET] Target SoC (100 %) = 100  
  2025-06-10 10:02:02 [INFO] [SET] Charge Power (500 W) = 500  
  2025-06-10 10:02:02 [INFO] [SET] Period (2 min) = 2  
  2025-06-10 10:02:02 [INFO] [SET] Trigger Charge = 1  
  2025-06-10 10:04:02 [INFO] Stopping charge  
  …  
  ```

---

### ⚡ 4.3 Behavior & Error Tests (Inverter + Battery)

Verify “Inverter Behavior” and “Errors” from Section 4.3, including sleep/wake and Modbus alarms.

```bash
# TCP mode example
python scripts/inverter_behavior_tests.py \
  --mode tcp --host 192.168.1.100 --tcp_port 6607 --unit_id 0 --password 00000a
```

- **Tests Performed**:  
  1. **Empty SoC (4.3)**: Skip writing `STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC` → fallback & error.  
  2. **Out-of-Range SoC (4.3)**: Write 150 % or –20 % → clamp & error.  
  3. **Empty Power (4.3)**: Skip writing `STORAGE_FORCIBLE_CHARGE_POWER` → fallback & error.  
  4. **EMS Compatibility (4.3)**: Interleave “Grid Max Voltage” write with forced command → no lock.  
  5. **Sleep/Idle & Wake-Up**: Read `INV_SLEEP_TIMEOUT`, `INV_WAKE_VOLTAGE`, `INV_WAKE_POWER`, `INV_WAKE_TIME_PV`, `INV_WAKE_TIME_CMD`.  
  6. **Modbus Alarm Registers**: Read `INV_ALARM_GRID_DISCONNECT`, `INV_ALARM_PV_DISCONNECT`, `INV_ALARM_BAT_DISCONNECT`, `INV_ALARM_INVERTER_OFFLINE`, `INV_ALARM_OVER_VOLT`, `INV_ALARM_UNDER_VOLT`, and `INV_ERROR_FLAG`.  

- **Log File**:  
  - `logs/behavior_errors.log`  

- **Sample Log Excerpt**:  
  ```  
  2025-06-10 11:00:00 [INFO] [SET] Target SOC (empty) → using default fallback  
  2025-06-10 11:00:00 [INFO] [READ] Last Command Error Flag = 1  
  2025-06-10 11:00:05 [INFO] [READ] INV_SLEEP_TIMEOUT = 30 s  
  2025-06-10 11:00:05 [INFO] [READ] INV_WAKE_VOLTAGE = 120 V  
  2025-06-10 11:00:05 [INFO] [READ] INV_ALARM_PV_DISCONNECT = 0  
  …  
  ```

- **What It Does**:  
  Implements Section 4.3 test flows and logs all relevant error flags and wake/sleep parameters. 

---

### 📊 Performance Measurements (Section 4.3)

Export static battery/inverter performance data and lookup tables to CSV.

```bash
# TCP mode example
python scripts/inverter_performance_tests.py \
  --mode tcp --host 192.168.1.100 --tcp_port 6607 --unit_id 0 --password 00000a
```

- **Data Collected**:  
  1. **Battery Capacity (kWh)** – reads `STORAGE_BATTERY_CAPACITY`.  
  2. **Max Charge Power (W)** – reads `STORAGE_MAX_CHARGE_POWER`.  
  3. **Max Discharge Power (W)** – reads `STORAGE_MAX_DISCHARGE_POWER`.  
  4. **Depth of Discharge (%)** – reads `STORAGE_DEPTH_OF_DISCHARGE`.  
  5. **Efficiencies (%)** – `INV_PV_TO_AC_EFF`, `INV_PV_TO_BAT_EFF`, `INV_BAT_TO_AC_EFF`, `INV_AC_TO_BAT_EFF`.  
  6. **Voltage vs. SoC Table** – reads registers `BATTERY_DC_VOLTAGE_SOC_0`, `_10`, …, `_100`.  
  7. **Voltage vs. Power Table** – reads `BATTERY_DC_VOLTAGE_POWER_0`, `_500`, …, `_3000`.  

- **Output File**:  
  - `inverter_performance.csv`  

- **CSV Format Example**:  
  ```  
  Parameter,Value
  Battery Capacity (kWh),10.0
  Max Charge Power (W),2000
  Max Discharge Power (W),1500
  Depth of Discharge (%),80
  PV→AC Efficiency (%),95.5
  PV→Battery Efficiency (%),90.0
  Battery→AC Efficiency (%),93.0
  AC→Battery Efficiency (%),88.0

  SOC (%),Battery DC Voltage (V)
  0,48.0
  10,49.5
  …
  100,54.0

  Power (W),Battery DC Voltage (V)
  0,48.0
  500,50.0
  …
  3000,54.5
  ```

- **What It Does**:  
Reads static and table registers, converts raw values (via gain), and writes a well-formatted CSV.

---

## 🧾 Register Reference

For a complete register list and descriptions, refer to the `Hybrid_Inverter_Registers.xltx` in the `docs/` folder.  
Additional register-name mappings can be found in the `huawei_solar.register_names` module.

---

## 📂 Example Logs & CSV Outputs

- **`logs/telemetry.log`**: Sample telemetry polling output  
- **`logs/behavior_errors_4_2.log`**: Sample 4.2 behavior/error test output  
- **`logs/full_test.log`**: Sample end-to-end 4.2 suite output  
- **`logs/behavior_errors.log`**: Sample 4.3 behavior/error test output  
- **`inverter_register_map_tcp.csv`**: Example register map (TCP)  
- **`inverter_performance.csv`**: Example performance data CSV

---

## 🛠️ Troubleshooting & FAQ

- **Q: Telemetry polling suddenly stops**  
  A: Ensure the inverter is powered and reachable over Modbus. Check cable connections and log entries in `logs/telemetry.log`.  

- **Q: Scripts cannot connect over RTU**  
  A: On Linux, confirm your user belongs to the `dialout` group. On Windows, verify the COM port in Device Manager. Ensure baudrate and slave ID match inverter settings.  

- **Q: TCP login fails (“Login timeout” or “Invalid password”)**  
  A: Verify you can ping the inverter at `192.168.1.100:6607`. Confirm installer password in FusionSolar app or inverter GUI. If changed, update the script argument accordingly.  

- **Q: Forced charge commands are ignored**  
  A: Check if inverter is already in a forced session. End any previous session via `stop_charge()` before sending a new one. Also verify default parameters aren’t exceeding max limits.  

- **Q: “Clamped” messages in behavior tests**  
  A: The inverter enforces internal min/max. For example, a “Charge 1 000 000 W” command clamps to the hardware limit (e.g. 5000 W). Adjust tests or accept clamp behavior as expected.  

- **Q: Performance CSV shows zeros or NaNs**  
  A: The inverter needs to be idle (no PV generation or battery flow) when reading static performance registers. Ensure steady state before running `inverter_performance_tests.py`.  

For additional FAQs, refer to the `docs/` folder and the official FusionSolar/Inverter user manuals.

---

## 📜 License

MIT © 2025 Andraž Jančar  
Faculty of Electrical Engineering, University of Ljubljana 🎓
