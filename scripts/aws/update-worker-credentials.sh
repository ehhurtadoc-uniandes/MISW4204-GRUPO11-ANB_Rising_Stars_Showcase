#!/bin/bash
# Script to update AWS credentials in worker .env file
# Usage: ./update-worker-credentials.sh <ACCESS_KEY> <SECRET_KEY> <SESSION_TOKEN>

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <AWS_ACCESS_KEY_ID> <AWS_SECRET_ACCESS_KEY> [AWS_SESSION_TOKEN]"
    echo ""
    echo "Example:"
    echo "  $0 ASIA5GE6GSAWJ3OEGRON tqUUtKrCMTluoy0hJwaIAUeVsfcp3Cy2uJhwfpS1 IQoJb3JpZ2luX2VjEK7..."
    echo ""
    echo "To get new credentials:"
    echo "  1. Go to AWS Console -> IAM -> Users -> Your User -> Security Credentials"
    echo "  2. Click 'Create Access Key' or use existing temporary credentials"
    echo "  3. Copy the Access Key ID, Secret Access Key, and Session Token (if temporary)"
    exit 1
fi

ACCESS_KEY=$1
SECRET_KEY=$2
SESSION_TOKEN=${3:-""}

ENV_FILE="/opt/anb-worker/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    echo "Make sure you're running this script on the worker EC2 instance"
    exit 1
fi

echo "Updating AWS credentials in $ENV_FILE..."

# Backup original file
cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

# Update credentials using sed
sed -i "s/^AWS_ACCESS_KEY_ID=.*/AWS_ACCESS_KEY_ID=$ACCESS_KEY/" "$ENV_FILE"
sed -i "s/^AWS_SECRET_ACCESS_KEY=.*/AWS_SECRET_ACCESS_KEY=$SECRET_KEY/" "$ENV_FILE"

if [ -n "$SESSION_TOKEN" ]; then
    # Update or add session token
    if grep -q "^AWS_SESSION_TOKEN=" "$ENV_FILE"; then
        sed -i "s|^AWS_SESSION_TOKEN=.*|AWS_SESSION_TOKEN=$SESSION_TOKEN|" "$ENV_FILE"
    else
        # Add session token after AWS_SECRET_ACCESS_KEY
        sed -i "/^AWS_SECRET_ACCESS_KEY=.*/a AWS_SESSION_TOKEN=$SESSION_TOKEN" "$ENV_FILE"
    fi
else
    # Remove session token if not provided (for permanent credentials)
    sed -i "/^AWS_SESSION_TOKEN=/d" "$ENV_FILE"
fi

echo "Credentials updated successfully!"
echo ""
echo "To apply the changes, restart the worker container:"
echo "  docker restart anb-worker-sqs"
echo ""
echo "Or restart the service:"
echo "  systemctl restart anb-worker-sqs"
echo ""
echo "To verify the update, check the logs:"
echo "  docker logs -f anb-worker-sqs"

