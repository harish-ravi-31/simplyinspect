"""
Authentication Middleware for SimplyInspect
Provides authentication and authorization middleware for FastAPI routes
"""

from fastapi import Request, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
from typing import Dict, Any, List, Optional

from src.services.auth_service import auth_service
from src.db.db_handler import get_db_handler

logger = logging.getLogger(__name__)

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle JWT authentication for protected routes
    """
    
    def __init__(self, app, protected_paths: List[str] = None, excluded_paths: List[str] = None):
        super().__init__(app)
        # Default protected paths (can be overridden)
        self.protected_paths = protected_paths or [
            # Removed sharepoint paths - they use dependency injection for auth
            # "/api/v1/sharepoint",
            # "/api/v1/sharepoint-simple",
            "/api/v1/purview", 
            # "/api/v1/configuration",
            # "/api/v1/identity",
            # "/api/v1/admin",
            # "/api/v1/library-assignments"
        ]
        
        # Paths that don't require authentication
        self.excluded_paths = excluded_paths or [
            "/api/v1/auth/register",
            "/api/v1/auth/login", 
            "/api/v1/auth/refresh",
            "/api/v1/auth/health",
            "/health",
            "/",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request through authentication middleware"""
        
        path = request.url.path
        method = request.method
        
        # Skip authentication for excluded paths
        if self._is_excluded_path(path):
            return await call_next(request)
        
        # Skip authentication for non-protected paths
        if not self._is_protected_path(path):
            return await call_next(request)
        
        logger.info(f"Auth middleware checking protected path: {method} {path}")
        
        # Check for authentication token
        try:
            user_data = await self._authenticate_request(request)
            
            # Add user data to request state
            request.state.user = user_data
            request.state.authenticated = True
            
            # Log authenticated request
            logger.info(f"Authenticated request: {method} {path} by user {user_data['email']} (role: {user_data.get('role')})")
            
            return await call_next(request)
            
        except HTTPException as e:
            logger.warning(f"Authentication failed for {method} {path}: {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": "authentication_required",
                    "message": e.detail,
                    "path": path
                }
            )
        except Exception as e:
            logger.error(f"Authentication error for {method} {path}: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "authentication_error", 
                    "message": "Internal authentication error"
                }
            )
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    def _is_protected_path(self, path: str) -> bool:
        """Check if path requires authentication"""
        return any(path.startswith(protected) for protected in self.protected_paths)
    
    async def _authenticate_request(self, request: Request) -> Dict[str, Any]:
        """Extract and validate authentication token from request"""
        
        # Get Authorization header
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Parse Bearer token
        scheme, token = get_authorization_scheme_param(authorization)
        
        if not scheme or scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify token
        user_data = auth_service.extract_user_from_token(token)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify user exists and is active
        db_handler = get_db_handler()
        await db_handler.connect()
        
        try:
            user_record = await db_handler.fetch_one("""
                SELECT id, email, username, full_name, role, is_approved, is_active
                FROM public.users 
                WHERE id = $1 AND is_active = true AND is_approved = true
            """, user_data["user_id"])
            
            if not user_record:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            # Return combined user data
            return {
                **dict(user_record),
                "jti": user_data.get("jti")
            }
            
        finally:
            await db_handler.disconnect()

class RoleBasedMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle role-based access control
    """
    
    def __init__(self, app, role_restrictions: Dict[str, List[str]] = None):
        super().__init__(app)
        # Default role restrictions (path prefix -> allowed roles)
        self.role_restrictions = role_restrictions or {
            "/api/v1/admin": ["administrator"],
            "/api/v1/configuration": ["administrator"],  # Only admins can modify config
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through role-based authorization"""
        
        # Skip if user is not authenticated
        if not getattr(request.state, 'authenticated', False):
            return await call_next(request)
        
        path = request.url.path
        method = request.method
        user = getattr(request.state, 'user', None)
        
        if not user:
            return await call_next(request)
        
        # Check role restrictions
        for path_prefix, allowed_roles in self.role_restrictions.items():
            if path.startswith(path_prefix):
                if user.get('role') not in allowed_roles:
                    logger.warning(f"Access denied: {user.get('email')} ({user.get('role')}) tried to access {path}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "access_denied",
                            "message": f"Access denied. Required role(s): {', '.join(allowed_roles)}",
                            "user_role": user.get('role'),
                            "required_roles": allowed_roles
                        }
                    )
                break
        
        return await call_next(request)

# =====================================================
# UTILITY FUNCTIONS FOR MANUAL AUTH CHECKS
# =====================================================

def require_authentication(request: Request) -> Dict[str, Any]:
    """
    Utility function to manually check authentication in route handlers
    """
    if not getattr(request.state, 'authenticated', False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User data not found"
        )
    
    return user

def require_role(request: Request, allowed_roles: List[str]) -> Dict[str, Any]:
    """
    Utility function to manually check user role in route handlers
    """
    user = require_authentication(request)
    
    if user.get('role') not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}"
        )
    
    return user

def require_admin(request: Request) -> Dict[str, Any]:
    """
    Utility function to require admin role
    """
    return require_role(request, ["administrator"])

def get_current_user_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """
    Utility function to get current user from request (returns None if not authenticated)
    """
    if not getattr(request.state, 'authenticated', False):
        return None
    
    return getattr(request.state, 'user', None)