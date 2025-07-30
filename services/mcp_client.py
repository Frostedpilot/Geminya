import asyncio
import re
import json
import logging
from typing import Optional, List, Dict
from contextlib import AsyncExitStack
from openai import AsyncOpenAI

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config import Config
from services.state_manager import StateManager
from utils.utils import convert_tool_format


# Constants
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
ERROR_OCCURRED_MSG = "Error occurred"


class MCPClient:
    """Individual MCP client for a single server."""

    def __init__(
        self,
        server_name: str,
        config: Config,
        state_manager: StateManager,
        logger: logging.Logger,
    ):
        self.server_name = server_name
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.config = config
        self.state_manager = state_manager
        self.logger = logger
        self.openai = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=self.config.openrouter_api_key,
        )
        self.is_connected = False

    async def connect_to_server(self, instruction: dict):
        """Connect to the MCP server

        Args:
            instruction: Server configuration dict with command, args, env
        """
        if self.is_connected:
            self.logger.debug(f"Already connected to {self.server_name}")
            return

        command = instruction.get("command")
        args = instruction.get("args", [])
        env = instruction.get("env", None)

        if env:
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env,
            )
        else:
            server_params = StdioServerParameters(
                command=command,
                args=args,
            )

        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            await self.session.initialize()
            self.is_connected = True

            # List available tools
            response = await self.session.list_tools()
            tools = response.tools
            self.logger.info(
                f"Connected to {self.server_name} with tools: {[tool.name for tool in tools]}"
            )

        except Exception as e:
            self.logger.error(f"Failed to connect to {self.server_name}: {e}")
            self.is_connected = False
            raise

    async def get_available_tools(self) -> List[dict]:
        """Get list of available tools from this server, filtered by blacklist."""
        if not self.is_connected or not self.session:
            raise RuntimeError(f"Not connected to {self.server_name}")

        try:
            response = await self.session.list_tools()

            # Get blacklist for this server from config
            server_instruction = self.config.mcp_server_instruction.get(
                self.server_name, {}
            )
            blacklist = server_instruction.get("blacklist", [])

            # Filter out blacklisted tools
            filtered_tools = []
            for tool in response.tools:
                if tool.name not in blacklist:
                    converted_tool = convert_tool_format(tool)
                    filtered_tools.append(converted_tool)
                else:
                    self.logger.debug(
                        f"Blacklisted tool '{tool.name}' filtered out from {self.server_name}"
                    )

            self.logger.debug(
                f"Successfully converted {len(filtered_tools)} tools from {self.server_name} "
                f"(filtered out {len(response.tools) - len(filtered_tools)} blacklisted tools)"
            )
            return filtered_tools
        except Exception as e:
            self.logger.error(f"Error converting tools from {self.server_name}: {e}")
            raise

    async def call_tool(self, tool_name: str, tool_args: dict):
        """Call a specific tool on this server."""
        if not self.is_connected or not self.session:
            raise RuntimeError(f"Not connected to {self.server_name}")

        return await self.session.call_tool(tool_name, tool_args)

    async def disconnect(self):
        """Disconnect from the server and cleanup resources."""
        if self.is_connected:
            await self.exit_stack.aclose()
            self.is_connected = False
            self.session = None
            self.logger.info(f"Disconnected from {self.server_name}")

    def get_blacklisted_tools(self) -> List[str]:
        """Get list of blacklisted tools for this server."""
        server_instruction = self.config.mcp_server_instruction.get(
            self.server_name, {}
        )
        return server_instruction.get("blacklist", [])


class MCPClientManager:
    """Manager for multiple MCP clients."""

    def __init__(
        self, config: Config, state_manager: StateManager, logger: logging.Logger
    ):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.config = config
        self.state_manager = state_manager
        self.logger = logger
        self.clients: Dict[str, MCPClient] = {}
        self.openai = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=self.config.openrouter_api_key,
        )

    async def get_or_create_client(self, server_name: str) -> MCPClient:
        """Get existing client or create new one for the server."""
        if server_name not in self.clients:
            if server_name not in self.config.mcp_server_instruction:
                raise ValueError(f"No configuration found for server: {server_name}")

            client = MCPClient(
                server_name, self.config, self.state_manager, self.logger
            )
            instruction = self.config.mcp_server_instruction[server_name]
            await client.connect_to_server(instruction)
            self.clients[server_name] = client

        return self.clients[server_name]

    async def get_all_available_tools(self) -> List[dict]:
        """Get all available tools from all connected servers with server prefixes."""
        all_tools = []
        for server_name, client in self.clients.items():
            if client.is_connected:
                try:
                    tools = await client.get_available_tools()
                    # Add server prefix to tool names to avoid conflicts
                    for tool in tools:
                        # Modify the tool name to include server prefix
                        original_name = tool["function"]["name"]
                        tool["function"]["name"] = f"{server_name}__{original_name}"
                        # Store original name for later routing
                        tool["_original_name"] = original_name
                        tool["_server_name"] = server_name
                        all_tools.append(tool)
                except Exception as e:
                    self.logger.error(f"Error getting tools from {server_name}: {e}")
        return all_tools

    async def process_query(self, prompt: str, server_id: str) -> str:
        """Process a query using all available MCP servers automatically."""
        try:
            # Connect to all configured servers
            await self._ensure_all_servers_connected()

            # Get all tools from all servers
            all_tools = await self.get_all_available_tools()

            if not all_tools:
                return "No MCP tools are currently available."

            return await self._process_with_all_tools(all_tools, prompt, server_id)
        except Exception as e:
            self.logger.error(f"Error processing query with MCP: {e}")
            return f"Error: Failed to process query: {str(e)}"

    async def _ensure_all_servers_connected(self):
        """Ensure all configured servers are connected."""
        for server_name in self.config.mcp_server_instruction.keys():
            try:
                await self.get_or_create_client(server_name)
            except Exception as e:
                self.logger.warning(f"Failed to connect to {server_name}: {e}")

    async def _process_with_all_tools(
        self, all_tools: List[dict], prompt: str, server_id: str
    ) -> str:
        """Process query with tools from all servers, supporting iterative tool calls."""
        messages = [{"role": "user", "content": prompt}]
        final_text = []
        iteration_count = 0

        while iteration_count < self.config.max_tool_iterations:
            iteration_count += 1
            self.logger.debug(
                f"Starting tool iteration {iteration_count}/{self.config.max_tool_iterations}"
            )

            response = await self.openai.chat.completions.create(
                model=self.state_manager.get_model(server_id=server_id),
                messages=messages,
                tools=all_tools,
                parallel_tool_calls=True,
            )

            additional_tools = self.__deepseek_tool_patch(
                response.choices[0].message.content
            )

            self.logger.debug(
                f"Received response from OpenAI (Iteration {iteration_count}, Server ID: {server_id}): {response}"
            )

            if not response.choices:
                return "Nya! Something went wrong, please try again later."

            content = response.choices[0].message

            # Add assistant message to conversation
            messages.append(
                {
                    "role": "assistant",
                    "content": content.content,
                    "tool_calls": content.tool_calls,
                }
            )

            if content.tool_calls is not None or additional_tools:
                self.logger.debug(
                    f"Processing {len(content.tool_calls)} tool calls in iteration {iteration_count}"
                )

                # Execute all tool calls in this iteration
                tool_results = await self._execute_tool_calls(
                    content.tool_calls, additional_tools
                )

                # Add tool results to messages
                for tool_result in tool_results:
                    messages.append(tool_result)

                # If this was the last allowed iteration, force a final response
                if iteration_count >= self.config.max_tool_iterations:
                    self.logger.warning(
                        f"Reached maximum tool iterations ({self.config.max_tool_iterations}), forcing final response"
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
                    final_text.append(final_response.choices[0].message.content)
                    break

                # Continue to next iteration to see if AI wants to call more tools
            else:
                # No tool calls - this is our final response
                self.logger.debug(
                    f"No tool calls found in iteration {iteration_count}, returning final response"
                )
                final_text.append(content.content)
                break

        if not final_text:
            final_text.append(
                "I've completed the analysis but encountered an issue generating the final response."
            )

        result = "\n".join(final_text)
        self.logger.info(f"Completed tool processing in {iteration_count} iterations")
        return result

    async def _execute_tool_calls(self, tool_calls, additional_tools) -> List[dict]:
        """Execute a list of tool calls and return their results as message objects."""
        tool_results = []

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments
            tool_args = json.loads(tool_args) if tool_args else {}

            # Parse server name and original tool name
            if "__" in tool_name:
                server_name, original_tool_name = tool_name.split("__", 1)
            else:
                # Fallback: try to find the tool in any server
                server_name, original_tool_name = await self._find_tool_server(
                    tool_name
                )

            self.logger.debug(
                f"Calling tool {original_tool_name} on {server_name} with args {tool_args}"
            )

            try:
                client = self.clients.get(server_name)
                if not client or not client.is_connected:
                    raise RuntimeError(f"Server {server_name} not available")

                result = await client.call_tool(original_tool_name, tool_args)
                content_str = self._extract_content_from_result(result)

                # Log a snippet of the server response for debugging
                response_snippet = self._format_response_snippet(content_str)
                self.logger.debug(
                    f"Tool {original_tool_name} on {server_name} returned: {response_snippet}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error calling tool {original_tool_name} on {server_name}: {e}"
                )
                content_str = f"Error calling tool {original_tool_name}: {e}"

            # Create tool result message
            # Handle both OpenAI tool calls (with .id) and DeepSeek patch tool calls (dict without id)
            tool_call_id = getattr(tool_call, "id", f"regular_tool_{len(tool_results)}")
            tool_result = {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": content_str,
            }
            tool_results.append(tool_result)

        # Handle additional tools from DeepSeek patch
        for tool_call in additional_tools:
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]
            # Ensure tool_args is a dict
            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except json.JSONDecodeError:
                    tool_args = {}

            # Parse server name and original tool name
            if "__" in tool_name:
                server_name, original_tool_name = tool_name.split("__", 1)
            else:
                # Fallback: try to find the tool in any server
                server_name, original_tool_name = await self._find_tool_server(
                    tool_name
                )

            self.logger.debug(
                f"Calling tool {original_tool_name} on {server_name} with args {tool_args}"
            )

            try:
                client = self.clients.get(server_name)
                if not client or not client.is_connected:
                    raise RuntimeError(f"Server {server_name} not available")

                result = await client.call_tool(original_tool_name, tool_args)
                content_str = self._extract_content_from_result(result)

                # Log a snippet of the server response for debugging
                response_snippet = self._format_response_snippet(content_str)
                self.logger.debug(
                    f"Tool {original_tool_name} on {server_name} returned: {response_snippet}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error calling tool {original_tool_name} on {server_name}: {e}"
                )
                content_str = f"Error calling tool {original_tool_name}: {e}"

            # Create tool result message
            # For DeepSeek patch tools, generate a unique ID since they don't have one
            tool_call_id = tool_call.get("id", f"deepseek_tool_{len(tool_results)}")
            tool_result = {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": content_str,
            }
            tool_results.append(tool_result)

        return tool_results

    async def _handle_multi_server_tool_calls(
        self, tool_calls, messages: List[dict], server_id: str
    ) -> List[str]:
        """Handle tool calls that may span multiple servers."""
        final_text = []

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments
            tool_args = json.loads(tool_args) if tool_args else {}

            # Parse server name and original tool name
            if "__" in tool_name:
                server_name, original_tool_name = tool_name.split("__", 1)
            else:
                # Fallback: try to find the tool in any server
                server_name, original_tool_name = await self._find_tool_server(
                    tool_name
                )

            self.logger.debug(
                f"Calling tool {original_tool_name} on {server_name} with args {tool_args}"
            )

            try:
                client = self.clients.get(server_name)
                if not client or not client.is_connected:
                    raise RuntimeError(f"Server {server_name} not available")

                result = await client.call_tool(original_tool_name, tool_args)
                content_str = self._extract_content_from_result(result)
            except Exception as e:
                self.logger.error(
                    f"Error calling tool {original_tool_name} on {server_name}: {e}"
                )
                final_text.append(f"Error calling tool {original_tool_name}: {e}")
                content_str = ERROR_OCCURRED_MSG

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,  # Keep the prefixed name for consistency
                    "content": content_str,
                }
            )

        # Generate final response with tool results
        self.logger.debug("Finalizing response after multi-server tool calls")
        response = await self.openai.chat.completions.create(
            model=self.state_manager.get_model(server_id=server_id),
            messages=messages,
        )
        final_text.append(response.choices[0].message.content)

        return final_text

    async def _find_tool_server(self, tool_name: str) -> tuple[str, str]:
        """Find which server has the specified tool (fallback method)."""
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

        raise RuntimeError(f"No server found for tool: {tool_name}")

    # Remove the old process_query method that required server_name
    async def process_query_with_specific_server(
        self, prompt: str, server_name: str, server_id: str
    ) -> str:
        """Process a query using a specific MCP server (legacy method)."""
        try:
            client = await self.get_or_create_client(server_name)
            return await self._process_with_client(client, prompt, server_id)
        except Exception as e:
            self.logger.error(f"Error processing query with {server_name}: {e}")
            return f"Error: Failed to process query with {server_name}: {str(e)}"

    async def _process_with_client(
        self, client: MCPClient, prompt: str, server_id: str
    ) -> str:
        """Process query with a specific client."""
        messages = [{"role": "user", "content": prompt}]

        try:
            available_tools = await client.get_available_tools()
        except Exception as e:
            self.logger.error(f"Error getting tools from {client.server_name}: {e}")
            return f"Error: Could not get tools from {client.server_name}"

        response = await self.openai.chat.completions.create(
            model=self.state_manager.get_model(server_id=server_id),
            messages=messages,
            tools=available_tools,
            parallel_tool_calls=True,
        )

        self.logger.debug(
            f"Received response from {client.server_name} (Server ID: {server_id}): {response}"
        )

        if not response.choices:
            return "Nya! Something went wrong, please try again later."

        final_text = []
        content = response.choices[0].message

        if content.tool_calls is not None:
            final_text.extend(
                await self._handle_tool_calls(
                    client, content.tool_calls, messages, server_id
                )
            )
        else:
            self.logger.debug(
                f"No tool calls found, returning content directly (Server ID: {server_id})"
            )
            final_text.append(content.content)

        return "\n".join(final_text)

    async def _handle_tool_calls(
        self, client: MCPClient, tool_calls, messages: List[dict], server_id: str
    ) -> List[str]:
        """Handle tool calls for a specific client."""
        final_text = []

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments
            tool_args = json.loads(tool_args) if tool_args else {}

            self.logger.debug(
                f"Calling tool {tool_name} with args {tool_args} on {client.server_name}"
            )

            try:
                result = await client.call_tool(tool_name, tool_args)
                content_str = self._extract_content_from_result(result)

                # Log a snippet of the server response for debugging
                response_snippet = self._format_response_snippet(content_str)
                self.logger.debug(
                    f"Tool {tool_name} on {client.server_name} returned: {response_snippet}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error calling tool {tool_name} on {client.server_name}: {e}"
                )
                final_text.append(f"Error calling tool {tool_name}: {e}")
                content_str = ERROR_OCCURRED_MSG

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": content_str,
                }
            )

        # Generate final response with tool results
        self.logger.debug(
            f"Finalizing response after tool calls on {client.server_name}"
        )
        response = await self.openai.chat.completions.create(
            model=self.state_manager.get_model(server_id=server_id),
            messages=messages,
        )
        final_text.append(response.choices[0].message.content)

        return final_text

    def _extract_content_from_result(self, result) -> str:
        """Extract content string from MCP tool result."""
        if result is not None:
            if hasattr(result, "content") and result.content:
                return str(result.content)
            elif hasattr(result, "text"):
                return str(result.text)
            else:
                return str(result)
        return ERROR_OCCURRED_MSG

    def _format_response_snippet(self, content: str, max_length: int = 200) -> str:
        """Format a response snippet for logging, handling newlines and length."""
        if not content:
            return "<empty response>"

        # Replace newlines with spaces for cleaner logging
        clean_content = content.replace("\n", " ").replace("\r", " ")

        # Truncate if too long
        if len(clean_content) > max_length:
            return clean_content[:max_length] + "..."

        return clean_content

    async def disconnect_all(self):
        """Disconnect all clients and cleanup resources."""
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()
        self.logger.info("All MCP clients disconnected")

    def list_connected_servers(self) -> List[str]:
        """Get list of connected server names."""
        return [name for name, client in self.clients.items() if client.is_connected]

    def get_blacklist_info(self) -> Dict[str, Dict[str, int]]:
        """Get blacklist information for all servers."""
        info = {}
        for server_name, client in self.clients.items():
            if client.is_connected:
                blacklist = client.get_blacklisted_tools()
                info[server_name] = {
                    "blacklisted_count": len(blacklist),
                    "blacklisted_tools": blacklist,
                }
        return info

    def __deepseek_tool_patch(self, content):
        """
        Patch for DeepSeek tool calls.
        The pattern is:
        \n<｜tool▁call▁begin｜>function<｜tool▁sep｜>func_name\njson\nargs\n
        \n<｜tool▁call▁begin｜>function<｜tool▁sep｜> ...
        Other normal texts can be mixed in between these calls.
        """
        if "<｜tool▁call▁begin｜>function<｜tool▁sep｜>" not in content:
            self.logger.debug("No DeepSeek tool calls found in content, skipping patch")
            return []
        self.logger.debug("Patching DeepSeek tool calls in content")
        patched_tools = []

        # First, find all occurences of the DeepSeek tool call pattern
        pattern = re.compile(
            r"\n<｜tool▁call▁begin｜>function<｜tool▁sep｜>(.*?)\njson\n({.*?})\n",
            re.DOTALL,
        )

        matches = pattern.findall(content)
        if not matches:
            self.logger.debug("No DeepSeek tool calls found in content, skipping patch")
            return []
        self.logger.debug(f"Found {len(matches)} DeepSeek tool calls in content")

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

        if not patched_tools:
            self.logger.debug("No valid DeepSeek tool calls found after patching")
            return []
        self.logger.debug(f"Patched {len(patched_tools)} DeepSeek tool calls")
        return patched_tools
