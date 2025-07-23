from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from gateway.core.logging import get_logger

_log = get_logger(__name__)
_HEADER = "x-request-id"

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and manage X-Request-ID headers.
    
    - Re-uses an incoming X-Request-ID or generates a uuid4.
    - Stores it on request.state.request_id for later use.
    - Adds the header back to the response.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get the X-Request-ID from the incoming request headers or generate a new one
        rid = request.headers.get(_HEADER, str(uuid.uuid4()))
        
        # Store the request ID in the request state
        request.state.request_id = rid
        
        # Call the next middleware or route handler
        response: Response = await call_next(request)
        
        # Add the X-Request-ID to the response headers
        response.headers[_HEADER] = rid
        
        # Log the assigned request ID
        _log.debug("request_id.assigned", path=request.url.path, rid=rid)
        
        return response