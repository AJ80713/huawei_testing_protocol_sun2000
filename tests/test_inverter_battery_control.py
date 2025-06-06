import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

import importlib
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
ibc = importlib.import_module(
    "huawei_sun2000_control.inverter_battery_control"
)


@pytest.mark.asyncio
async def test_ensure_and_set(monkeypatch):
    register = SimpleNamespace(name="REG")
    bridge = SimpleNamespace(slave_id=42)
    bridge.ensure_logged_in = AsyncMock()
    bridge.set = AsyncMock()
    bridge.client = SimpleNamespace()
    bridge.client.get = AsyncMock(return_value=SimpleNamespace(value=1))

    await ibc.ensure_and_set(bridge, register, 1, "Label")

    bridge.ensure_logged_in.assert_awaited_once()
    bridge.set.assert_awaited_once_with(register, 1)
    bridge.client.get.assert_awaited_once_with(register, slave=42)


@pytest.mark.asyncio
async def test_read_param_returns_value():
    register = SimpleNamespace(name="REG")
    bridge = SimpleNamespace(slave_id=1, client=SimpleNamespace())
    bridge.client.get = AsyncMock(return_value=SimpleNamespace(value=5))

    value = await ibc.read_param(bridge, register, "Label")
    assert value == 5


@pytest.mark.asyncio
async def test_stop_charge_cancels_monitor_task(monkeypatch):
    bridge = SimpleNamespace(slave_id=1)
    bridge.client = SimpleNamespace()
    bridge.client.get = AsyncMock(return_value=SimpleNamespace(value=0))
    bridge._monitor_task = asyncio.create_task(asyncio.sleep(0.05))

    ensure_mock = AsyncMock()
    monkeypatch.setattr(ibc, "ensure_and_set", ensure_mock)

    await ibc.stop_charge(bridge)

    assert bridge._monitor_task.cancelled()
    assert ensure_mock.await_count == 4
