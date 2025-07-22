"""
Tests for webhook signature verification
"""
import json
import time
import pytest
from src.security import verify, generate_signature


class TestSignatureVerification:
    """Test webhook signature verification functionality"""
    
    def test_valid_signature(self):
        """Test verification with valid signature"""
        secret = "test-secret-key"
        body = json.dumps({"contactId": "123", "message": "test"})
        
        # Generate valid signature
        header = generate_signature(body, secret)
        
        # Verify it
        assert verify(body, header, secret) is True
        
    def test_invalid_signature(self):
        """Test verification with invalid signature"""
        secret = "test-secret-key"
        body = json.dumps({"contactId": "123", "message": "test"})
        
        # Generate signature with wrong secret
        header = generate_signature(body, "wrong-secret")
        
        # Should fail verification
        assert verify(body, header, secret) is False
        
    def test_missing_signature_header(self):
        """Test verification with missing signature header"""
        secret = "test-secret-key"
        body = json.dumps({"contactId": "123", "message": "test"})
        
        # Empty header should fail
        assert verify(body, "", secret) is False
        assert verify(body, None, secret) is False
        
    def test_invalid_header_format(self):
        """Test verification with invalid header format"""
        secret = "test-secret-key"
        body = json.dumps({"contactId": "123", "message": "test"})
        
        # Invalid formats
        with pytest.raises(ValueError, match="Invalid signature header format"):
            verify(body, "invalid-format", secret)
            
        with pytest.raises(ValueError, match="Invalid signature header format"):
            verify(body, "timestamp=123", secret)  # Missing signature
            
        with pytest.raises(ValueError, match="Invalid signature header format"):
            verify(body, "signature=abc123", secret)  # Missing timestamp
            
    def test_replay_attack_prevention(self):
        """Test that old timestamps are rejected"""
        secret = "test-secret-key"
        body = json.dumps({"contactId": "123", "message": "test"})
        
        # Generate signature with old timestamp (10 minutes ago)
        old_timestamp = int(time.time()) - 600
        header = generate_signature(body, secret, timestamp=old_timestamp)
        
        # Should fail due to timestamp being too old
        assert verify(body, header, secret) is False
        
    def test_replay_window_edge_cases(self):
        """Test timestamp validation edge cases"""
        secret = "test-secret-key"
        body = json.dumps({"contactId": "123", "message": "test"})
        
        # Just within 5 minute window (299 seconds)
        timestamp_ok = int(time.time()) - 299
        header_ok = generate_signature(body, secret, timestamp=timestamp_ok)
        assert verify(body, header_ok, secret) is True
        
        # Just outside 5 minute window (301 seconds)
        timestamp_old = int(time.time()) - 301
        header_old = generate_signature(body, secret, timestamp=timestamp_old)
        assert verify(body, header_old, secret) is False
        
    def test_custom_max_age(self):
        """Test custom max age for timestamp validation"""
        secret = "test-secret-key"
        body = json.dumps({"contactId": "123", "message": "test"})
        
        # Generate signature 30 seconds ago
        timestamp = int(time.time()) - 30
        header = generate_signature(body, secret, timestamp=timestamp)
        
        # Should pass with 60 second window
        assert verify(body, header, secret, max_age_seconds=60) is True
        
        # Should fail with 20 second window
        assert verify(body, header, secret, max_age_seconds=20) is False
        
    def test_bytes_vs_string_body(self):
        """Test that both bytes and string bodies work"""
        secret = "test-secret-key"
        body_dict = {"contactId": "123", "message": "test"}
        body_str = json.dumps(body_dict)
        body_bytes = body_str.encode('utf-8')
        
        # Generate with string
        header_str = generate_signature(body_str, secret)
        
        # Both should verify
        assert verify(body_str, header_str, secret) is True
        assert verify(body_bytes, header_str, secret) is True
        
        # Generate with bytes
        header_bytes = generate_signature(body_bytes, secret)
        
        # Both should verify
        assert verify(body_str, header_bytes, secret) is True
        assert verify(body_bytes, header_bytes, secret) is True
        
    def test_modified_body_fails(self):
        """Test that modifying the body invalidates the signature"""
        secret = "test-secret-key"
        body = json.dumps({"contactId": "123", "message": "test"})
        
        # Generate valid signature
        header = generate_signature(body, secret)
        
        # Modify body
        modified_body = json.dumps({"contactId": "123", "message": "modified"})
        
        # Should fail verification
        assert verify(modified_body, header, secret) is False
        
    def test_empty_secret_fails(self):
        """Test that empty secret is rejected"""
        body = json.dumps({"contactId": "123", "message": "test"})
        header = "timestamp=123,signature=abc"
        
        assert verify(body, header, "") is False
        assert verify(body, header, None) is False