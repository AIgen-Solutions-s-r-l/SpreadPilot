# watchdog/app/main.py
import asyncio
import signal
import sys

from spreadpilot_core.logging.logger import get_logger
from .service.monitor import MonitorService

logger = get_logger(__name__)

async def main():
    """Initializes and runs the MonitorService."""
    monitor_service = MonitorService()

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received.")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda signum, frame: signal_handler())

    monitor_task = asyncio.create_task(monitor_service.start())
    stop_wait_task = asyncio.create_task(stop_event.wait())

    # Wait for either the monitor task to finish (unexpectedly) or stop signal
    done, pending = await asyncio.wait(
        {monitor_task, stop_wait_task},
        return_when=asyncio.FIRST_COMPLETED
    )

    if stop_wait_task in done:
        logger.info("Stopping monitor service gracefully...")
        await monitor_service.stop()
        # Wait for the monitor task to finish cleanup
        await monitor_task
    else:
        logger.warning("Monitor task exited unexpectedly.")
        # Attempt graceful stop anyway
        if not monitor_service._stop_event.is_set():
             await monitor_service.stop()
        # Propagate exception if monitor task failed
        monitor_task.result() # This will raise exception if monitor_task failed

    # Cancel any pending tasks (should ideally be none)
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    logger.info("Watchdog service shut down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt caught, shutting down.")
    except Exception as e:
        logger.critical(f"Unhandled exception at top level: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Ensure logs are flushed etc. if needed
        pass