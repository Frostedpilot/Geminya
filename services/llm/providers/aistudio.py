"""Google (AI Studio) provider implementation."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from google.genai import Client
from google.genai import types as genai_types

from mcp.types import Tool
from ..provider import LLMProvider
from ..types import (
    LLMRequest,
    LLMResponse,
    ModelInfo,
    ToolCall,
    ProviderConfig,
    ImageRequest,
    ImageResponse,
)
from ..exceptions import (
    ProviderError,
    ModelNotFoundError,
    QuotaExceededError,
    RetriableError,
)


class AIStudioProvider(LLMProvider):
    def __init__(self, config: ProviderConfig, logger: logging.Logger):
        super().__init__("aistudio", config, logger)
        self.client: Optional[Client] = None

        self._retriable_errors = [
            genai_types.FinishReason.MALFORMED_FUNCTION_CALL,
            genai_types.FinishReason.BLOCKLIST,
            genai_types.FinishReason.PROHIBITED_CONTENT,
            genai_types.FinishReason.SPII,
        ]

        self._retriable_codes = [
            429,  # Too Many Requests
            500,  # Internal Server Error
            503,  # Service Unavailable
        ]

    async def initialize(self):
        try:
            # Get the api key from the config
            aistudio_api_key = self.config.api_key
            self.client = Client(api_key=aistudio_api_key)
            self._set_initialized(True)
            self.logger.info("AI Studio client initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Studio client: {e}")
            raise ProviderError("aistudio", "Initialization failed") from e

    async def cleanup(self):
        try:
            if self.client:
                self.client = None
                self.logger.info("AI Studio client cleaned up successfully.")
                self._set_initialized(False)
        except Exception as e:
            self.logger.error(f"Failed to cleanup AI Studio client: {e}")
            raise ProviderError("aistudio", "Cleanup failed") from e

    def get_models(self):
        model_infos = self.config.model_infos
        return {
            display_name: model_info
            for display_name, model_info in model_infos.items()
            if model_info.provider == "aistudio"
        }

    def get_model_info(self, model_id: str) -> ModelInfo:
        models = self.get_models()
        # First check if model_id is a display name (key in models dict)
        if model_id in models:
            return models[model_id]
        # Then check if model_id matches any model's actual ID
        for model_info in models.values():
            if model_info.id == model_id:
                return model_info
        # If not found, raise error
        raise ModelNotFoundError(model_id, "aistudio")

    def supports_model(self, model_id: str) -> bool:
        """Check if AI Studio supports the given model."""
        # Get model info from config
        model_infos = self.config.model_infos

        # Check if model_id is in display name keys (direct match)
        if model_id in model_infos:
            return model_infos[model_id].provider == "aistudio"

        # Check if model_id matches any ModelInfo.id values for this provider
        for model_info in model_infos.values():
            if model_info.provider == "aistudio" and model_info.id == model_id:
                return True

        # Check for short format (e.g., "gemini-2.5-flash-lite")
        # by checking if "aistudio/" + model_id matches any ModelInfo.id
        prefixed_model_id = f"aistudio/{model_id}"
        for model_info in model_infos.values():
            if model_info.provider == "aistudio" and model_info.id == prefixed_model_id:
                return True

        return False

    def convert_mcp_tools(self, mcp_tools: List[Tool]) -> List[Dict[str, Any]]:
        # Implement conversion logic here
        google_functions = []
        for tool in mcp_tools:
            try:
                name = tool.name
                description = tool.description or "No description"
                schema = tool.inputSchema
                tmp = {
                    "name": name,
                    "description": description,
                }
                if schema:
                    basic_structure = {"type": "object"}
                    if "properties" in schema:
                        cleaned_props = self._convert_properties(schema["properties"])
                        if cleaned_props:
                            basic_structure["properties"] = cleaned_props

                    if "required" in schema and isinstance(schema["required"], list):
                        # Only include required fields that exist in cleaned properties
                        if "properties" in basic_structure:
                            valid_required = [
                                field
                                for field in schema["required"]
                                if field in basic_structure["properties"]
                            ]
                            if valid_required:
                                basic_structure["required"] = valid_required

                    tmp["parameters"] = basic_structure
                else:
                    tmp["parameters"] = {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    }

            except Exception as e:
                self.logger.error(f"Failed to convert tool {tool.name}: {e}")
                continue
            google_functions.append(tmp)
            self.logger.debug(f"Converted tool {tool.name} to Google format: {tmp}")

        return google_functions

    def _convert_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Clean property definitions to be Google compatible."""
        cleaned = {}

        for prop_name, prop_def in properties.items():
            if not isinstance(prop_def, dict):
                continue

            clean_prop = {
                "type": self._sanitize_type(str(prop_def.get("type", "string")))
            }

            # Add description if present
            if "description" in prop_def:
                clean_prop["description"] = prop_def["description"]

            # Handle enum values
            if "enum" in prop_def:
                clean_prop["enum"] = prop_def["enum"]

            # Handle array items
            if clean_prop["type"] == "ARRAY" and "items" in prop_def:
                items = prop_def["items"]
                if isinstance(items, dict) and "type" in items:
                    clean_prop["items"] = {
                        "type": self._sanitize_type(str(items["type"]))
                    }
                    if "description" in items:
                        clean_prop["items"]["description"] = items["description"]

            # Handle nested objects (simplified)
            if clean_prop["type"] == "OBJECT" and "properties" in prop_def:
                # For nested objects, only include simple properties
                # TODO: Expand to ARRAY and OBJECT
                nested_props = {}
                for nested_name, nested_def in prop_def["properties"].items():
                    if isinstance(nested_def, dict) and "type" in nested_def:
                        nested_type = self._sanitize_type(str(nested_def["type"]))
                        if nested_type in ["STRING", "NUMBER", "INTEGER", "BOOLEAN"]:
                            nested_props[nested_name] = {"type": nested_type}
                            if "description" in nested_def:
                                nested_props[nested_name]["description"] = nested_def[
                                    "description"
                                ]

                if nested_props:
                    clean_prop["properties"] = nested_props

            cleaned[prop_name] = clean_prop

        return cleaned

    def _sanitize_type(self, type_value: str) -> str:
        """
        Convert MCP type to Google Gemini compatible type.

        Google supports: 'STRING', 'NUMBER', 'INTEGER', 'BOOLEAN', 'ARRAY', 'OBJECT'
        """
        if isinstance(type_value, list):
            # Handle multi-type fields like ['string', 'number']
            # Choose the first non-null type
            for t in type_value:
                if t != "null":
                    return self._sanitize_single_type(t)
            return "STRING"  # Default fallback

        return self._sanitize_single_type(type_value)

    def _sanitize_single_type(self, type_str: str) -> str:
        """Convert a single type string to Google format."""
        type_mapping = {
            "string": "STRING",
            "number": "NUMBER",
            "integer": "INTEGER",
            "boolean": "BOOLEAN",
            "array": "ARRAY",
            "object": "OBJECT",
        }
        return type_mapping.get(type_str, "STRING")

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        if not self.is_initialized() or not self.client:
            raise ProviderError("aistudio", "Provider not initialized")

        if not self.supports_model(request.model):
            raise ModelNotFoundError(request.model, "aistudio")

        tools = request.tools

        try:
            model_id = request.model
            resolved_model_id = self._resolve_model_id(model_id)

            contents = request.messages

            # Build the messages object for aistudio
            messages = []
            for m in contents:
                tool_flag = False
                role = "model"
                if m["role"] == "user":
                    role = "user"
                if m["role"] == "tool":
                    role = "user"
                    tool_flag = True

                content = m["content"]
                if tool_flag:
                    parts = [
                        genai_types.Part.from_function_response(
                            name=m["name"], response={"result": m["content"]}
                        )
                    ]
                # Handle content - it could be a string or a list
                elif isinstance(content, str):
                    parts = [genai_types.Part.from_text(text=content)]
                elif isinstance(content, list):
                    parts = [genai_types.Part.from_text("\n".join(content))]
                else:
                    parts = [genai_types.Part.from_text(text=str(content))]

                messages.append(genai_types.Content(role=role, parts=parts))

            # Get the tools
            google_tools = None
            if tools:
                google_functions = self.convert_mcp_tools(tools)
                google_tools = genai_types.Tool(function_declarations=google_functions)

            # Get the config
            additional_config = request.provider_specific or {}
            config = self._get_gen_config(
                request.temperature, additional_config, google_tools
            )

            # Now call the API
            self.logger.debug(f"Calling AI Studio API with model: {resolved_model_id}")

            response = self.client.models.generate_content(
                model=resolved_model_id, contents=messages, config=config
            )
            self.logger.debug(f"AI Studio raw response: {response}")
            self.logger.debug(
                f"AI Studio processed response: {response.text}, {type(response)}"
            )

            # Parse the result
            if not response:
                raise ProviderError("aistudio", "No response from API")

            response_text = response.text
            self.logger.debug(f"AI Studio response text: {response_text}")
            tool_calls = []
            if (
                response.candidates
                and len(response.candidates) > 0
                and hasattr(response.candidates[0], "content")
                and response.candidates[0].content
            ):
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        tool_calls.append(
                            {
                                "id": part.function_call.id,
                                "function": {
                                    "name": part.function_call.name,
                                    "arguments": part.function_call.args,
                                },
                            }
                        )

            self.logger.debug(
                f"Generated AI Studio response: {len(response_text if response_text else '')} characters and {len(tool_calls)} tool calls"
            )

            if not (response.text or tool_calls):
                self.logger.warning(f"No content or tool calls in response: {response}")

                # Check if candidates exist and have finish_reason
                if response.candidates and len(response.candidates) > 0:
                    finish_reason = response.candidates[0].finish_reason
                    if finish_reason in self._retriable_errors:
                        raise RetriableError("aistudio", str(finish_reason))

                # Check if content was blocked
                if hasattr(response, "prompt_feedback") and response.prompt_feedback:
                    if (
                        hasattr(response.prompt_feedback, "block_reason")
                        and response.prompt_feedback.block_reason
                    ):
                        block_reason = response.prompt_feedback.block_reason
                        self.logger.warning(
                            f"Content blocked by AI Studio: {block_reason}"
                        )
                        raise RetriableError(
                            "aistudio", f"Content blocked: {block_reason}"
                        )

                raise ProviderError("aistudio", "No response from API")

            llmresponse = LLMResponse(
                content=response_text,
                model_used=request.model,
                provider_used="aistudio",
                tool_calls=tool_calls,  # No tool calls implemented yet
                usage=None,
                metadata={
                    "finish_reason": "stop",
                    "response_id": response.response_id,
                },
            )

            return llmresponse

        except Exception as e:

            if isinstance(e, RetriableError):
                # Forward that upstream
                raise RetriableError("aistudio", str(e)) from e

            # else, maybe a http code error
            error_str = str(e).lower()
            for code in self._retriable_codes:
                if str(code) in error_str:
                    raise RetriableError("aistudio", str(e)) from e

            raise ProviderError("aistudio", str(e)) from e

    async def generate_image(self, request: ImageRequest) -> ImageResponse:
        return ImageResponse()

    def _resolve_model_id(self, model_id: str) -> str:
        if not model_id.startswith("aistudio/"):
            raise ProviderError("aistudio", f"Invalid model ID format: {model_id}")
        return model_id[len("aistudio/") :]

    def _get_gen_config(
        self,
        temperature: float,
        provider_specific_config: dict,
        google_tools: genai_types.Tool,
    ) -> genai_types.GenerateContentConfig:
        tmp = {
            "temperature": temperature,
            "safety_settings": [
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=genai_types.HarmBlockThreshold.OFF,
                ),
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                    threshold=genai_types.HarmBlockThreshold.OFF,
                ),
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=genai_types.HarmBlockThreshold.OFF,
                ),
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=genai_types.HarmBlockThreshold.OFF,
                ),
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=genai_types.HarmBlockThreshold.OFF,
                ),
            ],
            **provider_specific_config,
        }

        if google_tools:
            tmp["tools"] = [google_tools]
            tmp["tool_config"] = genai_types.ToolConfig(
                function_calling_config=genai_types.FunctionCallingConfig(mode="AUTO")
            )
            tmp["automatic_function_calling"] = (
                genai_types.AutomaticFunctionCallingConfig(disable=True)
            )

        cfg = genai_types.GenerateContentConfig(**tmp)
        return cfg
