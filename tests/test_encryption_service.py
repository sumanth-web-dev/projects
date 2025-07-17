"""
Unit tests for the encryption service.
"""
import os
import pytest
import json
from services import encryption_service, EncryptionService


class TestEncryptionService:
    """Test cases for the EncryptionService."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock Flask app for testing."""
        class MockApp:
            def __init__(self):
                # Generate a valid Fernet key for testing
                from cryptography.fernet import Fernet
                self.config = {
                    'ENCRYPTION_KEY': Fernet.generate_key().decode(),
                    'DEBUG': True
                }
        return MockApp()
    
    @pytest.fixture
    def service(self, mock_app):
        """Create an encryption service instance for testing."""
        return EncryptionService(mock_app)
    
    def test_initialization(self, mock_app):
        """Test service initialization with app."""
        service = EncryptionService(mock_app)
        assert service.app == mock_app
        assert service._master_key is not None
    
    def test_encrypt_decrypt_string(self, service):
        """Test encrypting and decrypting a string."""
        original_data = "This is sensitive data"
        
        # Encrypt the data
        encrypted = service.encrypt(original_data)
        assert encrypted != original_data
        
        # Decrypt the data
        decrypted = service.decrypt(encrypted)
        assert decrypted == original_data
    
    def test_encrypt_decrypt_dict(self, service):
        """Test encrypting and decrypting a dictionary."""
        original_data = {
            "first_name": "John",
            "last_name": "Doe",
            "ssn": "123-45-6789",
            "address": "123 Main St"
        }
        
        # Encrypt the data
        encrypted = service.encrypt(original_data)
        assert encrypted != json.dumps(original_data)
        
        # Decrypt the data
        decrypted = service.decrypt(encrypted)
        assert decrypted == original_data
    
    def test_user_specific_encryption(self, service):
        """Test user-specific encryption and decryption."""
        user_id_1 = "user-123"
        user_id_2 = "user-456"
        data = {"secret": "confidential information"}
        
        # Encrypt with user 1's key
        encrypted_1 = service.encrypt(data, user_id_1)
        
        # Encrypt with user 2's key
        encrypted_2 = service.encrypt(data, user_id_2)
        
        # The encrypted values should be different
        assert encrypted_1 != encrypted_2
        
        # Each user should be able to decrypt their own data
        assert service.decrypt(encrypted_1, user_id_1) == data
        assert service.decrypt(encrypted_2, user_id_2) == data
        
        # User 1 should not be able to decrypt user 2's data
        with pytest.raises(ValueError):
            service.decrypt(encrypted_2, user_id_1)
    
    def test_credentials_encryption(self, service):
        """Test encrypting and decrypting credentials."""
        user_id = "user-789"
        credentials = {
            "username": "johndoe",
            "password": "securepassword123",
            "api_key": "abcdef123456"
        }
        
        # Encrypt credentials
        encrypted = service.encrypt_credentials(credentials, user_id)
        
        # Decrypt credentials
        decrypted = service.decrypt_credentials(encrypted, user_id)
        
        # Verify the decrypted data matches the original
        assert decrypted == credentials
        assert decrypted["username"] == "johndoe"
        assert decrypted["password"] == "securepassword123"
    
    def test_empty_data_handling(self, service):
        """Test handling of empty data."""
        # Empty string
        assert service.decrypt(service.encrypt("")) == ""
        
        # Empty dict
        assert service.decrypt(service.encrypt({})) == {}
        
        # None/empty input to decrypt
        assert service.decrypt("") == ""
    
    def test_key_generation(self, service):
        """Test key generation functionality."""
        key = service.generate_key()
        assert key is not None
        assert len(key) > 0
        
        # Verify it's a valid Fernet key by using it
        from cryptography.fernet import Fernet
        cipher = Fernet(key.encode())
        test_data = cipher.encrypt(b"test")
        assert cipher.decrypt(test_data) == b"test"
    
    def test_environment_key_priority(self, mock_app, monkeypatch):
        """Test that environment variable key takes priority over app config."""
        # Set environment variable with a valid Fernet key
        from cryptography.fernet import Fernet
        env_key = Fernet.generate_key().decode()
        monkeypatch.setenv("ENCRYPTION_KEY", env_key)
        
        # Create service
        service = EncryptionService(mock_app)
        
        # Encrypt data
        data = "test data"
        encrypted = service.encrypt(data)
        
        # Verify the environment key was used by creating a new service
        # that will use the environment variable
        new_service = EncryptionService()
        assert new_service.decrypt(encrypted) == data
        
        # Clean up
        monkeypatch.delenv("ENCRYPTION_KEY")
    
    def test_invalid_encrypted_data(self, service):
        """Test handling of invalid encrypted data."""
        with pytest.raises(ValueError):
            service.decrypt("not-valid-encrypted-data")
    
    def test_different_key_failure(self, mock_app):
        """Test that decryption fails with a different key."""
        # Create a service with one key
        service1 = EncryptionService(mock_app)
        
        # Create a service with a different key
        from cryptography.fernet import Fernet
        class MockApp2:
            def __init__(self):
                self.config = {
                    'ENCRYPTION_KEY': Fernet.generate_key().decode(),
                    'DEBUG': True
                }
        mock_app2 = MockApp2()
        service2 = EncryptionService(mock_app2)
        
        # Encrypt with service1
        data = "secret message"
        encrypted = service1.encrypt(data)
        
        # Try to decrypt with service2
        with pytest.raises(ValueError):
            service2.decrypt(encrypted)


if __name__ == "__main__":
    pytest.main([__file__])