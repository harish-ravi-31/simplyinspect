#!/usr/bin/env python3
"""
Test password verification directly
"""

from passlib.context import CryptContext

# Configure passlib context (same as in AuthService)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# The hash from the database
hash_from_db = '$2b$12$K6HXYqVVjNZH4dQXsNnYVuGXjLV5GYKxGZEGJYnXGZQKxVXJZ5j7i'

# Test password
password = 'Admin123!'

# Verify
result = pwd_context.verify(password, hash_from_db)
print(f"Password '{password}' verification: {result}")

# Also test if hash is valid bcrypt format
print(f"\nHash details:")
print(f"  Starts with $2b$: {hash_from_db.startswith('$2b$')}")
print(f"  Length: {len(hash_from_db)}")
print(f"  Cost factor: {hash_from_db.split('$')[2] if len(hash_from_db.split('$')) > 2 else 'N/A'}")

# Generate a new hash for comparison
new_hash = pwd_context.hash(password)
print(f"\nNew hash for same password: {new_hash}")
print(f"New hash verifies: {pwd_context.verify(password, new_hash)}")