# read_rtu.py
import logging
from pymodbus.client import ModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusIOException

# —— Inverter & Serial Configuration ——  
COM_PORT = "COM3"    # your USB-RS485 adapter  
BAUDRATE = 9600      # per inverter settings  
SLAVE_ID = 2         # RTU slave address  

# —— Logging setup ——  
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO
)

def connect_rtu(port, baudrate, bytesize, parity, stopbits, timeout):
    """
    Try opening the serial port with given settings.
    """
    client = ModbusClient(
        port=port, baudrate=baudrate,
        bytesize=bytesize, parity=parity,
        stopbits=stopbits, timeout=timeout
    )
    if client.connect():
        logging.info(f"Connected on {port} @ {baudrate}, {bytesize}-{parity}-{stopbits}")
        return client
    else:
        logging.warning(f"Failed to open {port} @ {baudrate}, {bytesize}-{parity}-{stopbits}")
        return None

def read_registers(client, start, count, slave):
    """
    Read `count` holding registers beginning at `start`.
    """
    try:
        rr = client.read_holding_registers(address=start, count=count, slave=slave)
        if rr.isError():
            logging.error(f"Modbus error: {rr}")
        else:
            logging.info(f"Registers {start}–{start+count-1}: {rr.registers}")
            return rr.registers
    except ModbusIOException as e:
        logging.error(f"I/O error: {e}")
    return None

def main():
    # 1) Ensure inverter is in RS-485/Modbus-RTU mode (not WIFI!) :contentReference[oaicite:1]{index=1}
    # 2) Wire A→485+, B→485−, and GND to ground on the inverter.
    # 3) If you see no response, add a 120 Ω terminator across 485+/485−.
    #
    # This loop tries 8-E-1 then 7-E-1 automatically:
    for bytesize, parity in [(8, 'E'), (7, 'E')]:
        client = connect_rtu(
            port=COM_PORT,
            baudrate=BAUDRATE,
            bytesize=bytesize,
            parity=parity,
            stopbits=1,
            timeout=1
        )
        if not client:
            continue

        # 4) Read registers 0–9 as a quick test
        regs = read_registers(client, start=0, count=10, slave=SLAVE_ID)
        client.close()
        if regs is not None:
            # success!
            break
    else:
        logging.error("All serial settings failed. Check inverter mode, wiring, and COM port.")

if __name__ == "__main__":
    main()
# This script reads Modbus registers from an inverter using a USB-RS485 adapter.
# It tries two serial configurations (8-E-1 and 7-E-1) and logs the results.