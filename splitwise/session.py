"""Async HTTP session management for Splitwise API.

This module provides efficient aiohttp session management with:
- Connection pooling for low-compute/edge devices
- Automatic retry with exponential backoff
- Timeout configurations
- Memory-efficient resource handling
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from splitwise.base import (
    DEFAULT_TIMEOUT,
    DEFAULT_POOL_SIZE,
    DEFAULT_POOL_TIMEOUT
)
from splitwise.exception import (
    SplitwiseException,
    SplitwiseUnauthorizedException,
    SplitwiseBadRequestException,
    SplitwiseNotAllowedException,
    SplitwiseNotFoundException
)


class AsyncSessionManager:
    """Manages aiohttp sessions with connection pooling and resource optimization.
    
    Designed for edge/low-compute devices with configurable:
    - Connection pool limits
    - Request timeouts
    - Retry policies
    
    Attributes:
        pool_size: Maximum number of concurrent connections
        timeout: Request timeout in seconds
        retry_attempts: Number of retry attempts for failed requests
        retry_delay: Base delay between retries (exponential backoff)
    """
    
    def __init__(
        self,
        pool_size: int = DEFAULT_POOL_SIZE,
        timeout: float = DEFAULT_TIMEOUT,
        pool_timeout: float = DEFAULT_POOL_TIMEOUT,
        retry_attempts: int = 3,
        retry_delay: float = 1.0
    ):
        """Initialize the session manager.
        
        Args:
            pool_size: Maximum concurrent connections (default: 10)
            timeout: Request timeout in seconds (default: 30)
            pool_timeout: Connection pool timeout (default: 60)
            retry_attempts: Number of retries for failed requests (default: 3)
            retry_delay: Base delay for exponential backoff (default: 1.0)
        """
        self.pool_size = pool_size
        self.timeout = timeout
        self.pool_timeout = pool_timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
    
    def _create_connector(self) -> aiohttp.TCPConnector:
        """Create a TCP connector with connection pooling.
        
        Returns:
            Configured TCPConnector for connection reuse
        """
        return aiohttp.TCPConnector(
            limit=self.pool_size,
            limit_per_host=self.pool_size,
            ttl_dns_cache=300,  # Cache DNS for 5 minutes
            enable_cleanup_closed=True,
            force_close=False,  # Reuse connections
        )
    
    def _create_timeout(self) -> aiohttp.ClientTimeout:
        """Create timeout configuration.
        
        Returns:
            ClientTimeout with configured values
        """
        return aiohttp.ClientTimeout(
            total=self.timeout,
            connect=10,
            sock_read=self.timeout,
            sock_connect=10
        )
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session.
        
        Returns:
            Reusable ClientSession with connection pooling
        """
        if self._session is None or self._session.closed:
            self._connector = self._create_connector()
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=self._create_timeout(),
                raise_for_status=False  # We handle status codes manually
            )
        return self._session
    
    async def close(self) -> None:
        """Close the session and release resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        if self._connector and not self._connector.closed:
            await self._connector.close()
            self._connector = None
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> str:
        """Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Optional request headers
            data: Optional form data
            params: Optional query parameters
            files: Optional file uploads
            
        Returns:
            Response content as string
            
        Raises:
            SplitwiseException: On API errors
        """
        session = await self.get_session()
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                # Handle file uploads
                if files:
                    form_data = aiohttp.FormData()
                    if data:
                        for key, value in data.items():
                            if value is not None:
                                form_data.add_field(key, str(value))
                    for name, file_obj in files.items():
                        form_data.add_field(name, file_obj)
                    request_data = form_data
                else:
                    request_data = data
                
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=request_data,
                    params=params
                ) as response:
                    content = await response.text()
                    return self._handle_response(response.status, content, response)
                    
            except aiohttp.ClientError as e:
                last_exception = e
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                continue
            except asyncio.TimeoutError as e:
                last_exception = e
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                continue
        
        raise SplitwiseException(f"Request failed after {self.retry_attempts} attempts: {last_exception}")
    
    def _handle_response(self, status_code: int, content: str, response: aiohttp.ClientResponse) -> str:
        """Handle HTTP response status codes.
        
        Args:
            status_code: HTTP status code
            content: Response content
            response: Full response object
            
        Returns:
            Response content on success
            
        Raises:
            SplitwiseException: On error status codes
        """
        if status_code == 200:
            return content
        
        if status_code == 401:
            raise SplitwiseUnauthorizedException(
                "Please check your token or consumer id and secret",
                response=response
            )
        
        if status_code == 403:
            raise SplitwiseNotAllowedException(
                "You are not allowed to perform this operation",
                response=response
            )
        
        if status_code == 400:
            raise SplitwiseBadRequestException(
                "Please check your request",
                response=response
            )
        
        if status_code == 404:
            raise SplitwiseNotFoundException(
                "Required resource is not found",
                response=response
            )
        
        raise SplitwiseException(f"Unknown error: {status_code}", response=response)
    
    async def __aenter__(self) -> 'AsyncSessionManager':
        """Async context manager entry."""
        await self.get_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


@asynccontextmanager
async def create_session(
    pool_size: int = DEFAULT_POOL_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
    **kwargs
):
    """Create a managed async session.
    
    Usage:
        async with create_session() as session_manager:
            content = await session_manager.request("GET", url)
    
    Args:
        pool_size: Maximum concurrent connections
        timeout: Request timeout
        **kwargs: Additional session manager options
        
    Yields:
        AsyncSessionManager instance
    """
    manager = AsyncSessionManager(pool_size=pool_size, timeout=timeout, **kwargs)
    try:
        yield manager
    finally:
        await manager.close()
