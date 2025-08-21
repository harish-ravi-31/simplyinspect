#!/usr/bin/env python3
import bcrypt

# Generate password hash for Admin123!
password = "Admin123!"
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
print(f"Password hash for '{password}':")
print(hashed.decode('utf-8'))