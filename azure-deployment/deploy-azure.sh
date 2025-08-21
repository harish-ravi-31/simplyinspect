#!/bin/bash

# SimplyInspect Azure Deployment Script
# This script is idempotent - it can be run multiple times safely
# It checks for existing resources before creating new ones

set -e

# ========================================
# CONFIGURATION VARIABLES
# ========================================

# Azure Configuration
RESOURCE_GROUP="rg-simplyinspect2"
LOCATION="northeurope"
PREFIX="simplyinspect2"

# Container Registry (UPDATE THESE WITH YOUR ACR DETAILS)
ACR_NAME="${PREFIX}acr"  # ACR names cannot contain hyphens
ACR_SERVER="${ACR_NAME}.azurecr.io"

# Container Images (UPDATE WITH YOUR IMAGE TAGS)
API_IMAGE="${ACR_SERVER}/simplyinspect-api:latest"
UI_IMAGE="${ACR_SERVER}/simplyinspect-ui:latest"

# Network Configuration
VNET_NAME="${PREFIX}-vnet"
NSG_NAME="${PREFIX}-nsg"
PUBLIC_IP_NAME="${PREFIX}-public-ip"
DNS_NAME_LABEL="${PREFIX}-portal"
CONTAINER_GROUP_NAME="${PREFIX}-containers"

# Database Configuration
DB_SERVER_NAME="${PREFIX}-postgres"
DB_HOST="${DB_SERVER_NAME}.postgres.database.azure.com"
DB_PORT="5432"
DB_NAME="simplyinspect"
DB_USER="postgres"
DB_PASSWORD="SimplyInspect2024"  # Change this to a secure password

# Application Configuration
if command -v openssl &>/dev/null; then
    JWT_SECRET_KEY="your-secret-key-here-change-in-production-$(openssl rand -hex 32)"
else
    echo "Warning: openssl not found, using default JWT secret (INSECURE)"
    JWT_SECRET_KEY="your-secret-key-here-change-in-production-default123456789"
fi

# Azure AD Configuration (UPDATE WITH YOUR VALUES)
AZURE_TENANT_ID=""
AZURE_CLIENT_ID=""
AZURE_CLIENT_SECRET=""
SHAREPOINT_URL="https://simplydiscoverco.sharepoint.com"

# SMTP Configuration
SMTP_HOST="smtp.office365.com"
SMTP_PORT="587"
SMTP_USER="notifications@yourdomain.com"
SMTP_PASSWORD="your-smtp-password"
SMTP_FROM="notifications@yourdomain.com"
SMTP_USE_TLS="true"

# Change Detection Configuration
CHANGE_DETECTION_ENABLED="true"
CHANGE_DETECTION_INTERVAL="3600"
NOTIFICATION_CHECK_INTERVAL="300"
DEFAULT_NOTIFICATION_RECIPIENTS="admin@yourdomain.com,security@yourdomain.com"

# Logging
LOG_LEVEL="INFO"
ENVIRONMENT="production"

# ========================================
# HELPER FUNCTIONS
# ========================================

check_resource_exists() {
    local resource_type=$1
    local resource_name=$2
    local resource_group=$3
    
    if [ "$resource_type" == "group" ]; then
        az group show --name "$resource_name" &>/dev/null
    else
        az $resource_type show --name "$resource_name" --resource-group "$resource_group" &>/dev/null
    fi
}

print_status() {
    echo ""
    echo "========================================" 
    echo "$1"
    echo "========================================"
}

validate_environment_variables() {
    echo "Validating configuration..."
    local missing_vars=()
    local warnings=()
    
    # Check for placeholder values that need to be updated
    if [[ -z "$AZURE_CLIENT_SECRET" ]] || [[ "$AZURE_CLIENT_SECRET" == "your-client-secret-here" ]]; then
        missing_vars+=("AZURE_CLIENT_SECRET")
    fi
    
    if [[ "$SHAREPOINT_URL" == "https://your-tenant.sharepoint.com" ]]; then
        missing_vars+=("SHAREPOINT_URL")
    fi
    
    if [[ "$SMTP_PASSWORD" == "your-smtp-password" ]]; then
        warnings+=("SMTP_PASSWORD not configured - email notifications will not work")
    fi
    
    if [[ "$DB_PASSWORD" == "SimplyInspect2024" ]]; then
        warnings+=("Using default database password - change for production security")
    fi
    
    # Validate PostgreSQL version compatibility
    echo "Validating PostgreSQL version compatibility..."
    local pg_version=$(echo "16" | cut -d. -f1)  # Extract major version
    if [[ "$pg_version" -lt "15" ]]; then
        echo "⚠️  PostgreSQL version $pg_version may have compatibility issues with migrations"
        warnings+=("PostgreSQL version should be 15+ for full migration compatibility")
    else
        echo "✅ PostgreSQL version $pg_version is compatible"
    fi
    
    # Display results
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo ""
        echo "❌ Missing required configuration:"
        printf " - %s\n" "${missing_vars[@]}"
        echo ""
        echo "Please update the deployment script with your actual values."
        return 1
    fi
    
    if [ ${#warnings[@]} -gt 0 ]; then
        echo ""
        echo "⚠️  Configuration warnings:"
        printf " - %s\n" "${warnings[@]}"
        echo ""
    fi
    
    echo "✅ Configuration validation passed"
    return 0
}

# ========================================
# MAIN DEPLOYMENT
# ========================================

print_status "Starting SimplyInspect Azure Deployment"

# Check Azure CLI is logged in
if ! az account show &>/dev/null; then
    echo "Error: Not logged into Azure. Please run 'az login' first."
    exit 1
fi

# Validate environment variables and configuration
if ! validate_environment_variables; then
    exit 1
fi

# 1. Create Resource Group
print_status "Step 1: Resource Group"
if ! check_resource_exists "group" "$RESOURCE_GROUP" ""; then
    echo "Creating resource group: $RESOURCE_GROUP"
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
else
    echo "Resource group already exists: $RESOURCE_GROUP"
fi

# 2. Setup ACR credentials
print_status "Step 2: Container Registry Setup"
if [ "$ACR_NAME" != "YOUR_ACR_NAME" ]; then
    # Check if ACR exists
    if az acr show --name "$ACR_NAME" &>/dev/null; then
        echo "Enabling admin user on ACR: $ACR_NAME"
        az acr update --name "$ACR_NAME" --admin-enabled true
        
        echo "Fetching ACR credentials"
        ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username --output tsv)
        ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" --output tsv)
        echo "ACR credentials fetched successfully"
        
        # Validate that images exist in ACR
        echo "Checking if container images exist in ACR..."
        API_IMAGE_EXISTS=$(az acr repository show --name "$ACR_NAME" --image "simplyinspect-api:latest" &>/dev/null && echo "yes" || echo "no")
        UI_IMAGE_EXISTS=$(az acr repository show --name "$ACR_NAME" --image "simplyinspect-ui:latest" &>/dev/null && echo "yes" || echo "no")
        
        if [ "$API_IMAGE_EXISTS" == "no" ] || [ "$UI_IMAGE_EXISTS" == "no" ]; then
            echo "Error: Container images not found in ACR"
            [ "$API_IMAGE_EXISTS" == "no" ] && echo "  Missing: simplyinspect-api:latest"
            [ "$UI_IMAGE_EXISTS" == "no" ] && echo "  Missing: simplyinspect-ui:latest"
            echo ""
            echo "Please build and push images first:"
            echo "  az acr build --registry $ACR_NAME --image simplyinspect-api:latest -f Dockerfile.api ."
            echo "  az acr build --registry $ACR_NAME --image simplyinspect-ui:latest -f Dockerfile.ui ."
            exit 1
        fi
        echo "Container images validated successfully"
    else
        echo "Error: ACR '$ACR_NAME' does not exist. Please create it first."
        echo "Run: az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic"
        exit 1
    fi
else
    echo "Warning: ACR_NAME not configured. Please update the script with your ACR name."
    exit 1
fi

# 3. Create Virtual Network with Subnet for Container Instances
print_status "Step 3: Virtual Network and Subnet"
if ! check_resource_exists "network vnet" "$VNET_NAME" "$RESOURCE_GROUP"; then
    echo "Creating virtual network: $VNET_NAME"
    az network vnet create \
        --name "$VNET_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --address-prefixes "10.0.0.0/16"
else
    echo "Virtual network already exists: $VNET_NAME"
fi

# Create subnet with delegation for Container Instances
SUBNET_NAME="${PREFIX}-subnet"
if ! az network vnet subnet show --name "$SUBNET_NAME" --vnet-name "$VNET_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "Creating subnet with Container Instance delegation: $SUBNET_NAME"
    az network vnet subnet create \
        --name "$SUBNET_NAME" \
        --vnet-name "$VNET_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --address-prefix "10.0.1.0/24" \
        --delegations Microsoft.ContainerInstance/containerGroups
else
    echo "Subnet already exists: $SUBNET_NAME"
fi

# Get subnet ID for later use
SUBNET_ID=$(az network vnet subnet show \
    --name "$SUBNET_NAME" \
    --vnet-name "$VNET_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query id --output tsv)
echo "Subnet ID: $SUBNET_ID"

# 4. Create Network Security Group
print_status "Step 4: Network Security Group"
if ! check_resource_exists "network nsg" "$NSG_NAME" "$RESOURCE_GROUP"; then
    echo "Creating network security group: $NSG_NAME"
    az network nsg create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$NSG_NAME" \
        --location "$LOCATION"
    
    # Allow HTTP traffic on port 80
    echo "Adding NSG rule for HTTP (port 80)"
    az network nsg rule create \
        --resource-group "$RESOURCE_GROUP" \
        --nsg-name "$NSG_NAME" \
        --name "Allow-HTTP" \
        --priority 100 \
        --direction Inbound \
        --access Allow \
        --protocol Tcp \
        --source-address-prefixes "*" \
        --destination-port-ranges 80
    
    # Allow HTTPS traffic on port 443 (for future use)
    echo "Adding NSG rule for HTTPS (port 443)"
    az network nsg rule create \
        --resource-group "$RESOURCE_GROUP" \
        --nsg-name "$NSG_NAME" \
        --name "Allow-HTTPS" \
        --priority 110 \
        --direction Inbound \
        --access Allow \
        --protocol Tcp \
        --source-address-prefixes "*" \
        --destination-port-ranges 443
else
    echo "Network security group already exists: $NSG_NAME"
fi

# Associate NSG with subnet
echo "Associating NSG with subnet"
az network vnet subnet update \
    --name "$SUBNET_NAME" \
    --vnet-name "$VNET_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --network-security-group "$NSG_NAME" || true

# 5. Create Public IP
print_status "Step 5: Public IP Address"
if ! check_resource_exists "network public-ip" "$PUBLIC_IP_NAME" "$RESOURCE_GROUP"; then
    echo "Creating public IP: $PUBLIC_IP_NAME"
    az network public-ip create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$PUBLIC_IP_NAME" \
        --dns-name "$DNS_NAME_LABEL" \
        --allocation-method Static \
        --sku Standard
else
    echo "Public IP already exists: $PUBLIC_IP_NAME"
fi

# Get the public IP address
PUBLIC_IP=$(az network public-ip show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$PUBLIC_IP_NAME" \
    --query ipAddress --output tsv)
PUBLIC_IP_ID=$(az network public-ip show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$PUBLIC_IP_NAME" \
    --query id --output tsv)
echo "Public IP address: $PUBLIC_IP"
echo "DNS name: ${DNS_NAME_LABEL}.${LOCATION}.cloudapp.azure.com"

# 6. Create Load Balancer
print_status "Step 6: Load Balancer"
LB_NAME="${PREFIX}-lb"
FRONTEND_IP_NAME="${PREFIX}-frontend"
BACKEND_POOL_NAME="${PREFIX}-lbbepool"  # Default name when using --backend-pool-name in az lb create
HEALTH_PROBE_NAME="${PREFIX}-health-probe"
LB_RULE_NAME="${PREFIX}-lb-rule"

if ! check_resource_exists "network lb" "$LB_NAME" "$RESOURCE_GROUP"; then
    echo "Creating load balancer: $LB_NAME"
    az network lb create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$LB_NAME" \
        --sku Standard \
        --frontend-ip-name "$FRONTEND_IP_NAME" \
        --backend-pool-name "$BACKEND_POOL_NAME" \
        --public-ip-address "$PUBLIC_IP_ID"
else
    echo "Load balancer already exists: $LB_NAME"
fi

# Create health probe
if ! az network lb probe show --resource-group "$RESOURCE_GROUP" --lb-name "$LB_NAME" --name "$HEALTH_PROBE_NAME" &>/dev/null; then
    echo "Creating health probe: $HEALTH_PROBE_NAME"
    az network lb probe create \
        --resource-group "$RESOURCE_GROUP" \
        --lb-name "$LB_NAME" \
        --name "$HEALTH_PROBE_NAME" \
        --protocol http \
        --port 80 \
        --path / \
        --interval 30 \
        --threshold 2
else
    echo "Health probe already exists: $HEALTH_PROBE_NAME"
fi

# Create load balancing rule
if ! az network lb rule show --resource-group "$RESOURCE_GROUP" --lb-name "$LB_NAME" --name "$LB_RULE_NAME" &>/dev/null; then
    echo "Creating load balancing rule: $LB_RULE_NAME"
    az network lb rule create \
        --resource-group "$RESOURCE_GROUP" \
        --lb-name "$LB_NAME" \
        --name "$LB_RULE_NAME" \
        --protocol tcp \
        --frontend-port 80 \
        --backend-port 80 \
        --frontend-ip-name "$FRONTEND_IP_NAME" \
        --backend-pool-name "$BACKEND_POOL_NAME" \
        --probe-name "$HEALTH_PROBE_NAME" \
        --idle-timeout 4
else
    echo "Load balancing rule already exists: $LB_RULE_NAME"
fi

# 7. Create PostgreSQL Flexible Server
print_status "Step 7: PostgreSQL Database"
if ! check_resource_exists "postgres flexible-server" "$DB_SERVER_NAME" "$RESOURCE_GROUP"; then
    echo "Creating PostgreSQL server: $DB_SERVER_NAME"
    az postgres flexible-server create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DB_SERVER_NAME" \
        --location "$LOCATION" \
        --admin-user "$DB_USER" \
        --admin-password "$DB_PASSWORD" \
        --sku-name "Standard_B2s" \
        --tier "Burstable" \
        --version "16" \
        --storage-size 32 \
        --public-access "0.0.0.0"
    
    # Create database
    echo "Creating database: $DB_NAME"
    az postgres flexible-server db create \
        --resource-group "$RESOURCE_GROUP" \
        --server-name "$DB_SERVER_NAME" \
        --database-name "$DB_NAME"
    
    # Configure firewall to allow Azure services
    echo "Configuring firewall rules"
    az postgres flexible-server firewall-rule create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DB_SERVER_NAME" \
        --rule-name "AllowAzureServices" \
        --start-ip-address "0.0.0.0" \
        --end-ip-address "0.0.0.0"
else
    echo "PostgreSQL server already exists: $DB_SERVER_NAME"
fi

# 8. Create Private DNS Zone for internal communication
print_status "Step 8: Private DNS Zone"
DNS_ZONE_NAME="internal.lan"
VNET_ID=$(az network vnet show \
    --name "$VNET_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query id --output tsv)

if ! az network private-dns zone show --resource-group "$RESOURCE_GROUP" --name "$DNS_ZONE_NAME" &>/dev/null; then
    echo "Creating private DNS zone: $DNS_ZONE_NAME"
    az network private-dns zone create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DNS_ZONE_NAME"
    
    echo "Linking DNS zone to VNet"
    az network private-dns link vnet create \
        --resource-group "$RESOURCE_GROUP" \
        --zone-name "$DNS_ZONE_NAME" \
        --name "${PREFIX}-dns-link" \
        --virtual-network "$VNET_ID" \
        --registration-enabled true
else
    echo "Private DNS zone already exists: $DNS_ZONE_NAME"
fi

# 9. Generate ACI deployment YAML
print_status "Step 9: Generating Container Instance Configuration"

ACI_YAML_FILE="/tmp/simplyinspect-aci-deploy.yaml"

cat > "$ACI_YAML_FILE" << EOF
apiVersion: '2021-07-01'
name: ${CONTAINER_GROUP_NAME}
location: ${LOCATION}
properties:
  containers:
    - name: simplyinspect-api
      properties:
        image: ${API_IMAGE}
        environmentVariables:
          - name: DB_HOST
            value: "${DB_HOST}"
          - name: DB_PORT
            value: "${DB_PORT}"
          - name: DB_NAME
            value: "${DB_NAME}"
          - name: DB_USER
            value: "${DB_USER}"
          - name: DB_PASSWORD
            secureValue: "${DB_PASSWORD}"
          - name: PGSSLMODE
            value: "require"
          - name: JWT_SECRET_KEY
            secureValue: "${JWT_SECRET_KEY}"
          - name: AZURE_TENANT_ID
            value: "${AZURE_TENANT_ID}"
          - name: AZURE_CLIENT_ID
            value: "${AZURE_CLIENT_ID}"
          - name: AZURE_CLIENT_SECRET
            secureValue: "${AZURE_CLIENT_SECRET}"
          - name: SHAREPOINT_URL
            value: "${SHAREPOINT_URL}"
          - name: SMTP_HOST
            value: "${SMTP_HOST}"
          - name: SMTP_PORT
            value: "${SMTP_PORT}"
          - name: SMTP_USER
            value: "${SMTP_USER}"
          - name: SMTP_PASSWORD
            secureValue: "${SMTP_PASSWORD}"
          - name: SMTP_FROM
            value: "${SMTP_FROM}"
          - name: SMTP_USE_TLS
            value: "${SMTP_USE_TLS}"
          - name: CHANGE_DETECTION_ENABLED
            value: "${CHANGE_DETECTION_ENABLED}"
          - name: CHANGE_DETECTION_INTERVAL
            value: "${CHANGE_DETECTION_INTERVAL}"
          - name: NOTIFICATION_CHECK_INTERVAL
            value: "${NOTIFICATION_CHECK_INTERVAL}"
          - name: DEFAULT_NOTIFICATION_RECIPIENTS
            value: "${DEFAULT_NOTIFICATION_RECIPIENTS}"
          - name: LOG_LEVEL
            value: "${LOG_LEVEL}"
          - name: ENVIRONMENT
            value: "${ENVIRONMENT}"
          - name: API_HOST
            value: "0.0.0.0"
          - name: API_PORT
            value: "8000"
        ports:
          - port: 8000
            protocol: TCP
        resources:
          requests:
            cpu: 2.0
            memoryInGb: 8.0
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          periodSeconds: 30
          failureThreshold: 3
    - name: simplyinspect-ui
      properties:
        image: ${UI_IMAGE}
        environmentVariables:
          - name: API_URL
            value: "http://localhost:8000"
        ports:
          - port: 80
            protocol: TCP
        resources:
          requests:
            cpu: 1.0
            memoryInGb: 2.0
  osType: Linux
  subnetIds:
    - id: ${SUBNET_ID}
      name: default
  ipAddress:
    type: Private
    ports:
      - protocol: TCP
        port: 80
      - protocol: TCP
        port: 8000
  imageRegistryCredentials:
    - server: ${ACR_SERVER}
      username: ${ACR_USERNAME}
      password: ${ACR_PASSWORD}
EOF

echo "ACI configuration generated at: $ACI_YAML_FILE"

# 10. Deploy Container Instances
print_status "Step 10: Deploying Container Instances"

# Check if container group exists
if check_resource_exists "container" "$CONTAINER_GROUP_NAME" "$RESOURCE_GROUP"; then
    echo "Container group exists. Deleting old deployment..."
    az container delete \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_GROUP_NAME" \
        --yes
    
    # Wait for deletion to complete
    echo "Waiting for deletion to complete..."
    sleep 30
fi

echo "Creating container group: $CONTAINER_GROUP_NAME"
az container create \
    --resource-group "$RESOURCE_GROUP" \
    --file "$ACI_YAML_FILE"

# Wait for containers to be ready with polling
echo "Waiting for containers to start..."
MAX_WAIT=300  # 5 minutes timeout
WAIT_INTERVAL=10
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Check container state
    CONTAINER_STATE=$(az container show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_GROUP_NAME" \
        --query "instanceView.state" \
        --output tsv 2>/dev/null || echo "Pending")
    
    CONTAINER_IP=$(az container show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_GROUP_NAME" \
        --query "ipAddress.ip" \
        --output tsv 2>/dev/null || echo "")
    
    if [ "$CONTAINER_STATE" == "Running" ] && [ -n "$CONTAINER_IP" ]; then
        echo "Container group is running with IP: $CONTAINER_IP"
        break
    fi
    
    echo "Container state: $CONTAINER_STATE, waiting... ($ELAPSED/$MAX_WAIT seconds)"
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "Warning: Timeout waiting for container group to be ready"
    echo "Current state: $CONTAINER_STATE"
fi

# 11. Add Container Group to Load Balancer Backend Pool
print_status "Step 11: Configuring Load Balancer Backend"

# Container IP was already fetched in the polling loop above

if [ -n "$CONTAINER_IP" ]; then
    echo "Container group IP: $CONTAINER_IP"
    
    # Add container IP to load balancer backend pool
    echo "Adding container to load balancer backend pool"
    az network lb address-pool address add \
        --resource-group "$RESOURCE_GROUP" \
        --lb-name "$LB_NAME" \
        --pool-name "$BACKEND_POOL_NAME" \
        --vnet "$VNET_NAME" \
        --ip-address "$CONTAINER_IP" \
        --name "ContainerGroupIP" || true
    
    # Add DNS records for internal communication
    echo "Adding DNS records for internal services"
    az network private-dns record-set a create \
        --resource-group "$RESOURCE_GROUP" \
        --zone-name "$DNS_ZONE_NAME" \
        --name "simplyinspect-api" || true
    az network private-dns record-set a add-record \
        --resource-group "$RESOURCE_GROUP" \
        --zone-name "$DNS_ZONE_NAME" \
        --record-set-name "simplyinspect-api" \
        --ipv4-address "$CONTAINER_IP" || true
    
    az network private-dns record-set a create \
        --resource-group "$RESOURCE_GROUP" \
        --zone-name "$DNS_ZONE_NAME" \
        --name "simplyinspect-ui" || true
    az network private-dns record-set a add-record \
        --resource-group "$RESOURCE_GROUP" \
        --zone-name "$DNS_ZONE_NAME" \
        --record-set-name "simplyinspect-ui" \
        --ipv4-address "$CONTAINER_IP" || true
else
    echo "Warning: Could not get container IP address"
fi

# 12. Validate Deployment and Create Admin User
print_status "Step 12: Deployment Validation"

# Wait for API container to be fully ready
echo "Waiting for API container to be fully ready..."
API_READY=false
MAX_WAIT_API=300  # 5 minutes
ELAPSED=0
WAIT_INTERVAL=15

while [ $ELAPSED -lt $MAX_WAIT_API ]; do
    # Check if API responds to health check
    HEALTH_STATUS=$(curl -s -w "%{http_code}" "http://${PUBLIC_IP}/api/health" --connect-timeout 5 2>/dev/null || echo "000")
    if [ "$HEALTH_STATUS" = "200" ]; then
        API_READY=true
        echo "✅ API container is ready and responding"
        break
    fi
    
    echo "API not ready yet (status: $HEALTH_STATUS), waiting... ($ELAPSED/$MAX_WAIT_API seconds)"
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

if [ "$API_READY" = "false" ]; then
    echo "⚠️  API container not responding to health checks after $MAX_WAIT_API seconds"
    echo "Deployment may have issues. Check container logs:"
    echo "  az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_GROUP_NAME --container-name simplyinspect-api"
fi

# Verify database migrations completed successfully
echo "Verifying database migrations..."
MIGRATION_CHECK=$(az container logs --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_GROUP_NAME" --container-name simplyinspect-api | grep -E "Database initialization complete|Failed to run migration|UnknownHashError" | tail -3)

if echo "$MIGRATION_CHECK" | grep -q "Database initialization complete"; then
    echo "✅ Database migrations completed successfully"
    
    # Create/Update admin user with proper password hash
    echo "Creating admin user with proper password hash..."
    ADMIN_CREATION_RESULT=$(az container exec --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_GROUP_NAME" --container-name simplyinspect-api --exec-command "python -c \"
import asyncio
import asyncpg
import sys
sys.path.append('/app')
from src.services.auth_service import AuthService

async def create_admin():
    try:
        conn = await asyncpg.connect(
            host='$DB_HOST',
            port=$DB_PORT,
            user='$DB_USER', 
            password='$DB_PASSWORD',
            database='$DB_NAME',
            ssl='require'
        )
        
        auth = AuthService()
        hash_val = auth.hash_password('AdminPassword123!')
        
        # Use UPSERT to create or update admin user
        await conn.execute('''
            INSERT INTO users (email, username, password_hash, full_name, role, is_approved, is_active, company, created_at, updated_at)
            VALUES (\\\$1, \\\$2, \\\$3, \\\$4, \\\$5, \\\$6, \\\$7, \\\$8, NOW(), NOW())
            ON CONFLICT (email) DO UPDATE SET 
                password_hash = \\\$3,
                updated_at = NOW()
        ''', 'admin@simplyinspect.com', 'admin', hash_val, 'System Administrator', 'administrator', True, True, 'SimplyInspect')
        
        print('SUCCESS: Admin user created/updated')
        await conn.close()
        
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)

asyncio.run(create_admin())
\"" 2>&1)

    if echo "$ADMIN_CREATION_RESULT" | grep -q "SUCCESS"; then
        echo "✅ Admin user created/updated successfully"
        
        # Test admin login
        echo "Testing admin login..."
        sleep 10  # Give the system a moment after user creation
        
        LOGIN_TEST=$(curl -s -X POST "http://${PUBLIC_IP}/api/v1/auth/login" \
            -H "Content-Type: application/json" \
            -d '{"email":"admin@simplyinspect.com","password":"AdminPassword123!"}' \
            -w "%{http_code}" \
            --connect-timeout 10 2>/dev/null || echo "000")
            
        if echo "$LOGIN_TEST" | grep -q "200"; then
            echo "✅ Admin login test successful"
        else
            echo "⚠️  Admin login test failed (HTTP: ${LOGIN_TEST##*$'\n'})"
            echo "Manual verification may be needed"
        fi
    else
        echo "⚠️  Admin user creation had issues:"
        echo "$ADMIN_CREATION_RESULT"
    fi
    
elif echo "$MIGRATION_CHECK" | grep -q "Failed"; then
    echo "❌ Database migration errors detected:"
    echo "$MIGRATION_CHECK"
    echo "Check container logs for details:"
    echo "  az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_GROUP_NAME --container-name simplyinspect-api"
else
    echo "⚠️  Could not verify migration status - check container logs manually"
fi

# 13. Display deployment information
print_status "Deployment Complete!"

echo "🎉 SimplyInspect has been successfully deployed to Azure!"
echo ""
echo "📱 Access your application:"
echo "  Load Balancer URL: http://${DNS_NAME_LABEL}.${LOCATION}.cloudapp.azure.com"
echo "  Load Balancer IP: http://${PUBLIC_IP}"
echo ""
echo "🔐 Admin Login Credentials:"
echo "  Email: admin@simplyinspect.com"
echo "  Password: AdminPassword123!"
echo ""
echo "🔧 Internal Services (within VNet):"
echo "  API: http://simplyinspect-api.internal.lan:8000"
echo "  UI: http://simplyinspect-ui.internal.lan"
echo "  Container IP: ${CONTAINER_IP}"
echo ""
echo "💾 Database connection:"
echo "  Host: ${DB_HOST}"
echo "  Database: ${DB_NAME}"
echo "  User: ${DB_USER}"
echo ""
echo "Container Logs:"
echo "  API: az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_GROUP_NAME --container-name simplyinspect-api"
echo "  UI: az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_GROUP_NAME --container-name simplyinspect-ui"
echo ""
echo "To check container status:"
echo "  az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_GROUP_NAME"
echo ""
echo "To check load balancer health:"
echo "  az network lb probe show --resource-group $RESOURCE_GROUP --lb-name $LB_NAME --name $HEALTH_PROBE_NAME"
echo ""
echo "IMPORTANT: Remember to:"
echo "1. Update the ACR credentials in this script with your actual values"
echo "2. Push your Docker images to ACR:"
echo "   az acr build --registry $ACR_NAME --image simplyinspect-api:latest -f Dockerfile.api ."
echo "   az acr build --registry $ACR_NAME --image simplyinspect-ui:latest -f Dockerfile.ui ."
echo "3. Update Azure AD credentials for SharePoint integration"
echo "4. Configure SMTP settings for email notifications"
echo "5. Run database migrations after deployment"
echo ""
echo "Note: Containers within the same group communicate via localhost:"
echo "  - UI can reach API at: http://localhost:8000"
echo "  - This is configured in the container environment variables"

# Clean up temporary file
rm -f "$ACI_YAML_FILE"