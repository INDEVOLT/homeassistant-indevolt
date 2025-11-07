from __future__ import annotations

"""Home Assistant integration for indevolt device."""

import logging
from typing import Any, Dict
from datetime import timedelta

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .indevolt_api import IndevoltAPI
from .utils import get_device_gen

_LOGGER = logging.getLogger(__name__)

class IndevoltCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=config.get("scan_interval", DEFAULT_SCAN_INTERVAL)),
        )
        self.config = config
        self.session = async_get_clientsession(hass)
        
        # Initialize Indevolt API.
        self.api = IndevoltAPI(
            host=config['host'],
            port=config['port'],
            session=async_get_clientsession(self.hass)
        )
    
    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch latest data from device."""
        try:
            keys=[]
            if get_device_gen(self.config["device_model"])==1:
                keys=[7101,1664,1665,2108,1502,1505,2101,2107,1501,6000,6001,6002,6105,6004,6005,6006,6007,7120,21028]
            else:
                keys=[7101,1664,1665,1666,1667,1501,2108,1502,1505,2101,2107,142,6000,6001,6009,6105,6004,6005,6006,6007,7120,11016,667]
            
            data: Dict[str, Any]={}
            for key in keys:
                result=await self.api.fetch_data([key])
                data.update(result)

            return data
        
        except Exception as err:
            _LOGGER.error("API request failed: %s", str(err))
            return self.data or {}
        
        except Exception as err:
            _LOGGER.exception("Unexpected update error")
            raise UpdateFailed(f"Update failed: {err}") from err
