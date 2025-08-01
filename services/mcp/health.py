"""Health monitoring and diagnostics for MCP components."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

from .manager import MCPClientManager
from .types import ServerInfo


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""

    name: str
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class SystemHealth:
    """Overall system health status."""

    status: HealthStatus
    checks: List[HealthCheck]
    summary: str
    timestamp: float

    @classmethod
    def from_checks(cls, checks: List[HealthCheck]) -> "SystemHealth":
        """Create system health from individual checks."""
        if not checks:
            return cls(
                status=HealthStatus.UNKNOWN,
                checks=[],
                summary="No health checks performed",
                timestamp=time.time(),
            )

        # Determine overall status
        has_critical = any(check.status == HealthStatus.CRITICAL for check in checks)
        has_warning = any(check.status == HealthStatus.WARNING for check in checks)

        if has_critical:
            status = HealthStatus.CRITICAL
        elif has_warning:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        # Create summary
        healthy_count = sum(
            1 for check in checks if check.status == HealthStatus.HEALTHY
        )
        warning_count = sum(
            1 for check in checks if check.status == HealthStatus.WARNING
        )
        critical_count = sum(
            1 for check in checks if check.status == HealthStatus.CRITICAL
        )

        summary = f"{healthy_count} healthy, {warning_count} warnings, {critical_count} critical"

        return cls(status=status, checks=checks, summary=summary, timestamp=time.time())


class MCPHealthMonitor:
    """Health monitoring system for MCP components."""

    def __init__(self, manager: MCPClientManager, logger: logging.Logger):
        self.manager = manager
        self.logger = logger
        self._last_health_check: Optional[SystemHealth] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = 60  # seconds
        self._is_monitoring = False

    async def perform_full_health_check(self) -> SystemHealth:
        """Perform a comprehensive health check of all MCP components.

        Returns:
            SystemHealth: Overall system health status
        """
        checks = []

        # Check server registry
        checks.append(self._check_server_registry())

        # Check individual servers
        server_checks = await self._check_all_servers()
        checks.extend(server_checks)

        # Check manager performance
        checks.append(self._check_manager_performance())

        # Check configuration validity
        checks.append(self._check_configuration())

        health = SystemHealth.from_checks(checks)
        self._last_health_check = health

        self.logger.info(f"Health check completed: {health.summary}")
        return health

    def _check_server_registry(self) -> HealthCheck:
        """Check the health of the server registry."""
        try:
            servers = self.manager.registry.list_servers()
            if not servers:
                return HealthCheck(
                    name="server_registry",
                    status=HealthStatus.WARNING,
                    message="No servers configured",
                    details={"configured_servers": 0},
                )

            # Validate all configurations
            errors = self.manager.registry.validate_all()
            if errors:
                return HealthCheck(
                    name="server_registry",
                    status=HealthStatus.CRITICAL,
                    message=f"Configuration errors: {', '.join(errors[:3])}{'...' if len(errors) > 3 else ''}",
                    details={"errors": errors, "configured_servers": len(servers)},
                )

            return HealthCheck(
                name="server_registry",
                status=HealthStatus.HEALTHY,
                message=f"{len(servers)} servers configured",
                details={"configured_servers": len(servers)},
            )

        except Exception as e:
            return HealthCheck(
                name="server_registry",
                status=HealthStatus.CRITICAL,
                message=f"Registry check failed: {e}",
                details={"error": str(e)},
            )

    async def _check_all_servers(self) -> List[HealthCheck]:
        """Check the health of all servers."""
        checks = []
        server_info_list = self.manager.get_server_info()

        for server_info in server_info_list:
            check = await self._check_single_server(server_info)
            checks.append(check)

        return checks

    async def _check_single_server(self, server_info: ServerInfo) -> HealthCheck:
        """Check the health of a single server."""
        try:
            # Handle both enum and string status values safely
            if hasattr(server_info.status, "value"):
                status_value = server_info.status.value
            else:
                status_value = str(server_info.status)

            # Normalize to uppercase for comparison
            status_upper = status_value.upper()

            if status_upper == "DISCONNECTED":
                return HealthCheck(
                    name=f"server_{server_info.name}",
                    status=HealthStatus.WARNING,
                    message=f"Server {server_info.name} is disconnected",
                    details={
                        "server_name": server_info.name,
                        "status": status_value,
                        "tool_count": server_info.tool_count,
                    },
                )

            elif status_upper == "ERROR":
                return HealthCheck(
                    name=f"server_{server_info.name}",
                    status=HealthStatus.CRITICAL,
                    message=f"Server {server_info.name} has errors: {server_info.last_error}",
                    details={
                        "server_name": server_info.name,
                        "status": status_value,
                        "error": server_info.last_error,
                        "tool_count": server_info.tool_count,
                    },
                )

            elif status_upper == "CONNECTED":
                # Perform actual health check
                client = self.manager.clients.get(server_info.name)
                if client:
                    is_healthy = await client.health_check()
                    if is_healthy:
                        return HealthCheck(
                            name=f"server_{server_info.name}",
                            status=HealthStatus.HEALTHY,
                            message=f"Server {server_info.name} is healthy",
                            details={
                                "server_name": server_info.name,
                                "status": status_value,
                                "tool_count": server_info.tool_count,
                                "uptime": server_info.uptime,
                            },
                        )
                    else:
                        return HealthCheck(
                            name=f"server_{server_info.name}",
                            status=HealthStatus.WARNING,
                            message=f"Server {server_info.name} failed health check",
                            details={
                                "server_name": server_info.name,
                                "status": status_value,
                                "tool_count": server_info.tool_count,
                            },
                        )

            return HealthCheck(
                name=f"server_{server_info.name}",
                status=HealthStatus.UNKNOWN,
                message=f"Server {server_info.name} status unknown",
                details={"server_name": server_info.name},
            )

        except Exception as e:
            return HealthCheck(
                name=f"server_{server_info.name}",
                status=HealthStatus.CRITICAL,
                message=f"Health check failed for {server_info.name}: {e}",
                details={"server_name": server_info.name, "error": str(e)},
            )

    def _check_manager_performance(self) -> HealthCheck:
        """Check the performance metrics of the manager."""
        try:
            stats = self.manager.get_performance_stats()

            # Check for performance issues
            warnings = []

            if stats["average_execution_time"] > 30:  # 30 seconds
                warnings.append("High average execution time")

            if stats["average_tool_calls_per_query"] > 10:
                warnings.append("High tool calls per query")

            if stats["connected_servers"] < stats["total_configured_servers"]:
                warnings.append("Some servers not connected")

            if warnings:
                return HealthCheck(
                    name="manager_performance",
                    status=HealthStatus.WARNING,
                    message=f"Performance issues: {', '.join(warnings)}",
                    details=stats,
                )
            else:
                return HealthCheck(
                    name="manager_performance",
                    status=HealthStatus.HEALTHY,
                    message="Performance metrics within normal range",
                    details=stats,
                )

        except Exception as e:
            return HealthCheck(
                name="manager_performance",
                status=HealthStatus.CRITICAL,
                message=f"Performance check failed: {e}",
                details={"error": str(e)},
            )

    def _check_configuration(self) -> HealthCheck:
        """Check the configuration validity."""
        try:
            # Check if OpenAI client is properly configured
            if not hasattr(self.manager, "openai") or not self.manager.openai:
                return HealthCheck(
                    name="configuration",
                    status=HealthStatus.CRITICAL,
                    message="OpenAI client not configured",
                    details={"issue": "missing_openai_client"},
                )

            # Check max iterations setting
            if self.manager.config.max_tool_iterations <= 0:
                return HealthCheck(
                    name="configuration",
                    status=HealthStatus.WARNING,
                    message="Invalid max_tool_iterations setting",
                    details={
                        "max_tool_iterations": self.manager.config.max_tool_iterations
                    },
                )

            return HealthCheck(
                name="configuration",
                status=HealthStatus.HEALTHY,
                message="Configuration is valid",
                details={
                    "max_tool_iterations": self.manager.config.max_tool_iterations,
                    "configured_servers": len(self.manager.registry.list_servers()),
                },
            )

        except Exception as e:
            return HealthCheck(
                name="configuration",
                status=HealthStatus.CRITICAL,
                message=f"Configuration check failed: {e}",
                details={"error": str(e)},
            )

    def start_monitoring(self, interval: int = 60) -> None:
        """Start continuous health monitoring.

        Args:
            interval: Monitoring interval in seconds
        """
        if self._is_monitoring:
            self.logger.warning("Health monitoring is already running")
            return

        self._monitoring_interval = interval
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info(f"Started health monitoring with {interval}s interval")

    def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        if not self._is_monitoring:
            return

        self._is_monitoring = False
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()

        self.logger.info("Stopped health monitoring")

    async def _monitoring_loop(self) -> None:
        """Continuous monitoring loop."""
        while self._is_monitoring:
            try:
                health = await self.perform_full_health_check()

                # Log significant health changes
                if health.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
                    self.logger.warning(f"Health check alert: {health.summary}")

                    # Log details of failed checks
                    for check in health.checks:
                        if check.status in [
                            HealthStatus.WARNING,
                            HealthStatus.CRITICAL,
                        ]:
                            self.logger.warning(f"  {check.name}: {check.message}")

                await asyncio.sleep(self._monitoring_interval)

            except asyncio.CancelledError:
                self.logger.info("Health monitoring cancelled")
                raise
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self._monitoring_interval)

    def get_last_health_check(self) -> Optional[SystemHealth]:
        """Get the results of the last health check.

        Returns:
            Last health check results or None if no check performed
        """
        return self._last_health_check

    def is_healthy(self) -> bool:
        """Quick check if the system is healthy based on last check.

        Returns:
            True if system is healthy, False otherwise
        """
        if not self._last_health_check:
            return False

        return self._last_health_check.status == HealthStatus.HEALTHY
