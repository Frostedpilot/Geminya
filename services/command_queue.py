"""Command Queue Service for preventing race conditions.

This service ensures that commands from the same user are executed sequentially
to prevent database race conditions and data corruption.
"""

import asyncio
import logging
from typing import Dict, Callable, Any, Awaitable
from collections import defaultdict
from functools import wraps


class CommandQueueService:
    """Service to manage command execution queues per user to prevent race conditions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Queue per user (user_id -> asyncio.Queue)
        self.user_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        # Lock per user to ensure only one worker per user
        self.user_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        # Track active workers per user
        self.active_workers: Dict[str, bool] = defaultdict(bool)

    async def enqueue_command(
        self, 
        user_id: str, 
        command_func: Callable[..., Awaitable[Any]], 
        *args, 
        **kwargs
    ) -> Any:
        """
        Enqueue a command for sequential execution per user.
        
        Args:
            user_id: Discord user ID
            command_func: Async function to execute
            *args, **kwargs: Arguments for the command function
            
        Returns:
            The result of the command function
        """
        # Create a future to get the result
        result_future = asyncio.Future()
        
        # Package the command with its arguments and result future
        command_item = {
            'func': command_func,
            'args': args,
            'kwargs': kwargs,
            'result_future': result_future
        }
        
        # Add to user's queue
        await self.user_queues[user_id].put(command_item)
        
        # Start worker for this user if not already running
        await self._ensure_worker_running(user_id)
        
        # Wait for the result
        return await result_future

    async def _ensure_worker_running(self, user_id: str) -> None:
        """Ensure a worker is running for the given user."""
        async with self.user_locks[user_id]:
            if not self.active_workers[user_id]:
                self.active_workers[user_id] = True
                # Start the worker task
                asyncio.create_task(self._worker(user_id))

    async def _worker(self, user_id: str) -> None:
        """Worker that processes commands sequentially for a user."""
        try:
            while True:
                try:
                    # Get next command with a timeout
                    command_item = await asyncio.wait_for(
                        self.user_queues[user_id].get(), 
                        timeout=30.0  # 30 second timeout
                    )
                    
                    # Execute the command
                    try:
                        result = await command_item['func'](*command_item['args'], **command_item['kwargs'])
                        command_item['result_future'].set_result(result)
                    except Exception as e:
                        self.logger.error(f"Error executing command for user {user_id}: {e}")
                        command_item['result_future'].set_exception(e)
                    
                    # Mark task as done
                    self.user_queues[user_id].task_done()
                    
                except asyncio.TimeoutError:
                    # No commands for 30 seconds, stop the worker
                    break
                    
        except Exception as e:
            self.logger.error(f"Worker error for user {user_id}: {e}")
        finally:
            # Mark worker as inactive
            async with self.user_locks[user_id]:
                self.active_workers[user_id] = False
            self.logger.debug(f"Worker stopped for user {user_id}")

    def queued_command(self, func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        """
        Decorator to automatically queue commands per user.
        
        Usage:
            @command_queue.queued_command
            async def some_command(self, ctx, ...):
                # Command implementation
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract context and user ID
            # Assume the second argument is the context (after self)
            if len(args) >= 2:
                ctx = args[1]
                if hasattr(ctx, 'author') and hasattr(ctx.author, 'id'):
                    user_id = str(ctx.author.id)
                    # Queue the original function
                    return await self.enqueue_command(user_id, func, *args, **kwargs)
            
            # Fallback: execute directly if we can't extract user ID
            self.logger.warning(f"Could not extract user ID from {func.__name__}, executing directly")
            return await func(*args, **kwargs)
        
        return wrapper

    async def get_queue_status(self, user_id: str) -> Dict[str, Any]:
        """Get queue status for a user (for debugging)."""
        return {
            'queue_size': self.user_queues[user_id].qsize(),
            'has_active_worker': self.active_workers[user_id],
            'has_lock': user_id in self.user_locks
        }

    async def clear_user_queue(self, user_id: str) -> int:
        """Clear all pending commands for a user. Returns number of cleared commands."""
        cleared = 0
        while not self.user_queues[user_id].empty():
            try:
                command_item = self.user_queues[user_id].get_nowait()
                command_item['result_future'].cancel()
                self.user_queues[user_id].task_done()
                cleared += 1
            except asyncio.QueueEmpty:
                break
        return cleared

    async def shutdown(self):
        """Shutdown all queues and workers."""
        self.logger.info("Shutting down command queue service")
        for user_id in list(self.user_queues.keys()):
            await self.clear_user_queue(user_id)
        self.user_queues.clear()
        self.user_locks.clear()
        self.active_workers.clear()
