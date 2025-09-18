"""
DEPRECATED: Expedition State Manager - Auto-processing is disabled

⚠️  DEPRECATED: This module is kept for compatibility but is no longer used.
    The new simplified expedition lifecycle uses MANUAL COMPLETION ONLY.

Original purpose:
- Check for completed expeditions
- Process expedition results
- Update expedition states
- Handle cleanup and maintenance

NEW APPROACH: Users must manually complete expeditions using:
- ExpeditionService.complete_expedition()
- All resolution happens at completion time
- No background processing needed
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from .expedition_service import ExpeditionService


class ExpeditionStateManager:
    """Background manager for expedition state processing"""
    
    def __init__(self, expedition_service: ExpeditionService, check_interval: int = 60):
        self.expedition_service = expedition_service
        self.check_interval = check_interval  # seconds between checks
        self.logger = logging.getLogger(__name__)
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the background processing task"""
        if self._running:
            self.logger.warning("ExpeditionStateManager is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        self.logger.info("ExpeditionStateManager started with %ss interval", self.check_interval)
    
    async def stop(self):
        """Stop the background processing task"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("ExpeditionStateManager stopped")
    
    async def _process_loop(self):
        """Main processing loop"""
        while self._running:
            try:
                await self._process_expeditions()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in expedition processing loop: %s", e)
                await asyncio.sleep(self.check_interval)  # Continue after error
    
    async def _process_expeditions(self):
        """DEPRECATED: Auto-processing disabled in favor of manual completion only"""
        # The new simplified lifecycle uses manual completion only
        # This method is kept for compatibility but does nothing
        pass
    
    async def force_process_expedition(self, expedition_id: int) -> dict:
        """DEPRECATED: Use ExpeditionService.complete_expedition() instead for manual completion"""
        return {
            "success": False, 
            "error": "Auto-processing is deprecated. Use ExpeditionService.complete_expedition() for manual completion."
        }
    
    async def get_status(self) -> dict:
        """Get status of the state manager"""
        return {
            "running": self._running,
            "check_interval": self.check_interval,
            "last_check": datetime.utcnow().isoformat()
        }


class ExpeditionScheduler:
    """Simple scheduler for expedition-related tasks"""
    
    def __init__(self, expedition_service: ExpeditionService):
        self.expedition_service = expedition_service
        self.logger = logging.getLogger(__name__)
    
    async def cleanup_old_expeditions(self, days_old: int = 30):
        """Clean up very old completed expeditions (optional maintenance)"""
        # This could be implemented to clean up old expedition logs
        # to prevent database bloat
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        self.logger.info("Cleanup task for expeditions older than %s (not implemented)", cutoff_date)
    
    async def generate_daily_expeditions(self):
        """Generate daily expedition options (if needed for the game design)"""
        # This could be used to refresh available expeditions daily
        # or create special daily expeditions
        self.logger.info("Daily expedition generation (not implemented)")
    
    async def send_expedition_notifications(self):
        """Send notifications for completed expeditions (Discord integration)"""
        # This would integrate with Discord to notify users of completed expeditions
        # For now, just log what would be sent
        try:
            # Get all expeditions that completed in the last check interval
            # and haven't been notified yet
            self.logger.info("Expedition notification check (not implemented)")
        except Exception as e:
            self.logger.error("Error checking expedition notifications: %s", e)