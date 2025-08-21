"""
Authentication Service for SimplyInspect
Handles JWT tokens, password hashing, user authentication, and role-based access control
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from passlib.context import CryptContext
from jose import JWTError, jwt
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        # JWT Configuration
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        if jwt_secret:
            self.secret_key = jwt_secret
            logger.info(f"Using configured JWT secret key (length: {len(jwt_secret)})")
        else:
            self.secret_key = self._generate_secret_key()
            
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30  # Short-lived access tokens
        self.refresh_token_expire_days = 7     # Longer-lived refresh tokens
        
        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Token type constants
        self.ACCESS_TOKEN = "access"
        self.REFRESH_TOKEN = "refresh"
        
    def _generate_secret_key(self) -> str:
        """Generate a secure random secret key if none is provided"""
        key = secrets.token_urlsafe(32)
        logger.warning("Using auto-generated JWT secret key. Set JWT_SECRET_KEY environment variable for production!")
        return key
    
    # =====================================================
    # PASSWORD MANAGEMENT
    # =====================================================
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password meets security requirements"""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    # =====================================================
    # JWT TOKEN MANAGEMENT
    # =====================================================
    
    def create_access_token(self, user_id: int, email: str, role: str, 
                          session_jti: str = None) -> str:
        """Create a JWT access token"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        # Generate unique token ID
        if not session_jti:
            session_jti = secrets.token_urlsafe(16)
        
        payload = {
            "sub": str(user_id),        # Subject (user ID)
            "email": email,
            "role": role,
            "type": self.ACCESS_TOKEN,
            "jti": session_jti,         # JWT ID for tracking/revocation
            "iat": int(now.timestamp()),         # Issued at
            "exp": int(expire.timestamp()),      # Expires at
            "iss": "SimplyInspect"      # Issuer
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: int, session_jti: str) -> str:
        """Create a JWT refresh token"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": str(user_id),
            "type": self.REFRESH_TOKEN,
            "jti": session_jti,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "iss": "SimplyInspect"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token has expired
            if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
                return None
                
            return payload
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
    
    def extract_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract user information from a valid access token"""
        payload = self.verify_token(token)
        
        if not payload or payload.get("type") != self.ACCESS_TOKEN:
            return None
        
        return {
            "user_id": int(payload["sub"]),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "jti": payload.get("jti")
        }
    
    def is_token_expired(self, token: str) -> bool:
        """Check if a token is expired without full verification"""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("exp", 0) < datetime.now(timezone.utc).timestamp()
        except JWTError:
            return True
    
    # =====================================================
    # ROLE-BASED ACCESS CONTROL
    # =====================================================
    
    def has_permission(self, user_role: str, resource: str, action: str, 
                      permissions: List[Dict[str, Any]] = None) -> bool:
        """Check if a user role has permission for a specific resource/action"""
        
        # Default permissions if not provided from database
        if not permissions:
            permissions = self.get_default_permissions()
        
        # Check for exact match
        for perm in permissions:
            if (perm["role"] == user_role and 
                perm["resource"] == resource and 
                perm["action"] == action):
                return perm.get("is_allowed", True)
        
        # Administrator has access to everything by default
        if user_role == "administrator":
            return True
            
        # Deny by default
        return False
    
    def get_default_permissions(self) -> List[Dict[str, Any]]:
        """Get default role permissions"""
        return [
            # Administrator permissions
            {"role": "administrator", "resource": "users", "action": "create", "is_allowed": True},
            {"role": "administrator", "resource": "users", "action": "read", "is_allowed": True},
            {"role": "administrator", "resource": "users", "action": "update", "is_allowed": True},
            {"role": "administrator", "resource": "users", "action": "delete", "is_allowed": True},
            {"role": "administrator", "resource": "users", "action": "approve", "is_allowed": True},
            {"role": "administrator", "resource": "sharepoint", "action": "read", "is_allowed": True},
            {"role": "administrator", "resource": "sharepoint", "action": "write", "is_allowed": True},
            {"role": "administrator", "resource": "purview", "action": "read", "is_allowed": True},
            {"role": "administrator", "resource": "purview", "action": "write", "is_allowed": True},
            {"role": "administrator", "resource": "settings", "action": "read", "is_allowed": True},
            {"role": "administrator", "resource": "settings", "action": "write", "is_allowed": True},
            
            # Reviewer permissions
            {"role": "reviewer", "resource": "users", "action": "read_self", "is_allowed": True},
            {"role": "reviewer", "resource": "sharepoint", "action": "read", "is_allowed": True},
            {"role": "reviewer", "resource": "purview", "action": "read", "is_allowed": True},
            {"role": "reviewer", "resource": "settings", "action": "read", "is_allowed": True},
        ]
    
    # =====================================================
    # UTILITY FUNCTIONS
    # =====================================================
    
    def generate_password_reset_token(self) -> str:
        """Generate a secure password reset token"""
        return secrets.token_urlsafe(32)
    
    def sanitize_email(self, email: str) -> str:
        """Sanitize and normalize email address"""
        return email.lower().strip()
    
    def is_strong_password(self, password: str) -> bool:
        """Quick check if password meets minimum strength requirements"""
        return self.validate_password_strength(password)["valid"]

# Global instance
auth_service = AuthService()