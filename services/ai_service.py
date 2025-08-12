"""AI Service - High-level orchestrator for all AI operations."""

from __future__ import annotations
import logging
from typing import Optional, TYPE_CHECKING
from discord import Message

if TYPE_CHECKING:
    from config import Config

from services.state_manager import StateManager
from services.llm import LLMManager
from services.mcp import MCPClientManager
from services.llm.types import LLMRequest
from services.mcp.types import ToolResult


class AIService:
    """High-level AI service that orchestrates LLM and MCP operations."""

    def __init__(
        self,
        config: Config,
        state_manager: StateManager,
        llm_manager: LLMManager,
        mcp_client: MCPClientManager,
        logger: logging.Logger,
    ):
        self.config = config
        self.state_manager = state_manager
        self.llm_manager = llm_manager
        self.mcp_client = mcp_client
        self.logger = logger

    async def get_response(self, message: Message, server_id: str) -> str:
        """Main entry point for AI responses - orchestrates LLM and MCP."""
        if not self.llm_manager._initialized:
            self.logger.error("AI Service not ready - LLM Manager not initialized")
            return "Nya! I'm not ready yet, please try again in a moment."

        try:
            # Determine if we should use MCP tools
            use_mcp = self.state_manager.use_mcp

            model = self.state_manager.get_tool_model(server_id)
            model_info = self.llm_manager.get_model_info(model)

            model_tool_capabilities = model_info.supports_tools

            self.logger.debug(
                f"Model tool capabilities for {model}: {model_tool_capabilities}"
            )

            if use_mcp and model_tool_capabilities:
                return await self._get_response_with_tools(message, server_id)
            else:
                return await self._get_simple_response(message, server_id)

        except Exception as e:
            self.logger.error(f"Error in AI Service: {e}")
            return "Nya! Something went wrong, please try again later."

    # NOTE: Check response is not currently used or implemented, also disabled upstream
    # async def get_check_response(self, prompt: str, message) -> str:
    #     """Get a check response (delegated to LLM Manager)."""
    #     return await self.llm_manager.get_check_response(prompt, message)

    def get_available_models(self):
        """Get available models (delegated to LLM Manager)."""
        return self.llm_manager.get_available_models()

    async def _get_simple_response(self, message: Message, server_id: str) -> str:
        """Get response without tools using LLM Manager."""
        # Prepare the request
        server_id_str = str(message.guild.id) if message.guild else "default"
        if server_id_str != server_id:
            self.logger.warning(
                f"Server ID mismatch: message id {server_id_str} != given id {server_id}"
            )
        self.state_manager.initialize_server(server_id_str)

        model = self.state_manager.get_model(server_id_str)

        # NOTE: Race condition! This could lead to inconsistent history being used
        history = self.state_manager.get_history(message.channel.id)

        # Get persona-specific lore book
        persona_name = self.state_manager.persona.get(
            server_id_str, self.config.default_persona
        )
        lore_books = self.state_manager.get_lore_books()
        lore_book = lore_books.get(persona_name) if lore_books else None

        # Build prompt (extracted from LLM Manager)
        prompt = self._build_prompt(message, history, lore_book, use_tools=False)

        # Create LLM request
        request = LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=getattr(self.config, "temperature", 0.7),
        )

        # Get response from LLM Manager
        response = await self.llm_manager._generate_with_provider(request)

        self.logger.info(
            f"Generated simple response for {message.author.name} ({len(response.content)} chars)"
        )

        return response.content.strip()

    async def _get_response_with_tools(self, message, server_id: str) -> str:
        """Get response with tools using coordinated LLM + MCP approach."""
        server_id_str = str(message.guild.id) if message.guild else "default"
        if server_id_str != server_id:
            self.logger.warning(
                f"Server ID mismatch: message id {server_id_str} != given id {server_id}"
            )
        self.state_manager.initialize_server(server_id_str)

        tool_model = self.state_manager.get_tool_model(server_id_str)
        core_model = self.state_manager.get_model(server_id_str)

        # NOTE: Race condition! This could lead to inconsistent history being used
        history = self.state_manager.get_history(message.channel.id)

        # Get persona-specific lore book
        persona_name = self.state_manager.persona.get(
            server_id_str, self.config.default_persona
        )
        lore_books = self.state_manager.get_lore_books()
        lore_book = lore_books.get(persona_name) if lore_books else None

        # Build initial prompt
        prompt = self._build_tool_prompt(message, history)

        # Start iterative tool calling process
        tool_response = await self.mcp_client.process_query(
            prompt, server_id_str, tool_model
        )

        core_prompt = self._build_augment_prompt(
            message, tool_response.content, lore_book
        )

        # Use core model for final response generation
        core_response = await self.llm_manager._generate_with_provider(
            LLMRequest(
                messages=[{"role": "user", "content": core_prompt}],
                model=core_model,
                temperature=getattr(self.config, "temperature", 0.7),
            )
        )

        # NOTE: response is MCPResponse type, additional information can be return together with the information.

        tool_calls_made = tool_response.tool_calls_made
        execution_time = tool_response.execution_time
        server_used = tool_response.servers_used

        pre_message = f"[{tool_calls_made} tools called, {execution_time:.2f}s elapsed, servers used: {', '.join(server_used)}]\n"

        return pre_message + core_response.content.strip()

    def _build_prompt(
        self, message: Message, history, lore_book, use_tools: bool = True
    ) -> str:
        """Build the complete prompt for AI generation."""
        # This is copied from LLM Manager but simplified for tools
        author = message.author
        author_name = author.name
        if author.nick:
            author_name = f"{author.nick} ({author.name})"

        # Get personality prompt
        personality_prompt = self._get_personality_prompt(message)

        # Build history section
        history_prompt = ""
        if history:
            for entry in history:
                nick_part = f" (aka {entry['nick']})" if entry["nick"] else ""
                line = f"From: {entry['name']}{nick_part}\n{entry['content']}\n\n"
                history_prompt += line
        history_prompt = history_prompt.strip()

        # Build lore book section
        lore_prompt = ""
        if lore_book:
            for category_name, category_data in lore_book.items():
                if isinstance(category_data, dict) and "keywords" in category_data:
                    keywords = category_data.get("keywords", [])

                    if any(keyword in message.content.lower() for keyword in keywords):
                        example = category_data.get("example", "")
                        if example:
                            lore_prompt += f"\n\n{example}"
                            self.logger.debug(
                                f"Added lore example from category: {category_name}"
                            )
                            break

        # Collect all participants
        authors = {author_name}
        if history:
            for entry in history:
                authors.add(entry["name"])

        # Get persona name
        server_id = str(message.guild.id) if message.guild else "default"
        persona_name = self.state_manager.persona.get(
            server_id, self.config.default_persona
        )

        # Build final prompt
        final_prompt = f"""
Write {persona_name}'s next reply in a fictional chat between participants and {author_name}.
{personality_prompt}
{lore_prompt}
[Start a new group chat. Group members: {persona_name}, {', '.join(authors)}]
{history_prompt}
[Write the next reply only as {persona_name}. Only use information related to {author_name}'s message and only answer {author_name} directly. Do not start with "From {persona_name}:" or similar.]
{"[You have access to tools, so leverage them as much as possible. You can use more than one tool at a time, and you can iteratively call them up to {self.config.max_tool_iterations} times with consecutive messages before giving answer, so plan accordingly. For tasks you deemed as hard, start with the sequential-thinking tool.]" if use_tools else ""}
""".replace(
            "{{user}}", author_name
        )

        return final_prompt.strip()

    def _build_tool_prompt(self, message: Message, history):
        """Build the tool prompt for AI generation."""
        author = message.author
        author_name = author.name
        if author.nick:
            author_name = f"{author.nick} ({author.name})"

        # Build history section
        history_prompt = ""
        if history:
            for entry in history:
                nick_part = f" (aka {entry['nick']})" if entry["nick"] else ""
                line = f"From: {entry['name']}{nick_part}\n{entry['content']}\n\n"
                history_prompt += line
        history_prompt = history_prompt.strip()
        # Collect all participants
        authors = {author_name}
        if history:
            for entry in history:
                authors.add(entry["name"])

        # Get persona name
        server_id = str(message.guild.id) if message.guild else "default"
        persona_name = self.state_manager.persona.get(
            server_id, self.config.default_persona
        )

        # Build final prompt
        final_prompt = f"""
Write {persona_name}'s next reply in a fictional chat between participants and {author_name}.
[Start a new group chat. Group members: {persona_name}, {', '.join(authors)}]
{history_prompt}
[Write the next reply only as {persona_name}. Only use information related to {author_name}'s message and only answer {author_name} directly.]
[You have access to tools, so leverage them as much as possible. You can use more than one tool at a time, and you can iteratively call them up to {self.config.max_tool_iterations} times with consecutive messages before giving answer, so plan accordingly. For tasks you deem as hard, start with the sequential-thinking tool.]
[Always try to use the tools to search the web when you need information. When you do so, use both the google and tavily tools together to cross-check information.]
[Based on the results from tool calls, make your answer as detailed as possible, including information not exactly relevant to {{user}}'s message.]
""".replace(
            "{{user}}", author_name
        )

        return final_prompt.strip()

    def _build_augment_prompt(
        self, message: Message, tool_response_content: str, lore_book
    ):
        """Build the augment prompt for AI generation."""
        """Build the complete prompt for AI generation."""
        # This is copied from LLM Manager but simplified for tools
        author = message.author
        author_name = author.name
        if author.nick:
            author_name = f"{author.nick} ({author.name})"

        # Get personality prompt
        personality_prompt = self._get_personality_prompt(message)

        # Build lore book section
        lore_prompt = ""
        if lore_book:
            for category_name, category_data in lore_book.items():
                if isinstance(category_data, dict) and "keywords" in category_data:
                    keywords = category_data.get("keywords", [])

                    if any(keyword in message.content.lower() for keyword in keywords):
                        example = category_data.get("example", "")
                        if example:
                            lore_prompt += f"\n\n{example}"
                            self.logger.debug(
                                f"Added lore example from category: {category_name}"
                            )
                            break

        # Get persona name
        server_id = str(message.guild.id) if message.guild else "default"
        persona_name = self.state_manager.persona.get(
            server_id, self.config.default_persona
        )

        # Build final prompt
        final_prompt = f"""
Rewrite the following message in {persona_name}'s style. Try to retain the message context and meaning while incorporating relevant personality traits.
---
[{persona_name}'s description]
{personality_prompt}
{lore_prompt}
---
[The message to rewrite]
{tool_response_content}
""".replace(
            "{{user}}", author_name
        )

        return final_prompt.strip()

    def _get_personality_prompt(self, message) -> str:
        """Get the personality system prompt."""
        try:
            from utils.config_load import load_language_file

            # Get server ID and ensure it's initialized
            server_id = str(message.guild.id) if message.guild else "default"
            self.state_manager.initialize_server(server_id)

            # Get persona name for this server
            persona_name = self.state_manager.persona.get(
                server_id, self.config.default_persona
            )

            # Load language data
            lang_data = load_language_file()
            characters = lang_data.get("characters", {})
            character = characters.get(persona_name, {})

            self.logger.debug(f"Using persona '{persona_name}' for server {server_id}")

            personality = character.get(
                "personality", "You are Geminya, a helpful AI assistant."
            )

            self.logger.debug(f"Personality prompt length: {len(personality)} chars")
            return personality

        except Exception as e:
            self.logger.error(f"Failed to load personality prompt: {e}")
            return "You are Geminya, a helpful AI assistant."
