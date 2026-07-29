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

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import device_registry as dr
# Reason: Hard-coding 10800 separately in the Action and number paths could let
# their limits drift during later maintenance.
# Usage: The service handler uses this constant to enforce the real-time power
# limit before target resolution and device writes.
# Impact: This adds only a read-only constant reference; DOMAIN, PLATFORMS, load
# order, and import side effects are unchanged.
from .const import DOMAIN, MAX_REAL_TIME_CONTROL_POWER, PLATFORMS
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
