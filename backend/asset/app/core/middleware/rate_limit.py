import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, Request


class AbstractRateLimiter(ABC):
    """Abstract interface defining the rate limiter contract."""
    @abstractmethod
    async def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Checks if a key (e.g. client IP, user ID) exceeds the allowed requests limit
        within the specified window.
        Returns True if rate limit is exceeded, False otherwise.
        """
        pass


class InMemoryRateLimiter(AbstractRateLimiter):
    """
    In-memory rate limiter using a simple sliding window log.
    Thread-safe enough for local development and in-memory testing.
    """
    def __init__(self):
        # Maps key -> list of request timestamps
        self._history: Dict[str, List[float]] = defaultdict(list)

    async def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        
        # Filter out requests that are older than the window sliding range
        self._history[key] = [t for t in self._history[key] if t > cutoff]
        
        if len(self._history[key]) >= limit:
            return True
            
        self._history[key].append(now)
        return False


# Shared instance for runtime
rate_limiter = InMemoryRateLimiter()


async def rate_limit(request: Request, limit: int = 100, window_seconds: int = 60):
    """
    FastAPI dependency to rate limit a route.
    Default limit is 100 requests per 60 seconds per IP address.
    """
    client_ip = request.client.host if request.client else "unknown-ip"
    # Formulate key based on client IP and requested route path
    key = f"rate:{client_ip}:{request.url.path}"
    
    is_limited = await rate_limiter.check_rate_limit(key, limit, window_seconds)
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )
