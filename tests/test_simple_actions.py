"""Verify the simple control actions (charge, discharge, stop, mode switches).

Coverage goal: Check payloads, target resolution, and validation of the thin
wrapper actions added on top of the existing 47005 / 47015 write points.
Implementation: Use fakes for the services registry, config entries, device
registry, and API to verify call order, payloads, and zero-write behavior.
Proves: The actions write the expected points and reject invalid requests
before any write.
Does not prove: The tests do not connect to an HA instance or physical device and
cannot prove physical output or command readback.
"""

from types import SimpleNamespace

import pytest
import yaml
from pathlib import Path

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ServiceValidationError

from custom_components.indevolt import _register_services
from custom_components.indevolt import dr as device_registry_module


class FakeServices:
    def __init__(self) -> None:
        self.handlers = {}

    def async_register(self, domain, service, handler) -> None:
        self.handlers[(domain, service)] = handler


class FakeAPI:
    def __init__(self) -> None:
        self.writes = []

    async def set_data(self, *, point, value):
        self.writes.append((point, value))
        return True


class FakeCoordinator:
    def __init__(self) -> None:
        self.api = FakeAPI()
        self.request_refreshes = 0

    async def async_request_refresh(self) -> None:
        self.request_refreshes += 1


def make_entry(entry_id: str, model: str, state=ConfigEntryState.LOADED):
    return SimpleNamespace(
        entry_id=entry_id,
        state=state,
        data={"device_model": model},
        runtime_data=FakeCoordinator(),
    )


class FakeConfigEntries:
    def __init__(self, entries) -> None:
        self.entries = {entry.entry_id: entry for entry in entries}

    def async_entries(self, domain):
        assert domain == "indevolt"
        return list(self.entries.values())

    def async_get_entry(self, entry_id):
        return self.entries.get(entry_id)


class FakeRegistry:
    """Map device id "device-<entry id>" to the config entry "<entry id>"."""

    def __init__(self, known_entries) -> None:
        self.known_entries = set(known_entries)

    def async_get(self, device_id):
        entry_id = device_id.removeprefix("device-")
        if entry_id not in self.known_entries:
            return None
        return SimpleNamespace(config_entries={entry_id})


def setup(monkeypatch, *entries):
    hass = SimpleNamespace(
        services=FakeServices(),
        config_entries=FakeConfigEntries(entries),
    )
    registry = FakeRegistry(entry.entry_id for entry in entries)
    monkeypatch.setattr(device_registry_module, "async_get", lambda hass: registry)
    _register_services(hass)
    return hass


async def call(hass, service, **data):
    await hass.services.handlers[("indevolt", service)](
        SimpleNamespace(service=service, data=data)
    )


def test_all_actions_registered_and_declared(monkeypatch) -> None:
    hass = setup(monkeypatch, make_entry("a", "PowerFlex2000"))
    services_yaml = yaml.safe_load(
        (Path(__file__).parents[1] / "services.yaml").read_text(encoding="utf-8")
    )
    for service in (
        "charge",
        "discharge",
        "stop",
        "set_realtime_mode",
        "set_self_consumption_mode",
        "set_schedule_mode",
    ):
        assert ("indevolt", service) in hass.services.handlers
        assert services_yaml[service]["target"]["device"]["integration"] == "indevolt"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service", "state", "default_soc"), [("charge", 1, 100), ("discharge", 2, 5)]
)
async def test_gen2_charge_discharge_defaults(
    monkeypatch, service, state, default_soc
) -> None:
    entry = make_entry("a", "SolidFlex2000")
    hass = setup(monkeypatch, entry)

    await call(hass, service, power=800)

    assert entry.runtime_data.api.writes == [
        (47005, [4]),
        (47015, [state, 800, default_soc]),
    ]
    assert entry.runtime_data.request_refreshes == 1


@pytest.mark.asyncio
async def test_charge_uses_explicit_soc_and_device_target(monkeypatch) -> None:
    first = make_entry("a", "PowerFlex2000")
    second = make_entry("b", "PowerFlex2000")
    hass = setup(monkeypatch, first, second)

    await call(hass, "charge", device_id=["device-b"], power=500, soc=80)

    assert first.runtime_data.api.writes == []
    assert second.runtime_data.api.writes == [(47005, [4]), (47015, [1, 500, 80])]


@pytest.mark.asyncio
async def test_stop_writes_standby(monkeypatch) -> None:
    entry = make_entry("a", "PowerFlex2000")
    hass = setup(monkeypatch, entry)

    await call(hass, "stop")

    assert entry.runtime_data.api.writes == [(47005, [4]), (47015, [0, 0, 5])]
    assert entry.runtime_data.request_refreshes == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service", "mode"),
    [
        ("set_realtime_mode", 4),
        ("set_self_consumption_mode", 1),
        ("set_schedule_mode", 5),
    ],
)
async def test_mode_actions_write_work_mode_only(monkeypatch, service, mode) -> None:
    entry = make_entry("a", "PowerFlex2000")
    hass = setup(monkeypatch, entry)

    await call(hass, service)

    assert entry.runtime_data.api.writes == [(47005, [mode])]
    assert entry.runtime_data.request_refreshes == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("service", ["set_self_consumption_mode", "set_schedule_mode"])
async def test_bk1600_rejects_unsupported_modes(monkeypatch, service) -> None:
    entry = make_entry("a", "BK1600")
    hass = setup(monkeypatch, entry)

    with pytest.raises(ServiceValidationError, match="BK1600"):
        await call(hass, service)

    assert entry.runtime_data.api.writes == []


@pytest.mark.asyncio
async def test_bk1600_realtime_mode_allowed(monkeypatch) -> None:
    entry = make_entry("a", "BK1600 Ultra")
    hass = setup(monkeypatch, entry)

    await call(hass, "set_realtime_mode")

    assert entry.runtime_data.api.writes == [(47005, [4])]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service", "power", "accepted"),
    [
        ("charge", 1_200, True),
        ("charge", 1_201, False),
        ("discharge", 800, True),
        ("discharge", 801, False),
        ("charge", -1, False),
    ],
)
async def test_bk1600_power_limits(monkeypatch, service, power, accepted) -> None:
    entry = make_entry("a", "BK1600")
    hass = setup(monkeypatch, entry)

    if accepted:
        await call(hass, service, power=power)
        assert len(entry.runtime_data.api.writes) == 2
    else:
        with pytest.raises(ServiceValidationError, match="Power"):
            await call(hass, service, power=power)
        assert entry.runtime_data.api.writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("power", "soc", "accepted"),
    [
        (50, 5, True),
        (10_800, 100, True),
        (49, 50, False),
        (10_801, 50, False),
        (500, 4, False),
        (500, 101, False),
    ],
)
async def test_gen2_limits(monkeypatch, power, soc, accepted) -> None:
    entry = make_entry("a", "PowerFlex2000")
    hass = setup(monkeypatch, entry)

    if accepted:
        await call(hass, "charge", power=power, soc=soc)
        assert entry.runtime_data.api.writes[-1] == (47015, [1, power, soc])
    else:
        with pytest.raises(ServiceValidationError):
            await call(hass, "charge", power=power, soc=soc)
        assert entry.runtime_data.api.writes == []


@pytest.mark.asyncio
async def test_missing_power_is_rejected(monkeypatch) -> None:
    entry = make_entry("a", "PowerFlex2000")
    hass = setup(monkeypatch, entry)

    with pytest.raises(ServiceValidationError, match="power is required"):
        await call(hass, "charge")

    assert entry.runtime_data.api.writes == []


@pytest.mark.asyncio
async def test_all_targets_validated_before_first_write(monkeypatch) -> None:
    gen2 = make_entry("a", "PowerFlex2000")
    bk = make_entry("b", "BK1600")
    hass = setup(monkeypatch, gen2, bk)

    # 1500 W is valid for the Gen2 device but not for the BK1600.
    with pytest.raises(ServiceValidationError):
        await call(hass, "charge", device_id=["device-a", "device-b"], power=1_500)

    assert gen2.runtime_data.api.writes == []
    assert bk.runtime_data.api.writes == []


@pytest.mark.asyncio
async def test_several_devices_without_target_is_rejected(monkeypatch) -> None:
    first = make_entry("a", "PowerFlex2000")
    second = make_entry("b", "PowerFlex2000")
    hass = setup(monkeypatch, first, second)

    with pytest.raises(ServiceValidationError, match="No device selected"):
        await call(hass, "stop")

    assert first.runtime_data.api.writes == []
    assert second.runtime_data.api.writes == []


@pytest.mark.asyncio
async def test_not_loaded_entry_is_not_used_as_default(monkeypatch) -> None:
    loaded = make_entry("a", "PowerFlex2000")
    broken = make_entry("b", "PowerFlex2000", state=ConfigEntryState.SETUP_ERROR)
    hass = setup(monkeypatch, loaded, broken)

    await call(hass, "stop")

    assert loaded.runtime_data.api.writes == [(47005, [4]), (47015, [0, 0, 5])]
    assert broken.runtime_data.api.writes == []


@pytest.mark.asyncio
async def test_unknown_device_is_rejected(monkeypatch) -> None:
    entry = make_entry("a", "PowerFlex2000")
    hass = setup(monkeypatch, entry)

    with pytest.raises(ServiceValidationError, match="not found"):
        await call(hass, "stop", device_id="device-unknown")

    assert entry.runtime_data.api.writes == []
