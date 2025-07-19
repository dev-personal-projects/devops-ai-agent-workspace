#!/usr/bin/env python3
"""
Test script for gRPC auth events
Run this to verify your gRPC server and client are working correctly
"""

import asyncio
import logging
import time
from gateway.app.auth.proto.grpc_client import auth_event_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_health_check():
    """Test gRPC server connectivity"""
    logger.info("Testing gRPC server health check...")

    is_healthy = auth_event_client.health_check()

    if is_healthy:
        logger.info("✅ gRPC server is reachable!")
        return True
    else:
        logger.error("❌ gRPC server is not reachable")
        logger.error("Make sure to start the gRPC server first:")
        logger.error("python grpc_auth_server.py")
        return False


def test_signup_event():
    """Test signup event emission"""
    logger.info("Testing signup event...")

    result = auth_event_client.emit_signup_event(
        user_id="test-user-123",
        email="test@example.com",
        full_name="Test User",
        role="developer"
    )

    if result and result.get("success"):
        logger.info("✅ Signup event emitted successfully!")
        logger.info(f"Response: {result}")
        return True
    else:
        logger.error("❌ Signup event failed")
        return False


def test_login_event():
    """Test login event emission"""
    logger.info("Testing login event...")

    result = auth_event_client.emit_login_event(
        user_id="test-user-123",
        email="test@example.com",
        token="sample-jwt-token-12345"
    )

    if result and result.get("success"):
        logger.info("✅ Login event emitted successfully!")
        logger.info(f"Response: {result}")
        return True
    else:
        logger.error("❌ Login event failed")
        return False


def main():
    """Main test function"""
    logger.info("🚀 Starting gRPC Auth Events Test Suite")
    logger.info("=" * 50)

    # Test 1: Health check
    if not test_health_check():
        return

    time.sleep(1)  # Small delay between tests

    # Test 2: Signup event
    test_signup_event()

    time.sleep(1)  # Small delay between tests

    # Test 3: Login event
    test_login_event()

    logger.info("=" * 50)
    logger.info("🏁 Test suite completed!")

    logger.info("\n💡 Tips:")
    logger.info("- Check the gRPC server logs to see the events being processed")
    logger.info("- The server shows mock services (user, analytics, notification) responding to events")
    logger.info("- In production, replace mock subscribers with real service integrations")


if __name__ == "__main__":
    main()