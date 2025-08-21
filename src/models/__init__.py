"""
Models package for SimplyInspect
Contains Pydantic models for API requests and responses
"""

from .auth_models import *

__all__ = [
    # User roles and status
    "UserRole",
    "UserStatus",
    
    # Request models
    "UserRegistrationRequest",
    "UserLoginRequest",
    "PasswordChangeRequest",
    "PasswordResetRequest", 
    "PasswordResetConfirmRequest",
    "RefreshTokenRequest",
    "UserApprovalRequest",
    "UserRoleUpdateRequest",
    "UserUpdateRequest",
    
    # Response models
    "TokenResponse",
    "UserResponse",
    "UserProfileResponse", 
    "LoginResponse",
    "RegistrationResponse",
    "AdminUserListItem",
    "AdminUserListResponse",
    "UserApprovalResponse",
    
    # Error models
    "AuthErrorResponse",
    "ValidationErrorResponse",
    
    # Audit and notification models
    "UserAuditLogEntry",
    "UserAuditLogResponse",
    "NotificationResponse",
    "NotificationListResponse"
]