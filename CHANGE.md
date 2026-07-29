<!--
Reason: README is for installation and daily use, so it is not the right place
for functional differences between versions.
Goal: Provide a separate, traceable, and reviewable user-visible change record
for each version.
Implementation: Record local-history versions 1.2, 1.1, and 1.0 in reverse order,
keeping only functional changes, compatibility boundaries, and user-visible
documentation changes. Version 1.2 first identifies the problem caused by the
previous 2400 W input limit and then lists the documentation deliverables.
Impact: Reviewers can judge what each version changed independently, while README
remains focused on user guidance.
Scope: Do not record deployment or version-switching procedures, internal functions,
test commands, or development environments, and do not claim that a physical device
has produced 10800 W.
Validation: Local manifest.json history confirms versions 1.0, 1.1, and 1.2; each
entry was checked against the configuration and entity differences in that version.
Risk: Adding procedural guidance would overlap with README again, so this file keeps
only version facts.
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
