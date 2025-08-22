"""
Database initialization script for SimplyInspect
Runs migrations automatically on application startup
"""

import os
import sys
import asyncio
import asyncpg
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self):
        self.db_host = os.getenv('DB_HOST', 'postgres')
        self.db_port = int(os.getenv('DB_PORT', 5432))
        self.db_name = os.getenv('DB_NAME', 'simplyinspect')
        self.db_user = os.getenv('DB_USER', 'postgres')
        self.db_password = self._get_db_password()
        self.db_ssl = os.getenv('PGSSLMODE', 'prefer')  # Support SSL for Azure PostgreSQL
        self.migrations_dir = Path(__file__).parent.parent.parent / 'migrations'
    
    def _get_db_password(self) -> str:
        """Get database password from Azure Key Vault or environment variable"""
        # First try to get from Azure Key Vault if configured
        key_vault_uri = os.getenv("KEY_VAULT_URI")
        key_vault_name = os.getenv("KEY_VAULT_NAME")
        
        if key_vault_uri and key_vault_name:
            try:
                from azure.keyvault.secrets import SecretClient
                
                # Try managed identity first (for Azure), then DefaultAzureCredential (for local dev)
                try:
                    from azure.identity import ManagedIdentityCredential
                    logger.info(f"Using ManagedIdentityCredential for Key Vault: {key_vault_name}")
                    credential = ManagedIdentityCredential()
                except Exception:
                    from azure.identity import DefaultAzureCredential
                    logger.info(f"Using DefaultAzureCredential for Key Vault: {key_vault_name}")
                    credential = DefaultAzureCredential()
                
                client = SecretClient(vault_url=key_vault_uri, credential=credential)
                
                secret = client.get_secret("db-password")
                logger.info("Successfully retrieved DB password from Azure Key Vault")
                return secret.value
            except Exception as e:
                logger.warning(f"Could not retrieve DB password from Key Vault: {e}")
        
        # Fall back to environment variable (no default password for security)
        password = os.getenv('DB_PASSWORD')
        if not password:
            logger.error("DB_PASSWORD not found in environment variables or Key Vault")
            raise ValueError("Database password not configured")
        return password
        
    async def wait_for_database(self, max_retries=30):
        """Wait for database to be available"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                conn = await asyncpg.connect(
                    host=self.db_host,
                    port=self.db_port,
                    user=self.db_user,
                    password=self.db_password,
                    database=self.db_name,
                    ssl=self.db_ssl  # Add SSL support
                )
                await conn.close()
                logger.info("✓ Database is ready")
                return True
            except Exception as e:
                retry_count += 1
                # Log the actual error for better debugging
                error_msg = str(e)
                if "password authentication failed" in error_msg.lower():
                    logger.error(f"Database authentication failed: {error_msg}")
                    logger.error("Check that the password in Key Vault matches the PostgreSQL server password")
                elif "could not connect" in error_msg.lower() or "timeout" in error_msg.lower():
                    logger.warning(f"Database connection attempt {retry_count}/{max_retries}: {error_msg}")
                else:
                    logger.warning(f"Database not ready ({retry_count}/{max_retries}): {error_msg}")
                
                if retry_count < max_retries:
                    await asyncio.sleep(2)
                else:
                    logger.error(f"Failed to connect to database after {max_retries} attempts")
                    logger.error(f"Final error: {e}")
                    return False
        return False
        
    async def ensure_backward_compatibility(self, conn):
        """Handle legacy schemas that conflict with consolidated migrations"""
        try:
            legacy_role_permissions = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema='public' 
                      AND table_name='role_permissions' 
                      AND column_name='permission'
                )
                """
            )
            if legacy_role_permissions:
                logger.info("Detected legacy 'role_permissions' schema. Dropping to apply new schema.")
                await conn.execute("DROP TABLE IF EXISTS public.role_permissions")
        except Exception as e:
            logger.error(f"Error during backward-compatibility checks: {e}")
            # Continue; main migration may still succeed

    async def check_migration_status(self, conn):
        """Check if migrations table exists and get list of applied migrations"""
        try:
            # Check if migrations table exists
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema='public' 
                    AND table_name='schema_migrations'
                )
            """)
            
            if not result:
                logger.info("Migration table does not exist")
                return set()
                
            # Get list of applied migrations
            applied_migrations = await conn.fetch("""
                SELECT version FROM schema_migrations ORDER BY applied_at
            """)
            
            return set(row['version'] for row in applied_migrations)
            
        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return set()
            
    async def run_migration(self, conn, migration_file):
        """Run a single migration file"""
        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False
            
        try:
            logger.info(f"Running migration: {migration_file}")
            
            # Read and execute the migration file
            with open(migration_file, 'r') as f:
                sql_content = f.read()
                
            # Execute the migration
            await conn.execute(sql_content)
            
            logger.info(f"✓ Migration completed successfully: {migration_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to run migration {migration_file.name}: {e}")
            return False
            
    async def run_pending_migrations(self, conn, applied_migrations):
        """Run all pending migrations in order"""
        # Determine which migration files to run (prefer consolidated script)
        migrations = []
        init_v2 = self.migrations_dir / 'init_database.sql'
        complete_v1 = self.migrations_dir / '000_complete_schema.sql'
        auth_only = self.migrations_dir / '002_auth_only_schema.sql'
        extra_reviewer = self.migrations_dir / '003_reviewer_library_assignments.sql'
        permission_baselines = self.migrations_dir / '004_permission_baselines.sql'

        if init_v2.exists():
            # Fully idempotent consolidated initializer creates all tables and records version 'init_database_v2'
            migrations.append('init_database.sql')
        elif complete_v1.exists():
            # Older full schema, optionally followed by reviewer assignments
            migrations.append('000_complete_schema.sql')
            if extra_reviewer.exists():
                migrations.append('003_reviewer_library_assignments.sql')
        elif auth_only.exists():
            # Fallback minimal auth-only schema (may fail verification for non-auth tables)
            migrations.append('002_auth_only_schema.sql')
        
        # Add permission baselines migration if it exists and hasn't been applied
        if permission_baselines.exists():
            migrations.append('004_permission_baselines.sql')
        
        # Map filenames to the version strings recorded in schema_migrations
        version_aliases = {
            'init_database.sql': 'init_database_v2',
            '000_complete_schema.sql': '000_complete_schema',
            '002_auth_only_schema.sql': '002_auth_only_schema',
            '003_reviewer_library_assignments.sql': '003_reviewer_library_assignments',
            '004_permission_baselines.sql': '004_permission_baselines',
        }

        for migration_filename in migrations:
            migration_version = version_aliases.get(
                migration_filename, migration_filename.replace('.sql', '')
            )
            
            if migration_version in applied_migrations:
                logger.info(f"✓ Migration {migration_version} already applied")
                continue
                
            migration_file = self.migrations_dir / migration_filename
            if not await self.run_migration(conn, migration_file):
                return False
                
        return True
            
    async def verify_tables(self, conn):
        """Verify that all required tables exist"""
        required_tables = [
            'sharepoint_permissions',
            'group_memberships',
            'ExternalAuditLogs',
            'Configurations',
            'users',
            'user_sessions',
            'user_audit_log',
            'password_reset_tokens',
            'user_notifications',
            'role_permissions',
            # New baseline and notification tables
            'permission_baselines',
            'permission_changes',
            'notification_queue',
            'notification_recipients',
            'baseline_comparison_cache'
        ]
        
        all_exist = True
        for table in required_tables:
            result = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema='public' 
                    AND table_name='{table}'
                )
            """)
            
            if result:
                logger.info(f"✓ Table '{table}' exists")
            else:
                logger.error(f"✗ Table '{table}' is missing!")
                all_exist = False
                
        return all_exist
        
    async def initialize(self):
        """Main initialization process"""
        logger.info("=" * 50)
        logger.info("Starting database initialization...")
        logger.info("=" * 50)
        
        # Wait for database
        if not await self.wait_for_database():
            logger.error("Database is not available. Exiting.")
            return False
            
        # Connect to database
        try:
            conn = await asyncpg.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name,
                ssl=self.db_ssl  # Add SSL support
            )
            
            # Adjust legacy schemas before running consolidated migrations
            await self.ensure_backward_compatibility(conn)

            # Check migration status
            applied_migrations = await self.check_migration_status(conn)
            
            if not applied_migrations or len(applied_migrations) == 0:
                logger.info("Running initial database migrations...")
            else:
                logger.info(f"Found {len(applied_migrations)} applied migrations: {sorted(applied_migrations)}")
            
            # Run any pending migrations
            if not await self.run_pending_migrations(conn, applied_migrations):
                await conn.close()
                return False
                
            # Verify tables
            if not await self.verify_tables(conn):
                logger.error("Database verification failed")
                await conn.close()
                return False
                
            await conn.close()
            
            logger.info("=" * 50)
            logger.info("✓ Database initialization complete!")
            logger.info("=" * 50)
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False

async def main():
    """Run database initialization"""
    initializer = DatabaseInitializer()
    success = await initializer.initialize()
    
    if not success:
        logger.error("Database initialization failed!")
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())