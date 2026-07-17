"""Load the integration source from this repository for focused tests.

Coverage goal: Ensure focused tests execute the current repository source, not
another installed copy that may exist in the environment.
Implementation: Construct the custom_components.indevolt package inside the
pytest process and execute the repository-root entry point.
Proves: Relative imports and tested objects come from the source under review.
Does not prove: This loader does not represent the complete HA lifecycle or
prove behavior on a physical device.
"""

# Reason: The repository root is not a standard importable package directory, so
# the package must be constructed from a file path.
# Usage: spec_from_file_location defines the package entry point and
# module_from_spec creates the corresponding module object.
# Impact: The module exists only in the current pytest process and is not installed
# into the system Python environment.
from importlib.util import module_from_spec, spec_from_file_location

# Reason: Test commands may start in different working directories and cannot
# rely on a relative current working directory.
# Usage: Derive the repository root and __init__.py from conftest.py's fixed path.
# Impact: This only resolves local paths; it neither reads nor modifies directories
# outside the repository scope.
from pathlib import Path

# Reason: A dynamic package must be registered in sys.modules and needs a minimal
# parent-package object.
# Usage: sys stores the package registration and ModuleType creates the
# custom_components parent namespace.
# Impact: This changes only memory in the current test process; it does not
# overwrite files or affect a running HA instance.
import sys
from types import ModuleType


# Reason: Package registration, the spec, and test imports reuse the import path
# and package name.
# Implementation: Define the repository root and standard HA package name once to
# prevent different literals inside the loader helper.
# Impact: This constrains only the test load location and does not change the
# runtime installation directory.
INTEGRATION_ROOT = Path(__file__).parents[1]
PACKAGE_NAME = "custom_components.indevolt"


def _load_integration_package() -> None:
    """Construct custom_components.indevolt in memory without copying files."""
    # Reason: The custom_components parent package may not yet exist in the test
    # environment.
    # Implementation: Use setdefault to add the minimal namespace, while reusing
    # an existing parent package when present.
    # Impact: This does not overwrite parent-package state injected by other tests.
    custom_components = sys.modules.setdefault(
        "custom_components", ModuleType("custom_components")
    )
    if not hasattr(custom_components, "__path__"):
        custom_components.__path__ = []

    # Reason: Importing the repository-root file as a regular module would break
    # relative imports such as .const.
    # Implementation: Declare __init__.py as the package entry point with
    # PACKAGE_NAME and submodule_search_locations.
    # Impact: A spec-construction failure stops test collection instead of silently
    # falling back to another installed copy.
    spec = spec_from_file_location(
        PACKAGE_NAME,
        INTEGRATION_ROOT / "__init__.py",
        submodule_search_locations=[str(INTEGRATION_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the INDEVOLT integration package")

    # Reason: Relative imports executed by the package entry point must find the
    # complete package name in sys.modules first.
    # Implementation: Register the module before the loader executes the current
    # repository entry point.
    # Impact: This executes only module imports and service definitions; it does
    # not start the HA lifecycle or device communication.
    module = module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = module
    spec.loader.exec_module(module)


# Reason: Test modules import custom_components.indevolt immediately during
# collection.
# Implementation: Complete package registration once while conftest is loading.
# Impact: The scope is limited to this pytest process and is released when the
# process exits.
_load_integration_package()
