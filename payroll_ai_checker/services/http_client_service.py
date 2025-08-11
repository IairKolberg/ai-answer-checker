"""HTTP client service for communicating with AI agent endpoints."""

import time
import logging
from typing import Dict, Any, Optional
import httpx

from ..models import AgentConfig, HttpRequest, HttpResponse, HttpMethod


logger = logging.getLogger(__name__)


class HttpClientService:
    """Service for making HTTP requests to AI agent endpoints."""
    
    def __init__(self, agent_config: AgentConfig):
        """Initialize the HTTP client with agent configuration.
        
        Args:
            agent_config: Configuration for the AI agent endpoint
        """
        self.agent_config = agent_config
        self.client = self._create_client()
        
    def _create_client(self) -> httpx.Client:
        """Create a configured httpx client with retry logic."""
        headers = {}
        
        # Set default headers
        if self.agent_config.headers:
            headers.update(self.agent_config.headers)
        
        # Set authentication header if provided
        if self.agent_config.auth_header:
            headers["Authorization"] = self.agent_config.auth_header
        
        # Set cookie header if provided
        if self.agent_config.cookie_header:
            headers["Cookie"] = self.agent_config.cookie_header
        
        # Create client with configuration
        client = httpx.Client(
            headers=headers,
            timeout=self.agent_config.timeout_seconds,
            verify=self.agent_config.verify_ssl
        )
        
        logger.debug(f"Created HTTP client for agent '{self.agent_config.agent_name}'")
        return client
    
    def send_request(self, http_request: HttpRequest) -> HttpResponse:
        """Send an HTTP request and return the response.
        
        Args:
            http_request: HTTP request configuration
            
        Returns:
            HttpResponse containing the response data
            
        Raises:
            httpx.RequestError: If the request fails after all retries
            ValueError: If the request configuration is invalid
        """
        start_time = time.time()
        
        # Implement retry logic manually since httpx doesn't have built-in retries
        last_exception = None
        
        for attempt in range(self.agent_config.max_retries + 1):
            try:
                # Prepare request parameters
                request_kwargs = self._prepare_request_kwargs(http_request)
                
                logger.info(f"Sending {http_request.method} request to {http_request.url} (attempt {attempt + 1})")
                logger.debug(f"Request params: {request_kwargs}")
                
                # Send the request
                response = self.client.request(**request_kwargs)
                
                # Calculate response time
                response_time_ms = (time.time() - start_time) * 1000
                
                # Log the status code and response details for debugging
                logger.info(f"Request completed: {response.status_code} in {response_time_ms:.2f}ms")
                if response.status_code >= 400:
                    logger.warning(f"HTTP error response: {response.text[:200]}...")
                
                # Parse response (don't raise exceptions for 4xx/5xx here - let runner handle it)
                http_response = self._parse_response(response, response_time_ms, http_request.url)
                
                return http_response
                
            except httpx.RequestError as e:
                # Only retry on connection/network errors, not on HTTP status errors
                last_exception = e
                response_time_ms = (time.time() - start_time) * 1000
                
                # Check if we should retry (only for connection errors)
                if attempt < self.agent_config.max_retries:
                    retry_delay = self.agent_config.retry_delay_seconds * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {retry_delay}s: {e}")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Request failed after {attempt + 1} attempts in {response_time_ms:.2f}ms: {e}")
                    
                    # Provide user-friendly error message for connection issues
                    if isinstance(e, httpx.ConnectError) or "Connection refused" in str(e) or "Errno 61" in str(e):
                        friendly_message = (
                            f"❌ Unable to connect to AI agent at {http_request.url}\n"
                            f"   This usually means:\n"
                            f"   • The AI agent service is not running on localhost:9007\n"
                            f"   • The agent endpoint URL is incorrect\n"
                            f"   • There's a network connectivity issue\n"
                            f"\n"
                            f"   💡 To fix this:\n"
                            f"   1. Verify the AI agent is running: curl {http_request.url}\n"
                            f"   2. Check the agent configuration in configs/pay-details-us-agent.yaml\n"
                            f"   3. Ensure the correct port and endpoint path are configured"
                        )
                        raise ConnectionError(friendly_message) from e
                    else:
                        raise
            except Exception as e:
                logger.error(f"Unexpected error during request: {e}")
                raise
    
    def _prepare_request_kwargs(self, http_request: HttpRequest) -> Dict[str, Any]:
        """Prepare keyword arguments for httpx.Client.request()."""
        kwargs = {
            "method": http_request.method.value,
            "url": http_request.url,
        }
        
        # Set timeout if specified
        if http_request.timeout_seconds:
            kwargs["timeout"] = http_request.timeout_seconds
        
        # Add headers if provided
        if http_request.headers:
            kwargs["headers"] = http_request.headers
        
        # Add request body based on content type
        if http_request.json_data:
            kwargs["json"] = http_request.json_data
        elif http_request.form_data:
            kwargs["data"] = http_request.form_data
        
        # Add query parameters
        if http_request.query_params:
            kwargs["params"] = http_request.query_params
        
        return kwargs
    
    def _parse_response(self, response: httpx.Response, response_time_ms: float, url: str) -> HttpResponse:
        """Parse httpx.Response into HttpResponse model."""
        # Try to parse JSON response
        json_data = None
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                json_data = response.json()
        except Exception:
            logger.debug("Response is not valid JSON or not JSON content-type")
        
        # Convert headers to dict
        headers = dict(response.headers)
        
        return HttpResponse(
            status_code=response.status_code,
            headers=headers,
            text=response.text,
            json_data=json_data,
            response_time_ms=response_time_ms,
            url=url
        )
    
    def send_agent_request(self, url_path: str, json_data: Dict[str, Any], 
                          method: HttpMethod = HttpMethod.POST) -> HttpResponse:
        """Send a request to the AI agent endpoint.
        
        This is a convenience method that constructs the full URL and sends a request.
        
        Args:
            url_path: Path to append to the base URL (e.g., "/query", "/status")
            json_data: JSON payload to send
            method: HTTP method to use
            
        Returns:
            HttpResponse from the agent
        """
        # Construct full URL
        base_url = str(self.agent_config.base_url).rstrip('/')
        full_url = f"{base_url}{url_path}"
        
        # Create HTTP request
        http_request = HttpRequest(
            method=method,
            url=full_url,
            json_data=json_data
        )
        
        return self.send_request(http_request)
    
    def test_connection(self) -> bool:
        """Test connection to the agent endpoint.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to send a simple GET request to the base URL
            response = self.send_agent_request("/health", {}, HttpMethod.GET)
            return response.status_code < 400
        except Exception as e:
            logger.warning(f"Connection test failed for agent '{self.agent_config.agent_name}': {e}")
            return False
    
    def close(self):
        """Close the HTTP client and clean up resources."""
        if self.client:
            self.client.close()
            logger.debug(f"Closed HTTP client for agent '{self.agent_config.agent_name}'")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()