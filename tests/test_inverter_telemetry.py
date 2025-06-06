from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

import importlib
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
it = importlib.import_module(
    "huawei_sun2000_control.inverter_telemetry"
)


@pytest.mark.asyncio
async def test_read_param_returns_value():
    register = SimpleNamespace(name="REG")
    bridge = SimpleNamespace(slave_id=1, client=SimpleNamespace())
    bridge.client.get = AsyncMock(return_value=SimpleNamespace(value=7))

    val = await it.read_param(bridge, register, "Label")
    assert val == 7


@pytest.mark.asyncio
async def test_read_active_power_uses_read_param(monkeypatch):
    bridge = object()
    dummy_reg = object()
    monkeypatch.setattr(it.rn, "INV_ACTIVE_POWER", dummy_reg, raising=False)
    rp = AsyncMock(return_value=11)
    monkeypatch.setattr(it, "read_param", rp)

    result = await it.read_active_power(bridge)
    rp.assert_awaited_once_with(bridge, dummy_reg, "Inverter Active Power (W)")
    assert result == 11
