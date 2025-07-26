import asyncio
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


class MCPClient:
    def __init__(
        self, config: Config, state_manager: StateManager, logger: logging.Logger
    ):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.config = config
        self.state_manager = state_manager
        self.logger = logger
        self.openai = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.config.openrouter_api_key,
        )

    async def connect_to_server(self, instruction: dict):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """

        command = instruction.get("command")
        args = instruction.get("args", [])
        env = instruction.get("env", None)

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env,
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, prompt: str, server_id: str) -> str:
        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        tmp = await self.session.list_tools()
        available_tools = [convert_tool_format(tool) for tool in tmp.tools]

        response = await self.openai.chat.completions.create(
            model=self.state_manager.get_model(server_id=server_id),
            messages=messages,
            tools=available_tools,
        )

        self.logger.debug(
            f"Received response from MCP server (Server ID: {server_id}): {response}"
        )

        if not response.choices:
            return "Nya! Something went wrong, please try again later."

        final_text = []
        content = response.choices[0].message
        if content.tool_calls is not None:
            for tool_call in content.tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments
                tool_args = json.loads(tool_args) if tool_args else {}

                # Execute the tool call
                self.logger.debug(
                    f"Calling tool {tool_name} with args {tool_args} (Server ID: {server_id})"
                )

                self.logger.debug(f"Arguments for tool {tool_name}: {tool_args}")

                try:
                    result = await self.session.call_tool(tool_name, tool_args)
                    # final_text.append(
                    #     f"[Calling tool {tool_name} with args {tool_args}]"
                    # )
                except Exception as e:
                    self.logger.error(
                        f"Error calling tool {tool_name} with args {tool_args}: {e}"
                    )
                    final_text.append(f"Error calling tool {tool_name}: {e}")
                    result = None

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": result.content,
                    }
                )

            # Only call the final response when all tools are called
            # TODO: Highly inefficient, should be optimized, maybe by using a special prompt for MCP only then augment with personality?
            self.logger.debug(
                f"Finalizing response after tool calls (Server ID: {server_id})"
            )
            response = await self.openai.chat.completions.create(
                model=self.state_manager.get_model(server_id=server_id),
                messages=messages,
            )

            final_text.append(response.choices[0].message.content)

        else:
            # If no tool calls, just return the content directly
            self.logger.debug(
                f"No tool calls found, returning content directly (Server ID: {server_id})"
            )
            final_text.append(content.content)

        return "\n".join(final_text)
