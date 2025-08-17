"""Individual MCP client for connecting to and managing a single server."""

import asyncio
import json
import logging
import time
from contextlib import AsyncExitStack
from typing import Dict, List, Optional, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool

from .types import ServerConfig, ServerStatus, ToolResult, ServerInfo
from .exceptions import MCPConnectionError, MCPToolError, MCPServerError
from utils.utils import convert_tool_format


class MCPClient:
    """Individual MCP client for a single server with enhanced error handling and monitoring."""

    def __init__(self, config: ServerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        # Connection state
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.status = ServerStatus.DISCONNECTED

        # Monitoring
        self.connection_time: Optional[float] = None
        self.last_error: Optional[str] = None
        self.retry_count = 0

        # Tools cache
        self._tools_cache: List[Tool] = []
        self._tools_cache_time: Optional[float] = None
        self._tools_cache_ttl = 600  # 10 minutes

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to server."""
        return self.status == ServerStatus.CONNECTED and self.session is not None

    @property
    def uptime(self) -> Optional[float]:
        """Get uptime in seconds since connection."""
        if self.connection_time and self.is_connected:
            return time.time() - self.connection_time
        return None

    async def connect(self) -> None:
        """Connect to the MCP server with retry logic.

        Raises:
            MCPConnectionError: If connection fails after all retries
        """
        if self.is_connected:
            self.logger.debug(f"Already connected to {self.config.name}")
            return

        self.status = ServerStatus.CONNECTING
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                await self._attempt_connection()
                self.status = ServerStatus.CONNECTED
                self.connection_time = time.time()
                self.last_error = None
                self.retry_count = 0
                self.logger.info(f"Successfully connected to {self.config.name}")
                return

            except Exception as e:
                last_exception = e
                self.retry_count += 1
                self.last_error = str(e)

                if attempt < self.config.max_retries:
                    self.logger.warning(
                        f"Connection attempt {attempt + 1} failed for {self.config.name}: {e}. "
                        f"Retrying in {self.config.retry_delay} seconds..."
                    )
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    self.logger.error(
                        f"All connection attempts failed for {self.config.name}"
                    )

        self.status = ServerStatus.ERROR
        raise MCPConnectionError(
            f"Failed to connect to {self.config.name} after {self.config.max_retries + 1} attempts: {last_exception}",
            self.config.name,
        )

    async def _attempt_connection(self) -> None:
        """Attempt a single connection to the server."""
        try:
            server_params = StdioServerParameters(
                command=self.config.command, args=self.config.args, env=self.config.env
            )
            
            # Create connection
            stdio_transport = await asyncio.wait_for(
                self.exit_stack.enter_async_context(stdio_client(server_params)),
                timeout=self.config.timeout,
            )

            stdio, write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )

            # Initialize session
            await asyncio.wait_for(
                self.session.initialize(), timeout=self.config.timeout
            )

            # Verify connection by listing tools
            tools_response = await self.session.list_tools()
            tool_names = [tool.name for tool in tools_response.tools]

            self.logger.info(
                f"Connected to {self.config.name} with {len(tool_names)} tools: {tool_names}"
            )

        except asyncio.TimeoutError:
            raise MCPConnectionError(f"Connection to {self.config.name} timed out")
        except Exception as e:
            raise MCPConnectionError(f"Failed to connect to {self.config.name}: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the server and cleanup resources."""
        if self.status != ServerStatus.DISCONNECTED:
            try:
                await self.exit_stack.aclose()
                self.status = ServerStatus.DISCONNECTED
                self.session = None
                self.connection_time = None
                self._clear_tools_cache()
                self.logger.info(f"Disconnected from {self.config.name}")
            except Exception as e:
                self.logger.error(
                    f"Error during disconnect from {self.config.name}: {e}"
                )

    async def get_available_tools(self, use_cache: bool = True) -> List[Tool]:
        """Get list of available tools from server, filtered by blacklist.

        Args:
            use_cache: Whether to use cached tools if available

        Returns:
            List of tool definitions in OpenAI format

        Raises:
            MCPServerError: If server is not connected or tool listing fails
        """
        if not self.is_connected:
            raise MCPServerError(
                f"Not connected to {self.config.name}", self.config.name
            )

        # Check cache
        if use_cache and self._is_tools_cache_valid():
            self.logger.debug(f"Using cached tools for {self.config.name}")
            return self._tools_cache.copy()

        try:
            response = await self.session.list_tools()
            filtered_tools = []

            for tool in response.tools:
                if tool.name not in self.config.blacklist:
                    filtered_tools.append(tool)
                else:
                    self.logger.debug(
                        f"Blacklisted tool '{tool.name}' filtered out from {self.config.name}"
                    )

            # Update cache
            self._tools_cache = filtered_tools
            self._tools_cache_time = time.time()

            self.logger.debug(
                f"Retrieved {len(filtered_tools)} tools from {self.config.name} "
                f"(filtered out {len(response.tools) - len(filtered_tools)} blacklisted tools)"
            )

            return filtered_tools.copy()

        except Exception as e:
            self.logger.error(f"Error getting tools from {self.config.name}: {e}")
            raise MCPServerError(
                f"Failed to get tools from {self.config.name}: {e}", self.config.name
            )

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Call a specific tool on this server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPServerError: If server is not connected
            MCPToolError: If tool execution fails
        """
        if not self.is_connected:
            raise MCPServerError(
                f"Not connected to {self.config.name}", self.config.name
            )

        if tool_name in self.config.blacklist:
            raise MCPToolError(
                f"Tool {tool_name} is blacklisted on {self.config.name}",
                tool_name,
                self.config.name,
            )

        start_time = time.time()

        try:
            result = await self.session.call_tool(tool_name, arguments)
            execution_time = time.time() - start_time

            # Extract content from result
            content = self._extract_content_from_result(result)

            self.logger.debug(
                f"Tool {tool_name} on {self.config.name} completed in {execution_time:.2f}s"
            )

            return ToolResult(
                tool_call_id="",  # Will be set by caller
                name=tool_name,
                content=content,
                success=True,
                execution_time=execution_time,
                server_name=self.config.name,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error calling tool {tool_name} on {self.config.name}: {e}"
            self.logger.error(error_msg)

            return ToolResult(
                tool_call_id="",  # Will be set by caller
                name=tool_name,
                content=f"Error: {e}",
                success=False,
                error=str(e),
                execution_time=execution_time,
                server_name=self.config.name,
            )

    def _extract_content_from_result(self, result) -> str:
        """Extract content string from MCP tool result."""
        if result is not None:
            if hasattr(result, "content") and result.content:
                return str(result.content)
            elif hasattr(result, "text"):
                return str(result.text)
            else:
                return str(result)
        return "No content returned"

    def _is_tools_cache_valid(self) -> bool:
        """Check if tools cache is still valid."""
        if not self._tools_cache or self._tools_cache_time is None:
            return False
        return time.time() - self._tools_cache_time < self._tools_cache_ttl

    def _clear_tools_cache(self) -> None:
        """Clear the tools cache."""
        self._tools_cache = []
        self._tools_cache_time = None

    def get_info(self) -> ServerInfo:
        """Get information about this server.

        Returns:
            Server information
        """
        return ServerInfo(
            name=self.config.name,
            status=self.status,
            tool_count=len(self._tools_cache) if self._tools_cache else 0,
            blacklisted_tools=self.config.blacklist.copy(),
            last_error=self.last_error,
            connection_time=self.connection_time,
            uptime=self.uptime,
        )

    async def health_check(self) -> bool:
        """Perform a health check on the server.

        Returns:
            True if server is healthy, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            # Try to list tools as a health check
            await self.get_available_tools(use_cache=False)
            return True
        except Exception as e:
            self.logger.warning(f"Health check failed for {self.config.name}: {e}")
            return False
