"""
Script to check and validate the encryption key format.
This can help diagnose issues with encryption/decryption.
"""
import os
import base64
import sys
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# Load environment variables
load_dotenv()

def check_key_format(key):
    """Check if a key is in valid Fernet format."""
    try:
        # Check if key is None or empty
        if not key:
            print("ERROR: Key is empty or None")
            return False
        
        # Check key length (Fernet keys are 32 bytes, base64-encoded)
        if len(key.encode()) != 44 or not key.endswith('='):
            print(f"WARNING: Key is not in standard Fernet format (length: {len(key.encode())})")
            print("A valid Fernet key should be 44 bytes long and end with '='")
            return False
        
        # Try to create a Fernet instance with the key
        Fernet(key.encode())
        print("SUCCESS: Key is in valid Fernet format")
        return True
    except Exception as e:
        print(f"ERROR: Invalid key format - {str(e)}")
        return False

def convert_to_fernet_key(input_key):
    """Convert any string to a valid Fernet key using PBKDF2."""
    try:
        # Use PBKDF2 to derive a key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'static_salt_for_key_derivation',
            iterations=100000,
            backend=default_backend()
        )
        
        # Derive key from input
        derived_key = base64.urlsafe_b64encode(kdf.derive(input_key.encode()))
        return derived_key.decode()
    except Exception as e:
        print(f"ERROR: Failed to convert key - {str(e)}")
        return None

def main():
    """Main function to check encryption key."""
    # Get key from environment
    key = os.environ.get('ENCRYPTION_KEY')
    
    print("=== Encryption Key Check ===")
    
    if not key:
        print("ERROR: ENCRYPTION_KEY not found in environment variables")
        return
    
    print(f"Key prefix: {key[:5]}...")
    print(f"Key length: {len(key.encode())} bytes")
    
    # Check if key is in valid format
    is_valid = check_key_format(key)
    
    if not is_valid:
        print("\n=== Converting to Valid Format ===")
        converted_key = convert_to_fernet_key(key)
        
        if converted_key:
            print(f"Converted key: {converted_key[:5]}... (length: {len(converted_key.encode())} bytes)")
            print("\nTo use this key, update your .env file with:")
            print(f'ENCRYPTION_KEY="{converted_key}"')
            
            # Verify the converted key
            print("\n=== Verifying Converted Key ===")
            check_key_format(converted_key)

if __name__ == "__main__":
    main()