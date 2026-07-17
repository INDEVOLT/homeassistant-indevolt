"""Verify the Gen2 10800 W input boundary and prevent BK/write-path regressions.

Coverage goal: Check the Action, number, YAML, shared constant, and non-target BK
boundaries together.
Implementation: Use parametrization, fakes, monkeypatching, and configuration
parsing to verify call order, payloads, and zero-write behavior.
Proves: Both Gen2 integration entry points agree at the 10800/10801 W boundary.
Does not prove: The tests do not connect to an HA instance or physical device and
cannot prove physical output or command readback.
"""

# Reason: The test must parse the repository's services.yaml read-only without
# depending on the process working directory.
# Usage: Derive the repository root from the test file and read the service
# configuration for consistency assertions.
# Impact: This reads only the current repository file and does not modify runtime
# configuration.
from pathlib import Path

# Reason: Tests need minimal ConfigEntry, ServiceCall, and runtime_data stand-ins.
# Usage: SimpleNamespace gives fake objects the attributes accessed by production
# code.
# Impact: This provides only test attribute containers and does not replace the
# full HA lifecycle or physical-device acceptance testing.
from types import SimpleNamespace

# Reason: The suite needs asynchronous cases, parameter matrices, monkeypatching,
# and exception assertions.
# Usage: Pytest drives representative values, out-of-range values, and BK
# regression matrices across both entry points.
# Impact: It drives only fake objects and triggers no network or device side effects.
import pytest

# Reason: YAML cannot import the shared Python constant directly and must be
# checked independently after parsing.
# Usage: safe_load reads the selector for comparison with Python descriptions and
# the existing BK boundary.
# Impact: This validates only configuration structure and does not change
# services.yaml.
import yaml

# Reason: The product contract requires out-of-range requests to return the
# standard HA validation error.
# Usage: pytest.raises asserts both the error type and the 10800 W error message.
# Impact: This is used only for test capture and does not change production
# exception handling.
from homeassistant.exceptions import ServiceValidationError

# Reason: Copying handler logic would let tests diverge from production behavior.
# Usage: Call the real _register_services, capture its actual closure, and verify
# write ordering.
# Impact: Registration targets FakeServices and does not write to a running HA
# instance.
from custom_components.indevolt import _register_services

# Reason: A 10801 W request must fail before registry access, so the reference
# actually used by the production module must be observed.
# Usage: Monkeypatch async_get with either a fake or a failure sentinel.
# Impact: The replacement applies only within one test and does not modify the
# production module file.
from custom_components.indevolt import dr as device_registry_module

# Reason: Checking NUMBERS_GEN2 alone does not prove that setup selects it for
# both target models.
# Usage: Call the real number.async_setup_entry and replace entity construction to
# collect the selected descriptions.
# Impact: This replaces only entity construction in the test and creates no HA
# entities.
from custom_components.indevolt import number as number_platform

# Reason: The Action, number, and YAML must be reviewed against the same 10800 W
# source of truth.
# Usage: Assert the constant directly and use it as the expected selector and
# entity-description value.
# Impact: This only reads the constant and does not change runtime state.
from custom_components.indevolt.const import MAX_REAL_TIME_CONTROL_POWER

# Reason: The tests need the real Gen1/Gen2 descriptions and entity setter to
# avoid reimplementing the production contract.
# Usage: Select the actual power_setting description and call the
# IndevoltNumberEntity setter directly.
# Impact: FakeAPI replaces the API, so no physical point 47016 write occurs.
from custom_components.indevolt.number import (
    NUMBERS_GEN1,
    NUMBERS_GEN2,
    IndevoltNumberEntity,
)


# Coverage goal: Observe service registration, point payloads, and both refresh
# calls while isolating external side effects.
# Implementation: FakeServices stores handlers, FakeAPI records writes, and
# FakeCoordinator counts refresh calls.
# Proves: Which calls production logic makes and whether their ordering is preserved.
# Does not prove: A successful fake response does not mean a physical device accepts
# the command or produces the corresponding output.
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
    def __init__(self, model: str = "PowerFlex2000") -> None:
        self.api = FakeAPI()
        self.config_entry = SimpleNamespace(
            unique_id="test-device",
            data={"device_model": model},
        )
        self.data = {}
        self.request_refreshes = 0
        self.refreshes = 0

    async def async_request_refresh(self) -> None:
        self.request_refreshes += 1

    async def async_refresh(self) -> None:
        self.refreshes += 1


# Coverage goal: Preserve the registry → ConfigEntry → coordinator resolution
# chain for valid Actions.
# Implementation: FakeRegistry returns a fixed entry_id and FakeConfigEntries
# returns the injected coordinator.
# Proves: Valid requests still use the existing target resolution and out-of-range
# requests can fail before that chain.
# Does not prove: The test does not read the real HA registry, ConfigEntry,
# permissions, or credential state.
class FakeConfigEntries:
    def __init__(self, coordinator) -> None:
        self.entry = SimpleNamespace(runtime_data=coordinator)

    def async_get_entry(self, entry_id):
        assert entry_id == "entry-id"
        return self.entry


class FakeRegistry:
    def async_get(self, device_id):
        assert device_id == "device-id"
        return SimpleNamespace(config_entries={"entry-id"})


# Coverage goal: Give Action cases the same minimal HA context and fixed real-time
# control inputs.
# Implementation: make_hass assembles service and ConfigEntry fakes, while
# service_call creates the standard payload.
# Proves: Different power values change only the variable under test, without
# fixture-template differences.
# Does not prove: A fixed single-target payload does not cover real multi-target,
# permission, or concurrency behavior.
def make_hass(coordinator):
    return SimpleNamespace(
        services=FakeServices(),
        config_entries=FakeConfigEntries(coordinator),
    )


def service_call(service: str, power: int):
    return SimpleNamespace(
        service=service,
        data={
            "device_id": ["device-id"],
            "mode": "Real-Time Control",
            "state": "Charging",
            "power": power,
            "soc": 80,
        },
    )


# Coverage goal: After raising the limit, valid Action write points, order, and
# payloads must remain unchanged.
# Implementation: Parameterize 2400, 2401, 4800, 7200, and 10800 W across both
# Gen2 models.
# Proves: Valid values write points 47005/47015 in order, pass the original power
# value through, and request exactly one refresh.
# Does not prove: A successful fake write does not mean a device physically outputs
# the corresponding power.
@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["SolidFlex2000", "PowerFlex2000"])
@pytest.mark.parametrize("power", [2_400, 2_401, 4_800, 7_200, 10_800])
async def test_gen2_action_accepts_supported_power(monkeypatch, model, power) -> None:
    coordinator = FakeCoordinator(model)
    hass = make_hass(coordinator)
    monkeypatch.setattr(
        device_registry_module, "async_get", lambda hass: FakeRegistry()
    )
    _register_services(hass)

    await hass.services.handlers[("indevolt", "set_solidflex_powerflex_work_mode")](
        service_call("set_solidflex_powerflex_work_mode", power)
    )

    assert coordinator.api.writes == [(47005, [4]), (47015, [1, power, 80])]
    assert coordinator.request_refreshes == 1
    assert coordinator.refreshes == 0


# Coverage goal: A 10801 W request must fail before registry access, points
# 47005/47015, and refresh.
# Implementation: Replace registry access with a failure sentinel, then call the
# real service handler.
# Proves: An out-of-range request performs no target resolution, API write, or
# refresh.
# Does not prove: This single-target case does not redefine the existing partial-
# success semantics of valid multi-target requests.
@pytest.mark.asyncio
async def test_solidflex_action_rejects_10801_before_registry_or_api(
    monkeypatch,
) -> None:
    coordinator = FakeCoordinator()
    hass = make_hass(coordinator)

    def unexpected_registry_access(hass):
        raise AssertionError("device registry must not be accessed")

    monkeypatch.setattr(device_registry_module, "async_get", unexpected_registry_access)
    _register_services(hass)

    with pytest.raises(ServiceValidationError, match="10800 W"):
        await hass.services.handlers[("indevolt", "set_solidflex_powerflex_work_mode")](
            service_call("set_solidflex_powerflex_work_mode", 10_801)
        )

    assert coordinator.api.writes == []
    assert coordinator.request_refreshes == 0
    assert coordinator.refreshes == 0


# Coverage goal: The Gen2 condition in the shared handler must not affect the BK
# Action.
# Implementation: Send the existing 1200 W request through set_bk1600_work_mode
# and record the complete call sequence.
# Proves: BK retains its original points, payload, and one requested refresh.
# Does not prove: This case neither raises the BK limit nor covers every physical
# BK device state.
@pytest.mark.asyncio
async def test_bk_action_keeps_existing_selector_maximum(monkeypatch) -> None:
    coordinator = FakeCoordinator("BK1600")
    hass = make_hass(coordinator)
    monkeypatch.setattr(
        device_registry_module, "async_get", lambda hass: FakeRegistry()
    )
    _register_services(hass)

    await hass.services.handlers[("indevolt", "set_bk1600_work_mode")](
        service_call("set_bk1600_work_mode", 1_200)
    )

    assert coordinator.api.writes == [(47005, [4]), (47015, [1, 1_200, 80])]
    assert coordinator.request_refreshes == 1
    assert coordinator.refreshes == 0


# Coverage goal: Isolate the real description/setter contract from unrelated HA
# lifecycle behavior.
# Implementation: Create the entity with object.__new__, then inject only the
# coordinator and description.
# Proves: Setter points, boundaries, and refresh behavior for the real description.
# Does not prove: Full entity construction and registration are not covered; a
# separate case verifies setup routing.
def make_number_entity(coordinator, description):
    entity = object.__new__(IndevoltNumberEntity)
    entity.coordinator = coordinator
    entity.entity_description = description
    return entity


# Coverage goal: The Gen2 number must independently accept the same valid power
# matrix as the Action.
# Implementation: Call the real entity setter directly and record FakeAPI and
# refresh counts.
# Proves: The original value is written to point 47016 without truncation or
# conversion, followed by one full refresh.
# Does not prove: The test does not promise that a physical device accepts the
# command or produces the corresponding power.
@pytest.mark.asyncio
@pytest.mark.parametrize("power", [2_400, 2_401, 4_800, 7_200, 10_800])
async def test_gen2_number_accepts_supported_power(power) -> None:
    coordinator = FakeCoordinator()
    description = next(item for item in NUMBERS_GEN2 if item.key == "power_setting")
    entity = make_number_entity(coordinator, description)

    await entity.async_set_native_value(power)
    assert coordinator.api.writes == [(47016, [power])]
    assert coordinator.request_refreshes == 0
    assert coordinator.refreshes == 1


# Coverage goal: A direct entity call that bypasses the UI must reject 10801 W
# with zero writes.
# Implementation: Pass 10801 directly to the real setter and capture the standard
# validation error.
# Proves: set_fn, point 47016, and refresh are never executed.
# Does not prove: The test does not verify HA frontend error presentation or the
# lower-level API's general input validation.
@pytest.mark.asyncio
async def test_gen2_number_rejects_10801_before_write() -> None:
    coordinator = FakeCoordinator()
    description = next(item for item in NUMBERS_GEN2 if item.key == "power_setting")
    entity = make_number_entity(coordinator, description)

    with pytest.raises(ServiceValidationError, match="10800 W"):
        await entity.async_set_native_value(10_801)

    assert coordinator.api.writes == []
    assert coordinator.request_refreshes == 0
    assert coordinator.refreshes == 0


# Coverage goal: Gen1 BK retains its dynamic 1200/800 W boundary while sharing the
# entity class.
# Implementation: Parameterize states 1001/1000 and call the real setter at each
# corresponding maximum.
# Proves: BK maximum calculation and the original point 47016 write/refresh contract
# have not regressed.
# Does not prove: This does not add 10800 W capability to BK or cover other device-
# state combinations.
@pytest.mark.asyncio
@pytest.mark.parametrize(("state", "maximum"), [(1001, 1_200), (1000, 800)])
async def test_gen1_number_keeps_existing_dynamic_boundary(state, maximum) -> None:
    coordinator = FakeCoordinator("BK1600")
    coordinator.data["6001"] = state
    description = next(item for item in NUMBERS_GEN1 if item.key == "power_setting")
    entity = make_number_entity(coordinator, description)

    assert entity.native_max_value == maximum

    await entity.async_set_native_value(maximum)

    assert coordinator.api.writes == [(47016, [maximum])]
    assert coordinator.request_refreshes == 0
    assert coordinator.refreshes == 1


# Coverage goal: SolidFlex2000 and PowerFlex2000 must both select the Gen2
# descriptions during setup.
# Implementation: Replace entity construction with a description collector, then
# call the real async_setup_entry.
# Proves: Both models expose min=50, max=10800, and step=1.
# Does not prove: No real entity is created, and out-of-scope models and HA UI
# rendering are not verified.
@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["SolidFlex2000", "PowerFlex2000"])
async def test_gen2_setup_exposes_real_time_number(monkeypatch, model) -> None:
    descriptions = []
    coordinator = FakeCoordinator(model)
    entry = SimpleNamespace(
        data={"device_model": model},
        runtime_data=coordinator,
    )
    monkeypatch.setattr(
        number_platform,
        "IndevoltNumberEntity",
        lambda coordinator, description: description,
    )

    await number_platform.async_setup_entry(
        None,
        entry,
        lambda entities: descriptions.extend(entities),
    )

    power = next(item for item in descriptions if item.key == "power_setting")

    assert power.native_min_value == 50
    assert power.native_max_value == MAX_REAL_TIME_CONTROL_POWER
    assert power.native_step == 1


# Coverage goal: Prevent later drift among the YAML selector, shared Python
# constant, and entity descriptions.
# Implementation: Parse services.yaml and compare it field by field with the real
# Gen1/Gen2 descriptions and constant.
# Proves: Target entry points use 10800 W and the BK selector/descriptions retain
# their existing boundaries.
# Does not prove: This is a static test-time consistency check and does not repair
# an incorrect runtime configuration automatically.
def test_yaml_and_python_use_the_same_maximum() -> None:
    services = yaml.safe_load((Path(__file__).parents[1] / "services.yaml").read_text())
    selector = services["set_solidflex_powerflex_work_mode"]["fields"]["power"][
        "selector"
    ]["number"]
    bk_selector = services["set_bk1600_work_mode"]["fields"]["power"]["selector"][
        "number"
    ]
    gen2_power = next(item for item in NUMBERS_GEN2 if item.key == "power_setting")
    gen1_power = next(item for item in NUMBERS_GEN1 if item.key == "power_setting")

    assert MAX_REAL_TIME_CONTROL_POWER == 10_800
    assert selector == {
        "min": 50,
        "max": MAX_REAL_TIME_CONTROL_POWER,
        "step": 10,
        "unit_of_measurement": "W",
    }
    assert gen2_power.native_max_value == MAX_REAL_TIME_CONTROL_POWER
    assert gen2_power.native_min_value == 50
    assert gen2_power.native_step == 1
    assert gen1_power.native_max_value is None
    assert bk_selector == {
        "min": 0,
        "max": 1_200,
        "step": 10,
        "unit_of_measurement": "W",
    }
