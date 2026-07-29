from homeassistant.const import Platform

DOMAIN = "indevolt"
DEFAULT_PORT = 8080
DEFAULT_SCAN_INTERVAL = 30
# Reason: The Action and Gen2 number paths must enforce the same product limit;
# duplicating the value would create configuration-drift risk.
# Goal: Establish one Python runtime source of truth so both entry points use the
# reviewed 10800 W boundary.
# Implementation: Define a named constant in const.py and import it in both the
# service handler and the Gen2 number implementation.
# Impact: Future limit changes require one edit, reducing maintenance and review
# cost for both entry points.
# Scope: This does not change the scan interval, platform list, device protocol,
# or any non-target power limit.
# Validation: Tests assert the constant is 10800 and verify that the Action
# selector and Gen2 description use the same value.
# Trade-off: Use a shared constant instead of hard-coding the value separately in
# two Python files.
MAX_REAL_TIME_CONTROL_POWER = 10800
PLATFORMS = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]