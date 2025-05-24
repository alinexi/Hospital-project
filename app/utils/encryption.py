import os
import logging
from Crypto.Cipher import DES
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad, unpad
from config import Config

def generate_rsa_keys():
    """Generate RSA key pair if not already present"""
    try:
        if not os.path.exists(Config.RSA_PRIVATE_KEY_PATH) or not os.path.exists(Config.RSA_PUBLIC_KEY_PATH):
            # Generate 2048-bit RSA key pair
            key = RSA.generate(2048)
            
            # Save private key
            with open(Config.RSA_PRIVATE_KEY_PATH, 'wb') as f:
                f.write(key.export_key())
            
            # Save public key
            with open(Config.RSA_PUBLIC_KEY_PATH, 'wb') as f:
                f.write(key.publickey().export_key())
            
            print(f"RSA key pair generated: {Config.RSA_PRIVATE_KEY_PATH}, {Config.RSA_PUBLIC_KEY_PATH}")
        else:
            print("RSA key pair already exists.")
    except Exception as e:
        logging.error(f"Error generating RSA keys: {str(e)}")
        raise

def load_private_key():
    """Load RSA private key"""
    try:
        with open(Config.RSA_PRIVATE_KEY_PATH, 'rb') as f:
            return RSA.import_key(f.read())
    except Exception as e:
        logging.error(f"Error loading private key: {str(e)}")
        raise

def load_public_key():
    """Load RSA public key"""
    try:
        with open(Config.RSA_PUBLIC_KEY_PATH, 'rb') as f:
            return RSA.import_key(f.read())
    except Exception as e:
        logging.error(f"Error loading public key: {str(e)}")
        raise

def encrypt_and_sign(data: bytes) -> tuple:
    """
    Encrypt data using DES in CBC mode and sign with RSA
    Returns: (ciphertext: bytes, signature: bytes)
    """
    try:
        # Step 1: Encrypt data using DES in CBC mode with PKCS7 padding
        cipher = DES.new(Config.DES_KEY, DES.MODE_CBC, Config.DES_IV)
        padded_data = pad(data, DES.block_size)
        ciphertext = cipher.encrypt(padded_data)
        
        # Step 2: Compute SHA256 hash of ciphertext
        hash_obj = SHA256.new(ciphertext)
        
        # Step 3: Sign hash with RSA private key (PKCS#1 v1.5)
        private_key = load_private_key()
        signature = pkcs1_15.new(private_key).sign(hash_obj)
        
        return ciphertext, signature
        
    except Exception as e:
        logging.error(f"Error in encrypt_and_sign: {str(e)}")
        raise

def verify_and_decrypt(ciphertext: bytes, signature: bytes) -> bytes:
    """
    Verify signature and decrypt data
    Returns: decrypted data
    """
    try:
        # Step 1: Verify signature against SHA256 hash of ciphertext using RSA public key
        hash_obj = SHA256.new(ciphertext)
        public_key = load_public_key()
        pkcs1_15.new(public_key).verify(hash_obj, signature)
        
        # Step 2: Decrypt ciphertext using DES in CBC mode with PKCS7 padding
        cipher = DES.new(Config.DES_KEY, DES.MODE_CBC, Config.DES_IV)
        padded_data = cipher.decrypt(ciphertext)
        data = unpad(padded_data, DES.block_size)
        
        return data
        
    except Exception as e:
        logging.error(f"Error in verify_and_decrypt: {str(e)}")
        raise

def encrypt_medical_record(record_data: dict) -> tuple:
    """
    Helper function to encrypt medical record data
    Args:
        record_data: Dictionary containing medical record information
    Returns:
        (encrypted_blob, signature) tuple
    """
    try:
        import json
        # Convert dictionary to JSON bytes
        json_data = json.dumps(record_data, default=str).encode('utf-8')
        return encrypt_and_sign(json_data)
    except Exception as e:
        logging.error(f"Error encrypting medical record: {str(e)}")
        raise

def decrypt_medical_record(encrypted_blob: bytes, signature: bytes) -> dict:
    """
    Helper function to decrypt medical record data
    Args:
        encrypted_blob: Encrypted medical record data
        signature: Digital signature
    Returns:
        Dictionary containing medical record information
    """
    try:
        import json
        # Verify and decrypt
        json_data = verify_and_decrypt(encrypted_blob, signature)
        # Convert JSON bytes back to dictionary
        return json.loads(json_data.decode('utf-8'))
    except Exception as e:
        logging.error(f"Error decrypting medical record: {str(e)}")
        raise 