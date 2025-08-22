#!/usr/bin/env python
"""
Debug script to diagnose login issues
"""
import asyncio
import asyncpg
import os
import bcrypt
from passlib.context import CryptContext

# Configure passlib context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def debug_auth():
    print("==== SimplyInspect Authentication Debugger ====")
    
    # Get database connection details from environment
    db_host = os.getenv('DB_HOST', 'pgvector-postgres-simplyinspect')
    db_port = int(os.getenv('DB_PORT', 5432))
    db_name = os.getenv('DB_NAME', 'simplyinspect')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'Wa239KpL3dw')
    
    # Connect to database
    print(f"Connecting to database: {db_host}:{db_port}/{db_name}")
    conn = await asyncpg.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password
    )
    print("Connected successfully!")
    
    # Fetch admin user
    print("\nFetching admin user details...")
    user = await conn.fetchrow("""
        SELECT id, email, username, password_hash, role, is_approved, is_active
        FROM public.users
        WHERE email = 'admin@simplyinspect.com'
    """)
    
    if not user:
        print("ERROR: Admin user not found!")
        return
    
    print(f"Found user: {user['email']} (ID: {user['id']}, Role: {user['role']})")
    print(f"Account status: Active: {user['is_active']}, Approved: {user['is_approved']}")
    
    # Hash info
    print("\nPassword hash info:")
    hash_value = user['password_hash']
    print(f"Current hash: {hash_value}")
    print(f"Hash length: {len(hash_value)}")
    print(f"Hash type: {'bcrypt' if hash_value.startswith('$2') else 'unknown'}")
    
    # Test passwords
    test_passwords = ["Admin123!", "simplyinspect", "password"]
    print("\nVerifying test passwords:")
    for password in test_passwords:
        is_valid = pwd_context.verify(password, hash_value)
        print(f"Password '{password}': {'✅ VALID' if is_valid else '❌ INVALID'}")
    
    # Generate new hash and compare
    print("\nGenerating new hash for comparison:")
    new_hash = pwd_context.hash("Admin123!")
    print(f"New hash: {new_hash}")
    print(f"Comparing new hash to stored hash: {'Same' if new_hash == hash_value else 'Different'}")
    print(f"Cross-verification: {pwd_context.verify('Admin123!', new_hash)}")
    
    # Update password if needed
    update = input("\nWould you like to update the admin password? (yes/no): ").strip().lower()
    if update == "yes":
        new_password = "Admin123!"
        new_hash = pwd_context.hash(new_password)
        await conn.execute(
            "UPDATE public.users SET password_hash = $1 WHERE email = $2",
            new_hash, "admin@simplyinspect.com"
        )
        print(f"Password updated to '{new_password}'")
    
    # Close connection
    await conn.close()
    print("\nDebug complete.")

if __name__ == "__main__":
    asyncio.run(debug_auth())
