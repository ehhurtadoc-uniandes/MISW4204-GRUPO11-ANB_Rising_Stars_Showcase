#!/bin/bash
# Script to verify AWS credentials format in .env file
# This helps diagnose SignatureDoesNotMatch errors

ENV_FILE="${1:-/opt/anb-worker/.env}"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    echo "Usage: $0 [path/to/.env]"
    exit 1
fi

echo "Verifying AWS credentials in: $ENV_FILE"
echo "=========================================="
echo ""

# Check if credentials exist
if ! grep -q "^AWS_ACCESS_KEY_ID=" "$ENV_FILE"; then
    echo "✗ AWS_ACCESS_KEY_ID not found in .env file"
    exit 1
fi

if ! grep -q "^AWS_SECRET_ACCESS_KEY=" "$ENV_FILE"; then
    echo "✗ AWS_SECRET_ACCESS_KEY not found in .env file"
    exit 1
fi

# Extract credentials
ACCESS_KEY=$(grep "^AWS_ACCESS_KEY_ID=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '[:space:]')
SECRET_KEY=$(grep "^AWS_SECRET_ACCESS_KEY=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '[:space:]')
SESSION_TOKEN=$(grep "^AWS_SESSION_TOKEN=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '[:space:]' || echo "")

echo "✓ AWS_ACCESS_KEY_ID found"
echo "  - Starts with: ${ACCESS_KEY:0:4}..."
echo "  - Length: ${#ACCESS_KEY} characters"
echo "  - Contains spaces/newlines: $([ "$ACCESS_KEY" != "$(echo "$ACCESS_KEY" | tr -d '[:space:]')" ] && echo "YES (PROBLEM!)" || echo "NO (OK)")"
echo ""

echo "✓ AWS_SECRET_ACCESS_KEY found"
echo "  - Length: ${#SECRET_KEY} characters"
echo "  - Contains spaces/newlines: $([ "$SECRET_KEY" != "$(echo "$SECRET_KEY" | tr -d '[:space:]')" ] && echo "YES (PROBLEM!)" || echo "NO (OK)")"
echo ""

if [ -n "$SESSION_TOKEN" ]; then
    echo "✓ AWS_SESSION_TOKEN found"
    echo "  - Length: ${#SESSION_TOKEN} characters"
    echo "  - Contains spaces/newlines: $([ "$SESSION_TOKEN" != "$(echo "$SESSION_TOKEN" | tr -d '[:space:]')" ] && echo "YES (PROBLEM!)" || echo "NO (OK)")"
    echo "  - Starts with: ${SESSION_TOKEN:0:20}..."
else
    echo "⚠ AWS_SESSION_TOKEN not found (OK if using permanent credentials)"
    echo ""
fi

# Check for common issues
echo "Checking for common issues..."
echo "============================="
echo ""

ISSUES=0

# Check if access key starts with ASIA (temporary) but no session token
if [[ "$ACCESS_KEY" == ASIA* ]] && [ -z "$SESSION_TOKEN" ]; then
    echo "✗ ISSUE: Access Key starts with 'ASIA' (temporary) but no SESSION_TOKEN found"
    echo "  Temporary credentials require AWS_SESSION_TOKEN"
    ISSUES=$((ISSUES + 1))
fi

# Check for spaces in credentials (common cause of SignatureDoesNotMatch)
if echo "$ACCESS_KEY" | grep -q '[[:space:]]'; then
    echo "✗ ISSUE: AWS_ACCESS_KEY_ID contains spaces or newlines"
    echo "  This will cause SignatureDoesNotMatch errors"
    ISSUES=$((ISSUES + 1))
fi

if echo "$SECRET_KEY" | grep -q '[[:space:]]'; then
    echo "✗ ISSUE: AWS_SECRET_ACCESS_KEY contains spaces or newlines"
    echo "  This will cause SignatureDoesNotMatch errors"
    ISSUES=$((ISSUES + 1))
fi

if [ -n "$SESSION_TOKEN" ] && echo "$SESSION_TOKEN" | grep -q '[[:space:]]'; then
    echo "✗ ISSUE: AWS_SESSION_TOKEN contains spaces or newlines"
    echo "  This will cause SignatureDoesNotMatch errors"
    ISSUES=$((ISSUES + 1))
fi

# Check for quotes around values (common mistake)
if grep -q "^AWS_ACCESS_KEY_ID=['\"]" "$ENV_FILE"; then
    echo "✗ ISSUE: AWS_ACCESS_KEY_ID is wrapped in quotes"
    echo "  Remove quotes from .env file"
    ISSUES=$((ISSUES + 1))
fi

if grep -q "^AWS_SECRET_ACCESS_KEY=['\"]" "$ENV_FILE"; then
    echo "✗ ISSUE: AWS_SECRET_ACCESS_KEY is wrapped in quotes"
    echo "  Remove quotes from .env file"
    ISSUES=$((ISSUES + 1))
fi

if [ -n "$SESSION_TOKEN" ] && grep -q "^AWS_SESSION_TOKEN=['\"]" "$ENV_FILE"; then
    echo "✗ ISSUE: AWS_SESSION_TOKEN is wrapped in quotes"
    echo "  Remove quotes from .env file"
    ISSUES=$((ISSUES + 1))
fi

# Check credential lengths
if [ ${#ACCESS_KEY} -lt 16 ]; then
    echo "✗ ISSUE: AWS_ACCESS_KEY_ID seems too short (${#ACCESS_KEY} chars, expected ~20)"
    ISSUES=$((ISSUES + 1))
fi

if [ ${#SECRET_KEY} -lt 30 ]; then
    echo "✗ ISSUE: AWS_SECRET_ACCESS_KEY seems too short (${#SECRET_KEY} chars, expected ~40)"
    ISSUES=$((ISSUES + 1))
fi

if [ -n "$SESSION_TOKEN" ] && [ ${#SESSION_TOKEN} -lt 100 ]; then
    echo "⚠ WARNING: AWS_SESSION_TOKEN seems short (${#SESSION_TOKEN} chars, expected ~1000+)"
    echo "  Session token might be truncated"
fi

echo ""
if [ $ISSUES -eq 0 ]; then
    echo "✓ No issues found! Credentials appear to be properly formatted."
    echo ""
    echo "If you're still getting SignatureDoesNotMatch errors:"
    echo "1. Verify credentials are not expired"
    echo "2. Make sure you copied the complete session token (it's very long)"
    echo "3. Try using the update-worker-credentials.sh script to update them"
else
    echo "✗ Found $ISSUES issue(s) that need to be fixed"
    echo ""
    echo "To fix these issues, use:"
    echo "  ./scripts/aws/update-worker-credentials.sh <ACCESS_KEY> <SECRET_KEY> [SESSION_TOKEN]"
    echo ""
    echo "Or manually edit $ENV_FILE and ensure:"
    echo "  - No spaces or newlines in credential values"
    echo "  - No quotes around values"
    echo "  - Complete session token if using temporary credentials"
fi

