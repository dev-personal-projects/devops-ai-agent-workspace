import grpc
import logging
from typing import Optional
from services.shared.grpc_stubs import auth_events_pb2_grpc, auth_events_pb2

logger = logging.getLogger(__name__)


class AuthEventClient:
    def __init__(self, grpc_server_url: str = "localhost:50051"):  # Changed port to 50051
        self.grpc_server_url = grpc_server_url

    def _get_channel(self):
        """Create gRPC channel with proper error handling"""
        return grpc.insecure_channel(self.grpc_server_url)

    def health_check(self) -> bool:
        """Check if the gRPC server is reachable"""
        try:
            with self._get_channel() as channel:
                # Try to create a stub and make a simple call
                stub = auth_events_pb2_grpc.AuthEventEmitterStub(channel)

                # Test with a dummy event (this might fail at service level but connection should work)
                test_event = auth_events_pb2.SignupEvent(
                    user_id="health_check",
                    email="test@health.check",
                    full_name="Health Check",
                    role="test"
                )

                # Set a short timeout for health check
                response = stub.EmitSignup(test_event, timeout=2.0)
                return True

        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                logger.warning(f"gRPC server unavailable at {self.grpc_server_url}")
                return False
            # Other gRPC errors might still indicate connectivity
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    def emit_signup_event(self, user_id: str, email: str, full_name: str, role: str) -> Optional[dict]:
        """
        Emit signup event to gRPC server

        Args:
            user_id: User ID from Supabase
            email: User email
            full_name: User's full name
            role: User role (e.g., 'developer')

        Returns:
            dict: Response from gRPC server or None if failed
        """
        try:
            with self._get_channel() as channel:
                stub = auth_events_pb2_grpc.AuthEventEmitterStub(channel)

                # Create signup event
                event = auth_events_pb2.SignupEvent(
                    user_id=user_id,
                    email=email,
                    full_name=full_name,
                    role=role
                )

                # Set timeout for the call
                response = stub.EmitSignup(event, timeout=5.0)

                logger.info(f"Signup event emitted for user {user_id}: {response.success}")

                return {
                    "success": response.success,
                    "message": response.message
                }

        except grpc.RpcError as e:
            logger.error(f"gRPC error emitting signup event: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error emitting signup event: {str(e)}")
            return None

    def emit_login_event(self, user_id: str, email: str, token: str) -> Optional[dict]:
        """
        Emit login event to gRPC server

        Args:
            user_id: User ID from Supabase
            email: User email
            token: Access token from login

        Returns:
            dict: Response from gRPC server or None if failed
        """
        try:
            with self._get_channel() as channel:
                stub = auth_events_pb2_grpc.AuthEventEmitterStub(channel)

                # Create login event
                event = auth_events_pb2.LoginEvent(
                    user_id=user_id,
                    email=email,
                    token=token
                )

                # Set timeout for the call
                response = stub.EmitLogin(event, timeout=5.0)

                logger.info(f"Login event emitted for user {user_id}: {response.success}")

                return {
                    "success": response.success,
                    "message": response.message
                }

        except grpc.RpcError as e:
            logger.error(f"gRPC error emitting login event: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error emitting login event: {str(e)}")
            return None


# Global instance - now pointing to correct port
auth_event_client = AuthEventClient("localhost:50051")