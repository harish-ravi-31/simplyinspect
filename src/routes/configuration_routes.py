"""
Configuration Management Routes for SimplyInspect
Handles Azure credentials and application settings
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from src.db.db_handler import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Configuration"])

class AzureConfiguration(BaseModel):
    tenant_id: str = Field(..., description="Azure Tenant ID")
    client_id: str = Field(..., description="Azure Application (Client) ID")
    client_secret: Optional[str] = Field(None, description="Azure Client Secret")

class ConfigurationResponse(BaseModel):
    tenant_id: str
    client_id: str
    client_secret_configured: bool
    client_secret_masked: str

@router.get("/configuration/azure")
async def get_azure_configuration(db_handler = Depends(get_db)):
    """Get current Azure configuration with masked client secret"""
    try:
        config = await db_handler.fetch_one("""
            SELECT 
                "TenantId",
                "ClientId",
                "ClientSecret"
            FROM public."Configurations"
            WHERE "Name" = 'Archive'
        """)
        
        if not config:
            # Return empty configuration if none exists
            return ConfigurationResponse(
                tenant_id="",
                client_id="",
                client_secret_configured=False,
                client_secret_masked=""
            )
        
        # Mask the client secret
        secret_configured = bool(config['ClientSecret'] and len(config['ClientSecret']) > 0)
        secret_masked = ""
        if secret_configured:
            # Show first 4 and last 4 characters with asterisks in between
            secret = config['ClientSecret']
            if len(secret) > 8:
                secret_masked = f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"
            else:
                secret_masked = '*' * len(secret)
        
        return ConfigurationResponse(
            tenant_id=config['TenantId'] or "",
            client_id=config['ClientId'] or "",
            client_secret_configured=secret_configured,
            client_secret_masked=secret_masked
        )
        
    except Exception as e:
        logger.error(f"Failed to get Azure configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/configuration/azure")
async def update_azure_configuration(
    config: AzureConfiguration,
    db_handler = Depends(get_db)
):
    """Update Azure configuration in database"""
    try:
        # Check if configuration exists
        existing = await db_handler.fetch_one("""
            SELECT "Id" FROM public."Configurations" WHERE "Name" = 'Archive'
        """)
        
        if existing:
            # Update existing configuration
            if config.client_secret and not config.client_secret.startswith('*'):
                # Update with new client secret
                await db_handler.execute("""
                    UPDATE public."Configurations"
                    SET "TenantId" = $1,
                        "ClientId" = $2,
                        "ClientSecret" = $3
                    WHERE "Name" = 'Archive'
                """, config.tenant_id, config.client_id, config.client_secret)
            else:
                # Update without changing client secret
                await db_handler.execute("""
                    UPDATE public."Configurations"
                    SET "TenantId" = $1,
                        "ClientId" = $2
                    WHERE "Name" = 'Archive'
                """, config.tenant_id, config.client_id)
        else:
            # Insert new configuration
            await db_handler.execute("""
                INSERT INTO public."Configurations" (
                    "Name", "TenantId", "ClientId", "ClientSecret",
                    "SharePointUrl", "GraphApiScopes", "PurviewEndpoint",
                    "Settings", "CreationTime"
                ) VALUES (
                    'Archive', $1, $2, $3, '',
                    'https://graph.microsoft.com/.default',
                    'https://manage.office.com',
                    '{"sync_interval_hours": 24}'::jsonb,
                    CURRENT_TIMESTAMP
                )
            """, config.tenant_id, config.client_id, config.client_secret or '')
        
        logger.info(f"Azure configuration updated for tenant: {config.tenant_id}")
        return {"status": "success", "message": "Configuration updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update Azure configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configuration/test")
async def test_azure_configuration(db_handler = Depends(get_db)):
    """Test Azure configuration by attempting to get an access token"""
    try:
        import aiohttp
        
        # Get configuration
        config = await db_handler.fetch_one("""
            SELECT "TenantId", "ClientId", "ClientSecret"
            FROM public."Configurations"
            WHERE "Name" = 'Archive'
        """)
        
        if not config or not all([config['TenantId'], config['ClientId'], config['ClientSecret']]):
            return {
                "status": "error",
                "message": "Azure configuration is incomplete"
            }
        
        # Try to get an access token
        token_url = f"https://login.microsoftonline.com/{config['TenantId']}/oauth2/v2.0/token"
        token_data = {
            'client_id': config['ClientId'],
            'client_secret': config['ClientSecret'],
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=token_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if 'access_token' in data:
                        return {
                            "status": "success",
                            "message": "Azure configuration is valid and working"
                        }
                else:
                    error_data = await resp.json()
                    return {
                        "status": "error",
                        "message": f"Authentication failed: {error_data.get('error_description', 'Unknown error')}"
                    }
        
    except Exception as e:
        logger.error(f"Failed to test Azure configuration: {e}")
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}"
        }