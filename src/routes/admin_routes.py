"""
Admin Routes for SimplyInspect
Handles user management, approval, role assignment, and admin operations
"""

from datetime import datetime
from typing import List, Optional
import json
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
import logging

from src.models.auth_models import (
    UserRegistrationRequest, UserApprovalRequest, UserRoleUpdateRequest, UserUpdateRequest,
    AdminUserListResponse, AdminUserListItem, UserApprovalResponse,
    UserAuditLogResponse, UserAuditLogEntry
)
from src.routes.auth_routes import get_current_user, require_admin, log_user_action
from src.db.db_handler import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin - User Management"])

# =====================================================
# USER MANAGEMENT ENDPOINTS
# =====================================================

@router.get("/admin/users", response_model=AdminUserListResponse)
async def list_all_users(
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    role_filter: Optional[str] = Query(None, description="Filter by role: administrator, reviewer"),
    search: Optional[str] = Query(None, description="Search by name, email, or username"),
    limit: int = Query(50, le=100, description="Maximum number of users to return"),
    offset: int = Query(0, description="Number of users to skip"),
    current_user: dict = Depends(require_admin),
    db_handler = Depends(get_db)
):
    """Get list of all users (admin only)"""
    
    # Build query with filters
    where_clauses = []
    params = []
    param_count = 0
    
    if status_filter == "pending":
        where_clauses.append("is_approved = false")
    elif status_filter == "approved":
        where_clauses.append("is_approved = true")
    elif status_filter == "rejected":
        where_clauses.append("is_approved = false AND approved_by IS NOT NULL")
    
    if role_filter in ["administrator", "reviewer"]:
        param_count += 1
        where_clauses.append(f"role = ${param_count}")
        params.append(role_filter)
    
    if search:
        param_count += 1
        search_term = f"%{search.lower()}%"
        where_clauses.append(f"(LOWER(full_name) LIKE ${param_count} OR LOWER(email) LIKE ${param_count} OR LOWER(username) LIKE ${param_count})")
        params.append(search_term)
    
    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Get users with pagination
    param_count += 1
    params.append(limit)
    param_count += 1
    params.append(offset)
    
    users_query = f"""
        SELECT u.id, u.email, u.username, u.full_name, u.role, u.is_approved, 
               u.is_active, u.department, u.company, u.approved_by, u.approved_at,
               u.last_login, u.created_at,
               approver.full_name as approved_by_name
        FROM public.users u
        LEFT JOIN public.users approver ON approver.id = u.approved_by
        WHERE {where_clause}
        ORDER BY u.created_at DESC
        LIMIT ${param_count-1} OFFSET ${param_count}
    """
    
    users = await db_handler.fetch_all(users_query, *params)
    
    # Get counts for summary
    counts_query = f"""
        SELECT 
            COUNT(*) as total_count,
            COUNT(*) FILTER (WHERE is_approved = false AND approved_by IS NULL) as pending_count,
            COUNT(*) FILTER (WHERE is_approved = true AND is_active = true) as active_count
        FROM public.users u
        WHERE {where_clause.replace(f'LIMIT ${param_count-1} OFFSET ${param_count}', '')}
    """
    
    counts = await db_handler.fetch_one(counts_query, *(params[:-2]))  # Exclude limit/offset params
    
    return AdminUserListResponse(
        users=[AdminUserListItem(**dict(user)) for user in users],
        total_count=counts["total_count"],
        pending_count=counts["pending_count"],
        active_count=counts["active_count"]
    )

@router.post("/admin/users/create")
async def create_user(
    user_data: UserRegistrationRequest,
    request: Request,
    current_user: dict = Depends(require_admin),
    db_handler = Depends(get_db)
):
    """Create a new user (admin only) - auto-approved and active"""
    
    from src.services.auth_service import auth_service
    
    # Validate password strength
    password_validation = auth_service.validate_password_strength(user_data.password)
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
    """, user_data.email.lower(), user_data.username.lower())
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Hash password
    password_hash = auth_service.hash_password(user_data.password)
    
    # Create user record (auto-approved by admin)
    try:
        user_id = await db_handler.fetch_value("""
            INSERT INTO public.users (
                email, username, password_hash, full_name, department, 
                company, phone, role, is_approved, is_active,
                approved_by, approved_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, true, true, $9, $10)
            RETURNING id
        """, 
            user_data.email.lower(), user_data.username.lower(), password_hash,
            user_data.full_name, user_data.department, 
            user_data.company, user_data.phone,
            'reviewer',  # Default role, can be changed after creation
            current_user["id"], datetime.utcnow()
        )
        
        # Log admin action
        await log_user_action(
            "admin_created_user",
            current_user["id"],
            {
                "created_user_id": user_id,
                "email": user_data.email,
                "username": user_data.username,
                "full_name": user_data.full_name
            },
            request,
            db_handler
        )
        
        # Send welcome notification to new user
        await db_handler.execute("""
            INSERT INTO public.user_notifications (user_id, type, title, message, data)
            VALUES ($1, 'account_created', 'Welcome to SimplyInspect', $2, $3::jsonb)
        """, 
            user_id,
            f"Your account has been created by {current_user['full_name']}. You can now log in with your credentials.",
            json.dumps({"created_by": current_user["id"], "created_by_name": current_user["full_name"]})
        )
        
        return {
            "message": "User created successfully",
            "user_id": user_id,
            "email": user_data.email,
            "username": user_data.username
        }
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user. Please try again."
        )

@router.get("/admin/users/pending", response_model=AdminUserListResponse)
async def list_pending_users(
    current_user: dict = Depends(require_admin),
    db_handler = Depends(get_db)
):
    """Get list of users pending approval"""
    
    users = await db_handler.fetch_all("""
        SELECT id, email, username, full_name, role, is_approved, is_active,
               department, company, approved_by, approved_at, last_login, created_at
        FROM public.users 
        WHERE is_approved = false AND approved_by IS NULL
        ORDER BY created_at ASC
    """)
    
    total_count = len(users)
    
    return AdminUserListResponse(
        users=[AdminUserListItem(**dict(user)) for user in users],
        total_count=total_count,
        pending_count=total_count,
        active_count=0
    )

@router.put("/admin/users/{user_id}/approve", response_model=UserApprovalResponse)
async def approve_or_reject_user(
    user_id: int,
    approval_request: UserApprovalRequest,
    request: Request,
    current_user: dict = Depends(require_admin),
    db_handler = Depends(get_db)
):
    """Approve or reject a user registration"""
    
    # Check if user exists and is pending
    user_record = await db_handler.fetch_one("""
        SELECT id, email, username, full_name, is_approved, approved_by
        FROM public.users 
        WHERE id = $1
    """, user_id)
    
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user_record["is_approved"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already been approved"
        )
    
    if user_record["approved_by"] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already been processed"
        )
    
    # Update user approval status
    if approval_request.approve:
        await db_handler.execute("""
            UPDATE public.users 
            SET is_approved = true, approved_by = $1, approved_at = $2, updated_at = $3
            WHERE id = $4
        """, current_user["id"], datetime.utcnow(), datetime.utcnow(), user_id)
        
        action = "user_approved"
        message = f"User {user_record['full_name']} has been approved"
        
        # Send approval notification to user
        await db_handler.execute("""
            INSERT INTO public.user_notifications (user_id, type, title, message, data)
            VALUES ($1, 'user_approved', 'Account Approved', $2, $3::jsonb)
        """, 
            user_id,
            f"Your SimplyInspect account has been approved. You can now log in.",
            json.dumps({"approved_by": current_user["id"], "approved_by_name": current_user["full_name"]})
        )
        
    else:
        await db_handler.execute("""
            UPDATE public.users 
            SET approved_by = $1, rejection_reason = $2, updated_at = $3
            WHERE id = $4
        """, current_user["id"], approval_request.rejection_reason, datetime.utcnow(), user_id)
        
        action = "user_rejected"
        message = f"User {user_record['full_name']} has been rejected"
        
        # Send rejection notification to user
        await db_handler.execute("""
            INSERT INTO public.user_notifications (user_id, type, title, message, data)
            VALUES ($1, 'user_rejected', 'Account Rejected', $2, $3::jsonb)
        """, 
            user_id,
            f"Your SimplyInspect account registration has been rejected. {approval_request.rejection_reason or ''}",
            json.dumps({
                "rejected_by": current_user["id"], 
                "rejected_by_name": current_user["full_name"],
                "reason": approval_request.rejection_reason
            })
        )
    
    # Log admin action
    await log_user_action(
        action, 
        current_user["id"], 
        {
            "target_user_id": user_id,
            "target_user_email": user_record["email"],
            "approved": approval_request.approve,
            "rejection_reason": approval_request.rejection_reason
        },
        request,
        db_handler
    )
    
    return UserApprovalResponse(
        message=message,
        user_id=user_id,
        approved=approval_request.approve,
        approved_by=current_user["id"]
    )

@router.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdateRequest,
    request: Request,
    current_user: dict = Depends(require_admin),
    db_handler = Depends(get_db)
):
    """Update a user's role"""
    
    # Check if user exists
    user_record = await db_handler.fetch_one("""
        SELECT id, email, username, full_name, role
        FROM public.users 
        WHERE id = $1
    """, user_id)
    
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user_record["role"] == role_update.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User already has role '{role_update.role}'"
        )
    
    # Update role
    await db_handler.execute("""
        UPDATE public.users 
        SET role = $1, updated_at = $2
        WHERE id = $3
    """, role_update.role, datetime.utcnow(), user_id)
    
    # Log role change
    await log_user_action(
        "user_role_changed",
        current_user["id"],
        {
            "target_user_id": user_id,
            "target_user_email": user_record["email"],
            "old_role": user_record["role"],
            "new_role": role_update.role
        },
        request,
        db_handler
    )
    
    # Notify user of role change
    await db_handler.execute("""
        INSERT INTO public.user_notifications (user_id, type, title, message, data)
        VALUES ($1, 'role_changed', 'Role Updated', $2, $3::jsonb)
    """, 
        user_id,
        f"Your role has been changed to {role_update.role} by {current_user['full_name']}",
        json.dumps({
            "changed_by": current_user["id"],
            "changed_by_name": current_user["full_name"],
            "old_role": user_record["role"],
            "new_role": role_update.role
        })
    )
    
    return {
        "message": f"User role updated to {role_update.role}",
        "user_id": user_id,
        "new_role": role_update.role
    }

@router.put("/admin/users/{user_id}")
async def update_user(
    user_id: int,
    user_update: UserUpdateRequest,
    request: Request,
    current_user: dict = Depends(require_admin),
    db_handler = Depends(get_db)
):
    """Update user information"""
    
    # Check if user exists
    user_record = await db_handler.fetch_one("""
        SELECT id, email, full_name, is_active
        FROM public.users 
        WHERE id = $1
    """, user_id)
    
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Build update query dynamically
    update_fields = []
    params = []
    param_count = 0
    
    if user_update.full_name is not None:
        param_count += 1
        update_fields.append(f"full_name = ${param_count}")
        params.append(user_update.full_name)
    
    if user_update.department is not None:
        param_count += 1
        update_fields.append(f"department = ${param_count}")
        params.append(user_update.department)
    
    if user_update.company is not None:
        param_count += 1
        update_fields.append(f"company = ${param_count}")
        params.append(user_update.company)
    
    if user_update.phone is not None:
        param_count += 1
        update_fields.append(f"phone = ${param_count}")
        params.append(user_update.phone)
    
    if user_update.is_active is not None:
        param_count += 1
        update_fields.append(f"is_active = ${param_count}")
        params.append(user_update.is_active)
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Add updated_at and user_id
    param_count += 1
    update_fields.append(f"updated_at = ${param_count}")
    params.append(datetime.utcnow())
    
    param_count += 1
    params.append(user_id)
    
    # Execute update
    query = f"UPDATE public.users SET {', '.join(update_fields)} WHERE id = ${param_count}"
    await db_handler.execute(query, *params)
    
    # Log update
    await log_user_action(
        "user_updated",
        current_user["id"],
        {
            "target_user_id": user_id,
            "target_user_email": user_record["email"],
            "updated_fields": list(user_update.dict(exclude_unset=True).keys())
        },
        request,
        db_handler
    )
    
    return {"message": "User updated successfully", "user_id": user_id}

@router.delete("/admin/users/{user_id}")
async def deactivate_user(
    user_id: int,
    request: Request,
    current_user: dict = Depends(require_admin),
    db_handler = Depends(get_db)
):
    """Deactivate a user (soft delete)"""
    
    # Check if user exists
    user_record = await db_handler.fetch_one("""
        SELECT id, email, username, full_name, is_active
        FROM public.users 
        WHERE id = $1
    """, user_id)
    
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user_record["id"] == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    if not user_record["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already deactivated"
        )
    
    # Deactivate user
    await db_handler.execute("""
        UPDATE public.users 
        SET is_active = false, updated_at = $1
        WHERE id = $2
    """, datetime.utcnow(), user_id)
    
    # Invalidate all user sessions
    await db_handler.execute("""
        UPDATE public.user_sessions 
        SET is_active = false 
        WHERE user_id = $1
    """, user_id)
    
    # Log deactivation
    await log_user_action(
        "user_deactivated",
        current_user["id"],
        {
            "target_user_id": user_id,
            "target_user_email": user_record["email"]
        },
        request,
        db_handler
    )
    
    return {
        "message": f"User {user_record['full_name']} has been deactivated",
        "user_id": user_id
    }

# =====================================================
# AUDIT LOG ENDPOINTS
# =====================================================

@router.get("/admin/audit-logs", response_model=UserAuditLogResponse)
async def get_audit_logs(
    user_id: Optional[int] = Query(None, description="Filter by specific user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    limit: int = Query(100, le=500, description="Maximum number of logs to return"),
    offset: int = Query(0, description="Number of logs to skip"),
    current_user: dict = Depends(require_admin),
    db_handler = Depends(get_db)
):
    """Get audit logs (admin only)"""
    
    # Build query with filters
    where_clauses = []
    params = []
    param_count = 0
    
    if user_id:
        param_count += 1
        where_clauses.append(f"user_id = ${param_count}")
        params.append(user_id)
    
    if action:
        param_count += 1
        where_clauses.append(f"action = ${param_count}")
        params.append(action)
    
    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Add limit and offset
    param_count += 1
    params.append(limit)
    param_count += 1
    params.append(offset)
    
    logs = await db_handler.fetch_all(f"""
        SELECT id, user_id, action, details, ip_address, user_agent, created_at
        FROM public.user_audit_log
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_count-1} OFFSET ${param_count}
    """, *params)
    
    # Get total count
    total_count = await db_handler.fetch_value(f"""
        SELECT COUNT(*) FROM public.user_audit_log WHERE {where_clause}
    """, *(params[:-2]))  # Exclude limit/offset
    
    return UserAuditLogResponse(
        logs=[UserAuditLogEntry(**dict(log)) for log in logs],
        total_count=total_count
    )

# =====================================================
# SYSTEM STATUS ENDPOINTS
# =====================================================

@router.get("/admin/system/stats")
async def get_system_stats(
    current_user: dict = Depends(require_admin),
    db_handler = Depends(get_db)
):
    """Get system statistics"""
    
    stats = await db_handler.fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM public.users) as total_users,
            (SELECT COUNT(*) FROM public.users WHERE is_active = true) as active_users,
            (SELECT COUNT(*) FROM public.users WHERE is_approved = false AND approved_by IS NULL) as pending_users,
            (SELECT COUNT(*) FROM public.users WHERE role = 'administrator') as admin_users,
            (SELECT COUNT(*) FROM public.user_sessions WHERE is_active = true) as active_sessions,
            (SELECT COUNT(*) FROM public.sharepoint_permissions) as sharepoint_permissions,
            (SELECT COUNT(*) FROM public."ExternalAuditLogs") as audit_logs
    """)
    
    return dict(stats)

# =====================================================
# HEALTH CHECK
# =====================================================

@router.get("/admin/health")
async def admin_health_check():
    """Health check for admin service"""
    return {
        "status": "healthy",
        "service": "admin",
        "timestamp": datetime.utcnow().isoformat()
    }