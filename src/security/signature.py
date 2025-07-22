"""
Webhook signature verification for GoHighLevel

Implements HMAC-SHA256 signature verification with timestamp validation
to prevent replay attacks.
"""
import hashlib
import hmac
import time


def verify(
    body: str | bytes,
    header: str,
    secret: str,
    max_age_seconds: int = 300
) -> bool:
    """
    Verify webhook signature with timestamp validation.

    Args:
        body: The raw request body (string or bytes)
        header: The X-GHL-Signature header value (format: "timestamp=xxx,signature=yyy")
        secret: The webhook secret key
        max_age_seconds: Maximum allowed age of the request in seconds (default: 5 minutes)

    Returns:
        True if signature is valid and within time window, False otherwise

    Raises:
        ValueError: If header format is invalid
    """
    if not header or not secret:
        return False

    # Parse header format: "timestamp=xxx,signature=yyy"
    try:
        parts = header.split(',')
        timestamp_part = None
        signature_part = None

        for part in parts:
            if part.startswith('timestamp='):
                timestamp_part = part[len('timestamp='):]
            elif part.startswith('signature='):
                signature_part = part[len('signature='):]

        if not timestamp_part or not signature_part:
            raise ValueError("Invalid header format")

        timestamp = int(timestamp_part)
        provided_signature = signature_part

    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid signature header format: {header}") from e

    # Check timestamp to prevent replay attacks
    current_time = int(time.time())
    if abs(current_time - timestamp) > max_age_seconds:
        return False

    # Convert body to bytes if string
    body_bytes = body.encode('utf-8') if isinstance(body, str) else body

    # Compute expected signature
    # Format: HMAC-SHA256(timestamp + "." + body)
    payload = f"{timestamp}.".encode() + body_bytes
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, provided_signature)


def generate_signature(
    body: str | bytes,
    secret: str,
    timestamp: int | None = None
) -> str:
    """
    Generate a webhook signature for testing purposes.

    Args:
        body: The request body (string or bytes)
        secret: The webhook secret key
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Signature header value in format: "timestamp=xxx,signature=yyy"
    """
    if timestamp is None:
        timestamp = int(time.time())

    # Convert body to bytes if string
    body_bytes = body.encode('utf-8') if isinstance(body, str) else body

    # Compute signature
    payload = f"{timestamp}.".encode() + body_bytes
    signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return f"timestamp={timestamp},signature={signature}"
