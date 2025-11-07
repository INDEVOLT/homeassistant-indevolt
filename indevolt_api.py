import asyncio
import aiohttp
import json
from typing import Dict, Any, List

class IndevoltAPI:
    """Handles all HTTP communication with Indevolt devices"""
    
    def __init__(self, host: str, port: int, session: aiohttp.ClientSession):
        self.host = host
        self.port = port
        self.session = session
        self.base_url = f"http://{host}:{port}/rpc"
        self.timeout = aiohttp.ClientTimeout(total=60)
    
    async def fetch_data(self, keys: List[str]) -> Dict[str, Any]:
        """Fetch raw JSON data from the device"""
        config_param = json.dumps({"t": keys}).replace(" ", "")
        url = f"{self.base_url}/Indevolt.GetData?config={config_param}"
        
        try:
            async with self.session.post(url, timeout=self.timeout) as response:
                if response.status != 200:
                    raise Exception(f"HTTP status error: {response.status}")
                return await response.json()
                
        except asyncio.TimeoutError:
            raise Exception("Indevolt.GetData Request timed out")
        except aiohttp.ClientError as err:
            raise Exception(f"Indevolt.GetData Network error: {err}")

