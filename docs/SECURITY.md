# Webhook Security

## Overview

The GoHighLevel webhook endpoint (`/webhook/ghl`) implements HMAC-SHA256 signature verification to ensure webhook authenticity and prevent replay attacks.

## Key Features

- **HMAC-SHA256 Signature Verification**: Validates that webhooks originate from GoHighLevel
- **Replay Attack Prevention**: Rejects requests older than 5 minutes (configurable)
- **Timing Attack Resistance**: Uses constant-time comparison for signature validation

## Configuration

Set the webhook secret in your environment:

```bash
GHL_WEBHOOK_SECRET=your-webhook-secret-here
```

If not configured, the endpoint operates in development mode without signature verification (logs a warning).

## Signature Format

GoHighLevel sends the signature in the `X-GHL-Signature` header:

```
X-GHL-Signature: timestamp=1234567890,signature=abc123def456...
```

## Key Rotation

To rotate the webhook secret:

1. Update `GHL_WEBHOOK_SECRET` in your environment
2. Restart the application
3. Update the webhook secret in GoHighLevel settings

During rotation, consider temporarily accepting both old and new secrets to ensure zero downtime.

## Replay Window

By default, webhooks are rejected if the timestamp is more than 5 minutes old. This prevents replay attacks while allowing for reasonable network delays and clock skew.