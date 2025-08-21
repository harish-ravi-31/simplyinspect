"""
Startup configuration for SimplyInspect
Runs database migrations and ensures configuration exists
"""

import os
import asyncio
import logging
from src.db.db_handler import get_db_handler
from src.db.init_database import DatabaseInitializer

logger = logging.getLogger(__name__)

async def initialize_database():
    """Run database migrations"""
    logger.info("Running database initialization...")
    initializer = DatabaseInitializer()
    success = await initializer.initialize()
    
    if not success:
        logger.error("Database initialization failed!")
        raise Exception("Database initialization failed")
    
    return True

async def setup_configuration():
    """Ensure configuration exists in database and start scheduler"""
    # Database initialization is now handled in API lifespan
    
    db_handler = get_db_handler()
    await db_handler.connect()
    
    # Initialize scheduler service
    try:
        from src.services.scheduler_service import get_scheduler_service
        scheduler = get_scheduler_service()
        await scheduler.initialize()
        logger.info("Scheduler service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize scheduler service: {e}")
        # Don't fail startup if scheduler fails
    
    try:
        # Check if configuration exists
        existing = await db_handler.fetch_one(
            'SELECT "TenantId", "ClientId" FROM public."Configurations" WHERE "Name" = $1',
            'Archive'
        )
        
        if not existing:
            # Insert default/placeholder configuration if none exists
            # Users will need to update this through the UI or database
            await db_handler.execute("""
                INSERT INTO public."Configurations" (
                    "Name", "TenantId", "ClientId", "ClientSecret",
                    "SharePointUrl", "GraphApiScopes", "PurviewEndpoint",
                    "Settings", "CreatedAt", "UpdatedAt"
                ) VALUES (
                    'Archive', '', '', '',
                    'https://your-tenant.sharepoint.com',
                    'https://graph.microsoft.com/.default',
                    'https://manage.office.com',
                    '{"sync_interval_hours": 24}'::jsonb,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created empty configuration record - Azure credentials need to be configured")
        else:
            # Configuration exists - log status
            if existing['TenantId'] and existing['ClientId']:
                logger.info(f"Azure configuration found for tenant: {existing['TenantId']}")
            else:
                logger.warning("Configuration exists but Azure credentials are not set")
            
    except Exception as e:
        logger.error(f"Failed to check configuration: {e}")
    finally:
        await db_handler.disconnect()

if __name__ == "__main__":
    asyncio.run(setup_configuration())