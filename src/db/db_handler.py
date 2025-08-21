"""
Simplified Database Handler for SimplyInspect
"""

import os
import asyncpg
import logging
from typing import List, Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)

class DatabaseHandler:
    def __init__(self):
        self.pool = None
        self.db_config = {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'port': int(os.environ.get('DB_PORT', 5432)),
            'database': os.environ.get('DB_NAME', 'simplyarchive'),
            'user': os.environ.get('DB_USER', 'postgres'),
            'password': os.environ.get('DB_PASSWORD', '')
        }
        
    async def connect(self):
        """Create database connection pool"""
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    host=self.db_config['host'],
                    port=self.db_config['port'],
                    database=self.db_config['database'],
                    user=self.db_config['user'],
                    password=self.db_config['password'],
                    min_size=2,
                    max_size=10,
                    command_timeout=60.0
                )
                logger.info(f"Connected to database at {self.db_config['host']}:{self.db_config['port']}")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
                
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection closed")
            
    async def execute(self, query: str, *args):
        """Execute a query without returning results"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
            
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch a single row"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
            
    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
            
    async def fetch_value(self, query: str, *args):
        """Fetch a single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

# Global instance
_db_handler = None

def get_db_handler():
    """Get or create the global database handler"""
    global _db_handler
    if _db_handler is None:
        _db_handler = DatabaseHandler()
    return _db_handler

async def get_db():
    """Dependency for FastAPI routes"""
    handler = get_db_handler()
    if handler.pool is None:
        await handler.connect()
    return handler