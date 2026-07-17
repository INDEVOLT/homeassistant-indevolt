<!--
原因：README 面向安装和日常使用，不适合承载各版本之间的功能差异。
目标：为每个版本提供独立、可追溯且便于审核的用户可见变更记录。
实现：按版本倒序记录本地历史中的 1.2、1.1 和 1.0，只保留功能变化、兼容边界和
用户可见的文档变化；1.2 先说明原有 2400 W 输入上限造成的问题，再列出文档交付。
影响：审核者可以单独判断各版本改变了什么，README 的用户指南定位保持不变。
边界：不记录部署或版本切换操作指南、内部函数、测试命令或开发环境，也不宣称真实
设备已经输出 10800 W。
验证：本地 manifest.json 历史确认版本为 1.0、1.1 和 1.2；各版本内容已对照对应版本的
配置和实体差异。
风险：若混入操作指南，变更记录与 README 的职责会再次重叠，因此只保留版本事实。
-->

# Change log

This file records user-visible changes to the INDEVOLT integration.

## 1.2

### Fixed

- Fixed a Home Assistant input cap that prevented SolidFlex2000 and
  PowerFlex2000 users from entering **Real-Time Control** values above 2400 W.
  Automations and the **Power (Real-time control)** setting now accept values
  up to 10800 W.

### Documentation

- Corrected the installation file list to use `services.yaml` and clarified
  which integration files need to be copied.
- Added Simplified Chinese versions of the user guide and change log.

### Compatibility and limits

- The minimum remains 50 W.
- Automations continue to use 10 W steps, while the **Power (Real-time
  control)** setting continues to use 1 W steps.
- BK1600 and BK1600 Ultra control behavior and limits are unchanged.
- 10800 W is the Home Assistant input limit. It does not guarantee that a
  device will output 10800 W; actual output depends on the model, firmware,
  operating state, and current system conditions.
- The integration configuration format is unchanged.

## 1.1

### Added

- Added Home Assistant controls for work mode, real-time control, target SOC,
  power limits, grid charging, bypass, and supported device switches.
- Added automation actions for changing the work mode of SolidFlex2000,
  PowerFlex2000, BK1600, and BK1600 Ultra devices.
- Expanded SolidFlex2000 and PowerFlex2000 monitoring to include firmware,
  grid, PV, battery, energy, operating-state, and connected battery-pack
  information.

### Changed

- Simplified setup to use the device IP address and update interval. The
  integration detects the supported device family, serial number, and firmware
  information from the device.
- Added duplicate-device protection based on the detected serial number.
- Added number, select, and switch controls alongside the existing sensors.

### Compatibility and limits

- The SolidFlex2000 and PowerFlex2000 **Real-Time Control** inputs exposed a
  maximum of 2400 W in this version.
- BK1600 and BK1600 Ultra retained their separate charging and discharging
  limits.

## 1.0

### Added

- Initial Home Assistant integration for local monitoring of INDEVOLT devices.
- Added support for BK1600, BK1600 Ultra, SolidFlex2000, and PowerFlex2000.
- Added setup fields for device address, port, update interval, and device
  family.
- Added sensors for power, energy, battery, meter, and operating-state
  information.

### Fixed

- Corrected the SolidFlex2000 and PowerFlex2000 battery SOC reading during the
  1.0 version line.
