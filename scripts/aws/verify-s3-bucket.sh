#!/bin/bash
# Script to verify S3 bucket exists and is accessible
# Usage: ./verify-s3-bucket.sh [bucket-name]

BUCKET_NAME="${1:-anb-rising-starts-videos-east1}"
REGION="${2:-us-east-1}"

echo "Verifying S3 bucket: $BUCKET_NAME"
echo "Region: $REGION"
echo "================================"
echo ""

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI not found. Install it first."
    exit 1
fi

# Check if bucket exists
echo "Checking if bucket exists..."
if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q "NoSuchBucket"; then
    echo "✗ Bucket '$BUCKET_NAME' does NOT exist"
    echo ""
    echo "To create the bucket, run:"
    echo "  aws s3 mb s3://$BUCKET_NAME --region $REGION"
    echo ""
    echo "Or create it from the AWS Console:"
    echo "  1. Go to S3 Dashboard"
    echo "  2. Click 'Create bucket'"
    echo "  3. Bucket name: $BUCKET_NAME"
    echo "  4. Region: $REGION"
    echo "  5. Uncheck 'Block all public access' (for public read access)"
    echo "  6. Click 'Create bucket'"
    exit 1
elif aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q "AccessDenied"; then
    echo "⚠ Bucket might exist but access is denied"
    echo "Check your AWS credentials and permissions"
    exit 1
else
    echo "✓ Bucket '$BUCKET_NAME' exists and is accessible"
    echo ""
    
    # List bucket contents
    echo "Bucket contents:"
    aws s3 ls "s3://$BUCKET_NAME/" 2>/dev/null || echo "  (empty or cannot list)"
    echo ""
    
    # Check bucket policy
    echo "Checking bucket policy..."
    POLICY=$(aws s3api get-bucket-policy --bucket "$BUCKET_NAME" --query Policy --output text 2>/dev/null)
    if [ -n "$POLICY" ]; then
        echo "✓ Bucket policy exists"
        echo "$POLICY" | python3 -m json.tool 2>/dev/null || echo "$POLICY"
    else
        echo "⚠ No bucket policy found"
        echo "  You may need to add a public read policy for video access"
    fi
    echo ""
    
    # Test write access
    echo "Testing write access..."
    TEST_FILE="/tmp/s3-test-$(date +%s).txt"
    echo "test" > "$TEST_FILE"
    if aws s3 cp "$TEST_FILE" "s3://$BUCKET_NAME/test-write-access.txt" 2>/dev/null; then
        echo "✓ Write access works"
        aws s3 rm "s3://$BUCKET_NAME/test-write-access.txt" 2>/dev/null
        rm -f "$TEST_FILE"
    else
        echo "✗ Write access failed"
        echo "  Check your AWS credentials and IAM permissions"
        rm -f "$TEST_FILE"
    fi
fi

