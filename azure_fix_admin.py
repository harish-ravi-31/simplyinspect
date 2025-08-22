#!/usr/bin/env python3
"""
Fix admin user password for Azure deployment
Run this locally with Azure database credentials
"""
import asyncio
import asyncpg
import bcrypt
import sys

async def fix_admin_user():
    """Reset admin user password in Azure database"""
    
    # Azure database connection
    db_config = {
        'host': 'simplyinspect3-postgres.postgres.database.azure.com',
        'port': 5432,
        'user': 'postgres',
        'password': 'SimplyInspect2024',
        'database': 'simplyinspect',
        'ssl': 'require'
    }
    
    try:
        print(f"Connecting to Azure database at {db_config['host']}...")
        conn = await asyncpg.connect(**db_config)
        
        # Check if admin user exists
        print("Checking for existing admin user...")
        existing_user = await conn.fetchrow(
            "SELECT id, email, username, role, is_active, is_approved, password_hash FROM users WHERE email = $1",
            'admin@simplyinspect.com'
        )
        
        if existing_user:
            print(f"Found existing admin user:")
            print(f"  - ID: {existing_user['id']}")
            print(f"  - Email: {existing_user['email']}")
            print(f"  - Username: {existing_user['username']}")
            print(f"  - Role: {existing_user['role']}")
            print(f"  - Active: {existing_user['is_active']}")
            print(f"  - Approved: {existing_user['is_approved']}")
        else:
            print("Admin user not found - will create new one")
        
        # Generate password hash using bcrypt (compatible with passlib)
        password = 'AdminPassword123!'
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        print(f"\nGenerated password hash: {password_hash[:20]}...")
        
        # Create or update admin user
        result = await conn.execute('''
            INSERT INTO users (
                email, username, password_hash, full_name, role, 
                is_approved, is_active, company, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
            ON CONFLICT (email) DO UPDATE SET 
                password_hash = $3,
                role = $5,
                is_approved = $6,
                is_active = $7,
                updated_at = NOW()
        ''', 
            'admin@simplyinspect.com',  # email
            'admin',                     # username
            password_hash,               # password_hash
            'System Administrator',      # full_name
            'administrator',            # role
            True,                       # is_approved
            True,                       # is_active
            'SimplyInspect'            # company
        )
        
        print("✅ Admin user created/updated successfully")
        
        # Verify the update
        updated_user = await conn.fetchrow(
            "SELECT id, email, password_hash FROM users WHERE email = $1",
            'admin@simplyinspect.com'
        )
        
        if updated_user:
            print(f"\nVerified admin user in database:")
            print(f"  - Email: {updated_user['email']}")
            print(f"  - Password hash starts with: {updated_user['password_hash'][:20]}")
            
            # Verify the password can be checked
            stored_hash = updated_user['password_hash'].encode('utf-8')
            if bcrypt.checkpw(password_bytes, stored_hash):
                print("✅ Password verification successful!")
            else:
                print("❌ Password verification failed!")
        
        await conn.close()
        
        print("\n" + "="*50)
        print("Admin user has been fixed!")
        print("="*50)
        print("\nLogin credentials:")
        print(f"  Email: admin@simplyinspect.com")
        print(f"  Password: {password}")
        print("\nYou can now login at:")
        print("  http://simplyinspect3-portal.northeurope.cloudapp.azure.com")
        print("  or http://4.210.74.71")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(fix_admin_user())