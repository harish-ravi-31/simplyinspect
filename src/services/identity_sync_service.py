"""
Identity Sync Service
Syncs users and groups from Microsoft Entra ID to the Identities table
"""

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
import aiohttp
import asyncpg
import json

logger = logging.getLogger(__name__)


class IdentitySyncService:
    """Service for syncing identities from Entra ID"""
    
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
                self.token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=55)
                return self.access_token
    
    async def sync_all_groups_and_members(self) -> Dict[str, Any]:
        """Sync all groups and their members from Entra ID"""
        try:
            logger.info("Starting comprehensive group and member sync from Entra ID")
            
            # Get access token
            access_token = await self.get_access_token()
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            results = {
                'groups_synced': 0,
                'users_synced': 0,
                'memberships_created': 0,
                'errors': []
            }
            
            async with aiohttp.ClientSession() as session:
                # Get all groups
                groups_url = f"{self.graph_base_url}/groups?$select=id,displayName,mail,description,groupTypes&$top=999"
                all_groups = []
                
                while groups_url:
                    async with session.get(groups_url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            all_groups.extend(data.get('value', []))
                            groups_url = data.get('@odata.nextLink')
                        else:
                            error_text = await resp.text()
                            logger.error(f"Failed to get groups: {error_text}")
                            break
                
                logger.info(f"Found {len(all_groups)} groups in Entra ID")
                
                # Process each group
                for group in all_groups:
                    try:
                        group_id = group['id']
                        group_name = group.get('displayName', '')
                        
                        # Insert/update group in Identities table as a group entity
                        await self.db_handler.execute("""
                            INSERT INTO "Identities" ("ClientId", "Name", "Email", "Roles", "TenantId")
                            VALUES ($1, $2, $3, 'group', $4)
                            ON CONFLICT ("ClientId") 
                            DO UPDATE SET 
                                "Name" = EXCLUDED."Name",
                                "Email" = EXCLUDED."Email",
                                "Roles" = EXCLUDED."Roles"
                        """, group_id, group_name, group.get('mail', ''), config['TenantId'])
                        
                        results['groups_synced'] += 1
                        
                        # Get group members
                        members_url = f"{self.graph_base_url}/groups/{group_id}/members?$select=id,displayName,mail,userPrincipalName,jobTitle,department,officeLocation&$top=999"
                        
                        while members_url:
                            async with session.get(members_url, headers=headers) as resp:
                                if resp.status == 200:
                                    members_data = await resp.json()
                                    members = members_data.get('value', [])
                                    
                                    for member in members:
                                        member_type = member.get('@odata.type', '').replace('#microsoft.graph.', '')
                                        
                                        if 'user' in member_type.lower():
                                            # Insert/update user in Identities table
                                            await self.db_handler.execute("""
                                                INSERT INTO "Identities" ("ClientId", "Name", "Email", "Roles", "TenantId")
                                                VALUES ($1, $2, $3, 'user', $4)
                                                ON CONFLICT ("ClientId") 
                                                DO UPDATE SET 
                                                    "Name" = EXCLUDED."Name",
                                                    "Email" = EXCLUDED."Email"
                                            """, 
                                                member.get('id', ''),
                                                member.get('displayName', ''),
                                                member.get('mail') or member.get('userPrincipalName', ''),
                                                config['TenantId']
                                            )
                                            results['users_synced'] += 1
                                        
                                        # Store membership in group_memberships table
                                        await self.db_handler.execute("""
                                            INSERT INTO group_memberships (
                                                group_id, group_name, group_type, 
                                                member_id, member_name, member_email, 
                                                member_type, member_upn, job_title, 
                                                department, office_location, is_active, metadata
                                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, TRUE, $12)
                                            ON CONFLICT (group_id, member_id) 
                                            DO UPDATE SET 
                                                member_name = EXCLUDED.member_name,
                                                member_email = EXCLUDED.member_email,
                                                is_active = TRUE,
                                                updated_at = CURRENT_TIMESTAMP
                                        """, 
                                            group_id,
                                            group_name,
                                            'entra',
                                            member.get('id', ''),
                                            member.get('displayName', ''),
                                            member.get('mail', ''),
                                            member_type or 'user',
                                            member.get('userPrincipalName', ''),
                                            member.get('jobTitle'),
                                            member.get('department'),
                                            member.get('officeLocation'),
                                            member
                                        )
                                        results['memberships_created'] += 1
                                    
                                    members_url = members_data.get('@odata.nextLink')
                                else:
                                    logger.warning(f"Failed to get members for group {group_id}")
                                    break
                        
                    except Exception as e:
                        logger.error(f"Error processing group {group.get('displayName', group_id)}: {e}")
                        results['errors'].append(str(e))
            
            logger.info(f"Sync completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to sync identities: {e}")
            return {
                'error': str(e),
                'groups_synced': 0,
                'users_synced': 0
            }
    
    async def get_group_members_from_cache(self, group_identifier: str) -> Dict[str, Any]:
        """Get group members from cache, supporting both Entra IDs and SharePoint group names"""
        
        # First check if this is a GUID (Entra ID)
        is_guid = False
        try:
            # Simple GUID validation
            if len(group_identifier) == 36 and group_identifier.count('-') == 4:
                is_guid = True
        except:
            pass
        
        if is_guid:
            # Look up by group_id in group_memberships
            members = await self.db_handler.fetch_all("""
                SELECT * FROM group_memberships 
                WHERE group_id = $1 AND is_active = TRUE
                ORDER BY member_type, member_name
            """, group_identifier)
            
            group_info = await self.db_handler.fetch_one("""
                SELECT "Name" as name, "Email" as email 
                FROM "Identities" 
                WHERE "ClientId" = $1 AND "Roles" = 'group'
            """, group_identifier)
        else:
            # Try to decode base64 group name
            import base64
            try:
                # Add padding if needed
                padding = 4 - (len(group_identifier) % 4)
                if padding != 4:
                    group_identifier += '=' * padding
                group_name = base64.b64decode(group_identifier).decode('utf-8')
            except:
                group_name = group_identifier
            
            # Look up by group name
            members = await self.db_handler.fetch_all("""
                SELECT * FROM group_memberships 
                WHERE group_name = $1 AND is_active = TRUE
                ORDER BY member_type, member_name
            """, group_name)
            
            group_info = await self.db_handler.fetch_one("""
                SELECT "Name" as name, "Email" as email 
                FROM "Identities" 
                WHERE "Name" = $1 AND "Roles" = 'group'
            """, group_name)
        
        # Format response
        formatted_members = []
        for m in members:
            formatted_members.append({
                "id": m.get('member_id', ''),
                "displayName": m.get('member_name', ''),
                "email": m.get('member_email', ''),
                "userPrincipalName": m.get('member_upn', ''),
                "memberType": m.get('member_type', 'user'),
                "jobTitle": m.get('job_title', ''),
                "department": m.get('department', ''),
                "officeLocation": m.get('office_location', '')
            })
        
        return {
            'group': {
                'id': group_identifier,
                'name': group_info['name'] if group_info else group_name if not is_guid else group_identifier,
                'email': group_info['email'] if group_info else None
            },
            'members': formatted_members,
            'totalMembers': len(formatted_members),
            'source': 'cache'
        }