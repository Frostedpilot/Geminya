"""MCP health and status command for debugging and monitoring."""

import discord
from discord.ext import commands
from typing import Optional

from cogs.base_command import BaseCommand
from services.container import ServiceContainer
from services.mcp import HealthStatus


class MCPStatusCog(BaseCommand):
    """
    MCP (Model Context Protocol) status and health monitoring command.

    Provides administrators with insights into MCP server health,
    performance statistics, and configuration status.
    """

    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

    @commands.hybrid_command(
        name="mcp-status",
        description="Show MCP server status and health information",
    )
    @commands.has_permissions(manage_guild=True)
    async def mcp_status(self, ctx: commands.Context):
        """Display comprehensive MCP system status."""

        try:
            # Get MCP manager from services
            mcp_manager = self.services.mcp_client

            # Create health monitor
            from services.mcp import MCPHealthMonitor

            health_monitor = MCPHealthMonitor(mcp_manager, self.logger)

            # Perform health check
            health = await health_monitor.perform_full_health_check()

            # Create main status embed
            embed = discord.Embed(
                title="🔧 MCP System Status",
                color=self._get_status_color(health.status),
                timestamp=discord.utils.utcnow(),
            )

            # Overall health status
            status_emoji = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.WARNING: "⚠️",
                HealthStatus.CRITICAL: "❌",
                HealthStatus.UNKNOWN: "❓",
            }

            embed.add_field(
                name="Overall Health",
                value=f"{status_emoji[health.status]} {health.status.value.title()}",
                inline=True,
            )

            embed.add_field(name="Health Summary", value=health.summary, inline=True)

            # Performance statistics
            stats = mcp_manager.get_performance_stats()
            embed.add_field(
                name="Performance",
                value=(
                    f"Queries: {stats['total_queries']}\n"
                    f"Tool Calls: {stats['total_tool_calls']}\n"
                    f"Avg Time: {stats['average_execution_time']:.2f}s"
                ),
                inline=True,
            )

            # Server overview
            connected_servers = mcp_manager.list_connected_servers()
            server_info = mcp_manager.get_server_info()

            embed.add_field(
                name="Servers",
                value=(
                    f"Connected: {len(connected_servers)}\n"
                    f"Configured: {len(server_info)}\n"
                    f"Registry: {len(mcp_manager.registry.list_servers())}"
                ),
                inline=True,
            )

            # Individual server statuses (limited to avoid embed limits)
            server_statuses = []
            for info in server_info[:5]:  # Limit to first 5 servers
                status_value = (
                    info.status.value
                    if hasattr(info.status, "value")
                    else str(info.status)
                )
                status_icon = "✅" if status_value.upper() == "CONNECTED" else "❌"
                server_statuses.append(f"{status_icon} {info.name}")

            if server_statuses:
                embed.add_field(
                    name="Server Status", value="\n".join(server_statuses), inline=False
                )

            # Health check details for issues
            issues = [
                check
                for check in health.checks
                if check.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]
            ]

            if issues:
                issue_details = []
                for issue in issues[:3]:  # Limit to avoid embed size limits
                    issue_details.append(f"• {issue.name}: {issue.message}")

                embed.add_field(
                    name="⚠️ Issues Detected",
                    value="\n".join(issue_details),
                    inline=False,
                )

            embed.set_footer(text="Use /mcp-health for detailed health information")

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in mcp_status command: {e}")

            error_embed = discord.Embed(
                title="❌ MCP Status Error",
                description=f"Failed to retrieve MCP status: {str(e)}",
                color=0xFF6B6B,
            )
            await ctx.send(embed=error_embed)

    @commands.hybrid_command(
        name="mcp-health",
        description="Perform detailed MCP health check",
    )
    @commands.has_permissions(manage_guild=True)
    async def mcp_health(self, ctx: commands.Context):
        """Perform and display detailed health check results."""

        try:
            # Get MCP manager
            mcp_manager = self.services.mcp_client

            # Create health monitor
            from services.mcp import MCPHealthMonitor

            health_monitor = MCPHealthMonitor(mcp_manager, self.logger)

            # Perform comprehensive health check
            await ctx.send("🔍 Performing comprehensive health check...")

            health = await health_monitor.perform_full_health_check()

            # Create detailed health embed
            embed = discord.Embed(
                title="🏥 MCP Health Check Results",
                color=self._get_status_color(health.status),
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(
                name="Overall Status",
                value=f"{health.status.value.title()} - {health.summary}",
                inline=False,
            )

            # Group checks by status
            healthy_checks = [
                c for c in health.checks if c.status == HealthStatus.HEALTHY
            ]
            warning_checks = [
                c for c in health.checks if c.status == HealthStatus.WARNING
            ]
            critical_checks = [
                c for c in health.checks if c.status == HealthStatus.CRITICAL
            ]

            if healthy_checks:
                healthy_names = [f"✅ {c.name}" for c in healthy_checks[:5]]
                embed.add_field(
                    name=f"Healthy ({len(healthy_checks)})",
                    value="\n".join(healthy_names),
                    inline=True,
                )

            if warning_checks:
                warning_details = [
                    f"⚠️ {c.name}: {c.message}" for c in warning_checks[:3]
                ]
                embed.add_field(
                    name=f"Warnings ({len(warning_checks)})",
                    value="\n".join(warning_details),
                    inline=True,
                )

            if critical_checks:
                critical_details = [
                    f"❌ {c.name}: {c.message}" for c in critical_checks[:3]
                ]
                embed.add_field(
                    name=f"Critical Issues ({len(critical_checks)})",
                    value="\n".join(critical_details),
                    inline=False,
                )

            # Performance insights
            stats = mcp_manager.get_performance_stats()
            if stats["total_queries"] > 0:
                embed.add_field(
                    name="Performance Insights",
                    value=(
                        f"Avg execution: {stats['average_execution_time']:.2f}s\n"
                        f"Tools per query: {stats['average_tool_calls_per_query']:.1f}\n"
                        f"Total runtime: {stats['total_execution_time']:.1f}s"
                    ),
                    inline=True,
                )

            embed.set_footer(text="Health checks help identify and prevent issues")

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in mcp_health command: {e}")

            error_embed = discord.Embed(
                title="❌ Health Check Error",
                description=f"Failed to perform health check: {str(e)}",
                color=0xFF6B6B,
            )
            await ctx.send(embed=error_embed)

    @commands.hybrid_command(
        name="mcp-servers",
        description="List all MCP servers and their details",
    )
    @commands.has_permissions(manage_guild=True)
    async def mcp_servers(self, ctx: commands.Context):
        """Display detailed information about all MCP servers."""

        try:
            mcp_manager = self.services.mcp_client
            server_info = mcp_manager.get_server_info()

            if not server_info:
                embed = discord.Embed(
                    title="📋 MCP Servers",
                    description="No MCP servers are configured.",
                    color=0x95A5A6,
                )
                await ctx.send(embed=embed)
                return

            embed = discord.Embed(
                title="📋 MCP Servers", color=0x3498DB, timestamp=discord.utils.utcnow()
            )

            for info in server_info:
                status_icons = {
                    "CONNECTED": "🟢",
                    "DISCONNECTED": "🔴",
                    "ERROR": "❌",
                    "CONNECTING": "🟡",
                    "RECONNECTING": "🟠",
                }

                status_value = (
                    info.status.value
                    if hasattr(info.status, "value")
                    else str(info.status)
                )
                status_icon = status_icons.get(status_value.upper(), "❓")

                server_details = [
                    f"Status: {status_icon} {status_value.upper()}",
                    f"Tools: {info.tool_count}",
                ]

                if info.blacklisted_tools:
                    server_details.append(f"Blacklisted: {len(info.blacklisted_tools)}")

                if info.uptime:
                    server_details.append(f"Uptime: {info.uptime:.0f}s")

                if info.last_error:
                    server_details.append(f"Error: {info.last_error[:50]}...")

                embed.add_field(
                    name=info.name, value="\n".join(server_details), inline=True
                )

            embed.set_footer(text=f"Total servers: {len(server_info)}")

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in mcp_servers command: {e}")

            error_embed = discord.Embed(
                title="❌ Server List Error",
                description=f"Failed to retrieve server information: {str(e)}",
                color=0xFF6B6B,
            )
            await ctx.send(embed=error_embed)

    def _get_status_color(self, status: HealthStatus) -> int:
        """Get Discord color for health status."""
        color_map = {
            HealthStatus.HEALTHY: 0x2ECC71,  # Green
            HealthStatus.WARNING: 0xF39C12,  # Orange
            HealthStatus.CRITICAL: 0xE74C3C,  # Red
            HealthStatus.UNKNOWN: 0x95A5A6,  # Gray
        }
        return color_map.get(status, 0x95A5A6)

    @mcp_status.error
    @mcp_health.error
    @mcp_servers.error
    async def mcp_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        """Handle MCP command errors."""
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need the 'Manage Server' permission to use MCP commands.",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
        else:
            # Let the base class handle other errors
            await super().cog_command_error(ctx, error)


async def setup(bot: commands.Bot):
    """Setup the MCP status cog."""
    await bot.add_cog(MCPStatusCog(bot, bot.services))
