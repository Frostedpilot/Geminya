"""Manager for multiple MCP clients with improved architecture and monitoring."""

import asyncio
import json
import logging
import re
import time
from typing import Dict, List, Optional, Any

from openai import AsyncOpenAI

from config import Config
from services.state_manager import StateManager
from .client import MCPClient
from .registry import MCPServerRegistry
from .types import (
    ServerInfo,
    ToolCall,
    ToolResult,
    MCPResponse,
    ServerStatus,
    ServerConfig,
)
from .exceptions import MCPError, MCPToolError, MCPServerError


class MCPClientManager:
    """Enhanced manager for multiple MCP clients with improved monitoring and error handling."""

    def __init__(
        self, config: Config, state_manager: StateManager, logger: logging.Logger
    ):
        self.config = config
        self.state_manager = state_manager
        self.logger = logger

        # Client management
        self.clients: Dict[str, MCPClient] = {}
        self.registry = MCPServerRegistry(logger)

        # OpenAI client for tool processing
        self.openai = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.openrouter_api_key,
        )

        # Load server configurations
        self._load_server_configs()

        # Performance monitoring
        self._total_queries = 0
        self._total_tool_calls = 0
        self._total_execution_time = 0.0

    def _load_server_configs(self) -> None:
        """Load server configurations from config into registry."""
        try:
            self.registry.load_from_dict(self.config.mcp_server_instruction)
            self.logger.info(
                f"Loaded {len(self.registry.list_servers())} MCP server configurations"
            )

            # Validate configurations
            errors = self.registry.validate_all()
            if errors:
                self.logger.error(f"Configuration validation errors: {errors}")

        except Exception as e:
            self.logger.error(f"Failed to load server configurations: {e}")

    async def get_or_create_client(self, server_name: str) -> MCPClient:
        """Get existing client or create new one for the server.

        Args:
            server_name: Name of the server

        Returns:
            MCP client instance

        Raises:
            MCPError: If server configuration not found or client creation fails
        """
        if server_name in self.clients and self.clients[server_name].is_connected:
            return self.clients[server_name]

        config = self.registry.get_server_config(server_name)
        if not config:
            raise MCPError(f"No configuration found for server: {server_name}")

        # Create new client if doesn't exist
        if server_name not in self.clients:
            client = MCPClient(config, self.logger)
            self.clients[server_name] = client
        else:
            client = self.clients[server_name]

        # Connect if not connected
        if not client.is_connected:
            await client.connect()

        return client

    async def ensure_all_servers_connected(self) -> None:
        """Ensure all configured servers are connected."""
        connection_tasks = []

        for server_name in self.registry.list_servers():
            task = asyncio.create_task(self._safe_connect_server(server_name))
            connection_tasks.append(task)

        if connection_tasks:
            await asyncio.gather(*connection_tasks, return_exceptions=True)

    async def _safe_connect_server(self, server_name: str) -> None:
        """Safely connect to a server with error handling."""
        try:
            await self.get_or_create_client(server_name)
        except Exception as e:
            self.logger.warning(f"Failed to connect to {server_name}: {e}")

    async def get_all_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from all connected servers with server prefixes.

        Returns:
            List of all available tools with server prefixes
        """
        all_tools = []

        for server_name, client in self.clients.items():
            if client.is_connected:
                try:
                    tools = await client.get_available_tools()
                    processed_tools = self._process_server_tools(tools, server_name)
                    all_tools.extend(processed_tools)
                except Exception as e:
                    self.logger.error(f"Error getting tools from {server_name}: {e}")

        self.logger.debug(
            f"Retrieved {len(all_tools)} tools from {len(self.clients)} servers"
        )
        return all_tools

    def _process_server_tools(
        self, tools: List[Dict[str, Any]], server_name: str
    ) -> List[Dict[str, Any]]:
        """Process tools from a server, adding prefixes and metadata.

        Args:
            tools: List of tools from the server
            server_name: Name of the server

        Returns:
            List of processed tools with server prefixes
        """
        processed_tools = []

        for tool in tools:
            # Create a deep copy to avoid modifying the original cached tool
            tool_copy = self._create_tool_copy(tool)

            # Store original name and apply server prefix
            original_name = tool_copy["function"]["name"]

            # Check if prefix is already applied to avoid duplication
            if not original_name.startswith(f"{server_name}__"):
                tool_copy["function"]["name"] = f"{server_name}__{original_name}"
            else:
                # If prefix already exists, use the tool as-is but log a warning
                self.logger.warning(
                    f"Tool {original_name} already has server prefix, using as-is"
                )

            tool_copy["_original_name"] = original_name
            tool_copy["_server_name"] = server_name
            processed_tools.append(tool_copy)

        return processed_tools

    def _create_tool_copy(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep copy of a tool to avoid modifying cached versions.

        Args:
            tool: Original tool dictionary

        Returns:
            Deep copy of the tool
        """
        return {
            "type": tool["type"],
            "function": {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "parameters": (
                    tool["function"]["parameters"].copy()
                    if "parameters" in tool["function"]
                    else {}
                ),
            },
        }

    async def process_query(self, prompt: str, server_id: str) -> MCPResponse:
        """Process a query using all available MCP servers automatically.

        Args:
            prompt: User query to process
            server_id: Server ID for model selection

        Returns:
            MCP response with processing details
        """
        start_time = time.time()
        self._total_queries += 1

        try:
            # Connect to all configured servers
            await self.ensure_all_servers_connected()

            # Get all tools from all servers
            all_tools = await self.get_all_available_tools()

            if not all_tools:
                return MCPResponse(
                    content="No MCP tools are currently available.",
                    tool_calls_made=0,
                    iterations=0,
                    execution_time=time.time() - start_time,
                    servers_used=[],
                    success=False,
                    error="No tools available",
                )

            return await self._process_with_all_tools(
                all_tools, prompt, server_id, start_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error processing query with MCP: {e}"
            self.logger.error(error_msg)

            return MCPResponse(
                content=f"Error: Failed to process query: {str(e)}",
                tool_calls_made=0,
                iterations=0,
                execution_time=execution_time,
                servers_used=[],
                success=False,
                error=str(e),
            )

    async def _process_with_all_tools(
        self,
        all_tools: List[Dict[str, Any]],
        prompt: str,
        server_id: str,
        start_time: float,
    ) -> MCPResponse:
        """Process query with tools from all servers, supporting iterative tool calls.

        Args:
            all_tools: List of all available tools
            prompt: User query
            server_id: Server ID for model selection
            start_time: Query start time

        Returns:
            MCP response with processing results
        """
        messages = [{"role": "user", "content": prompt}]
        final_text = []
        iteration_count = 0
        total_tool_calls = 0
        servers_used = set()

        while iteration_count < self.config.max_tool_iterations:
            iteration_count += 1
            self.logger.debug(
                f"Starting tool iteration {iteration_count}/{self.config.max_tool_iterations}"
            )

            # Get AI response
            response = await self._get_ai_response(messages, all_tools, server_id)
            if not response:
                return self._create_error_response(
                    "Empty response from AI",
                    total_tool_calls,
                    iteration_count,
                    start_time,
                    servers_used,
                )

            content = response.choices[0].message

            self.logger.debug(
                f"Received response from AI:\n{content.content}\nwith {len(content.tool_calls or [])} tool calls"
            )

            # Handle tool calls
            tool_processing_result = await self._process_iteration_tools(
                content,
                messages,
                total_tool_calls,
                servers_used,
                iteration_count,
                server_id,
            )

            if tool_processing_result.get("final_text"):
                final_text.append(tool_processing_result["final_text"])
                break
            elif tool_processing_result.get("continue"):
                total_tool_calls = tool_processing_result["total_tool_calls"]
            else:
                # No tool calls - final response
                final_text.append(content.content)
                break

        return self._create_success_response(
            final_text, total_tool_calls, iteration_count, start_time, servers_used
        )

    async def _get_ai_response(
        self,
        messages: List[Dict[str, Any]],
        all_tools: List[Dict[str, Any]],
        server_id: str,
    ):
        """Get AI response with tools."""
        return await self.openai.chat.completions.create(
            model=self.state_manager.get_model(server_id=server_id),
            messages=messages,
            tools=all_tools,
            parallel_tool_calls=True,
        )

    async def _process_iteration_tools(
        self,
        content,
        messages: List[Dict[str, Any]],
        total_tool_calls: int,
        servers_used: set,
        iteration_count: int,
        server_id: str,
    ) -> Dict[str, Any]:
        """Process tools for a single iteration."""
        # Handle DeepSeek tool call format if present
        additional_tools = (
            self._extract_deepseek_tool_calls(content.content)
            if content.content
            else []
        )

        # Add assistant message to conversation
        messages.append(
            {
                "role": "assistant",
                "content": content.content,
                "tool_calls": content.tool_calls,
            }
        )

        # Process tool calls if any
        if content.tool_calls or additional_tools:
            tool_calls_this_iteration = len(content.tool_calls or []) + len(
                additional_tools
            )
            total_tool_calls += tool_calls_this_iteration

            self.logger.debug(
                f"Processing {tool_calls_this_iteration} tool calls in iteration {iteration_count}"
            )

            # Execute tool calls
            tool_results = await self._execute_tool_calls(
                content.tool_calls or [], additional_tools
            )

            # Track servers used
            for result in tool_results:
                if hasattr(result, "server_name") and result.server_name:
                    servers_used.add(result.server_name)

            # Add tool results to messages
            for result in tool_results:
                messages.append(result.to_message_dict())

            # Check if we've reached max iterations
            if iteration_count >= self.config.max_tool_iterations:
                self.logger.warning(
                    f"Reached maximum tool iterations ({self.config.max_tool_iterations})"
                )

                # Get final response without tools
                final_response = await self.openai.chat.completions.create(
                    model=self.state_manager.get_model(server_id=server_id),
                    messages=messages
                    + [
                        {
                            "role": "user",
                            "content": "Please provide a final response based on the information gathered.",
                        }
                    ],
                )
                return {"final_text": final_response.choices[0].message.content}

            return {"continue": True, "total_tool_calls": total_tool_calls}

        return {"no_tools": True}

    def _create_error_response(
        self,
        error: str,
        total_tool_calls: int,
        iteration_count: int,
        start_time: float,
        servers_used: set,
    ) -> MCPResponse:
        """Create an error response."""
        return MCPResponse(
            content=f"Error: {error}",
            tool_calls_made=total_tool_calls,
            iterations=iteration_count,
            execution_time=time.time() - start_time,
            servers_used=list(servers_used),
            success=False,
            error=error,
        )

    def _create_success_response(
        self,
        final_text: List[str],
        total_tool_calls: int,
        iteration_count: int,
        start_time: float,
        servers_used: set,
    ) -> MCPResponse:
        """Create a success response."""
        if not final_text:
            final_text.append(
                "I've completed the analysis but encountered an issue generating the final response."
            )

        execution_time = time.time() - start_time
        self._total_execution_time += execution_time
        self._total_tool_calls += total_tool_calls

        result_content = "\n".join(final_text)

        self.logger.info(
            f"Completed MCP processing in {iteration_count} iterations, "
            f"{total_tool_calls} tool calls, {execution_time:.2f}s"
        )

        return MCPResponse(
            content=result_content,
            tool_calls_made=total_tool_calls,
            iterations=iteration_count,
            execution_time=execution_time,
            servers_used=list(servers_used),
            success=True,
        )

    async def _execute_tool_calls(
        self, tool_calls: List[Any], additional_tools: List[Dict[str, Any]]
    ) -> List[ToolResult]:
        """Execute a list of tool calls and return their results.

        Args:
            tool_calls: OpenAI format tool calls
            additional_tools: Additional tool calls from DeepSeek format

        Returns:
            List of tool execution results
        """
        tool_results = []

        # Process OpenAI format tool calls
        for tool_call in tool_calls:
            result = await self._execute_single_tool_call(tool_call)
            tool_results.append(result)

        # Process additional tools from DeepSeek format
        for tool_call in additional_tools:
            result = await self._execute_deepseek_tool_call(tool_call)
            tool_results.append(result)

        return tool_results

    async def _execute_single_tool_call(self, tool_call) -> ToolResult:
        """Execute a single OpenAI format tool call.

        Args:
            tool_call: OpenAI tool call object

        Returns:
            Tool execution result
        """
        tool_name = tool_call.function.name
        tool_args = tool_call.function.arguments

        self.logger.debug(f"Executing tool call: {tool_name} with args: {tool_args}")

        # Parse arguments if they're a string
        if isinstance(tool_args, str):
            try:
                tool_args = json.loads(tool_args)
            except json.JSONDecodeError:
                tool_args = {}
        elif not isinstance(tool_args, dict):
            tool_args = {}

        # Parse server name and original tool name
        server_name, original_tool_name = await self._parse_tool_name(tool_name)

        self.logger.debug(f"Calling tool {original_tool_name} on {server_name}")

        try:
            client = self.clients.get(server_name)
            if not client or not client.is_connected:
                raise MCPServerError(f"Server {server_name} not available", server_name)

            result = await client.call_tool(original_tool_name, tool_args)
            result.tool_call_id = tool_call.id

            self.logger.debug(
                f"Tool {original_tool_name} executed successfully on {server_name}"
            )
            self.logger.debug(
                f"Tool result:\n{result.content}\n(success: {result.success})"
            )

            return result

        except Exception as e:
            self.logger.error(
                f"Error calling tool {original_tool_name} on {server_name}: {e}"
            )

            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_name,
                content=f"Error calling tool {original_tool_name}: {e}",
                success=False,
                error=str(e),
            )

    async def _execute_deepseek_tool_call(
        self, tool_call: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool call from DeepSeek format.

        Args:
            tool_call: DeepSeek format tool call

        Returns:
            Tool execution result
        """
        tool_name = tool_call["function"]["name"]
        tool_args = tool_call["function"]["arguments"]

        # Parse server name and original tool name
        server_name, original_tool_name = await self._parse_tool_name(tool_name)

        self.logger.debug(
            f"Calling DeepSeek tool {original_tool_name} on {server_name}"
        )

        try:
            client = self.clients.get(server_name)
            if not client or not client.is_connected:
                raise MCPServerError(f"Server {server_name} not available", server_name)

            result = await client.call_tool(original_tool_name, tool_args)
            result.tool_call_id = tool_call.get("id", f"deepseek_tool_{id(tool_call)}")

            return result

        except Exception as e:
            self.logger.error(
                f"Error calling DeepSeek tool {original_tool_name} on {server_name}: {e}"
            )

            return ToolResult(
                tool_call_id=tool_call.get("id", f"deepseek_tool_{id(tool_call)}"),
                name=tool_name,
                content=f"Error calling tool {original_tool_name}: {e}",
                success=False,
                error=str(e),
            )

    async def _find_tool_server(self, tool_name: str) -> tuple[str, str]:
        """Find which server has the specified tool.

        Args:
            tool_name: Name of the tool to find

        Returns:
            Tuple of (server_name, tool_name)

        Raises:
            MCPToolError: If tool not found on any server
        """
        for server_name, client in self.clients.items():
            if client.is_connected:
                try:
                    tools = await client.get_available_tools()
                    for tool in tools:
                        if tool["function"]["name"] == tool_name:
                            return server_name, tool_name
                except Exception:
                    continue

        # If not found, return the first available server as fallback
        available_servers = [
            name for name, client in self.clients.items() if client.is_connected
        ]
        if available_servers:
            return available_servers[0], tool_name

        raise MCPToolError(f"No server found for tool: {tool_name}")

    def _extract_deepseek_tool_calls(
        self, content: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Extract tool calls from DeepSeek format in content.

        Args:
            content: Message content that may contain DeepSeek tool calls

        Returns:
            List of extracted tool calls
        """
        if not content or "<｜tool▁call▁begin｜>function<｜tool▁sep｜>" not in content:
            return []

        self.logger.debug("Extracting DeepSeek tool calls from content")
        patched_tools = []

        # Pattern to match DeepSeek tool calls
        pattern = re.compile(
            r"\n<｜tool▁call▁begin｜>function<｜tool▁sep｜>([^}]*?)\njson\n({[^}]*})\n",
            re.DOTALL,
        )

        matches = pattern.findall(content)
        if not matches:
            return []

        self.logger.debug(f"Found {len(matches)} DeepSeek tool calls")

        for match in matches:
            func_name, args_json = match
            try:
                args = json.loads(args_json)
                patched_tools.append(
                    {
                        "function": {
                            "name": func_name,
                            "arguments": args,
                        }
                    }
                )
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse DeepSeek tool args: {e}")
                continue

        return patched_tools

    async def disconnect_all(self) -> None:
        """Disconnect all clients and cleanup resources."""
        disconnect_tasks = []

        for client in self.clients.values():
            task = asyncio.create_task(client.disconnect())
            disconnect_tasks.append(task)

        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)

        self.clients.clear()
        self.logger.info("All MCP clients disconnected")

    async def _parse_tool_name(self, tool_name: str) -> tuple[str, str]:
        """Parse a tool name to extract server name and original tool name.

        Handles both single and double server prefixes to fix duplication issues.

        Args:
            tool_name: The full tool name (potentially with server prefix)

        Returns:
            Tuple of (server_name, original_tool_name)
        """
        if "__" not in tool_name:
            # No prefix, try to find the tool in any server
            return await self._find_tool_server(tool_name)

        # Split on first occurrence of __
        parts = tool_name.split("__", 1)
        server_name = parts[0]
        remaining_name = parts[1]

        # Check if the remaining name also has the server prefix (double prefix case)
        if remaining_name.startswith(f"{server_name}__"):
            # Remove the duplicate prefix
            original_tool_name = remaining_name[len(f"{server_name}__") :]
            self.logger.warning(
                f"Detected double prefix in tool name {tool_name}, using original name: {original_tool_name}"
            )
        else:
            original_tool_name = remaining_name

        return server_name, original_tool_name

    def list_connected_servers(self) -> List[str]:
        """Get list of connected server names.

        Returns:
            List of connected server names
        """
        return [name for name, client in self.clients.items() if client.is_connected]

    def get_server_info(self) -> List[ServerInfo]:
        """Get information about all servers.

        Returns:
            List of server information
        """
        info_list = []

        for server_name in self.registry.list_servers():
            if server_name in self.clients:
                info_list.append(self.clients[server_name].get_info())
            else:
                # Server not connected
                config = self.registry.get_server_config(server_name)
                info_list.append(
                    ServerInfo(
                        name=server_name,
                        status=ServerStatus.DISCONNECTED,
                        tool_count=0,
                        blacklisted_tools=config.blacklist.copy() if config else [],
                    )
                )

        return info_list

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics.

        Returns:
            Dictionary of performance statistics
        """
        return {
            "total_queries": self._total_queries,
            "total_tool_calls": self._total_tool_calls,
            "total_execution_time": self._total_execution_time,
            "average_execution_time": (
                self._total_execution_time / self._total_queries
                if self._total_queries > 0
                else 0
            ),
            "average_tool_calls_per_query": (
                self._total_tool_calls / self._total_queries
                if self._total_queries > 0
                else 0
            ),
            "connected_servers": len(self.list_connected_servers()),
            "total_configured_servers": len(self.registry.list_servers()),
        }

    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health checks on all connected servers.

        Returns:
            Dictionary mapping server names to health status
        """
        health_results = {}

        for server_name, client in self.clients.items():
            if client.is_connected:
                health_results[server_name] = await client.health_check()
            else:
                health_results[server_name] = False

        return health_results
