
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
# 引入原因：number 的直接调用需要使用 HA 标准验证错误阻止越界写入。
# 使用方式：async_set_native_value 在调用 set_fn 前用该异常终止 10801 W 及以上请求。
# 影响边界：只改变越界请求的失败位置和错误类型；合法值仍走原 47016 与刷新流程。
from homeassistant.exceptions import ServiceValidationError

# 引入原因：number 元数据和运行时校验必须与 Action 使用同一个 10800 W 真源。
# 使用方式：该常量同时赋给 Gen2 power_setting 最大值，并用于 setter 写前判断。
# 影响边界：只引入共享只读常量；API、coordinator 和其他实体的初始化不变。
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
        # 原因：旧元数据最大值 2400 会在 UI 层阻止已经批准的 2401～10800 W 输入。
        # 目标：让 Gen2 实时功率 number 展示并接受与 Action 相同的共享上限。
        # 实现：仅把 power_setting.native_max_value 从字面量 2400 改为共享常量。
        # 影响：HA UI 和实体元数据允许输入至 10800 W，不对请求值截断或换算。
        # 边界：最小值、步长、单位、47016、其他 Gen2 number 和 BK 动态上限不变。
        # 验证：两个 Gen2 型号的 setup 用例断言 min=50、max=10800、step=1。
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
        # 原因：实体服务或内部调用可以绕过 native_max_value，因此 UI 元数据不是写入保护。
        # 目标：让非 BK 的 power_setting 即使绕过 UI 也执行 10800 W 写前保护。
        # 实现：先按设备型号和 description key 缩小作用域，再在 set_fn 前比较共享常量。
        # 影响：10801 W 及以上不会调用 47016 或 refresh；合法值仍按原值写入。
        # 边界：BK number、SOC number、其他功率实体、点位、payload 和刷新方式不变。
        # 验证：负向用例断言越界时 FakeAPI 写入及两类刷新计数均为零。
        # 方案取舍：保护放在实体 setter，而非只依赖可绕过的 UI 元数据或修改通用 API。
        # 风险：校验若放在 set_fn 之后，越界值可能已经发送到 47016，不能再补救。
        # 回退：移除该条件分支并恢复元数据旧上限即可，不涉及实体注册或存储迁移。
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
