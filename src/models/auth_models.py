"""
Authentication Pydantic Models for SimplyInspect
Defines request/response models for authentication endpoints
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    """User roles enum"""
    ADMINISTRATOR = "administrator"
    REVIEWER = "reviewer"

class UserStatus(str, Enum):
    """User approval status"""
    PENDING = "pending"
    APPROVED = "approved" 
    REJECTED = "rejected"

# =====================================================
# AUTHENTICATION REQUESTS
# =====================================================

class UserRegistrationRequest(BaseModel):
    """User registration request model"""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    department: Optional[str] = Field(None, max_length=255, description="Department")
    company: Optional[str] = Field(None, max_length=255, description="Company name")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower()
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower()

class UserLoginRequest(BaseModel):
    """User login request model"""
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password")
    remember_me: Optional[bool] = Field(False, description="Remember login")

class PasswordChangeRequest(BaseModel):
    """Password change request model"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr = Field(..., description="Email address for password reset")

class PasswordResetConfirmRequest(BaseModel):
    """Password reset confirmation model"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

class RefreshTokenRequest(BaseModel):
    """Token refresh request model"""
    refresh_token: str = Field(..., description="Refresh token")

# =====================================================
# USER MANAGEMENT REQUESTS (Admin)
# =====================================================

class UserApprovalRequest(BaseModel):
    """User approval/rejection request model"""
    approve: bool = Field(..., description="True to approve, False to reject")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection")

class UserRoleUpdateRequest(BaseModel):
    """User role update request model"""
    role: UserRole = Field(..., description="New user role")

class UserUpdateRequest(BaseModel):
    """User profile update request model"""
    full_name: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = Field(None, description="Active status")

# =====================================================
# AUTHENTICATION RESPONSES
# =====================================================

class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")

class UserResponse(BaseModel):
    """User information response model"""
    id: int
    email: str
    username: str
    full_name: str
    role: UserRole
    is_approved: bool
    is_active: bool
    department: Optional[str]
    company: Optional[str]
    phone: Optional[str]
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        orm_mode = True

class UserProfileResponse(BaseModel):
    """Current user profile response"""
    id: int
    email: str
    username: str
    full_name: str
    role: UserRole
    department: Optional[str]
    company: Optional[str]
    phone: Optional[str]
    last_login: Optional[datetime]
    created_at: datetime
    permissions: List[str] = Field(default_factory=list, description="User permissions")

class LoginResponse(BaseModel):
    """Login response model"""
    user: UserProfileResponse
    tokens: TokenResponse
    message: str = Field(default="Login successful")

class RegistrationResponse(BaseModel):
    """Registration response model"""
    message: str
    user_id: int
    status: str = Field(default="pending_approval")

# =====================================================
# ADMIN RESPONSES
# =====================================================

class AdminUserListItem(BaseModel):
    """User list item for admin panel"""
    id: int
    email: str
    username: str
    full_name: str
    role: UserRole
    is_approved: bool
    is_active: bool
    department: Optional[str]
    company: Optional[str]
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    last_login: Optional[datetime]
    created_at: datetime

class AdminUserListResponse(BaseModel):
    """Admin user list response"""
    users: List[AdminUserListItem]
    total_count: int
    pending_count: int
    active_count: int

class UserApprovalResponse(BaseModel):
    """User approval response"""
    message: str
    user_id: int
    approved: bool
    approved_by: int

# =====================================================
# ERROR RESPONSES
# =====================================================

class AuthErrorResponse(BaseModel):
    """Authentication error response"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    error: str = "validation_error"
    message: str
    field_errors: Dict[str, List[str]]

# =====================================================
# AUDIT LOG MODELS
# =====================================================

class UserAuditLogEntry(BaseModel):
    """User audit log entry"""
    id: int
    user_id: Optional[int]
    action: str
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime

class UserAuditLogResponse(BaseModel):
    """User audit log response"""
    logs: List[UserAuditLogEntry]
    total_count: int

# =====================================================
# NOTIFICATION MODELS
# =====================================================

class NotificationResponse(BaseModel):
    """User notification response"""
    id: int
    type: str
    title: str
    message: Optional[str]
    data: Optional[Dict[str, Any]]
    is_read: bool
    created_at: datetime

class NotificationListResponse(BaseModel):
    """Notification list response"""
    notifications: List[NotificationResponse]
    unread_count: int
    total_count: int