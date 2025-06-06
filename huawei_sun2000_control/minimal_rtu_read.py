# minimal_rtu_read.py
import asyncio
import logging
from huawei_solar import create_rtu_bridge, register_names as rn
from pymodbus.pdu import ExceptionResponse

# —— Configuration ——
PORT = "COM3"
BAUDRATE = 9600
SLAVE_ID = 2

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s", level=logging.INFO
)


async def main():
    # 1) Open RTU bridge (no login)
    bridge = await create_rtu_bridge(
        port=PORT, baudrate=BAUDRATE, slave_id=SLAVE_ID
    )

    # 2) Read a simple input (State of Capacity)
    res = await bridge.client.get(rn.STORAGE_STATE_OF_CAPACITY, slave=SLAVE_ID)

    if isinstance(res, ExceptionResponse):
        logging.error(f"Modbus exception code: {res.exception_code}")
    else:
        logging.info(f"State of Capacity: {res.value}%")

    # 3) Clean up
    await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
