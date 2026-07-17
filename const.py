from homeassistant.const import Platform

DOMAIN = "indevolt"
DEFAULT_PORT = 8080
DEFAULT_SCAN_INTERVAL = 30
# 原因：Action 与 Gen2 number 都要执行同一个产品上限，重复数值会产生配置漂移风险。
# 目标：建立唯一 Python 运行时真源，让两个入口共同引用评审确认的 10800 W 边界。
# 实现：在 const.py 定义命名常量，由服务 handler 和 Gen2 number 同时导入使用。
# 影响：两个入口调整上限时只需修改一处，降低维护和审核成本。
# 边界：不改变扫描周期、平台列表、设备协议或任何非目标功率限制。
# 验证：测试直接断言常量为 10800，并核对 Action selector 与 Gen2 描述使用同一值。
# 方案取舍：使用共享常量而不是在两个 Python 文件中分别写死数值。
MAX_REAL_TIME_CONTROL_POWER = 10800
PLATFORMS = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]