"""
OTP (One-Time Password) service for user verification.

This module provides functionality for generating, storing, and validating OTPs
for user verification during registration and other security-sensitive operations.
"""
import os
import random
import string
import time
from typing import Dict, Optional, Tuple
import logging
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from models.database import db

# Set up logging
logger = logging.getLogger(__name__)

class OTPService:
    """Service for managing OTP generation and verification."""
    
    def __init__(self, app=None):
        """Initialize the OTP service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self.otp_expiry_seconds = 300  # Default 5 minutes
        self.otp_length = 6  # Default OTP length
        self.max_verification_attempts = 3  # Default max attempts
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the OTP service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self.otp_expiry_seconds = app.config.get('OTP_EXPIRY_SECONDS', 300)
        self.otp_length = app.config.get('OTP_LENGTH', 6)
        self.max_verification_attempts = app.config.get('MAX_VERIFICATION_ATTEMPTS', 3)
        
        # Create OTP table if it doesn't exist
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'otps' not in inspector.get_table_names():
                self._create_otp_table()
    
    def _create_otp_table(self):
        """Create the OTP table if it doesn't exist."""
        try:
            from sqlalchemy import text
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS otps (
                    id SERIAL PRIMARY KEY,
                    email TEXT NOT NULL,
                    otp TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    verified BOOLEAN DEFAULT FALSE,
                    verification_attempts INTEGER DEFAULT 0
                )
            """))
            db.session.commit()
            logger.info("OTP table created successfully")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating OTP table: {str(e)}")

    
    def generate_otp(self, email: str) -> str:
        """Generate a new OTP for a user.
        
        Args:
            email: The user's email
            
        Returns:
            str: The generated OTP
        """
        # Generate a random numeric OTP
        otp = ''.join(random.choices(string.digits, k=self.otp_length))
        
        try:
            # Calculate expiry time
            now = datetime.utcnow()
            expires_at = now + timedelta(seconds=self.otp_expiry_seconds)
            
            # Delete any existing OTPs for this email
            from sqlalchemy import text
            db.session.execute(text(
                "DELETE FROM otps WHERE email = :email"
            ), {
                "email": email.lower()
            })
            
            # Store the new OTP
            db.session.execute(text(
                """
                INSERT INTO otps (email, otp, created_at, expires_at, verified, verification_attempts)
                VALUES (:email, :otp, :created_at, :expires_at, FALSE, 0)
                """
            ), {
                "email": email.lower(),
                "otp": otp,
                "created_at": now,
                "expires_at": expires_at
            })
            db.session.commit()
            
            logger.info(f"Generated OTP for {email}")
            return otp
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error generating OTP: {str(e)}")
            # Return a default OTP in case of error (this should be handled better in production)
            return otp
    
    def verify_otp(self, email: str, otp: str) -> Tuple[bool, str]:
        """Verify an OTP for a user.
        
        Args:
            email: The user's email
            otp: The OTP to verify
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            from sqlalchemy import text
            
            # Get the OTP record
            result = db.session.execute(text(
                """
                SELECT otp, expires_at, verification_attempts
                FROM otps
                WHERE email = :email
                """
            ), {
                "email": email.lower()
            })
            
            row = result.fetchone()
            if not row:
                return False, "No OTP found for this email"
            
            stored_otp, expires_at, attempts = row
            
            # Check if OTP has expired
            if datetime.utcnow() > expires_at:
                return False, "OTP has expired"
            
            # Check if max attempts reached
            if attempts >= self.max_verification_attempts:
                return False, "Maximum verification attempts reached"
            
            # Increment verification attempts
            db.session.execute(text(
                """
                UPDATE otps
                SET verification_attempts = verification_attempts + 1
                WHERE email = :email
                """
            ), {
                "email": email.lower()
            })
            db.session.commit()
            
            # Verify OTP
            if otp != stored_otp:
                return False, "Invalid OTP"
            
            # Mark as verified
            db.session.execute(text(
                """
                UPDATE otps
                SET verified = TRUE
                WHERE email = :email
                """
            ), {
                "email": email.lower()
            })
            db.session.commit()
            
            logger.info(f"OTP verified for {email}")
            return True, "OTP verified successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error verifying OTP: {str(e)}")
            return False, f"Error verifying OTP: {str(e)}"
    
    def is_email_verified(self, email: str) -> bool:
        """Check if an email has been verified with OTP.
        
        Args:
            email: The user's email
            
        Returns:
            bool: True if verified, False otherwise
        """
        try:
            from sqlalchemy import text
            
            result = db.session.execute(text(
                """
                SELECT verified
                FROM otps
                WHERE email = :email
                """
            ), {
                "email": email.lower()
            })
            
            row = result.fetchone()
            if not row:
                return False
            
            return bool(row[0])
            
        except Exception as e:
            logger.error(f"Error checking email verification: {str(e)}")
            return False
    
    def clear_otp(self, email: str) -> bool:
        """Clear OTP records for an email.
        
        Args:
            email: The user's email
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from sqlalchemy import text
            
            db.session.execute(text(
                "DELETE FROM otps WHERE email = :email"
            ), {
                "email": email.lower()
            })
            db.session.commit()
            
            logger.info(f"Cleared OTP records for {email}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing OTP records: {str(e)}")
            return False


# Create a singleton instance

    
otp_service = OTPService()