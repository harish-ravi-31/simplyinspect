#!/bin/bash
set -e

# Install necessary packages
apt-get update
apt-get install -y build-essential git postgresql-server-dev-16

# Clone pgvector
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git

# Build and install pgvector
cd pgvector
make
make install

# Enable extension in database
psql -U postgres -d simplyinspect -c 'CREATE EXTENSION IF NOT EXISTS vector;'
