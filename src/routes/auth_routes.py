"""
Authentication Routes for SimplyInspect
Handles user registration, login, token management, and user profile operations
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from src.models.auth_models import (
    UserRegistrationRequest, UserLoginRequest, PasswordChangeRequest,
    PasswordResetRequest, RefreshTokenRequest, LoginResponse,
    RegistrationResponse, TokenResponse, UserProfileResponse,
    AuthErrorResponse, ValidationErrorResponse
)
from src.services.auth_service import auth_service
from src.db.db_handler import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Authentication"])
security = HTTPBearer()

# =====================================================
# AUTHENTICATION DEPENDENCIES
# =====================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db_handler = Depends(get_db)
) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    
    token = credentials.credentials
    logger.info(f"Token received: {token[:20]}... (length: {len(token)})")
    
    user_data = auth_service.extract_user_from_token(token)
    
    if not user_data:
        logger.warning(f"Failed to extract user from token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user exists and is active
    user_record = await db_handler.fetch_one("""
        SELECT id, email, username, full_name, role, is_approved, is_active,
               department, company, phone, last_login, created_at
        FROM public.users 
        WHERE id = $1 AND is_active = true AND is_approved = true
    """, user_data["user_id"])
    
    if not user_record:
        logger.warning(f"User {user_data['user_id']} not found or inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    logger.info(f"User authenticated: {user_record['email']} (role: {user_record['role']})")
    return dict(user_record)

async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency that requires admin role"""
    if current_user["role"] != "administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required"
        )
    return current_user

async def log_user_action(
    action: str, 
    user_id: int = None, 
    details: Dict[str, Any] = None,
    request: Request = None,
    db_handler = Depends(get_db)
):
    """Log user action to audit trail"""
    try:
        ip_address = None
        user_agent = None
        
        if request:
            # Get real IP (considering proxies)
            ip_address = (
                request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
                request.headers.get("X-Real-IP") or
                request.client.host if request.client else None
            )
            user_agent = request.headers.get("User-Agent")
        
        # Convert details to JSON if provided (JSONB expects dict, not str)
        import json
        details_json = json.dumps(details) if details else None
        
        await db_handler.execute("""
            INSERT INTO public.user_audit_log (user_id, action, details, ip_address, user_agent)
            VALUES ($1, $2, $3::jsonb, $4, $5)
        """, user_id, action, details_json, ip_address, user_agent)
        
    except Exception as e:
        logger.error(f"Failed to log user action: {e}")

# =====================================================
# PUBLIC AUTHENTICATION ENDPOINTS
# =====================================================

@router.post("/auth/register", response_model=RegistrationResponse)
async def register_user(
    registration: UserRegistrationRequest,
    request: Request,
    db_handler = Depends(get_db)
):
    """Register a new user (requires admin approval)"""
    
    # Validate password strength
    password_validation = auth_service.validate_password_strength(registration.password)
    if not password_validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "weak_password",
                "message": "Password does not meet security requirements",
                "errors": password_validation["errors"]
            }
        )
    
    # Check if user already exists
    existing_user = await db_handler.fetch_one("""
        SELECT id FROM public.users 
        WHERE email = $1 OR username = $2
    """, registration.email, registration.username)
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Hash password
    password_hash = auth_service.hash_password(registration.password)
    
    # Create user record
    try:
        user_id = await db_handler.fetch_value("""
            INSERT INTO public.users (
                email, username, password_hash, full_name, department, 
                company, phone, role, is_approved, is_active
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'reviewer', false, true)
            RETURNING id
        """, 
            registration.email, registration.username, password_hash,
            registration.full_name, registration.department, 
            registration.company, registration.phone
        )
        
        # Log registration
        await log_user_action(
            "user_registered",
            user_id,
            {
                "email": registration.email,
                "username": registration.username,
                "full_name": registration.full_name
            },
            request,
            db_handler
        )
        
        # Notify administrators of new registration
        admins = await db_handler.fetch_all("""
            SELECT id FROM public.users 
            WHERE role = 'administrator' AND is_active = true AND is_approved = true
        """)
        
        import json
        for admin in admins:
            await db_handler.execute("""
                INSERT INTO public.user_notifications (user_id, type, title, message, data)
                VALUES ($1, 'user_registered', 'New User Registration', $2, $3::jsonb)
            """, 
                admin["id"],
                f"{registration.full_name} ({registration.email}) has registered and is pending approval",
                json.dumps({"new_user_id": user_id, "email": registration.email})
            )
        
        return RegistrationResponse(
            message="Registration successful. Your account is pending admin approval.",
            user_id=user_id
        )
        
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )

@router.post("/auth/login", response_model=LoginResponse)
async def login(
    login_request: UserLoginRequest,
    request: Request,
    db_handler = Depends(get_db)
):
    """Authenticate user and return JWT tokens"""
    
    # Find user by email
    user_record = await db_handler.fetch_one("""
        SELECT id, email, username, password_hash, full_name, role, 
               is_approved, is_active, department, company, phone, 
               last_login, created_at
        FROM public.users 
        WHERE email = $1 AND is_active = true
    """, login_request.email.lower())
    
    if not user_record:
        await log_user_action("login_failed", None, {"email": login_request.email}, request, db_handler)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not auth_service.verify_password(login_request.password, user_record["password_hash"]):
        await log_user_action("login_failed", user_record["id"], {"reason": "invalid_password"}, request, db_handler)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if user is approved
    if not user_record["is_approved"]:
        await log_user_action("login_failed", user_record["id"], {"reason": "not_approved"}, request, db_handler)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending admin approval"
        )
    
    # Create session
    session_jti = secrets.token_urlsafe(16)
    
    # Get IP and user agent
    ip_address = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
        request.headers.get("X-Real-IP") or
        request.client.host if request.client else None
    )
    user_agent = request.headers.get("User-Agent")
    
    # Create session record
    session_id = await db_handler.fetch_value("""
        INSERT INTO public.user_sessions (user_id, token_jti, ip_address, user_agent, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """, 
        user_record["id"], session_jti, ip_address, user_agent,
        datetime.utcnow() + timedelta(days=auth_service.refresh_token_expire_days)
    )
    
    # Generate tokens
    access_token = auth_service.create_access_token(
        user_record["id"], user_record["email"], user_record["role"], session_jti
    )
    refresh_token = auth_service.create_refresh_token(user_record["id"], session_jti)
    
    # Update last login
    await db_handler.execute("""
        UPDATE public.users SET last_login = $1 WHERE id = $2
    """, datetime.utcnow(), user_record["id"])
    
    # Log successful login
    await log_user_action("login_success", user_record["id"], {"session_id": session_id}, request, db_handler)
    
    return LoginResponse(
        user=UserProfileResponse(
            id=user_record["id"],
            email=user_record["email"],
            username=user_record["username"],
            full_name=user_record["full_name"],
            role=user_record["role"],
            department=user_record["department"],
            company=user_record["company"],
            phone=user_record["phone"],
            last_login=user_record["last_login"],
            created_at=user_record["created_at"],
            permissions=[]  # TODO: Load from role_permissions table
        ),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_service.access_token_expire_minutes * 60
        )
    )

@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db_handler = Depends(get_db)
):
    """Refresh JWT access token using refresh token"""
    
    # Verify refresh token
    payload = auth_service.verify_token(refresh_request.refresh_token)
    
    if not payload or payload.get("type") != auth_service.REFRESH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = int(payload["sub"])
    session_jti = payload.get("jti")
    
    # Check if session is still valid
    session = await db_handler.fetch_one("""
        SELECT s.id, s.expires_at, u.email, u.role, u.is_active, u.is_approved
        FROM public.user_sessions s
        JOIN public.users u ON u.id = s.user_id
        WHERE s.user_id = $1 AND s.token_jti = $2 AND s.is_active = true
    """, user_id, session_jti)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or expired"
        )
    
    if not session["is_active"] or not session["is_approved"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    # Generate new access token
    access_token = auth_service.create_access_token(
        user_id, session["email"], session["role"], session_jti
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_request.refresh_token,  # Keep same refresh token
        expires_in=auth_service.access_token_expire_minutes * 60
    )

@router.post("/auth/logout")
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None,
    db_handler = Depends(get_db)
):
    """Logout user and invalidate session"""
    
    # Get token from request (we need the JTI)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        token_data = auth_service.verify_token(token)
        
        if token_data and token_data.get("jti"):
            # Invalidate session
            await db_handler.execute("""
                UPDATE public.user_sessions 
                SET is_active = false 
                WHERE token_jti = $1 AND user_id = $2
            """, token_data["jti"], current_user["id"])
    
    # Log logout
    await log_user_action("logout", current_user["id"], {}, request, db_handler)
    
    return {"message": "Logged out successfully"}

# =====================================================
# PROTECTED USER ENDPOINTS
# =====================================================

@router.get("/auth/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current user's profile"""
    
    return UserProfileResponse(
        id=current_user["id"],
        email=current_user["email"],
        username=current_user["username"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        department=current_user["department"],
        company=current_user["company"],
        phone=current_user["phone"],
        last_login=current_user["last_login"],
        created_at=current_user["created_at"],
        permissions=[]  # TODO: Load actual permissions
    )

@router.post("/auth/change-password")
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None,
    db_handler = Depends(get_db)
):
    """Change user's password"""
    
    # Get current password hash
    user_record = await db_handler.fetch_one("""
        SELECT password_hash FROM public.users WHERE id = $1
    """, current_user["id"])
    
    # Verify current password
    if not auth_service.verify_password(password_change.current_password, user_record["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    password_validation = auth_service.validate_password_strength(password_change.new_password)
    if not password_validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "weak_password",
                "errors": password_validation["errors"]
            }
        )
    
    # Hash new password
    new_password_hash = auth_service.hash_password(password_change.new_password)
    
    # Update password
    await db_handler.execute("""
        UPDATE public.users 
        SET password_hash = $1, password_changed_at = $2, updated_at = $3
        WHERE id = $4
    """, new_password_hash, datetime.utcnow(), datetime.utcnow(), current_user["id"])
    
    # Log password change
    await log_user_action("password_changed", current_user["id"], {}, request, db_handler)
    
    return {"message": "Password changed successfully"}

# =====================================================
# HEALTH CHECK
# =====================================================

@router.get("/auth/health")
async def auth_health_check():
    """Health check for authentication service"""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat()
    }