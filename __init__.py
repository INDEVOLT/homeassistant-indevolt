"""Home Assistant integration for indevolt device."""

# 调整原因：future import 位于模块说明之前时，该字符串不会被识别为模块 docstring。
# 实现方式：把既有模块说明移动到文件首行，再紧接 future import，满足 Python 位置约束。
# 影响边界：只修正模块元数据和静态检查结果，不改变集成加载或服务执行行为。
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import device_registry as dr
# 引入原因：Action 与 number 若分别写死 10800，后续维护可能出现入口上限漂移。
# 使用方式：服务 handler 在目标解析和设备写入前使用该常量判断实时功率上限。
# 影响边界：只新增只读常量引用；DOMAIN、PLATFORMS、加载顺序和导入副作用不变。
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

        # 原因：services.yaml 的 selector 只约束 UI，直接调用服务仍可能提交 10801 W。
        # 目标：让所有 SolidFlex/PowerFlex 实时控制入口执行同一写前上限保护。
        # 实现：读取 mode 后，以 service 名称和 Real-Time Control 模式限定作用域，再在
        # registry、ConfigEntry 和设备循环之前比较共享常量，越界时立即抛出验证错误。
        # 影响：10801 W 及以上会提前得到明确验证错误；不超过 10800 W 的请求继续使用
        # 原点位、原 payload 和原刷新顺序。
        # 边界：BK Action、非实时控制模式、多目标顺序、47005/47015 和刷新合同不变。
        # 验证：10801 W 用例把 registry 访问设为失败哨兵，并断言 API 写入和刷新均为零。
        # 方案取舍：在 handler 最早公共入口校验，而不是只依赖 UI 或在 API 层扩大影响面。
        # 风险：判断若移入设备循环，可能出现前序目标已经写入、后序目标才失败的部分成功。
        # 回退：移除该写前判断和共享常量引用即可恢复旧上限行为，不涉及持久化数据迁移。
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
