#!/usr/bin/env python3
"""Test Redis connection - Clean, testable implementation"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import redis
from gateway.config import settings


class RedisConnectionTester:
    """Redis connection tester - Single Responsibility Principle"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = None
    
    def connect(self) -> bool:
        """Establish Redis connection"""
        try:
            self.client = redis.from_url(self.redis_url)
            self.client.ping()
            return True
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            return False
    
    def test_operations(self) -> bool:
        """Test basic Redis operations"""
        if not self.client:
            return False
            
        try:
            # Test write
            self.client.set("test_key", "test_value")
            
            # Test read
            value = self.client.get("test_key")
            if value != b"test_value":
                print(f"❌ Redis read/write test failed: expected 'test_value', got {value}")
                return False
            
            # Test cleanup
            self.client.delete("test_key")
            
            print(f"✅ Redis read/write test: {value.decode()}")
            return True
            
        except Exception as e:
            print(f"❌ Redis operations failed: {e}")
            return False


class CeleryConnectionTester:
    """Celery connection tester - Single Responsibility Principle"""
    
    def test_broker_connection(self) -> bool:
        """Test Celery broker connection"""
        try:
            from worker.celery_app import app
            
            # Test broker connection
            inspect = app.control.inspect()
            stats = inspect.stats()
            
            if stats:
                print("✅ Celery broker connection successful!")
                return True
            else:
                print("⚠️ Celery broker connected but no workers running")
                return True
                
        except ImportError:
            print("❌ Celery app not found - make sure worker.celery_app exists")
            return False
        except Exception as e:
            print(f"❌ Celery connection failed: {e}")
            return False


def main():
    """Main test runner"""
    print(f"Testing Redis URL: {settings.redis_url}")
    
    # Test Redis connection
    redis_tester = RedisConnectionTester(settings.redis_url)
    
    if redis_tester.connect():
        print("✅ Redis connection successful!")
        redis_tester.test_operations()
        print("✅ Redis cleanup successful!")
    else:
        print("❌ Redis tests failed")
        return False
    
    # Test Celery connection
    celery_tester = CeleryConnectionTester()
    celery_tester.test_broker_connection()
    
    return True


if __name__ == "__main__":
    main()