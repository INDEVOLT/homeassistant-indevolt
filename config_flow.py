import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, SUPPORTED_MODELS
from .utils import get_device_gen
import logging
import asyncio
from .coordinator import IndevoltAPI

_LOGGER = logging.getLogger(__name__)

class IndevoltConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configuration flow for Indevolt integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """
        Handle the initial user configuration step.
        This method is called when the user initiates the integration setup.
        It presents a form for device connection parameters and validates them.
        """
        
        errors = {}
        if user_input is not None:
            host = user_input["host"]
            port = user_input.get("port", DEFAULT_PORT)
            scan_interval = user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL)
            device_model = user_input["device_model"]

            api = IndevoltAPI(host, port, async_get_clientsession(self.hass))

            device_gen = get_device_gen(device_model)
            

            try:
                fw_version=""
                if device_gen == 1:
                    fw_version="V1.3.0A_R006.072_M4848_00000039"
                else:
                    fw_version="V1.3.09_R00D.012_M4801_00000015"

                data = await api.fetch_data([0])
                device_sn = data.get("0")

                # Create configuration entry on successful connection.
                return self.async_create_entry(
                    title=f"INDEVOLT {device_model} ({host})", # Entry title shown in HA UI.
                    data={
                        "host": host,
                        "port": port,
                        "scan_interval": scan_interval,
                        "sn": device_sn,
                        "device_model": device_model,
                        "fw_version": fw_version
                    }
                )
            
            except asyncio.TimeoutError:
                errors["base"] = "timeout"
            except Exception as e:
                _LOGGER.error("Unknown error occurred while verifying device: %s", str(e), exc_info=True)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host"): str,
                vol.Optional("port", default=DEFAULT_PORT): int,
                vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): int,
                vol.Required("device_model"): vol.In(SUPPORTED_MODELS),
            }),
            errors=errors
        )