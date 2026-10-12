"""Home Assistant integration for indevolt device."""

# Reason: A string placed after a future import is not recognized as the module
# docstring.
# Implementation: Move the existing module description to the first line and put
# the future import immediately after it, satisfying Python's placement rules.
# Impact: This only corrects module metadata and static-check results; integration
# loading and service execution are unchanged.
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import device_registry as dr
# Reason: Hard-coding 10800 separately in the Action and number paths could let
# their limits drift during later maintenance.
# Usage: The service handler uses this constant to enforce the real-time power
# limit before target resolution and device writes.
# Impact: This adds only a read-only constant reference; DOMAIN, PLATFORMS, load
# order, and import side effects are unchanged.
from .const import (
    BK1600_MAX_CHARGE_POWER,
    BK1600_MAX_DISCHARGE_POWER,
    DOMAIN,
    MAX_REAL_TIME_CONTROL_POWER,
    MIN_REAL_TIME_CONTROL_POWER,
    PLATFORMS,
)
from .coordinator import IndevoltDeviceUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """
    Set up the indevolt integration component.
    This function is called when the integration is added to the Home Assistant configuration.
    """
    hass.data.setdefault(DOMAIN, {})
    if not hass.services.has_service(DOMAIN, "set_solidflex_powerflex_work_mode"):
        _register_services(hass)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up indevolt from a config entry.
    This is the main setup function called when a config entry is added.
    It initializes the coordinator and sets up platforms.
    """
    hass.data.setdefault(DOMAIN, {})
    
    try:
        coordinator = IndevoltDeviceUpdateCoordinator(hass, entry.data)
        # Perform initial data refresh.
        await coordinator.async_config_entry_first_refresh()
        # Store coordinator in hass.data for platform access.
        entry.runtime_data = coordinator

        # Set up all platforms (sensors, switches, etc.).
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True 
    
    except Exception as err:
        _LOGGER.exception("Unexpected error occurred while setting config entry.")
        
        # Clean up partially created resources.
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            del hass.data[DOMAIN][entry.entry_id]
        
        raise ConfigEntryNotReady from err

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry and clean up resources.
    This is called when the integration is removed or reloaded.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
        
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    
    return unload_ok

# Real-time control state values written to point 47015.
STATE_STANDBY = 0
STATE_CHARGING = 1
STATE_DISCHARGING = 2


def _is_bk1600(entry: ConfigEntry) -> bool:
    """Return True when the config entry is a BK1600 / BK1600 Ultra."""
    return "BK1600" in (entry.data.get("device_model") or "")


def _resolve_target_entries(hass: HomeAssistant, call: ServiceCall) -> list[ConfigEntry]:
    """Return the config entries targeted by a simple control action.

    The device target is optional: when none is given and exactly one INDEVOLT
    device is loaded, that device is used.
    """
    device_ids = call.data.get("device_id")
    if isinstance(device_ids, str):
        device_ids = [device_ids]

    if not device_ids:
        entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]
        if len(entries) == 1:
            return entries
        raise ServiceValidationError(
            "No device selected: choose a target device when several INDEVOLT "
            "devices are configured"
        )

    device_registry = dr.async_get(hass)
    entries = []
    for device_id in device_ids:
        device = device_registry.async_get(device_id)
        entry_id = next(iter(device.config_entries), None) if device else None
        entry = hass.config_entries.async_get_entry(entry_id) if entry_id else None
        if entry is None:
            raise ServiceValidationError(f"Device {device_id} not found")
        entries.append(entry)
    return entries


def _validate_real_time_request(
    entry: ConfigEntry, state: int, power: int, soc: int
) -> None:
    """Validate power and SOC for a charge / discharge request."""
    if _is_bk1600(entry):
        min_power = 0
        max_power = (
            BK1600_MAX_CHARGE_POWER
            if state == STATE_CHARGING
            else BK1600_MAX_DISCHARGE_POWER
        )
        min_soc = 0
    else:
        min_power = MIN_REAL_TIME_CONTROL_POWER
        max_power = MAX_REAL_TIME_CONTROL_POWER
        min_soc = 5

    if not min_power <= power <= max_power:
        raise ServiceValidationError(
            f"Power must be between {min_power} and {max_power} W"
        )
    if not min_soc <= soc <= 100:
        raise ServiceValidationError(f"SOC must be between {min_soc} and 100 %")


def _register_services(hass: HomeAssistant) -> None:
    """Register Indevolt services."""

    async def handle_set_work_mode(call: ServiceCall):

        device_ids = call.data.get("device_id")

        if not device_ids:
            raise ServiceValidationError("No device selected")

        mode: str = call.data["mode"]

        # Reason: The services.yaml selector constrains only the UI, so a direct
        # service call could still submit 10801 W.
        # Goal: Apply the same pre-write limit to every SolidFlex/PowerFlex
        # real-time control entry point.
        # Implementation: After reading mode, restrict the check to this service
        # and Real-Time Control, then compare against the shared constant before
        # registry access, ConfigEntry resolution, and the device loop; raise a
        # validation error immediately when the value is out of range.
        # Impact: Requests of 10801 W or more fail early with a clear validation
        # error; requests at or below 10800 W keep the original points, payload,
        # and refresh order.
        # Scope: BK Actions, non-real-time modes, multi-target ordering, points
        # 47005/47015, and the refresh contract are unchanged.
        # Validation: The 10801 W test replaces registry access with a failure
        # sentinel and asserts that API writes and refreshes remain at zero.
        # Trade-off: Validate at the handler's earliest common entry point instead
        # of relying only on the UI or broadening the change at the API layer.
        # Risk: Moving the check into the device loop could create partial success,
        # with an earlier target written before a later target fails.
        # Rollback: Remove this pre-write check and the shared constant reference to
        # restore the old limit behavior; no persistent-data migration is involved.
        if (
            call.service == "set_solidflex_powerflex_work_mode"
            and mode == "Real-Time Control"
        ):
            power: int = call.data.get("power", 0)
            if power > MAX_REAL_TIME_CONTROL_POWER:
                raise ServiceValidationError(
                    f"Power must not exceed {MAX_REAL_TIME_CONTROL_POWER} W"
                )

        MODE_MAP = {
            "Self-Consumed Prioritized": 1,
            "Real-Time Control": 4,
            "Charge/Discharge Schedule": 5,
        }

        device_registry = dr.async_get(hass)
        
        for device_id in device_ids:

            device = device_registry.async_get(device_id)
            entry_id = next(iter(device.config_entries), None)

            entry = hass.config_entries.async_get_entry(entry_id)
            coordinator = entry.runtime_data
            api = coordinator.api

            await api.set_data(
                point=47005,
                value=[MODE_MAP[mode]],
            )

            if mode == "Real-Time Control":
                state: str = call.data.get("state", "Standby")
                power: int = call.data.get("power", 0)
                soc: int = call.data.get("soc", 5)

                STATE_MAP = {
                    "Standby": 0,
                    "Charging": 1,
                    "Discharging": 2,
                }

                await api.set_data(
                    point=47015,
                    value=[
                        STATE_MAP.get(state),
                        power,
                        soc,
                    ],
                )

            await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "set_solidflex_powerflex_work_mode",
        handle_set_work_mode,
    )

    hass.services.async_register(
        DOMAIN,
        "set_bk1600_work_mode",
        handle_set_work_mode,
    )

    # Simple control actions.
    # These are thin wrappers around the same points used by
    # set_*_work_mode (47005 work mode, 47015 real-time state/power/SOC). The
    # device target is optional and defaults to the only loaded INDEVOLT device.

    async def _set_work_mode(call: ServiceCall, mode: int, *, bk1600: bool) -> None:
        entries = _resolve_target_entries(hass, call)
        if not bk1600 and any(_is_bk1600(entry) for entry in entries):
            raise ServiceValidationError(
                "This work mode is not supported by BK1600 / BK1600 Ultra"
            )

        for entry in entries:
            coordinator = entry.runtime_data
            await coordinator.api.set_data(point=47005, value=[mode])
            await coordinator.async_request_refresh()

    async def _set_real_time_state(
        call: ServiceCall, state: int, *, power: int, soc: int
    ) -> None:
        entries = _resolve_target_entries(hass, call)

        # Validate every target before the first write to avoid partial success.
        if state != STATE_STANDBY:
            for entry in entries:
                _validate_real_time_request(entry, state, power, soc)

        for entry in entries:
            coordinator = entry.runtime_data
            await coordinator.api.set_data(point=47005, value=[4])
            await coordinator.api.set_data(point=47015, value=[state, power, soc])
            await coordinator.async_request_refresh()

    def _read_power_and_soc(call: ServiceCall, default_soc: int) -> tuple[int, int]:
        try:
            power = int(call.data["power"])
            soc = int(call.data.get("soc", default_soc))
        except KeyError as err:
            raise ServiceValidationError("power is required") from err
        except (TypeError, ValueError) as err:
            raise ServiceValidationError("power and soc must be numbers") from err
        return power, soc

    async def handle_charge(call: ServiceCall) -> None:
        power, soc = _read_power_and_soc(call, default_soc=100)
        await _set_real_time_state(call, STATE_CHARGING, power=power, soc=soc)

    async def handle_discharge(call: ServiceCall) -> None:
        power, soc = _read_power_and_soc(call, default_soc=5)
        await _set_real_time_state(call, STATE_DISCHARGING, power=power, soc=soc)

    async def handle_stop(call: ServiceCall) -> None:
        await _set_real_time_state(call, STATE_STANDBY, power=0, soc=5)

    async def handle_set_realtime_mode(call: ServiceCall) -> None:
        await _set_work_mode(call, 4, bk1600=True)

    async def handle_set_self_consumption_mode(call: ServiceCall) -> None:
        await _set_work_mode(call, 1, bk1600=False)

    async def handle_set_schedule_mode(call: ServiceCall) -> None:
        await _set_work_mode(call, 5, bk1600=False)

    for service, handler in (
        ("charge", handle_charge),
        ("discharge", handle_discharge),
        ("stop", handle_stop),
        ("set_realtime_mode", handle_set_realtime_mode),
        ("set_self_consumption_mode", handle_set_self_consumption_mode),
        ("set_schedule_mode", handle_set_schedule_mode),
    ):
        hass.services.async_register(DOMAIN, service, handler)
