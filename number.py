
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Awaitable, Callable

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberDeviceClass,
    NumberMode
)
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfPower
# Reason: Direct number calls need the standard HA validation error to prevent an
# out-of-range write.
# Usage: async_set_native_value raises this exception before set_fn for requests
# of 10801 W or more.
# Impact: Only the failure point and error type for out-of-range requests change;
# valid values keep the original point 47016 and refresh flow.
from homeassistant.exceptions import ServiceValidationError

# Reason: The number metadata and runtime validation must use the same 10800 W
# source of truth as the Action.
# Usage: This constant supplies both the Gen2 power_setting maximum and the
# setter's pre-write check.
# Impact: This introduces only a shared read-only constant; API, coordinator, and
# other entity initialization are unchanged.
from .const import MAX_REAL_TIME_CONTROL_POWER
from .indevolt_api import IndevoltAPI
from .coordinator import IndevoltDeviceUpdateCoordinator
from .entity import IndevoltEntity


@dataclass(frozen=True, kw_only=True)
class IndevoltNumberEntityDescription(NumberEntityDescription):
    """Indevolt number entity description."""

    value_fn: Callable[[dict], int | None]
    set_fn: Callable[[IndevoltAPI, int], Awaitable[bool]]


NUMBERS_GEN2 = [
    IndevoltNumberEntityDescription(
        key="backup_soc",
        name="Backup SOC",
        device_class=NumberDeviceClass.BATTERY,
        entity_category=EntityCategory.CONFIG,
        native_min_value=5,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: data.get("6105"),
        set_fn=lambda api, value: api.set_data(
            point=1142,
            value=[value],
        ),
    ),
    IndevoltNumberEntityDescription(
        key="inverter_input_limit",
        name="Inverter Input Limit",
        device_class=NumberDeviceClass.POWER,
        entity_category=EntityCategory.CONFIG,
        native_min_value=50,
        native_max_value=2400,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: data.get("11009"),
        set_fn=lambda api, value: api.set_data(
            point=1138,
            value=[value],
        ),
    ),
    IndevoltNumberEntityDescription(
        key="max_output_power",
        name="Max AC Output Power",
        device_class=NumberDeviceClass.POWER,
        entity_category=EntityCategory.CONFIG,
        native_min_value=50,
        native_max_value=2400,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: data.get("11011"),
        set_fn=lambda api, value: api.set_data(
            point=1147,
            value=[value],
        ),
    ),
    IndevoltNumberEntityDescription(
        key="feed_in_power_limit",
        name="Feed-in Power Limit",
        device_class=NumberDeviceClass.POWER,
        entity_category=EntityCategory.CONFIG,
        native_min_value=50,
        native_max_value=2400,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: data.get("11010"),
        set_fn=lambda api, value: api.set_data(
            point=1146,
            value=[value],
        ),
    ),
    IndevoltNumberEntityDescription(
        key="power_setting",
        name="Power (Real-time control)",
        device_class=NumberDeviceClass.POWER,
        entity_category=EntityCategory.CONFIG,
        native_min_value=50,
        # Reason: The old metadata maximum of 2400 blocked approved inputs from
        # 2401 through 10800 W at the UI layer.
        # Goal: Make the Gen2 real-time power number expose and accept the same
        # shared maximum as the Action.
        # Implementation: Replace only the literal 2400 assigned to
        # power_setting.native_max_value with the shared constant.
        # Impact: The HA UI and entity metadata accept input through 10800 W
        # without truncating or converting the requested value.
        # Scope: The minimum, step, unit, point 47016, other Gen2 numbers, and BK
        # dynamic maximums are unchanged.
        # Validation: Setup tests for both Gen2 models assert min=50, max=10800,
        # and step=1.
        native_max_value=MAX_REAL_TIME_CONTROL_POWER,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: None,
        set_fn=lambda api, value: api.set_data(
            point=47016,
            value=[value],
        ),
    ),
    IndevoltNumberEntityDescription(
        key="soc_setting",
        name="Target SOC (Real-time control)",
        device_class=NumberDeviceClass.BATTERY,
        entity_category=EntityCategory.CONFIG,
        native_min_value=5,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: None,
        set_fn=lambda api, value: api.set_data(
            point=47017,
            value=[value],
        ),
    ),
]


NUMBERS_GEN1 = [
    IndevoltNumberEntityDescription(
        key="power_setting",
        name="Power (Real-time control)",
        device_class=NumberDeviceClass.POWER,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.SLIDER,
        native_min_value=0,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: None,
        set_fn=lambda api, value: api.set_data(
            point=47016,
            value=[value],
        ),
    ),
    IndevoltNumberEntityDescription(
        key="soc_setting",
        name="Target SOC (Real-time control)",
        device_class=NumberDeviceClass.BATTERY,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: None,
        set_fn=lambda api, value: api.set_data(
            point=47017,
            value=[value],
        ),
    ),
]

async def async_setup_entry(hass, entry, async_add_entities):
    if "BK1600" in entry.data.get("device_model"):
        async_add_entities(
            IndevoltNumberEntity(entry.runtime_data, description) for description in NUMBERS_GEN1
        )
    else:
        async_add_entities(
            IndevoltNumberEntity(entry.runtime_data, description) for description in NUMBERS_GEN2
        )


class IndevoltNumberEntity(IndevoltEntity, NumberEntity):
    """Indevolt number entity."""

    def __init__(
        self,
        coordinator: IndevoltDeviceUpdateCoordinator,
        description: IndevoltNumberEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (f"{coordinator.config_entry.unique_id}_{description.key}")


    @property
    def device_info(self):
        return self.device_info_main()

    @property
    def native_max_value(self) -> int:
        if "BK1600" not in self.coordinator.config_entry.data.get("device_model"):
            return self.entity_description.native_max_value
        
        if self.entity_description.key != "power_setting":
            return self.entity_description.native_max_value
        
        state = self.coordinator.data.get("6001")
        if state == 1001:
            return 1200
        else:
            return 800 
    
    @property
    def native_value(self) -> int | None:
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: int) -> None:
        # Reason: Entity services or internal callers can bypass native_max_value,
        # so UI metadata is not a write guard.
        # Goal: Enforce the 10800 W pre-write limit for non-BK power_setting calls
        # even when they bypass the UI.
        # Implementation: Narrow the scope by device model and description key,
        # then compare with the shared constant before calling set_fn.
        # Impact: Values of 10801 W or more do not invoke point 47016 or refresh;
        # valid values are still written unchanged.
        # Scope: BK numbers, SOC numbers, other power entities, points, payloads,
        # and refresh behavior are unchanged.
        # Validation: The negative test asserts zero FakeAPI writes and zero counts
        # for both refresh methods when the value is out of range.
        # Trade-off: Put the guard in the entity setter instead of relying only on
        # bypassable UI metadata or changing the general API.
        # Risk: If validation ran after set_fn, the out-of-range value might already
        # have been sent to point 47016 and could not be recalled.
        # Rollback: Remove this conditional branch and restore the old metadata
        # maximum; entity registration and stored data require no migration.
        if (
            "BK1600" not in self.coordinator.config_entry.data.get("device_model")
            and self.entity_description.key == "power_setting"
            and value > MAX_REAL_TIME_CONTROL_POWER
        ):
            raise ServiceValidationError(
                f"Power must not exceed {MAX_REAL_TIME_CONTROL_POWER} W"
            )

        await self.entity_description.set_fn(self.coordinator.api, value)
        await self.coordinator.async_refresh()
