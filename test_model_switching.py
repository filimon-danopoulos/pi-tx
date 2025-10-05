#!/usr/bin/env python3
"""
Test script to verify graceful model connect/disconnect.
"""
import asyncio
import sys
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "models"))

from pi_tx.logging_config import init_logging, get_logger
from models.cat_d6t import cat_d6t
from models.cat_950m import cat_950m

init_logging(level="INFO")
log = get_logger(__name__)


async def test_graceful_switching():
    """Test switching between models gracefully."""
    
    log.info("=== Testing Model Connect/Disconnect ===")
    
    # Test 1: Connect to cat_d6t
    log.info("\n--- Test 1: Connecting to cat_d6t ---")
    await cat_d6t.connect()
    await asyncio.sleep(2)  # Let it run for 2 seconds
    
    # Test 2: Disconnect cat_d6t
    log.info("\n--- Test 2: Disconnecting cat_d6t ---")
    await cat_d6t.disconnect()
    log.info("cat_d6t disconnected successfully")
    
    # Test 3: Connect to cat_950m
    log.info("\n--- Test 3: Connecting to cat_950m ---")
    await cat_950m.connect()
    await asyncio.sleep(2)  # Let it run for 2 seconds
    
    # Test 4: Disconnect cat_950m
    log.info("\n--- Test 4: Disconnecting cat_950m ---")
    await cat_950m.disconnect()
    log.info("cat_950m disconnected successfully")
    
    # Test 5: Reconnect to cat_d6t
    log.info("\n--- Test 5: Reconnecting to cat_d6t ---")
    await cat_d6t.connect()
    await asyncio.sleep(2)
    await cat_d6t.disconnect()
    log.info("cat_d6t reconnected and disconnected successfully")
    
    log.info("\n=== All tests passed! ===")


if __name__ == "__main__":
    try:
        asyncio.run(test_graceful_switching())
    except KeyboardInterrupt:
        log.info("Test interrupted by user")
    except Exception as e:
        log.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
