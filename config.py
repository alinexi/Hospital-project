import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # DES encryption configuration
    DES_KEY = b'8bytekey'  # 8 bytes for DES
    DES_IV = b'8byteIV!'   # 8 bytes for DES CBC mode
    
    # RSA key file paths
    RSA_PRIVATE_KEY_PATH = 'private.pem'
    RSA_PUBLIC_KEY_PATH = 'public.pem'
    
    # Logging configuration
    LOG_FILE = 'app.log' 