"""
Permission Baseline Service

Manages SharePoint permission baselines for change detection and compliance.
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.db.db_handler import DatabaseHandler

logger = logging.getLogger(__name__)

class BaselineService:
    """Service for managing permission baselines"""
    
    def __init__(self, db_handler: DatabaseHandler):
        self.db = db_handler
        
    async def create_baseline(
        self,
        site_id: str,
        site_url: str,
        baseline_name: str,
        created_by: str,
        created_by_email: str,
        baseline_description: Optional[str] = None,
        set_as_active: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new permission baseline for a site
        
        Args:
            site_id: SharePoint site ID
            site_url: SharePoint site URL
            baseline_name: Name for the baseline
            created_by: User ID who created the baseline
            created_by_email: Email of the user who created the baseline
            baseline_description: Optional description
            set_as_active: Whether to set this as the active baseline
            
        Returns:
            Created baseline record
        """
        try:
            logger.info(f"Creating baseline '{baseline_name}' for site {site_id}")
            
            # Fetch current permissions for the site
            permissions_query = """
                SELECT 
                    site_id,
                    site_url,
                    resource_id,
                    resource_name,
                    resource_type,
                    resource_url,
                    permission_type,
                    permission_level,
                    principal_id,
                    principal_name,
                    principal_email,
                    principal_type,
                    is_human,
                    has_broken_inheritance,
                    inherited_from_resource,
                    parent_resource_id,
                    parent_resource_name,
                    parent_resource_type,
                    inherited_from_parent
                FROM sharepoint_permissions
                WHERE site_id = $1
                ORDER BY resource_id, principal_id
            """
            
            permissions = await self.db.fetch_all(permissions_query, site_id)
            
            if not permissions:
                raise ValueError(f"No permissions found for site {site_id}")
            
            # Create baseline data structure
            baseline_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "site_id": site_id,
                "site_url": site_url,
                "total_permissions": len(permissions),
                "permissions": permissions
            }
            
            # Insert baseline record
            insert_query = """
                INSERT INTO permission_baselines (
                    site_id,
                    site_url,
                    baseline_name,
                    baseline_description,
                    baseline_data,
                    created_by,
                    created_by_email,
                    is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            """
            
            baseline = await self.db.fetch_one(
                insert_query,
                site_id,
                site_url,
                baseline_name,
                baseline_description,
                json.dumps(baseline_data),
                created_by,
                created_by_email,
                set_as_active
            )
            
            logger.info(f"Successfully created baseline with ID {baseline['id']}")
            
            # Calculate statistics
            stats = self._calculate_baseline_statistics(permissions)
            baseline['statistics'] = stats
            
            return baseline
            
        except Exception as e:
            logger.error(f"Error creating baseline: {e}")
            raise
    
    async def get_baselines(
        self,
        site_id: Optional[str] = None,
        include_inactive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get baselines, optionally filtered by site
        
        Args:
            site_id: Optional site ID filter
            include_inactive: Whether to include inactive baselines
            
        Returns:
            List of baseline records
        """
        try:
            query = """
                SELECT 
                    id,
                    site_id,
                    site_url,
                    baseline_name,
                    baseline_description,
                    created_by,
                    created_by_email,
                    created_at,
                    updated_at,
                    is_active,
                    jsonb_array_length(baseline_data->'permissions') as permission_count
                FROM permission_baselines
                WHERE 1=1
            """
            params = []
            param_counter = 1
            
            if site_id:
                query += f" AND site_id = ${param_counter}"
                params.append(site_id)
                param_counter += 1
            
            if not include_inactive:
                query += f" AND is_active = true"
            
            query += " ORDER BY created_at DESC"
            
            baselines = await self.db.fetch_all(query, *params)
            return baselines
            
        except Exception as e:
            logger.error(f"Error fetching baselines: {e}")
            raise
    
    async def get_baseline_by_id(self, baseline_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific baseline by ID
        
        Args:
            baseline_id: Baseline ID
            
        Returns:
            Baseline record with full data
        """
        try:
            query = """
                SELECT *
                FROM permission_baselines
                WHERE id = $1
            """
            
            baseline = await self.db.fetch_one(query, baseline_id)
            
            if baseline and baseline.get('baseline_data'):
                # Parse the JSON data
                baseline['baseline_data'] = json.loads(baseline['baseline_data']) if isinstance(baseline['baseline_data'], str) else baseline['baseline_data']
                
                # Calculate statistics
                permissions = baseline['baseline_data'].get('permissions', [])
                baseline['statistics'] = self._calculate_baseline_statistics(permissions)
            
            return baseline
            
        except Exception as e:
            logger.error(f"Error fetching baseline {baseline_id}: {e}")
            raise
    
    async def activate_baseline(self, baseline_id: int) -> Dict[str, Any]:
        """
        Set a baseline as active (deactivating others for the same site)
        
        Args:
            baseline_id: Baseline ID to activate
            
        Returns:
            Updated baseline record
        """
        try:
            # The trigger will handle deactivating other baselines
            query = """
                UPDATE permission_baselines
                SET is_active = true
                WHERE id = $1
                RETURNING *
            """
            
            baseline = await self.db.fetch_one(query, baseline_id)
            
            if not baseline:
                raise ValueError(f"Baseline {baseline_id} not found")
            
            logger.info(f"Activated baseline {baseline_id} for site {baseline['site_id']}")
            return baseline
            
        except Exception as e:
            logger.error(f"Error activating baseline {baseline_id}: {e}")
            raise
    
    async def deactivate_baseline(self, baseline_id: int) -> Dict[str, Any]:
        """
        Deactivate a baseline
        
        Args:
            baseline_id: Baseline ID to deactivate
            
        Returns:
            Updated baseline record
        """
        try:
            query = """
                UPDATE permission_baselines
                SET is_active = false
                WHERE id = $1
                RETURNING *
            """
            
            baseline = await self.db.fetch_one(query, baseline_id)
            
            if not baseline:
                raise ValueError(f"Baseline {baseline_id} not found")
            
            logger.info(f"Deactivated baseline {baseline_id}")
            return baseline
            
        except Exception as e:
            logger.error(f"Error deactivating baseline {baseline_id}: {e}")
            raise
    
    async def delete_baseline(self, baseline_id: int) -> bool:
        """
        Delete a baseline
        
        Args:
            baseline_id: Baseline ID to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            query = """
                DELETE FROM permission_baselines
                WHERE id = $1
                RETURNING id
            """
            
            result = await self.db.fetch_one(query, baseline_id)
            
            if not result:
                raise ValueError(f"Baseline {baseline_id} not found")
            
            logger.info(f"Deleted baseline {baseline_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting baseline {baseline_id}: {e}")
            raise
    
    async def compare_with_current(self, baseline_id: int) -> Dict[str, Any]:
        """
        Compare a baseline with current permissions
        
        Args:
            baseline_id: Baseline ID to compare
            
        Returns:
            Comparison results with changes
        """
        try:
            # Get baseline
            baseline = await self.get_baseline_by_id(baseline_id)
            if not baseline:
                raise ValueError(f"Baseline {baseline_id} not found")
            
            site_id = baseline['site_id']
            baseline_permissions = baseline['baseline_data'].get('permissions', [])
            
            # Get current permissions
            current_query = """
                SELECT 
                    site_id,
                    site_url,
                    resource_id,
                    resource_name,
                    resource_type,
                    resource_url,
                    permission_type,
                    permission_level,
                    principal_id,
                    principal_name,
                    principal_email,
                    principal_type,
                    is_human,
                    has_broken_inheritance,
                    inherited_from_resource,
                    parent_resource_id,
                    parent_resource_name,
                    parent_resource_type,
                    inherited_from_parent
                FROM sharepoint_permissions
                WHERE site_id = $1
                ORDER BY resource_id, principal_id
            """
            
            current_permissions = await self.db.fetch_all(current_query, site_id)
            
            # Perform comparison
            comparison = self._compare_permissions(baseline_permissions, current_permissions)
            
            # Store comparison in cache
            await self._cache_comparison(baseline_id, site_id, comparison)
            
            return {
                "baseline_id": baseline_id,
                "baseline_name": baseline['baseline_name'],
                "baseline_created_at": baseline['created_at'],
                "comparison_date": datetime.utcnow().isoformat(),
                "site_id": site_id,
                "site_url": baseline['site_url'],
                "changes": comparison
            }
            
        except Exception as e:
            logger.error(f"Error comparing baseline {baseline_id}: {e}")
            raise
    
    def _calculate_baseline_statistics(self, permissions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics for a set of permissions"""
        if not permissions:
            return {
                "total_permissions": 0,
                "unique_resources": 0,
                "unique_principals": 0,
                "unique_users": 0,
                "unique_groups": 0,
                "broken_inheritance_count": 0
            }
        
        resources = set()
        principals = set()
        users = set()
        groups = set()
        broken_inheritance = set()
        
        for perm in permissions:
            resources.add(perm.get('resource_id'))
            principals.add(perm.get('principal_id'))
            
            if perm.get('principal_type') == 'User':
                users.add(perm.get('principal_id'))
            elif perm.get('principal_type') == 'Group':
                groups.add(perm.get('principal_id'))
            
            if perm.get('has_broken_inheritance'):
                broken_inheritance.add(perm.get('resource_id'))
        
        return {
            "total_permissions": len(permissions),
            "unique_resources": len(resources),
            "unique_principals": len(principals),
            "unique_users": len(users),
            "unique_groups": len(groups),
            "broken_inheritance_count": len(broken_inheritance),
            "permission_levels": self._count_permission_levels(permissions)
        }
    
    def _count_permission_levels(self, permissions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count occurrences of each permission level"""
        levels = {}
        for perm in permissions:
            level = perm.get('permission_level', 'Unknown')
            levels[level] = levels.get(level, 0) + 1
        return levels
    
    def _compare_permissions(
        self,
        baseline_perms: List[Dict[str, Any]],
        current_perms: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare baseline permissions with current permissions
        
        Returns detailed change information
        """
        # Create permission keys for comparison
        def make_key(perm):
            return f"{perm.get('resource_id')}|{perm.get('principal_id')}"
        
        baseline_dict = {make_key(p): p for p in baseline_perms}
        current_dict = {make_key(p): p for p in current_perms}
        
        baseline_keys = set(baseline_dict.keys())
        current_keys = set(current_dict.keys())
        
        # Find changes
        added_keys = current_keys - baseline_keys
        removed_keys = baseline_keys - current_keys
        common_keys = baseline_keys & current_keys
        
        added = [current_dict[k] for k in added_keys]
        removed = [baseline_dict[k] for k in removed_keys]
        modified = []
        
        # Check for modifications in common permissions
        for key in common_keys:
            baseline_perm = baseline_dict[key]
            current_perm = current_dict[key]
            
            # Check if permission level or inheritance changed
            if (baseline_perm.get('permission_level') != current_perm.get('permission_level') or
                baseline_perm.get('has_broken_inheritance') != current_perm.get('has_broken_inheritance')):
                modified.append({
                    "resource_id": current_perm.get('resource_id'),
                    "resource_name": current_perm.get('resource_name'),
                    "principal_id": current_perm.get('principal_id'),
                    "principal_name": current_perm.get('principal_name'),
                    "old_permission_level": baseline_perm.get('permission_level'),
                    "new_permission_level": current_perm.get('permission_level'),
                    "old_inheritance": baseline_perm.get('has_broken_inheritance'),
                    "new_inheritance": current_perm.get('has_broken_inheritance')
                })
        
        return {
            "summary": {
                "total_baseline": len(baseline_perms),
                "total_current": len(current_perms),
                "added_count": len(added),
                "removed_count": len(removed),
                "modified_count": len(modified),
                "unchanged_count": len(common_keys) - len(modified)
            },
            "added_permissions": added,
            "removed_permissions": removed,
            "modified_permissions": modified
        }
    
    async def _cache_comparison(
        self,
        baseline_id: int,
        site_id: str,
        comparison: Dict[str, Any]
    ) -> None:
        """Cache comparison results for performance"""
        try:
            query = """
                INSERT INTO baseline_comparison_cache (
                    baseline_id,
                    site_id,
                    total_permissions_baseline,
                    total_permissions_current,
                    added_count,
                    removed_count,
                    modified_count,
                    comparison_summary
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (baseline_id, comparison_date) DO NOTHING
            """
            
            summary = comparison.get('summary', {})
            await self.db.execute(
                query,
                baseline_id,
                site_id,
                summary.get('total_baseline', 0),
                summary.get('total_current', 0),
                summary.get('added_count', 0),
                summary.get('removed_count', 0),
                summary.get('modified_count', 0),
                json.dumps(summary)
            )
            
        except Exception as e:
            logger.warning(f"Failed to cache comparison results: {e}")
            # Don't fail the comparison if caching fails