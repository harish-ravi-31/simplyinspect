"""
Middleware package for SimplyInspect
Contains authentication and other middleware components
"""

from .auth_middleware import (
    AuthenticationMiddleware,
    RoleBasedMiddleware,
    require_authentication,
    require_role,
    require_admin,
    get_current_user_from_request
)

__all__ = [
    "AuthenticationMiddleware",
    "RoleBasedMiddleware", 
    "require_authentication",
    "require_role",
    "require_admin",
    "get_current_user_from_request"
]