"""
Backend API client for BAFOKA services (or any HTTP backend).
"""

from __future__ import annotations
from typing import Optional, Dict, Any, TypeVar, Type, Union
from functools import lru_cache

import httpx
from pydantic import BaseModel, ValidationError

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class BackendAPIError(Exception):
    """Backend API error"""

    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"Backend API Error ({status_code}): {message}")


class BackendClient:
    """
    HTTP client for BAFOKA backend API.

    - Connection pooling via a single httpx.AsyncClient instance.
    - Basic retry logic on 5xx and network errors.
    - Typed responses via Pydantic models.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int,
        api_key: Optional[str] = None,
        max_retries: int = 3,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.api_key = api_key
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create underlying httpx.AsyncClient."""
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
            logger.info("Initialized BackendClient with base_url=%s", self.base_url)
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("Closed BackendClient for base_url=%s", self.base_url)

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], BaseModel]] = None,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Union[T, Dict[str, Any]]:
        """
        Make an HTTP request to the backend with basic retry on 5xx/network errors.

        If `response_model` is provided, parse JSON into that Pydantic model;
        otherwise return a plain dict.
        """
        url = endpoint
        last_error: Optional[Exception] = None

        # Convert Pydantic model to dict if needed
        if isinstance(data, BaseModel):
            json_body: Optional[Dict[str, Any]] = data.model_dump()
        else:
            json_body = data

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    "Backend request %s %s attempt=%s data=%s params=%s",
                    method,
                    url,
                    attempt,
                    json_body,
                    params,
                )
                response = await self.client.request(
                    method=method,
                    url=url,
                    json=json_body,
                    params=params,
                )

                if response.status_code >= 400:
                    # 4xx / 5xx -> raise BackendAPIError
                    try:
                        error_data: Dict[str, Any] = response.json() if response.content else {}
                    except Exception:
                        error_data = {}

                    message = (
                        error_data.get("message")
                        or response.reason_phrase
                        or "Unknown error"
                    )

                    logger.warning(
                        "Backend error %s %s status=%s body=%s",
                        method,
                        url,
                        response.status_code,
                        error_data,
                    )

                    # Retry only on 5xx
                    if 500 <= response.status_code < 600 and attempt < self.max_retries:
                        last_error = BackendAPIError(
                            status_code=response.status_code,
                            message=message,
                            details=error_data,
                        )
                        continue

                    raise BackendAPIError(
                        status_code=response.status_code,
                        message=message,
                        details=error_data,
                    )

                if not response.content:
                    if response_model is None:
                        return {}
                    try:
                        return response_model.model_validate({})
                    except ValidationError as ve:
                        logger.error(
                            "Response validation failed for %s %s: %s",
                            method,
                            url,
                            ve,
                        )
                        raise BackendAPIError(
                            status_code=500,
                            message="Invalid response format from backend",
                        ) from ve

                # Parse JSON
                try:
                    raw_json: Dict[str, Any] = response.json()
                except Exception as e:
                    logger.error("Failed to parse JSON from backend %s %s: %s", method, url, e)
                    raise BackendAPIError(
                        status_code=500,
                        message="Failed to parse JSON from backend",
                    ) from e

                if response_model is None:
                    return raw_json

                # Validate with Pydantic model
                try:
                    return response_model.model_validate(raw_json)
                except ValidationError as ve:
                    logger.error(
                        "Response validation failed for %s %s: %s",
                        method,
                        url,
                        ve,
                    )
                    raise BackendAPIError(
                        status_code=500,
                        message="Invalid response format from backend",
                        details={"errors": ve.errors(), "raw": raw_json},
                    ) from ve

            except httpx.RequestError as e:
                logger.error(
                    "Backend request error (%s %s) attempt=%s error=%s",
                    method,
                    url,
                    attempt,
                    e,
                )
                last_error = e
                if attempt < self.max_retries:
                    continue
                raise BackendAPIError(
                    status_code=503,
                    message=f"Failed to connect to backend: {str(e)}",
                ) from e

        raise BackendAPIError(
            status_code=503,
            message="Backend request failed after retries",
            details={"last_error": str(last_error) if last_error else None},
        )

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Union[T, Dict[str, Any]]:
        return await self._request(
            "GET",
            endpoint,
            params=params,
            response_model=response_model,
        )

    async def post(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], BaseModel]] = None,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Union[T, Dict[str, Any]]:
        return await self._request(
            "POST",
            endpoint,
            data=data,
            params=params,
            response_model=response_model,
        )

    async def put(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], BaseModel]] = None,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Union[T, Dict[str, Any]]:
        return await self._request(
            "PUT",
            endpoint,
            data=data,
            params=params,
            response_model=response_model,
        )

    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Union[T, Dict[str, Any]]:
        return await self._request(
            "DELETE",
            endpoint,
            params=params,
            response_model=response_model,
        )


@lru_cache
def get_bafoka_client() -> BackendClient:
    """
    Singleton BackendClient instance configured for BAFOKA backend.
    """
    return BackendClient(
        base_url=str(settings.BACKEND_BASE_URL),
        timeout=settings.BACKEND_TIMEOUT,
        api_key=settings.BACKEND_API_KEY,
        max_retries=3,
    )