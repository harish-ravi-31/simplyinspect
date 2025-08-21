"""
Group Membership Sync Service
Fetches and caches group memberships from Microsoft Entra ID (Azure AD)
"""

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
import aiohttp
import asyncpg

logger = logging.getLogger(__name__)


class GroupSyncService:
    """Service for syncing group memberships from Entra ID"""
    
    def __init__(self, db_handler):
        self.db_handler = db_handler
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        self.access_token = None
        self.token_expires_at = None
    
    async def get_access_token(self) -> str:
        """Get or refresh Microsoft Graph access token"""
        if self.access_token and self.token_expires_at and self.token_expires_at > datetime.now(timezone.utc):
            return self.access_token
        
        # Get Azure credentials from configuration
        config_query = """
        SELECT "TenantId", "ClientId", "ClientSecret"
        FROM public."Configurations" 
        WHERE "Name" = 'Archive'
        """
        config = await self.db_handler.fetch_one(config_query)
        
        if not config:
            raise Exception("Azure credentials not found in configuration")
        
        # Get new access token
        token_url = f"https://login.microsoftonline.com/{config['TenantId']}/oauth2/v2.0/token"
        token_data = {
            'client_id': config["ClientId"],
            'client_secret': config["ClientSecret"],
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=token_data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Failed to get access token: {error_text}")
                
                token_response = await resp.json()
                self.access_token = token_response['access_token']
                # Token expires in 1 hour, refresh 5 minutes before
                self.token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=55)
                return self.access_token
    
    async def sync_group_members(self, group_id: str, group_name: Optional[str] = None) -> Dict[str, Any]:
        """Sync members for a specific group from Entra ID"""
        try:
            logger.info(f"Starting sync for group {group_id} ({group_name})")
            
            # Update sync status to syncing
            await self.db_handler.execute("""
                INSERT INTO group_sync_status (group_id, group_name, sync_status, last_sync_at)
                VALUES ($1, $2, 'syncing', CURRENT_TIMESTAMP)
                ON CONFLICT (group_id) 
                DO UPDATE SET 
                    sync_status = 'syncing',
                    last_sync_at = CURRENT_TIMESTAMP,
                    error_message = NULL
            """, group_id, group_name)
            
            # Get access token
            access_token = await self.get_access_token()
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            members = []
            member_count = 0
            
            # Try to get group details first
            group_url = f"{self.graph_base_url}/groups/{group_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(group_url, headers=headers) as resp:
                    if resp.status == 200:
                        group_data = await resp.json()
                        group_name = group_data.get('displayName', group_name)
                        group_type = 'microsoft365' if group_data.get('groupTypes') and 'Unified' in group_data.get('groupTypes', []) else 'entra'
                    else:
                        logger.warning(f"Could not fetch group details for {group_id}: {resp.status}")
                        group_type = 'entra'
                
                # Get group members with pagination
                members_url = f"{self.graph_base_url}/groups/{group_id}/members?$select=id,displayName,mail,userPrincipalName,jobTitle,department,officeLocation,accountEnabled&$top=999"
                
                while members_url:
                    async with session.get(members_url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            members.extend(data.get('value', []))
                            members_url = data.get('@odata.nextLink')  # Handle pagination
                        elif resp.status == 404:
                            # Group might be a SharePoint group, try alternative approach
                            logger.info(f"Group {group_id} not found in Entra ID, might be SharePoint-only")
                            
                            # Mark as completed with 0 members
                            await self.db_handler.execute("""
                                UPDATE group_sync_status 
                                SET sync_status = 'completed',
                                    member_count = 0,
                                    updated_at = CURRENT_TIMESTAMP,
                                    next_sync_at = CURRENT_TIMESTAMP + INTERVAL '24 hours',
                                    error_message = 'Group not found in Entra ID (might be SharePoint-only)'
                                WHERE group_id = $1
                            """, group_id)
                            
                            return {
                                'success': False,
                                'group_id': group_id,
                                'message': 'Group not found in Entra ID',
                                'member_count': 0
                            }
                        else:
                            error_text = await resp.text()
                            raise Exception(f"Failed to get members: {resp.status} - {error_text}")
            
            # Clear existing members for this group
            await self.db_handler.execute("""
                UPDATE group_memberships 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE group_id = $1
            """, group_id)
            
            # Insert new members
            for member in members:
                member_type = member.get('@odata.type', '').replace('#microsoft.graph.', '')
                if not member_type:
                    if 'userPrincipalName' in member:
                        member_type = 'user'
                    elif 'groupTypes' in member:
                        member_type = 'group'
                    else:
                        member_type = 'unknown'
                
                await self.db_handler.execute("""
                    INSERT INTO group_memberships (
                        group_id, group_name, group_type, member_id, member_name, 
                        member_email, member_type, member_upn, job_title, 
                        department, office_location, is_active, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, TRUE, $12)
                    ON CONFLICT (group_id, member_id) 
                    DO UPDATE SET 
                        member_name = EXCLUDED.member_name,
                        member_email = EXCLUDED.member_email,
                        member_upn = EXCLUDED.member_upn,
                        job_title = EXCLUDED.job_title,
                        department = EXCLUDED.department,
                        office_location = EXCLUDED.office_location,
                        is_active = TRUE,
                        updated_at = CURRENT_TIMESTAMP,
                        metadata = EXCLUDED.metadata
                """, 
                    group_id, 
                    group_name,
                    group_type,
                    member.get('id', ''),
                    member.get('displayName', ''),
                    member.get('mail', ''),
                    member_type,
                    member.get('userPrincipalName', ''),
                    member.get('jobTitle'),
                    member.get('department'),
                    member.get('officeLocation'),
                    member  # Store full member data as JSONB
                )
                member_count += 1
            
            # Update sync status
            await self.db_handler.execute("""
                UPDATE group_sync_status 
                SET sync_status = 'completed',
                    member_count = $2,
                    updated_at = CURRENT_TIMESTAMP,
                    next_sync_at = CURRENT_TIMESTAMP + INTERVAL '24 hours'
                WHERE group_id = $1
            """, group_id, member_count)
            
            logger.info(f"Successfully synced {member_count} members for group {group_id}")
            
            return {
                'success': True,
                'group_id': group_id,
                'group_name': group_name,
                'member_count': member_count
            }
            
        except Exception as e:
            logger.error(f"Failed to sync group {group_id}: {e}")
            
            # Update sync status with error
            await self.db_handler.execute("""
                UPDATE group_sync_status 
                SET sync_status = 'failed',
                    error_message = $2,
                    updated_at = CURRENT_TIMESTAMP,
                    next_sync_at = CURRENT_TIMESTAMP + INTERVAL '1 hour'
                WHERE group_id = $1
            """, group_id, str(e))
            
            return {
                'success': False,
                'group_id': group_id,
                'error': str(e)
            }
    
    async def get_cached_group_members(self, group_id: str) -> Dict[str, Any]:
        """Get cached group members from database"""
        # Check if we have cached data
        sync_status = await self.db_handler.fetch_one("""
            SELECT * FROM group_sync_status WHERE group_id = $1
        """, group_id)
        
        # If never synced or stale (>24 hours), trigger sync
        should_sync = False
        if not sync_status:
            should_sync = True
        elif sync_status['last_sync_at']:
            age = datetime.now(timezone.utc) - sync_status['last_sync_at'].replace(tzinfo=timezone.utc)
            if age > timedelta(hours=24):
                should_sync = True
        else:
            should_sync = True
        
        if should_sync:
            # Get group name from SharePoint permissions if available
            group_info = await self.db_handler.fetch_one("""
                SELECT DISTINCT principal_name 
                FROM sharepoint_permissions 
                WHERE principal_id = $1 
                LIMIT 1
            """, group_id)
            
            group_name = group_info['principal_name'] if group_info else None
            
            # Trigger async sync (don't wait for it)
            asyncio.create_task(self.sync_group_members(group_id, group_name))
            
            # Return message that sync is in progress
            return {
                'group_id': group_id,
                'syncing': True,
                'members': [],
                'message': 'Group membership sync initiated. Please refresh in a few moments.'
            }
        
        # Get cached members
        members = await self.db_handler.fetch_all("""
            SELECT * FROM group_memberships 
            WHERE group_id = $1 AND is_active = TRUE
            ORDER BY member_type, member_name
        """, group_id)
        
        # Convert asyncpg Records to proper dicts
        members_list = []
        for m in members:
            member_dict = dict(m)
            # Ensure all expected fields exist with defaults
            member_dict.setdefault('member_id', '')
            member_dict.setdefault('member_name', '')
            member_dict.setdefault('member_email', '')
            member_dict.setdefault('member_upn', '')
            member_dict.setdefault('member_type', 'user')
            member_dict.setdefault('job_title', '')
            member_dict.setdefault('department', '')
            member_dict.setdefault('office_location', '')
            members_list.append(member_dict)
        
        return {
            'group_id': group_id,
            'group_name': sync_status['group_name'] if sync_status else None,
            'members': members_list,
            'last_sync': sync_status['last_sync_at'].isoformat() if sync_status and sync_status['last_sync_at'] else None,
            'member_count': len(members_list)
        }
    
    async def sync_all_sharepoint_groups(self) -> Dict[str, Any]:
        """Sync all SharePoint groups found in permissions table"""
        # Get all unique groups from SharePoint permissions
        groups = await self.db_handler.fetch_all("""
            SELECT DISTINCT principal_id, principal_name 
            FROM sharepoint_permissions 
            WHERE principal_type = 'group'
            ORDER BY principal_name
        """)
        
        results = {
            'total': len(groups),
            'success': 0,
            'failed': 0,
            'groups': []
        }
        
        for group in groups:
            result = await self.sync_group_members(group['principal_id'], group['principal_name'])
            if result['success']:
                results['success'] += 1
            else:
                results['failed'] += 1
            results['groups'].append(result)
        
        return results
    
    async def get_sync_status(self) -> List[Dict[str, Any]]:
        """Get sync status for all groups"""
        status = await self.db_handler.fetch_all("""
            SELECT * FROM group_sync_status 
            ORDER BY last_sync_at DESC
        """)
        return [dict(s) for s in status]