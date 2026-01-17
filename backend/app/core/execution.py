"""
Execution Engine Singleton

Provides a global execution engine instance for running strategies.
"""

from typing import Optional
import logging

from execution_engine.engine import ExecutionEngine

logger = logging.getLogger(__name__)

_engine: Optional[ExecutionEngine] = None


async def init_execution_engine(redis_url: str) -> ExecutionEngine:
    """
    Initialize the global execution engine.

    Should be called once at application startup.

    Args:
        redis_url: Redis connection URL for distributed state

    Returns:
        The initialized ExecutionEngine instance
    """
    global _engine

    if _engine is not None:
        logger.warning("Execution engine already initialized, returning existing instance")
        return _engine

    logger.info("Initializing execution engine...")
    _engine = ExecutionEngine(redis_url=redis_url)
    await _engine.start()
    logger.info("Execution engine initialized successfully")

    return _engine


def get_execution_engine() -> ExecutionEngine:
    """
    Get the global execution engine instance.

    Raises:
        RuntimeError: If engine has not been initialized

    Returns:
        The ExecutionEngine instance
    """
    if _engine is None:
        raise RuntimeError(
            "Execution engine not initialized. "
            "Call init_execution_engine() at application startup."
        )
    return _engine


async def shutdown_execution_engine() -> None:
    """
    Shutdown the global execution engine.

    Should be called at application shutdown.
    """
    global _engine

    if _engine is None:
        logger.warning("Execution engine not initialized, nothing to shutdown")
        return

    logger.info("Shutting down execution engine...")
    await _engine.stop()
    _engine = None
    logger.info("Execution engine shutdown complete")


def is_engine_initialized() -> bool:
    """Check if the execution engine has been initialized."""
    return _engine is not None
