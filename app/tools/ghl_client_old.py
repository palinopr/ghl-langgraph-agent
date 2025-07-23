"""
GoHighLevel API Client for Python
This is now a wrapper around the simplified client for backwards compatibility
"""
# Import everything from the simplified client
from app.tools.ghl_client_simple import *

# For backwards compatibility, also expose the GHLClient class name
GHLClient = SimpleGHLClient

# Keep the old exception for compatibility
class GHLRateLimitError(Exception):
    """Custom exception for GHL rate limits"""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"GHL rate limit exceeded. Retry after {retry_after} seconds")