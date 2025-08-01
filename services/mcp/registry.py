"""Registry for managing MCP server configurations."""

import logging
from typing import Dict, List, Optional
from .types import ServerConfig
from .exceptions import MCPConfigurationError


class MCPServerRegistry:
    """Registry for managing MCP server configurations and discovery."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._servers: Dict[str, ServerConfig] = {}

    def register_server(self, config: ServerConfig) -> None:
        """Register a new server configuration.

        Args:
            config: Server configuration to register

        Raises:
            MCPConfigurationError: If configuration is invalid
        """
        if not config.name:
            raise MCPConfigurationError("Server name cannot be empty")

        if not config.command:
            raise MCPConfigurationError(
                f"Command cannot be empty for server {config.name}"
            )

        self._servers[config.name] = config
        self.logger.debug(f"Registered MCP server: {config.name}")

    def unregister_server(self, name: str) -> None:
        """Remove a server from the registry.

        Args:
            name: Name of the server to remove
        """
        if name in self._servers:
            del self._servers[name]
            self.logger.debug(f"Unregistered MCP server: {name}")

    def get_server_config(self, name: str) -> Optional[ServerConfig]:
        """Get configuration for a specific server.

        Args:
            name: Name of the server

        Returns:
            Server configuration or None if not found
        """
        return self._servers.get(name)

    def list_servers(self) -> List[str]:
        """Get list of all registered server names.

        Returns:
            List of server names
        """
        return list(self._servers.keys())

    def get_all_configs(self) -> Dict[str, ServerConfig]:
        """Get all server configurations.

        Returns:
            Dictionary mapping server names to configurations
        """
        return self._servers.copy()

    def clear(self) -> None:
        """Remove all server configurations."""
        self._servers.clear()
        self.logger.debug("Cleared all server configurations")

    def load_from_dict(self, configs: Dict[str, dict]) -> None:
        """Load server configurations from a dictionary.

        Args:
            configs: Dictionary of server configurations

        Raises:
            MCPConfigurationError: If any configuration is invalid
        """
        for name, config_dict in configs.items():
            try:
                config = ServerConfig(
                    name=name,
                    command=config_dict.get("command", ""),
                    args=config_dict.get("args", []),
                    env=config_dict.get("env"),
                    blacklist=config_dict.get("blacklist", []),
                    timeout=config_dict.get("timeout", 30),
                    max_retries=config_dict.get("max_retries", 3),
                    retry_delay=config_dict.get("retry_delay", 5),
                )
                self.register_server(config)
            except Exception as e:
                raise MCPConfigurationError(
                    f"Invalid configuration for server {name}: {e}"
                )

        self.logger.info(f"Loaded {len(configs)} server configurations")

    def add_server_from_dict(self, name: str, config_dict: dict) -> None:
        """Add a single server from dictionary configuration.

        Args:
            name: Server name
            config_dict: Server configuration dictionary

        Raises:
            MCPConfigurationError: If configuration is invalid
        """
        try:
            config = ServerConfig(
                name=name,
                command=config_dict.get("command", ""),
                args=config_dict.get("args", []),
                env=config_dict.get("env"),
                blacklist=config_dict.get("blacklist", []),
                timeout=config_dict.get("timeout", 30),
                max_retries=config_dict.get("max_retries", 3),
                retry_delay=config_dict.get("retry_delay", 5),
            )
            self.register_server(config)
        except Exception as e:
            raise MCPConfigurationError(f"Invalid configuration for server {name}: {e}")

    def validate_all(self) -> List[str]:
        """Validate all server configurations.

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []

        for name, config in self._servers.items():
            if not config.command:
                errors.append(f"Server {name}: Command cannot be empty")

            if config.timeout <= 0:
                errors.append(f"Server {name}: Timeout must be positive")

            if config.max_retries < 0:
                errors.append(f"Server {name}: Max retries cannot be negative")

            if config.retry_delay < 0:
                errors.append(f"Server {name}: Retry delay cannot be negative")

        return errors
