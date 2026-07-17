"""验证 Gen2 10800 W 输入边界，并防止 BK 与既有写入路径回归。

覆盖目标：同时核对 Action、number、YAML、共享常量以及 BK 非目标边界。
实现方式：使用参数化、fake、monkeypatch 和配置解析验证调用顺序、payload 与零写入。
能够证明：集成层的两个 Gen2 入口在 10800/10801 W 边界上保持一致。
不能证明：测试不连接 HA 实例或真实设备，不能证明物理输出或命令读回。
"""

# 引入原因：需要只读解析仓库中的 services.yaml，并避免依赖启动目录。
# 使用方式：从测试文件位置推导仓库根，再读取服务配置进行一致性断言。
# 影响边界：只读取当前仓库文件，不修改运行配置。
from pathlib import Path

# 引入原因：测试需要最小化模拟 ConfigEntry、ServiceCall 和 runtime_data。
# 使用方式：SimpleNamespace 为 fake 对象提供生产代码实际访问的属性。
# 影响边界：只提供测试属性容器，不替代完整 HA 生命周期或真实设备验收。
from types import SimpleNamespace

# 引入原因：需要异步用例、参数矩阵、monkeypatch 和异常断言。
# 使用方式：pytest 驱动两个入口的代表值、越界值和 BK 回归矩阵。
# 影响边界：只驱动 fake 对象，不触发网络或设备副作用。
import pytest

# 引入原因：YAML 不能直接导入 Python 共享常量，需要解析后独立核对。
# 使用方式：safe_load 读取 selector，并与 Python 描述及 BK 旧边界比较。
# 影响边界：只验证配置结构，不改变 services.yaml。
import yaml

# 引入原因：产品合同要求越界请求返回 HA 标准验证错误。
# 使用方式：pytest.raises 同时断言错误类型和 10800 W 错误信息。
# 影响边界：只用于测试捕获，不改变生产异常处理。
from homeassistant.exceptions import ServiceValidationError

# 引入原因：复制 handler 逻辑会让测试与生产实现分叉。
# 使用方式：调用真实 _register_services，取得实际闭包并验证写入顺序。
# 影响边界：注册目标是 FakeServices，不会写入正在运行的 HA 实例。
from custom_components.indevolt import _register_services

# 引入原因：10801 W 必须在 registry 访问前失败，需要监测生产模块实际使用的引用。
# 使用方式：monkeypatch 将 async_get 替换为 fake 或失败哨兵。
# 影响边界：替换仅在单个测试内生效，不修改生产模块文件。
from custom_components.indevolt import dr as device_registry_module

# 引入原因：只检查 NUMBERS_GEN2 不能证明两个型号在 setup 时真的选择该列表。
# 使用方式：调用真实 number.async_setup_entry，并替换实体构造以收集描述。
# 影响边界：只替换测试中的实体构造，不创建 HA 实体。
from custom_components.indevolt import number as number_platform

# 引入原因：Action、number 与 YAML 必须围绕同一个 10800 W 真源接受审核。
# 使用方式：直接断言常量值，并作为 selector 与实体描述的预期值。
# 影响边界：只读取常量，不改变运行状态。
from custom_components.indevolt.const import MAX_REAL_TIME_CONTROL_POWER

# 引入原因：需要使用真实 Gen1/Gen2 描述和实体 setter，避免重写生产合同。
# 使用方式：选择实际 power_setting 描述并直接调用 IndevoltNumberEntity setter。
# 影响边界：API 被 FakeAPI 替代，不会产生真实 47016 写入。
from custom_components.indevolt.number import (
    NUMBERS_GEN1,
    NUMBERS_GEN2,
    IndevoltNumberEntity,
)


# 覆盖目标：观察服务注册、点位 payload 和两类刷新调用，同时隔离外部副作用。
# 实现方式：FakeServices 保存 handler，FakeAPI 记录写入，FakeCoordinator 记录刷新次数。
# 能够证明：生产逻辑发起了哪些调用以及调用顺序是否保持不变。
# 不能证明：fake 返回成功不代表真实设备接受命令或产生对应物理输出。
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


# 覆盖目标：保留合法 Action 的 registry → ConfigEntry → coordinator 解析链。
# 实现方式：FakeRegistry 返回固定 entry_id，FakeConfigEntries 返回注入的 coordinator。
# 能够证明：合法请求仍经过既有目标解析，而越界请求能否在该链路之前失败。
# 不能证明：不会读取 HA 的真实 registry、ConfigEntry、权限或凭据状态。
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


# 覆盖目标：让 Action 用例共享同一最小 HA 上下文和固定实时控制输入。
# 实现方式：make_hass 组装服务与 ConfigEntry fake，service_call 生成标准 payload。
# 能够证明：不同功率值只改变被测变量，不被样板差异干扰。
# 不能证明：固定单目标 payload 不覆盖真实多目标、权限或并发行为。
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


# 覆盖目标：放宽上限后，合法 Action 的写点、顺序和 payload 必须保持不变。
# 实现方式：对两个 Gen2 型号参数化 2400、2401、4800、7200、10800 W。
# 能够证明：合法值依次写 47005/47015，功率原值透传，并只请求一次刷新。
# 不能证明：fake 写入成功不代表设备实际输出对应功率。
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


# 覆盖目标：10801 W 必须在 registry、47005、47015 和刷新之前失败。
# 实现方式：把 registry 访问替换为失败哨兵，再调用真实服务 handler。
# 能够证明：越界请求没有目标解析、API 写入或刷新。
# 不能证明：该单目标用例不重新定义合法多目标请求的既有部分成功语义。
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


# 覆盖目标：共享 handler 中的 Gen2 判断不能误伤 BK Action。
# 实现方式：通过 set_bk1600_work_mode 发送既有 1200 W 请求并记录完整调用。
# 能够证明：BK 仍使用原点位、payload 和一次请求刷新。
# 不能证明：该用例不扩大 BK 上限，也不覆盖 BK 的全部真实设备状态。
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


# 覆盖目标：隔离验证真实 description 与 setter 合同，避免无关 HA 生命周期干扰。
# 实现方式：用 object.__new__ 创建实体，再只注入 coordinator 和 description。
# 能够证明：setter 对实际描述的写点、边界和刷新行为。
# 不能证明：不覆盖完整实体构造与注册生命周期；setup 路由由独立用例验证。
def make_number_entity(coordinator, description):
    entity = object.__new__(IndevoltNumberEntity)
    entity.coordinator = coordinator
    entity.entity_description = description
    return entity


# 覆盖目标：Gen2 number 必须独立接受与 Action 相同的合法功率矩阵。
# 实现方式：直接调用真实实体 setter，并记录 FakeAPI 与刷新计数。
# 能够证明：原值写入 47016、没有截断换算，并执行一次完整刷新。
# 不能证明：不承诺真实设备接受命令或输出对应功率。
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


# 覆盖目标：直接实体调用绕过 UI 时，10801 W 仍必须零写入失败。
# 实现方式：直接向真实 setter 传入 10801，并捕获标准验证错误。
# 能够证明：set_fn、47016 和刷新均未执行。
# 不能证明：不验证 HA 前端如何展示错误，也不测试更低层 API 的通用输入校验。
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


# 覆盖目标：Gen1 BK 共用实体类时仍保持 1200/800 W 动态边界。
# 实现方式：参数化状态 1001/1000，并以各自最大值执行真实 setter。
# 能够证明：BK 最大值计算及原 47016 写入和刷新合同未回归。
# 不能证明：不为 BK 引入 10800 W 能力，也不覆盖其他设备状态组合。
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


# 覆盖目标：SolidFlex2000 与 PowerFlex2000 在 setup 时都必须选择 Gen2 描述。
# 实现方式：替换实体构造为描述收集器，再调用真实 async_setup_entry。
# 能够证明：两个型号均暴露 min=50、max=10800、step=1。
# 不能证明：不创建真实实体，也不验证范围外型号或 HA UI 渲染。
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


# 覆盖目标：防止 YAML selector、Python 共享常量和实体描述后续发生漂移。
# 实现方式：解析 services.yaml，并与 Gen1/Gen2 实际描述和常量逐字段比较。
# 能够证明：目标入口均为 10800 W，且 BK selector/描述保持原边界。
# 不能证明：这是测试时静态一致性检查，不会在运行时自动修复错误配置。
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
