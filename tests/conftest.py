"""让聚焦测试直接加载仓库中的集成源码。

覆盖目标：保证聚焦测试执行当前仓库源码，而不是环境中可能存在的其他安装副本。
实现方式：在 pytest 进程内构造 custom_components.indevolt 包并执行仓库根入口。
能够证明：相对导入和测试对象来自本次待审源码。
不能证明：该加载方式不代表 HA 完整生命周期，也不能证明真实设备行为。
"""

# 引入原因：仓库根不是可直接导入的标准包目录，需要从文件路径构造包。
# 使用方式：spec_from_file_location 定义包入口，module_from_spec 创建对应模块对象。
# 影响边界：模块只进入当前 pytest 进程，不安装到系统 Python 环境。
from importlib.util import module_from_spec, spec_from_file_location

# 引入原因：测试命令可能从不同工作目录启动，不能依赖相对 cwd。
# 使用方式：由 conftest.py 的固定位置推导仓库根和 __init__.py。
# 影响边界：只解析本地路径，不读取或修改范围外目录。
from pathlib import Path

# 引入原因：动态包必须登记到 sys.modules，并需要一个最小父包对象。
# 使用方式：sys 保存包注册，ModuleType 构造 custom_components 父命名空间。
# 影响边界：只改变当前测试进程内存，不覆盖磁盘文件或 HA 运行实例。
import sys
from types import ModuleType


# 实现原因：导入路径和包名会被包注册、spec 和测试 import 重复使用。
# 实现方式：集中定义仓库根与标准 HA 包名，避免辅助代码内部出现不同字面量。
# 影响边界：只约束测试加载位置，不改变运行时安装目录。
INTEGRATION_ROOT = Path(__file__).parents[1]
PACKAGE_NAME = "custom_components.indevolt"


def _load_integration_package() -> None:
    """在内存中构造 custom_components.indevolt 包，不复制运行文件。"""
    # 实现原因：测试环境中可能尚不存在 custom_components 父包。
    # 实现方式：用 setdefault 补齐最小命名空间，已有父包则直接复用。
    # 影响边界：不覆盖其他测试预先注入的父包状态。
    custom_components = sys.modules.setdefault(
        "custom_components", ModuleType("custom_components")
    )
    if not hasattr(custom_components, "__path__"):
        custom_components.__path__ = []

    # 实现原因：把仓库根文件当普通模块导入会破坏 .const 等相对导入。
    # 实现方式：以 PACKAGE_NAME 和 submodule_search_locations 把 __init__.py 声明为包入口。
    # 影响边界：spec 创建失败会终止测试收集，不会静默回退到其他安装副本。
    spec = spec_from_file_location(
        PACKAGE_NAME,
        INTEGRATION_ROOT / "__init__.py",
        submodule_search_locations=[str(INTEGRATION_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the INDEVOLT integration package")

    # 实现原因：包入口执行时的相对导入需要先在 sys.modules 找到完整包名。
    # 实现方式：先登记 module，再由 loader 执行当前仓库入口。
    # 影响边界：只执行模块导入和服务定义，不启动 HA 生命周期或设备通信。
    module = module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = module
    spec.loader.exec_module(module)


# 实现原因：测试模块收集时会立即 import custom_components.indevolt。
# 实现方式：在 conftest 加载阶段先完成一次包注册。
# 影响边界：作用域限定在本次 pytest 进程，退出后自动释放。
_load_integration_package()
