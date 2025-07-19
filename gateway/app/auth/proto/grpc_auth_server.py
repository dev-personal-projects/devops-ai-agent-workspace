
#!/usr/bin/env python3
"""
Simple gRPC Auth Event Server
Handles auth events from the gateway and can broadcast to other services
"""

import asyncio
import  grpc
import logging
from concurrent import futures
from typing import  Dict, List, Callable
import  json
from services.shared.grpc_stubs import auth_events_pb2_grpc, auth_events_pb2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
class AuthEventService(auth_events_pb2_grpc.AuthEventEmitterServicer):
    """
       gRPC service for handling authentication events
       """

    def __init__(self):
        # Simple in-memory storage for demo/testing
        self.event_log: List[Dict] = []
        self.subscribers: List[Callable] = []

    def add_subscriber(self, callback: Callable):
        """Add a subscriber callback for events"""
        self.subscribers.append(callback)
        logger.info(f"Added subscriber. Total subscribers: {len(self.subscribers)}")

    def _broadcast_event(self, event_type: str, event_data: Dict):
        """Broadcast event to all subscribers"""
        try:
            # Log the event
            event_record = {
                "type": event_type,
                "data": event_data,
                "timestamp": asyncio.get_event_loop().time()
            }
            self.event_log.append(event_record)

            # Keep only last 100 events for demo
            if len(self.event_log) > 100:
                self.event_log.pop(0)

            logger.info(f"Broadcasting {event_type} event: {event_data}")

            # Notify subscribers
            for callback in self.subscribers:
                try:
                    callback(event_type, event_data)
                except Exception as e:
                    logger.error(f"Subscriber callback error: {e}")

        except Exception as e:
            logger.error(f"Error broadcasting event: {e}")

    def EmitSignup(self, request: auth_events_pb2.SignupEvent, context) -> auth_events_pb2.EventAck:
        """Handle signup events"""
        try:
            event_data = {
                "user_id": request.user_id,
                "email": request.email,
                "full_name": request.full_name,
                "role": request.role
            }

            logger.info(f"Received signup event for user: {request.user_id}")

            # Broadcast to subscribers (other services)
            self._broadcast_event("signup", event_data)

            return auth_events_pb2.EventAck(
                success=True,
                message=f"Signup event processed successfully for {request.email}"
            )

        except Exception as e:
            logger.error(f"Error processing signup event: {e}")
            return auth_events_pb2.EventAck(
                success=False,
                message=f"Failed to process signup event: {str(e)}"
            )


def EmitLogin(self, request: auth_events_pb2.LoginEvent, context) -> auth_events_pb2.EventAck:
    """Handle login events"""
    try:
        event_data = {
            "user_id": request.user_id,
            "email": request.email,
            "token": request.token[:20] + "..." if len(request.token) > 20 else request.token
            # Truncate token for logging
        }

        logger.info(f"Received login event for user: {request.user_id}")

        # Broadcast to subscribers (other services)
        self._broadcast_event("login", event_data)

        return auth_events_pb2.EventAck(
            success=True,
            message=f"Login event processed successfully for {request.email}"
        )

    except Exception as e:
        logger.error(f"Error processing login event: {e}")
        return auth_events_pb2.EventAck(
            success=False,
            message=f"Failed to process login event: {str(e)}"
        )


def get_recent_events(self, limit: int = 10) -> List[Dict]:
    """Get recent events for debugging/monitoring"""
    return self.event_log[-limit:] if self.event_log else []
class GRPCAuthServer:
    """
      gRPC server wrapper for easy management
      """

    def __init__(self, port: int = 50051):
        self.port = port
        self.server = None
        self.auth_service = AuthEventService()

    async def start(self):
        """Start the gRPC server"""
        self.server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))

        # Add the auth service
        auth_events_pb2_grpc.add_AuthEventEmitterServicer_to_server(
            self.auth_service, self.server
        )

        # Bind to port
        listen_addr = f'[::]:{self.port}'
        self.server.add_insecure_port(listen_addr)

        logger.info(f"Starting gRPC server on {listen_addr}")
        await self.server.start()

        # Add some demo subscribers
        self._add_demo_subscribers()

        logger.info(f"gRPC Auth Event Server is running on port {self.port}")

    def _add_demo_subscribers(self):
            """Add demo subscribers for testing"""

    def user_service_subscriber(event_type: str, event_data: Dict):
                """Mock user service subscriber"""
                logger.info(f"[USER_SERVICE] Received {event_type} event: {json.dumps(event_data, indent=2)}")

    def analytics_service_subscriber(event_type: str, event_data: Dict):
                """Mock analytics service subscriber"""
                logger.info(f"[ANALYTICS_SERVICE] Tracking {event_type} event for user: {event_data.get('user_id')}")

                def notification_service_subscriber(event_type: str, event_data: Dict):
                    """Mock notification service subscriber"""
                    if event_type == "signup":
                        logger.info(f"[NOTIFICATION_SERVICE] Sending welcome email to: {event_data.get('email')}")
                    elif event_type == "login":
                        logger.info(f"[NOTIFICATION_SERVICE] User {event_data.get('email')} logged in")

                # Add subscribers
                self.auth_service.add_subscriber(user_service_subscriber)
                self.auth_service.add_subscriber(analytics_service_subscriber)
                self.auth_service.add_subscriber(notification_service_subscriber)

    async def stop(self):
                    """Stop the gRPC server"""
                    if self.server:
                        logger.info("Stopping gRPC server...")
                        await self.server.stop(grace=5)
                        logger.info("gRPC server stopped")

    def add_subscriber(self, callback: Callable):
                    """Add a subscriber to the auth service"""
                    self.auth_service.add_subscriber(callback)

    def get_recent_events(self, limit: int = 10) -> List[Dict]:
                    """Get recent events"""
                    return self.auth_service.get_recent_events(limit)


async def main():
    """Main function to run the server"""
    server = GRPCAuthServer(port=50051)

    try:
        await server.start()

        # Keep the server running
        await server.server.wait_for_termination()

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
