#!/bin/bash

# Google Cloud Run Deployment Script
# Production-ready deployment for Synthea FHIR MCP Server

set -e  # Exit on error

echo "🚀 Deploying Synthea FHIR MCP Server to Google Cloud Run"
echo "========================================================="

# Check for required environment variables
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please copy ../.env.example to .env and configure it"
    exit 1
fi

# Source environment variables
source .env

# Validate required variables
if [ -z "$CLOUD_SQL_CONNECTION_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ]; then
    echo "❌ Error: Missing required environment variables"
    echo "Please ensure these are set in .env:"
    echo "  - CLOUD_SQL_CONNECTION_NAME"
    echo "  - DB_USER"
    echo "  - DB_PASSWORD"
    echo "  - DB_NAME"
    exit 1
fi

# Set defaults
SERVICE_NAME=${SERVICE_NAME:-"synthea-mcp"}
REGION=${REGION:-"us-central1"}
MEMORY=${MEMORY:-"512Mi"}
CPU=${CPU:-"1"}
TIMEOUT=${TIMEOUT:-"300"}
MAX_INSTANCES=${MAX_INSTANCES:-"10"}

echo ""
echo "📋 Configuration:"
echo "  Service: $SERVICE_NAME"
echo "  Region: $REGION"
echo "  Cloud SQL: $CLOUD_SQL_CONNECTION_NAME"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# Deploy to Cloud Run
echo "🏗️  Building and deploying..."
gcloud run deploy $SERVICE_NAME \
  --source ../.. \
  --add-cloudsql-instances $CLOUD_SQL_CONNECTION_NAME \
  --set-env-vars "CLOUD_SQL_CONNECTION_NAME=$CLOUD_SQL_CONNECTION_NAME,DB_USER=$DB_USER,DB_PASSWORD=$DB_PASSWORD,DB_NAME=$DB_NAME" \
  --region $REGION \
  --allow-unauthenticated \
  --memory $MEMORY \
  --cpu $CPU \
  --timeout $TIMEOUT \
  --max-instances $MAX_INSTANCES \
  --platform managed

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📍 Service URL: $SERVICE_URL"
echo "📍 SSE Endpoint: $SERVICE_URL/sse"
echo ""
echo "🔧 Claude Desktop Configuration:"
echo "Add this to your claude_desktop_config.json:"
echo ""
echo '{'
echo '  "mcpServers": {'
echo '    "synthea-fhir": {'
echo '      "command": "npx",'
echo '      "args": ['
echo '        "-y",'
echo '        "supergateway",'
echo '        "--sse",'
echo "        \"$SERVICE_URL/sse\""
echo '      ]'
echo '    }'
echo '  }'
echo '}'
echo ""
echo "🎉 Your Synthea FHIR MCP Server is ready!"