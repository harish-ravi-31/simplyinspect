"""
SimplyInspect API
A focused application for SharePoint permissions inspection and Purview audit log analysis
"""

import os
import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    logger.info("SimplyInspect API starting up...")
    
    # Run database migrations first
    from src.db.init_database import DatabaseInitializer
    logger.info("Checking database schema...")
    initializer = DatabaseInitializer()
    if not await initializer.initialize():
        logger.error("Failed to initialize database schema!")
        raise Exception("Database initialization failed")
    
    # Initialize database connection pools
    from src.db.db_handler import get_db_handler
    db_handler = get_db_handler()
    await db_handler.connect()
    
    # Setup configuration from environment
    from src.startup import setup_configuration
    await setup_configuration()
    
    yield
    
    # Cleanup
    logger.info("SimplyInspect API shutting down...")
    await db_handler.disconnect()

# Create FastAPI app
app = FastAPI(
    title="SimplyInspect API",
    description="SharePoint permissions and Purview audit log inspection",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SimplyInspect"}

@app.get("/")
async def root():
    return {
        "service": "SimplyInspect",
        "version": "1.0.0",
        "features": [
            "SharePoint Permissions Analysis",
            "SharePoint File/Folder Structure",
            "Microsoft Purview Audit Logs",
            "Group Membership Sync"
        ]
    }

# Add authentication middleware
try:
    from src.middleware.auth_middleware import AuthenticationMiddleware, RoleBasedMiddleware
    app.add_middleware(RoleBasedMiddleware)
    app.add_middleware(AuthenticationMiddleware)
    logger.info("Authentication middleware registered")
except Exception as e:
    logger.error(f"Failed to import authentication middleware: {e}")

# Import and register routers
try:
    from src.routes import auth_routes
    app.include_router(auth_routes.router, prefix="/api/v1")
    logger.info("Authentication routes registered")
except Exception as e:
    logger.error(f"Failed to import Authentication routes: {e}")

try:
    from src.routes import admin_routes
    app.include_router(admin_routes.router, prefix="/api/v1")
    logger.info("Admin routes registered")
except Exception as e:
    logger.error(f"Failed to import Admin routes: {e}")

try:
    from src.routes import sharepoint_routes
    app.include_router(sharepoint_routes.router, prefix="/api/v1")
    logger.info("SharePoint routes registered")
except Exception as e:
    logger.error(f"Failed to import SharePoint routes: {e}")

try:
    from src.routes import purview_routes
    app.include_router(purview_routes.router, prefix="/api/v1")
    logger.info("Purview routes registered")
except Exception as e:
    logger.error(f"Failed to import Purview routes: {e}")

try:
    from src.routes import identity_routes
    app.include_router(identity_routes.router, prefix="/api/v1")
    logger.info("Identity routes registered")
except Exception as e:
    logger.error(f"Failed to import Identity routes: {e}")

try:
    from src.routes import configuration_routes
    app.include_router(configuration_routes.router, prefix="/api/v1")
    logger.info("Configuration routes registered")
except Exception as e:
    logger.error(f"Failed to import Configuration routes: {e}")

try:
    from src.routes import library_assignment_routes
    app.include_router(library_assignment_routes.router)
    logger.info("Library Assignment routes registered")
except Exception as e:
    logger.error(f"Failed to import Library Assignment routes: {e}")

try:
    from src.routes import sync_libraries
    app.include_router(sync_libraries.router)
    logger.info("Sync routes registered")
except Exception as e:
    logger.error(f"Failed to import Sync routes: {e}")

try:
    from src.routes import baseline_routes
    app.include_router(baseline_routes.router, prefix="/api/v1")
    logger.info("Baseline routes registered")
except Exception as e:
    logger.error(f"Failed to import Baseline routes: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)