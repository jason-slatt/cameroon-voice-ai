"""Backend API client for BAFOKA services"""

import httpx
from typing import Optional, Dict, Any
from functools import lru_cache

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BackendAPIError(Exception):
    """Backend API error"""
    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"Backend API Error ({status_code}): {message}")


class BackendClient:
    """HTTP client for BAFOKA backend API"""
    
    def __init__(self):
        self.base_url = settings.BACKEND_BASE_URL
        self.timeout = settings.BACKEND_TIMEOUT
        self.api_key = settings.BACKEND_API_KEY
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the backend"""
        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                json=data,
                params=params,
            )
            
            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                raise BackendAPIError(
                    status_code=response.status_code,
                    message=error_data.get("message", "Unknown error"),
                    details=error_data,
                )
            
            return response.json() if response.content else {}
            
        except httpx.RequestError as e:
            logger.error(f"Backend request error: {e}")
            raise BackendAPIError(
                status_code=503,
                message=f"Failed to connect to backend: {str(e)}",
            )
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request"""
        return await self._request("GET", endpoint, params=params)
    
    async def post(
    self,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None,
) -> Dict[str, Any]:
        """POST request"""
        return await self._request("POST", endpoint, data=data, params=params)
    
    async def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """PUT request"""
        return await self._request("PUT", endpoint, data=data)
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request"""
        return await self._request("DELETE", endpoint)


# Singleton instance
backend_client = BackendClient()